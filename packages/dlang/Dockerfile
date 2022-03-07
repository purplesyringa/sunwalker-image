FROM ubuntu:latest
RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -yqq install bash curl gcc libxml2 perl unzip xz-utils zip
RUN cd /tmp && \
	curl https://dlang.org/install.sh >install.sh && \
	bash install.sh -p /dlang/dmd install dmd && \
	bash install.sh -p /dlang/gdc install gdc && \
	bash install.sh -p /dlang/ldc install ldc
