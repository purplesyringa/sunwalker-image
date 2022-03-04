#!/usr/bin/env bash
set -e

touch hello_world

run -fhello_world.rs -fhello_world rustc hello_world.rs -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
