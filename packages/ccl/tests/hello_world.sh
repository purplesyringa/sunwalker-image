#!/usr/bin/env bash
set -e

run ccl -V >/dev/null

diff <(run -fhello_world.lisp ccl -l hello_world.lisp -e "(quit)") <(echo "Hello, world!")
