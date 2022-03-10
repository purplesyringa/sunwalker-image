#!/usr/bin/env bash
set -e

touch hello_world.out

run -fhello_world.lua -fhello_world.out luac -o hello_world.out hello_world.lua
diff <(run -fhello_world.out lua hello_world.out) <(echo "Hello, world!")
