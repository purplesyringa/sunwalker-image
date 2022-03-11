#!/usr/bin/env bash
set -e

if ! [[ -e module ]]; then
	mkdir module
fi

cp hello_world.erl module/hello_world.erl
run -fmodule -dmodule erl -compile hello_world.erl
diff <(run -fhello_world.beam=module/hello_world.beam erl -noshell -s hello_world main -s init stop) <(echo "Hello, world!")
