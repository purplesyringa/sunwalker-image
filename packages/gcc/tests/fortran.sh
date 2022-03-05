#!/usr/bin/env bash
set -e

run gfortran -v 2>/dev/null

touch hello_world
run -fhello_world.f90 -fhello_world gfortran hello_world.f90 -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
