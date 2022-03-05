#!/usr/bin/env bash
set -e

touch hello_world
run -fhello_world.d -fhello_world gdc hello_world.d -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
