# sunwalker-image

This repository contains the scripts and configuration files for building a sunwalker image--a set of self-contained Linux environments for building and running programs written in C++, Rust, Go, Python, and many other languages. This is mainly of use for competitive programming judge systems.

For a list of supported environments, see the `packages` directory.


## Installation

You need Linux with bash, [util-linux](https://en.wikipedia.org/wiki/Util-linux), [ratarmount](https://github.com/mxmlnkn/ratarmount), [squashfs-tools](https://github.com/plougher/squashfs-tools), [squashfuse](https://github.com/vasi/squashfuse), Python 3.8+, Docker and [Docker SDK for Python](https://pypi.org/project/docker/), and a kernel supporting overlayfs, squashfs, and namespaces.

On Ubuntu the above can be installed using:

```shell
# apt-get install util-linux squashfs-tools squashfuse docker
# pip3 install ratarmount docker
```


## I just want to generate an image, what should I do?

Install the dependencies as specified above, make sure you have enough free disk space (and by that I mean *a lot*; 20 gigabytes should be enough), then:

```shell
$ ./scripts/build_packages.py
$ ./scripts/bake_image.sh
$ ./scripts/make_config.py
```

This generates `image.sfs` and `image.cfg` in the root sunwalker directory--these are the files you are looking for.


## Glossary

An *image* is a single disk image file in squashfs format, usually named `image.sfs` or similarly. An image is several gigabytes large and contains everything necessary to compile and run various programs written in different languages or for different SDKs.

An image contains several *packages*, which is approximately sunwalker's way of saying "SDK". A package may support a single language with a single compiler/interpreter, like the `cpython3` package does, or multiple languages with similar requirements or installed in a similar way (e.g. `sdkman`, which supports Java, Kotlin, and Scala), or a single language with several implementations (e.g. `dlang` supports both DMD, GDC, and LDC, because they all use the same stdlib).

A *configuration file*, usually named `image.cfg` or similarly, specifies which languages the image supports, exactly how the image should be used to compile and run programs and so on.


## Licensing

The few scripts and configuration files (`Dockerfile`, `manifest`, etc.) stored in this repository are licensed under GNU General Public License version 3 or later, at your option. The full text of GPLv3 is stored in [LICENSE](LICENSE).

The licenses of the contents of packages are stored in `packages/*/LICENSE`. IANAL, but I believe that all the packages in this repository are [GPL-compatible](https://www.gnu.org/licenses/license-list.en.html). Keep in mind that the licenses were pulled on March 8, 2022, so while they were correct (to the best of my knowledge) on that date, the latest versions of the packages may be licensed under different conditions. You are strongly advised to do the research yourself. If you find any discrepancies, please don't hesitate to contact me via GitHub issues--I do care about licensing and would like to resolve the problems, should they appear.


## Running programs

**N.B. The runner stored here in sunwalker-image is unsafe. You should only use it for unit tests or if you trust the code you run. If you need to run untrusted code, you should use a fully fledged sandbox, e.g. [firejail](https://github.com/netblue30/firejail) or [bubblewrap](https://github.com/containers/bubblewrap).**

To run a single command, use

```shell
$ ./scripts/run.sh <package name> <command line>
```

For example:

```shell
$ ./scripts/run.sh gcc gcc -v
```

If you need to share any files, directories, or devices with the container, you may use:

```shell
$ ./scripts/run.sh -f<file1> -f<file2> ... <package name> <command line>
```

Note that the files and directories have to exist in your environment. So if you want to compile a program, you have to create an empty file in place of the output beforehand:

```shell
$ touch a.out
$ ./scripts/run.sh -fsource.c -fa.out gcc gcc source.c
```

The CWD in the container is originally `/`. The file is placed to approximately the same location in the container as the source.

- `-fsource.c` mounts the `source.c` from the current directory to `./source.c` (that is, `/source.c`) in the container,
- `-f/home/ivanq/source.c` creates the directory `/home/ivanq` in the container and mounts `/home/ivanq/source.c` (outside the container) to `/home/ivanq/source.c` (inside the container).
- `-f/path/one=/path/two` mounts the file/directory `/path/two` (outside the container) to `/path/one` (inside the container).


## Development and testing

See [internals.md](internals.md).
