#!/usr/bin/env bash
set -e

touch hello_world

run -fhello_world.dart -fhello_world dart compile exe hello_world.dart -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
