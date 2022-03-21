## Image hierarchy

The image is a large filesystem in squashfs format. Each package corresponds to a subdirectory of this filesystem and abides [Filesystem Hierarchy Standard](https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard). So an unpacked image looks like this:

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

This structure is specifically designed so that you can use sunwalker images without any other tools. You can simply mount `image.sfs`, and then chroot into any of its packages. For instance:

```
# mount image.sfs /mnt
# chroot /mnt/gcc /usr/local/bin/gcc -v
```

Notice that everything unnecessary is stripped from the image. This includes busybox and bash, as well as other utilities you would probably expect to be included. Therefore, you can't just chroot into the package via bash and do things interactively via the shell; you'll probably need to do everything in a single line (like we did `chroot /mnt/gcc /usr/local/bin/gcc -v` above) or use a low-level programming language.

The `.sunwalker` directories contain various configuration data. `env`, for instance, contains environment variables in `name=value` format. This includes `PATH` and `LD_LIBRARY_PATH`, which have to be configured correctly for the packages to work. All these files are purely for your convenience--sunwalker itself does not use them, it gets the necessary information from `image.cfg`.


## Building an image

Firstly, you need to build each package. A built package is a single .tar.gz file stored in `packages/<name>/<name>.tar.gz`, containing a rootfs, and not wrapped in a directory called `gcc`, `go` or alike.

This builds all packages (be careful: this might require much disk space):

```shell
$ ./scripts/build_packages.py
```

You can build a single package using:

```shell
$ ./scripts/build_packages.py gcc
```

You can also specify several package names, e.g. `gcc go` to build both packages at once.

If you're running low on disk space, you can build the packages one by one and run something like `docker system prune` after building each package **(warning: pruning is a destructive operation, so make sure you know what you are doing!)**.

After building each package, you can build an image via:

```shell
$ ./scripts/bake_image.sh
```

After that, if you need to generate the configuration file for the image, you can do:

```shell
$ ./scripts/make_config.py
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

You can run the tests for multiple packages too.

Note that this tests the packages inside the current *image*, stored in `image.sfs`. If you're only just developing a package and you want to test a single package without baking a full-blown image (mksquashfs is slow), you can use

```shell
$ ./scripts/test_image.sh --dev gcc
```

You can use the `--dev` argument for `run.sh` too, e.g.:

```shell
$ ./scripts/run.sh --dev gcc gcc -v
```


## Repository directory structure

`scripts` is used for various build scripts.

`tmp` is an empty directory automatically created by the various scripts. It is used as an auxiliary mountpoint.

`packages` contains the source files for all the packages; each package gets its own subdirectory. Each package is of structure:

```
<name>/
	Dockerfile
	manifest
	LICENSE
	<name>.tar.gz
	tests/
		<test_name>.sh
		<artifact_name>
	languages/
		<language_name>.make
```


## Package build steps

sunwalker uses a two-step build system.


### Docker step

Firstly, it downloads and installs everything the package must contain while trying not to download too much. We use Docker to accomplish this. "Download whatever is needed to run my app" is a very common practical operation, so in most cases there is already a corresponding image on dockerhub, and the Dockerfile contains a single string like:

```
FROM golang:latest
```

If there is no frequently updated image on dockerhub, you'll have to get the necessary environment ready manually. The default Docker best practices apply: start with `alpine:latest` or `ubuntu:latest` and install the necessary requirements. Alpine Linux is preferred because it's more lightweight, but if you need glibc or weird libraries Alpine doesn't support, Ubuntu is a good choice too.

There are a few points where sunwalker differs from normal Docker installations though:

- Prefer to install the latest versions of the software. If you can only install a specific version, add an environment variable for the version so that it can be easily updated, for example:
```
FROM alpine:latest
ENV LUA_VERSION=5.4.4
RUN apk update && apk add bash gcc make musl-dev wget
RUN \
	cd /tmp && \
	wget -Olua.tar.gz http://www.lua.org/ftp/lua-$LUA_VERSION.tar.gz && \
	tar xf lua.tar.gz && \
	cd lua-* && \
	make && \
	make install && \
	rm -r /tmp/lua-*
