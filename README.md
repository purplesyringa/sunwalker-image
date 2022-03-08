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


## Glossary and the few inner workings

An *image* is a single file in squashfs format, usually named `image.sfs` or similarly, or a directory containing the unpacked contents of said file. An image is several gigabytes large and contains everything necessary to compile and run various programs written in different languages or for different SDKs.

An image contains several *packages*, which is approximately sunwalker's way of saying "SDK". A package is a full-blown rootfs abiding [FHS](https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard). Everything unnecessary is stripped, including busybox and bash. A package may support a single language with a single compiler/interpreter, like the `cpython3` package does, or multiple languages with similar requirements or installed in a similar way (e.g. `sdkman`, which supports Java, Kotlin, and Scala), or a single language with several implementations (e.g. `dlang` supports both DMD, GDC, and LDC, because they all use the same stdlib).

Physically, an unpacked image is of the following hierarchy:

```
/
	gcc/
		.sunwalker/
			env
		usr/
			...
		bin/
			...
	go/
		.sunwalker/
			env
		usr/
			...
		bin/
			...
	...
```

This structure is specifically designed so that you can use sunwalker-image without any other tools. You can simply mount `image.sfs`, and then chroot into any of its packages. For instance:

```
# mount image.sfs /mnt
# chroot /mnt/gcc /usr/local/bin/gcc -v
```

The `.sunwalker` directories contain various configuration data. `env`, for instance, contains environment variables in `name=value` format. This includes `PATH` and `LD_LIBRARY_PATH`, which have to be configured correctly for the packages to work.


## Licensing

The few scripts and configuration files (`Dockerfile`, `manifest`, etc.) stored in this repository are licensed under GNU General Public License version 3 or later, at your option. The full text of GPLv3 is stored in [LICENSE](LICENSE).

The licenses of the contents of packages are stored in `packages/*/LICENSE`. IANAL, but I believe that all the packages in this repository are [GPL-compatible](https://www.gnu.org/licenses/license-list.en.html). Keep in mind that the licenses were pulled on March 8, 2022, so while they were correct (to the best of my knowledge) on that date, the latest versions of the packages may be licensed under different conditions. You are strongly advised to do the research yourself. If you find any discrepancies, please don't hesitate to contact me via GitHub issues--I do care about licensing and would like to resolve the problems, should they appear.


## Building an image

Firstly, you need to build each package. A built package is a single .tar.gz file, containing a rootfs (not enclosed in a directory called `gcc`, `go`, etc.).

This builds all packages (be careful: this might require much disk space):

```shell
$ ./scripts/build_packages.py
```

You can build a single package using: (you can also specify several package names, e.g. `gcc go` to build both packages at once)

```shell
$ ./scripts/build_packages.py gcc
```

If you're running low on disk space, you can build the packages one by one and run something like `docker system prune` after building each package (note: pruning is a destructive operation, so make sure you know what you are doing!).

After building each package, you can build an image via:

```shell
$ ./scripts/bake_image.sh
```


## Testing

sunwalker-image provides (simple) unit tests for each package. You can run them using:

```shell
$ ./scripts/test_image.sh
```

If you want to test a single package, you can use

```shell
$ ./scripts/test_image.sh gcc
```

Note that this tests the packages inside the current *image*, stored in `image.sfs`. If you're only just developing a package and you want to test a single package without baking a full-blown image (mksquashfs is slow), you can use

```shell
$ ./scripts/test_image.sh --dev gcc
```


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

You can use the `--dev` argument here too:

```shell
$ ./scripts/run.sh --dev gcc gcc -v
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
