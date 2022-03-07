#!/usr/bin/env bash
set -e

touch hello_world

run ghc --version >/dev/null

run -fhello_world.hs -fhello_world ghc hello_world.hs -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
