#!/usr/bin/env bash
set -e

run g++ -v 2>/dev/null

touch hello_world
run -fhello_world.cpp -fhello_world g++ hello_world.cpp -o hello_world -std=c++17
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
