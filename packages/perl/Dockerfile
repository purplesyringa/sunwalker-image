FROM perl:latest
RUN apt-get update && apt-get install -yqq locales
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
