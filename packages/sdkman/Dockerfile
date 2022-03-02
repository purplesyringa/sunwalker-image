FROM alpine:latest
RUN apk update && apk add bash curl unzip zip
RUN \
	wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub && \
	wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.34-r0/glibc-2.34-r0.apk && \
	wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.34-r0/glibc-bin-2.34-r0.apk && \
	apk add glibc-2.34-r0.apk && \
	apk add glibc-bin-2.34-r0.apk
RUN curl -s https://get.sdkman.io | bash
RUN bash -c '. "$HOME/.sdkman/bin/sdkman-init.sh" && sdk install java && sdk install kotlin && sdk install scala'
RUN apk add zlib
RUN /usr/glibc-compat/sbin/ldconfig
