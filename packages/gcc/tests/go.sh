#!/usr/bin/env bash
set -e

run gccgo -v 2>/dev/null

touch hello_world
run -fhello_world.go -fhello_world gccgo hello_world.go -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
