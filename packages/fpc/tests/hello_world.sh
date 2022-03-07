#!/usr/bin/env bash
set -e

if ! [ -e module ]; then
	mkdir module
fi

run -fhello_world.pas -fmodule fpc -FEmodule hello_world.pas
diff <(run -fmodule ./module/hello_world) <(echo "Hello, world!")
