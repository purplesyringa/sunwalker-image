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
