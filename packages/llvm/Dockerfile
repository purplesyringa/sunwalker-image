FROM ubuntu:18.04
ENV LLVM_VERSION=13.0.1
RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -yqq install wget xz-utils
RUN cd / && \
	wget -O/tmp/clang+llvm.tar.xz https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVM_VERSION/clang+llvm-$LLVM_VERSION-x86_64-linux-gnu-ubuntu-18.04.tar.xz && \
	tar xf /tmp/clang+llvm.tar.xz && \
	mv clang+llvm* llvm && \
	rm /tmp/clang+llvm.tar.xz
RUN apt-get -yqq install binutils gcc libatomic1 libc6-dev libelf1 libstdc++-8-dev
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -yqq install gnustep gnustep-devel
