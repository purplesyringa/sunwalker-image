#!/usr/bin/env python3
from __future__ import annotations

import atexit
from collections import defaultdict
from dataclasses import dataclass
import docker
import os
import time
from typing import Optional
import shlex
import string
import subprocess
import sys


docker_client = docker.from_env()


class BuildFailure(Exception):
    pass


@dataclass
class PendingAdditionBinary:
    path: str

    # For ELF files, this is the kind of and the path to the dynamic linker this binary is expected to use (it might use
    # another linker, this is only an educated guess). linker_path may be None if ldd is to be used to resolve the
    # dependencies. For other files and for directories, these entries don't bear any particular meaning.
    linker_kind: str
    linker_path: Optional[str]


class PackageBuilder:
    def __init__(self, name: str, path: str):
        self.name: str = name  # name of package
        self.path: str = path  # path to package directory

        self.docker_image_id: Optional[str] = None  # the image ID of the built Dockerfile
        self.docker_container = None  # docker SDK container object

        self.env: dict[str, str] = {}  # environment variables; imported from Docker environment on start

        self.added_binaries: set[str] = set()  # binaries that were already completely analyzed and dependencies of which are pending addition
        self.pending_addition_binaries: dict[str, PendingAdditionBinary] = {}  # binaries/directories which are yet to be analyzed recursively; key is path of binary

        self.linker_kind_cache: dict[str, str] = {}  # key is absolute path to ld.so, value is gnu/musl

        self.readlink_supports_zero_terminated_output: Optional[bool] = None  # exactly what it says on the tin
        self.default_linker_kind: Optional[str] = None  # kind of default dynamic interpreter (that ldd uses; gnu/musl)


    def close(self) -> None:
        if self.docker_container:
            self.docker_container.stop()
            self.docker_container.remove()


    def __enter__(self) -> PackageBuilder:
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


    # Full build process: build Docker image, execute config, create .tar.gz
    def build(self) -> None:
        print("Building", self.name)

        if os.path.exists(os.path.join(self.path, "Dockerfile")):
            print("Dockerfile exists; running docker build")
            proc = subprocess.Popen(["docker", "build", self.path], stdout=subprocess.PIPE)
            for line in proc.stdout:
                if line.startswith(b"Successfully built "):
                    self.docker_image_id = line.split()[2].decode()
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            proc.wait()
            if proc.returncode != 0:
                print("docker build failed, exitting")
                raise BuildFailure()
            if not self.docker_image_id:
                print("Unexpected error: could not get image ID")
                raise BuildFailure()

            print("Starting Docker container")
            self.docker_container = docker_client.containers.run(self.docker_image_id, command=["sleep", "infinity"], detach=True)
        else:
            print("Dockerfile missing; this is not supported")
            raise BuildFailure()

        self.configure()

        self.import_env()

        with open(os.path.join(self.path, "manifest")) as f:
            for line in f:
                self.run_command(line)
                # argv = self._split_argv(self._substitute_exec(line))
                # self.run_command(argv)

        self.commit_binary_addition()

        print("Saving parameters")
        env_str = "".join(f"{key}={value}\n" for key, value in sorted(self.env.items()))
        self.run_docker_oneshot(["bash", "-c", "mkdir /.sunwalker && printf %s \"$1\" >/.sunwalker/env", "-", env_str], user="root")

        print("Saving image")
        target_path = os.path.join(self.path, self.name + ".tar.gz")
        with open(target_path, "wb") as f:
            proc = self.run_docker(["tar", "czf", "-", "/.sunwalker"] + list(self.added_binaries), stdout=f)
            if proc.returncode != 0:
                print("tar failed")
                raise BuildFailure()


    # Execute a command in the Docker container, possibly passing parameters to subprocess.run, returning a
    # subprocess.CompletedProcess object. Useful for when the output has to be redirected, which run_docker_oneshot does
    # not support.
    def run_docker(self, argv: list[str], **kwargs):
        return subprocess.run(["docker", "container", "exec", self.docker_container.id] + argv, **kwargs)
        # return subprocess.run(["docker", "run", self.docker_image_id] + argv, **kwargs)


    # Execute a command in the Docker container, using Docker SDK and returning output (if check=True) or (exit code,
    # output). Should be preferred to run_docker.
    def run_docker_oneshot(self, argv: list[str], check: bool=True, **kwargs) -> bytes | tuple[int, bytes]:
        returncode, stdout = self.docker_container.exec_run(argv, **kwargs, environment=self.env)
        if check:
            if returncode != 0:
                print("Command exitted with status", returncode, ":", argv)
                print(stdout.decode(), end="")
                raise BuildFailure()
            return stdout
        else:
            return returncode, stdout


    # Perform variable expansion (that is, $var is replaced with the value of variable 'var'), $(...) expansion, etc.,
    # and split the resulting string by whitespace, honoring escaping, quoting, etc. Basically does the same thing that
    # shells do to get from a shell command to an argv list.
    def substitute_and_split(self, s: str) -> list[str]:
        return self.split_null(self.run_docker_oneshot(["bash", "-c", r"printf '%s\0' '' " + s], stderr=False).decode()[1:])


    # Detect configuration of the Docker container and various utilities, such as:
    # - whether readlink supports -z argument;
    # - what is the default interpreter--that is, what interpreter ldd is for. This is just an optimization: we use this
    #   as the first guess for the interpreter ELF dynamic objects use. If we guess right, a single ldd call will yield
    #   the correct dependency list and verify that the binary uses the expected interpreter, and if we guess wrong, ldd
    #   will provide us with the path to the correct interpreter.
    def configure(self) -> None:
        readlink_help = self.run_docker_oneshot(["readlink", "--help"]).decode()
        self.readlink_supports_zero_terminated_output = " -z" in readlink_help
        print("-> readlink -z supported:", self.readlink_supports_zero_terminated_output)

        ldd_version = self.run_docker_oneshot(["ldd", "--version"], check=False)[1].decode()
        if "GLIBC" in ldd_version:
            self.default_linker_kind = "gnu"
        elif "musl libc" in ldd_version:
            self.default_linker_kind = "musl"
        else:
            print("Unknown linker (only GNU and musl ld are supported) at ldd")
            raise BuildFailure()

        print("-> Default linker:", self.default_linker_kind)


    # Run a single command from manifest
    def run_command(self, line: str) -> None:
        if line.startswith("RUN "):
            command = line[4:].strip()
            print("-> Run", command)
            out = self.run_docker_oneshot(["bash", "-c", f"{command}; echo; printf __SETENV__; env -0"]).decode()
            out, env = out[:out.index("\n__SETENV__")], out[out.index("\n__SETENV__") + len("\n__SETENV__"):]
            print(out, end="", flush=True)
            for line in self.split_null(env):
                key, value = line.split("=", 1)
                if self.env.get(key) != value:
                    print("-> Set", key, "=", value)
                    self.env[key] = value
            return

        argv = self.substitute_and_split(line)

        while argv and "=" in argv[0]:
            key, value = argv[0].split("=", 1)
            print("-> Set", key, "=", value)
            self.env[key] = value
            argv.pop(0)

        if not argv:
            return

        command, *args = argv

        if command == "RUN":
            print("-> Run", args)
            self.run_docker_oneshot(args, stdout=False, stderr=False)
        elif command == "BIN":
            for arg in args:
                self.add_binary(arg)
        else:
            print("-> Unknown command", argv)
            raise BuildFailure()


    # Add a file, along with its potential linker, to the pending addition list
    def add_binary(self, binary_path: str, linker_kind: Optional[str]=None, linker_path: Optional[str]=None) -> None:
        if binary_path[0] != "/":
            binary_path = self.run_docker_oneshot(["which", binary_path]).decode().strip("\n")

        if binary_path in self.pending_addition_binaries or binary_path in self.added_binaries:
            return

        if linker_kind is None:
            linker_kind = self.default_linker_kind

        self.pending_addition_binaries[binary_path] = PendingAdditionBinary(binary_path, linker_kind, linker_path)


    # Import environment variables from Docker container
    def import_env(self) -> None:
        env = self.run_docker_oneshot(["bash", "-c", "env -0"]).decode()
        for line in self.split_null(env):
            key, value = line.split("=", 1)
            if self.env.get(key) != value:
                print("-> Import", key, "=", value)
                self.env[key] = value


    # Batch-add binaries from the pending-addition list. Batch operations are more efficient because they allow us to
    # use O(1) commands in most cases, except when system tools don't support batch usage (e.g. busybox readlink and
    # musl ldd don't).
    def commit_binary_addition(self) -> None:
        while self.pending_addition_binaries:
            lst = self.pending_addition_binaries
            self.pending_addition_binaries = {}

            symlinks = self.split_null(self.run_docker_oneshot(["find", *lst.keys(), "-maxdepth", "0", "-type", "l", "-print0"]).decode())
            if symlinks:
                if self.readlink_supports_zero_terminated_output:
                    link_targets = self.split_null(self.run_docker_oneshot(["readlink", "-z", *symlinks]).decode())
                else:
                    link_targets = []
                    for symlink in symlinks:
                        link_targets.append(self.run_docker_oneshot(["readlink", symlink])[:-1].decode())
                assert len(symlinks) == len(link_targets)
                for symlink, link_target in zip(symlinks, link_targets):
                    abs_link_target = os.path.abspath(os.path.join(os.path.dirname(symlink), link_target))
                    print("-> Add symlink", symlink, "->", abs_link_target)
                    self.added_binaries.add(symlink)
                    self.add_binary(abs_link_target)

                for symlink in symlinks:
                    del lst[symlink]

            if not lst:
                continue

            # Try to guess what dependencies the binaries require. Of course, we cannot guess this 100% correctly, but
            # we can still try.

            # For scripts, read the shebang
            shebangs = self.split_null(self.run_docker_oneshot(["find", *lst.keys(), "-type", "f", "-executable", "-exec", "awk", "/^#!.*/{printf(\"%s%c\", $0, 0)} {nextfile}", "{}", "+"]).decode())
            for shebang in shebangs:
                splitted = shebang[2:].strip().split(" ", 1)
                interp = splitted[0]
                interp_arg = None if len(splitted) == 1 else splitted[1]
                self.add_binary(interp)
                if interp in ("env", "/usr/bin/env") and interp_arg:
                    self.add_binary(interp_arg)

            # For ELF files, split by dynamic linker and ask the linker about what shared libraries are requested
            files_by_linker: defaultdict[tuple[str, Optional[str]], list[str]] = defaultdict(list)
            for binary in lst.values():
                files_by_linker[binary.linker_kind, binary.linker_path].append(binary.path)

            for (linker_kind, linker_path), paths in files_by_linker.items():
                # Unpack directories to lists of files
                paths = self.split_null(self.run_docker_oneshot(["find", *paths, "-not", "-type", "d", "-print0"]).decode())
                if not paths:
                    continue

                success_list = self.add_shared_elf_recursively(paths, linker_kind, linker_path)

                # Add the binaries to the success list if the addition was successful
                for path, success in zip(paths, success_list):
                    if success:
                        if linker_path is None:
                            print("-> Add binary", path)
                        else:
                            print("-> Add binary", path)
                        self.added_binaries.add(path)


    # Add dependencies of shared ELF objects. Returns a list of bools indicating whether the parsing was
    # successful (True) or the file will have to be reconsidered with different linker settings (False).
    def add_shared_elf_recursively(self, files: list[str], linker_kind: str, linker_path: Optional[str]) -> list[bool]:
        command_prefix = ["ldd"] if linker_path is None else [linker_path, "--list"]

        success = []

        if linker_kind == "gnu" and linker_path is None:
            # GNU ldd supports multiple arguments
            stdout = self.run_docker_oneshot(command_prefix + files, check=False, stderr=False)[1].decode()

            # Split by file
            if len(files) == 1:
                success.append(self.add_dependencies_from_ldd_output(stdout.splitlines(), files[0], linker_kind))
            else:
                current_file: Optional[str] = None
                buffer_lines: list[str] = []
                for line in stdout.splitlines() + [":"]:
                    if not line.startswith("\t") and line.endswith(":"):
                        # Next file
                        if current_file is not None:
                            success.append(self.add_dependencies_from_ldd_output(buffer_lines, current_file, linker_kind))
                        current_file = line[:-1]
                        buffer_lines = []
                    else:
                        buffer_lines.append(line)
        else:
            # musl ldd does not support multiple arguments. ld.so --list doesn't support multiple arguments either, it
            # treats the second argument as a symbol name.
            for file in files:
                stdout = self.run_docker_oneshot(command_prefix + [file], check=False, stderr=False)[1].decode()
                success.append(self.add_dependencies_from_ldd_output(stdout.splitlines(), file, linker_kind))

        return success


    # Returns True if the dependencies were added successfully, False is the binary file is to be reconsidered with
    # different linekr settings
    def add_dependencies_from_ldd_output(self, lines: list[str], binary_path: str, linker_kind: str) -> bool:
        if not lines or lines[0] == "\tstatically linked":
            # Not a dynamic executable
            return True

        # Detect the linker that the binary expects. Of course, reading PT_INTERP would be a much more robust solution,
        # but unfortunately, neither objdump nor readelf are available on most systems, so it is what it is.
        expected_linker_paths = []
        for line in lines:
            if " => " in line and line.startswith("\tld-"):
                # Linker is specified by name--resolve path
                expected_linker_paths.append(line.partition(" => ")[2].partition(" (")[0])
            elif " => " not in line and "/ld-" in line:
                # Linker is specified by path
                expected_linker_paths.append(line[1:].partition(" (")[0])

        if not expected_linker_paths:
            print(binary_path, "does not have any dynamic linker detected while being a dynamic executable")
            raise BuildFailure()

        # Is any linker requested other than the current one? (musl ldd, for instance, always adds itself as a
        # dependency for no reason)
        different_linker_paths = []
        for expected_linker_path in expected_linker_paths:
            if self.get_kind_of_linker(expected_linker_path) != linker_kind:
                different_linker_paths.append(expected_linker_path)

        if len(different_linker_paths) == 1:
            # We guessed wrong. Add the same binary file to the queue with the correct linker
            path = different_linker_paths[0]
            self.add_binary(binary_path, self.get_kind_of_linker(path), path)
            return False
        elif different_linker_paths:
            # The binary requests several other linkers. This is not normal, but it sometimes happens due to symlinks.
            # Let us resolve them
            real_linker_paths = set()
            for path in different_linker_paths:
                real_linker_paths.add(self.run_docker_oneshot(["realpath", path])[:-1].decode())

            if len(real_linker_paths) > 1:
                print(binary_path, "has multiple linkers attached, even excluding the default one", different_linker_paths, linker_kind)
                raise BuildFailure()

            # We still need to add all the symlinks even though they point to the same file
            for linker_path in different_linker_paths:
                self.add_binary(linker_path)

            path = list(real_linker_paths)[0]
            self.add_binary(binary_path, self.get_kind_of_linker(path), path)
            return False

        # We guessed right, parse the output
        for line in lines:
            if line.startswith("\t"):
                if " => " in line:
                    name, dest = line.strip().split(" => ", 1)
                    dest = dest.split()[0]
                    self.add_binary(dest)
                elif " (" in line:
                    name = line.partition("(")[0].strip()
                    if name.startswith("/"):
                        self.add_binary(name)

        return True


    def get_kind_of_linker(self, linker_path: str) -> str:
        if linker_path not in self.linker_kind_cache:
            stdout = self.run_docker_oneshot([linker_path], check=False)[1].decode()
            if "You have invoked `ld.so'" in stdout:
                ld = "gnu"
            elif "musl libc" in stdout:
                ld = "musl"
            else:
                # Some versions of GNU ld support (and require) --help and use 'ld.so'; others don't support --help,
                # print the help when invoked with no arguments and use `ld.so'. I don't know who thought this would be
                # a good idea.
                stdout = self.run_docker_oneshot([linker_path, "--help"], check=False)[1].decode()
                if "You have invoked 'ld.so'" in stdout:
                    ld = "gnu"
                else:
                    print("Unknown linker (only GNU and musl ld are supported) at", linker_path)
                    raise BuildFailure()

            self.linker_kind_cache[linker_path] = ld

        return self.linker_kind_cache[linker_path]


    def split_null(self, s: str) -> list[str]:
        if s:
            return s.rstrip("\x00").split("\x00")
        else:
            return []


def main():
    package_name = sys.argv[1]
    path = os.path.join("packages", package_name)
    with PackageBuilder(package_name, path) as pkg:
        pkg.build()


if __name__ == "__main__":
    main()
