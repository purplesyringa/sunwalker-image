#!/usr/bin/env bash
set -e

run gcc -v 2>/dev/null

touch hello_world
run -fhello_world.c -fhello_world gcc hello_world.c -o hello_world -std=c11
diff <(./hello_world) <(echo "Hello, world!")
