FROM alpine:latest
RUN wget -O /tmp/fpc.tar --user-agent="Linux x86_64" https://sourceforge.net/projects/freepascal/files/latest/download?source=files
RUN apk update && apk add bash
RUN cd /tmp && \
	tar xf fpc.tar && \
	cd fpc-* && \
	yes "" | ./install.sh
RUN apk add binutils
