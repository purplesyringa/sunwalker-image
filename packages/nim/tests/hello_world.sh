#!/usr/bin/env bash
set -e

touch hello_world
run -fhello_world.nim -fhello_world nim compile -d:release hello_world.nim
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
