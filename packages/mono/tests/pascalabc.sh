#!/usr/bin/env bash
set -e

touch hello_world.exe
run -fhello_world.pas -fhello_world.exe mono /pascalabc/pabcnetc.exe hello_world.pas hello_world.exe
run -fhello_world.exe mono hello_world.exe
