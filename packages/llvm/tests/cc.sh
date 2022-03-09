#!/usr/bin/env bash
set -e

run clang -v 2>/dev/null

touch hello_world
run -fhello_world.c -fhello_world clang hello_world.c -o hello_world -std=c11
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
