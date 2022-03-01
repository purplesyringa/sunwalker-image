#!/usr/bin/env python3
import atexit
import docker
import os
import shlex
import string
import subprocess
import sys


docker_client = docker.from_env()


class BuildFailure(Exception):
    pass


class PackageBuilder:
    def __init__(self, name: str, path: str):
        self.name: str = name
        self.path: str = path

        self.docker_image_id: Optional[str] = None
        self.docker_container = None

        self.env: dict[str, str] = {}

        self.added_binaries: set[str] = set()
        self.pending_addition_binaries: set[str] = set()


    def close(self):
        if self.docker_container:
            self.docker_container.stop()
            self.docker_container.remove()


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


    def build(self):
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

        self.import_env()

        with open(os.path.join(self.path, "manifest")) as f:
            for line in f:
                self.run_command(line)
                # argv = self._split_argv(self._substitute_exec(line))
                # self.run_command(argv)

        self.commit_binary_addition()

        print("Saving parameters")
        env_str = "".join(f"{key}={value}\n" for key, value in sorted(self.env.items()))
        self._run_docker_oneshot(["bash", "-c", "mkdir /.sunwalker && printf %s \"$1\" >/.sunwalker/env", "-", env_str], user="root")

        print("Saving image")
        target_path = os.path.join(self.path, self.name + ".tar.gz")
        with open(target_path, "wb") as f:
            proc = self._run_docker(["tar", "czf", "-", "/.sunwalker"] + list(self.added_binaries), stdout=f)
            if proc.returncode != 0:
                print("tar failed")
                raise BuildFailure()


    def _run_docker(self, argv, **kwargs):
        return subprocess.run(["docker", "container", "exec", self.docker_container.id] + argv, **kwargs)
        # return subprocess.run(["docker", "run", self.docker_image_id] + argv, **kwargs)


    def _run_docker_oneshot(self, argv, check=True, **kwargs):
        returncode, stdout = self.docker_container.exec_run(argv, **kwargs, environment=self.env)
        if check:
            if returncode != 0:
                print("Command exitted with status", returncode, ":", argv)
                print(stdout.decode(), end="")
                raise BuildFailure()
            return stdout
        else:
            return returncode, stdout


    # def _substitute_exec(self, s):
    #     while "$(" in s:
    #         start = s.rindex("$(")
    #         end = s.index(")", start)
    #         nested = s[start + 2:end]
    #         stdout = self._run_docker_oneshot(self._split_argv(nested), stderr=False)
    #         res = stdout.decode().strip("\n")
    #         s = s[:start] + res + s[end + 1:]
    #     return s


    # def _substitute_var(self, s):
    #     return string.Template(s).safe_substitute(self.env)


    # def _split_argv(self, s):
    #     argv = shlex.split(s, comments=True)
    #     argv = [self._substitute_var(arg) for arg in argv]
    #     return argv


    def _substitute_and_split(self, s):
        return self.split_null(self._run_docker_oneshot(["bash", "-c", r"printf '%s\0' " + s], stderr=False).decode())


    def run_command(self, line):
        if line.startswith("RUN "):
            command = line[4:].strip()
            print("-> Run", command)
            out = self._run_docker_oneshot(["bash", "-c", f"{command}; echo; printf __SETENV__; env -0"]).decode()
            out, env = out[:out.index("\n__SETENV__")], out[out.index("\n__SETENV__") + len("\n__SETENV__"):]
            print(out, end="", flush=True)
            for line in self.split_null(env):
                key, value = line.split("=", 1)
                if self.env.get(key) != value:
                    print("-> Set", key, "=", value)
                    self.env[key] = value
            return

        argv = self._substitute_and_split(line)

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
            self._run_docker_oneshot(args, stdout=False, stderr=False)
        elif command == "BIN":
            for arg in args:
                self.add_binary(arg)
        else:
            print("-> Unknown command", argv)
            raise BuildFailure()


    def add_binary(self, binary):
        if binary[0] != "/":
            binary = self._run_docker_oneshot(["which", binary]).decode().strip("\n")

        if binary in self.pending_addition_binaries or binary in self.added_binaries:
            return

        self.pending_addition_binaries.add(binary)


    def import_env(self):
        env = self._run_docker_oneshot(["bash", "-c", "env -0"]).decode()
        for line in self.split_null(env):
            key, value = line.split("=", 1)
            if self.env.get(key) != value:
                print("-> Import", key, "=", value)
                self.env[key] = value



    def commit_binary_addition(self):
        while self.pending_addition_binaries:
            lst = self.pending_addition_binaries
            self.pending_addition_binaries = set()

            symlinks = self.split_null(self._run_docker_oneshot(["find", *lst, "-maxdepth", "0", "-type", "l", "-print0"]).decode())
            if symlinks:
                link_targets = self.split_null(self._run_docker_oneshot(["readlink", "-z", *symlinks]).decode())
                assert len(symlinks) == len(link_targets)
                for symlink, link_target in zip(symlinks, link_targets):
                    abs_link_target = os.path.abspath(os.path.join(os.path.dirname(symlink), link_target))
                    print("-> Add symlink", symlink, "->", abs_link_target)
                    self.added_binaries.add(symlink)
                    self.add_binary(abs_link_target)

                assert lst & set(symlinks) == set(symlinks)
                lst -= set(symlinks)

            if lst:
                files = self.split_null(self._run_docker_oneshot(["find", *lst, "-not", "-type", "d", "-print0"]).decode())
                if files:
                    for binary in files:
                        print("-> Add binary", binary)
                        self.added_binaries.add(binary)

                    _, stdout = self._run_docker_oneshot(["ldd", *files], check=False)
                    for line in stdout.decode().splitlines():
                        if line.startswith("\t"):
                            if " => " in line:
                                name, dest = line.strip().split(" => ", 1)
                                dest = dest.split()[0]
                                self.add_binary(dest)
                            elif " (" in line:
                                name = line.partition("(")[0].strip()
                                if name.startswith("/"):
                                    self.add_binary(name)


    def split_null(self, s):
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
