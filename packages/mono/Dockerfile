FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
RUN \
	apt-get update && \
	apt-get -yqq install ca-certificates gnupg && \
	apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF && \
	echo "deb https://download.mono-project.com/repo/ubuntu stable-focal main" >/etc/apt/sources.list.d/mono-official-stable.list && \
	apt-get update && \
	apt-get -yqq install mono-devel
RUN \
	apt-get -yqq install wget unzip && \
	wget -O/tmp/PABCNETC.zip http://pascalabc.net/downloads/PABCNETC.zip && \
	unzip /tmp/PABCNETC.zip -d/pascalabc