```

- Always install `bash` and `tar`. These are often built-in, but Alpine doesn't install `bash` by default. The build script needs these two programs.

- Don't add an EXEC statement: Docker is only used to build an image and not to start a container in runtime.

This step can be "debugged" by simply running `docker build` in the package directory and starting a container to check that everything is installed correctly.


### Manifest step

After building the Docker image, sunwalker cherry-picks the necessary files from the image according to the `manifest` configuration file. From a theoretical point of view, this step is unnecessary and you could just use the whole Docker image, but in practice this step helps shrink the image by removing the leftovers and unused modules.

The `manifest` file has syntax similar to that of `Dockerfile`: each line contains a single statement, the statements are evaluated from top to bottom and whatever is left at the end is packed into the image.

The simplest manifest looks like this:

```
BIN /
```

`BIN` means "add files to the archive", so `BIN /` means "add all the environment from the Docker image to the archive". In practice, this is a terrible idea because this would also include `/proc`, `/dev`, etc. So we can be a bit more specific:

```
BIN /usr
```

This includes all the files under `/usr`. `BIN` takes care of the *dependencies* of files of common formats, so this will likely pull some files outside `/usr` too. This likely includes the dynamic linker at `/lib64/ld-linux-x86-64.so.2`.

sunwalker knows how to pull (recursively):

- the dynamic libraries that ELF executables require (via `ldd`);
- the ELF interpreter of the executables;
- the interpreters specified in the shebang (and `#!/usr/bin/env <name>` is special-cased to pull `<name>` too).

So we only really have to specify the files that the compilers and interpreters access in runtime. This includes the C/C++ include files, language (standard) libraries (e.g. Python's `site-packages`), sometimes `/etc/passwd`, etc. So if we're lucky and the compiler/interpreter doesn't require any runtime, we can specify only the files we are going to use directly (notice that when we use a name without leading `/`, it is resolved via `PATH`):

```
BIN lua luac
```

If we are not so lucky, we might have to include other files and directories. You can enter the Docker container to find where stuff is stored. The following is a common idiom and appears in Ruby, Python, and other manifests:

```
BIN ruby
BIN /usr/local/lib/ruby
```

For compiled languages, this gets a bit more difficult because the compilers often require `ld`, `cc`, crt files, etc. In this case, you'll have to be a lot more specific, e.g.:

```
BIN ar as cpp ld nm objcopy objdump ranlib readelf size strip
BIN /usr/lib/*crt*.o /usr/lib/gcc/x86_64-alpine-linux-musl/*/{*crt*.o,libgcc*.a}
BIN /usr/lib/{libc.{so,a},libdl.a,libgcc_s.so{.1,},libm.a,libpthread.a,librt.a,libssp_nonshared.a,libutil.a}
BIN /usr/libexec/gcc/x86_64-alpine-linux-musl/*/{plugin,cc1,lto1,lto-wrapper,collect2,liblto*}
BIN /usr/include
```

The five lines above can often be copy-pasted into the appropriate manifest with a few changes to account for different installation paths.

Notice that `BIN` is a non-destructive operation: it does not destroy files or actively add them to the archive, it simply marks them as pending addition. To perform any operations in the container, you can use `RUN`, say, to delete unused files:

```
RUN find /opt/ghc/*/lib \( -name "*_p.a" -o -name "*.p_hi" -o -name "*.p_o" \) -delete
```

Notice that `(` and `)` are escaped because the comman is run via `bash`.

The manifest inherits the environment variables from the Docker image. You can access then via `$name`, as in bash. Generally speaking, *everything* in the manifest is evaluated as if it was a bash script, so you can use `$(...)` and other bashisms too.

Sometimes it is necessary to update the environment. One common use case is to set `LD_LIBRARY_PATH` so that we don't have to `BIN /etc/ld.so.conf`. The syntax for this is like in bash (yes, including quotes for escaping), so you can do:

```
LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH"
```

(this is only an example, `/usr/lib` is included by default)

It is also often useful to import the environment from an initialization script or enter a virtual environemnt; you can use `RUN` for this too:

```
RUN . "$HOME/.sdkman/bin/sdkman-init.sh"
```

This might seem a bit difficult and error-prone at first, but it's not drastically different from writing Dockerfiles if you have experience in that. This step can be "debugged" by running `./scripts/build_package.py <name>` in the package directory and checking for any errors or warnings.


## Tests

Each package can and should include tests. They can range from version checks to compiling and running a hello world to testing a full-blown application.

Each test corresponds to a single `.sh` file inside the `tests` subdirectory of the package. The test should be a bash script with `+x` permission and contain a shebang and `set -e`. To execute a command inside the container, prefix it with `run`, for instance:

```bash
#!/usr/bin/env bash
set -e
run gcc -v
```

Notice that this is not the same run script as `scripts/run.sh`, so you don't have to specify the package name after `run`, `--dev` won't work, etc. You can, however, use `-f` to sync files with the container:

```bash
touch hello_world  # Create the output file beforehand so that -fhello_world doesn't argue about a non-existing file
run -fhello_world.c -fhello_world gcc hello_world.c -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
```

Notice that this example references files `hello_world.c` and `hello_world`. They are resolved relatively to the `tests` directory, i.e. `tests/hello_world.c` and `tests/hello_world`. You probably want to include the former in the VCS, because it is *input* to the test, and exclude the latter--use `.gitignore` for that.

Additionally, you can use `-d` to run the command with a given working directory:

```bash
run -fsome_dir -dsome_dir ./file  # will run some_dir/file
```
