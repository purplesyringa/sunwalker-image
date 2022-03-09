#!/usr/bin/env bash
set -e

touch hello_world
run -fhello_world.m -fhello_world clang hello_world.m -lobjc -lgnustep-base -DGNUSTEP_BASE_LIBRARY=1 -DGNU_RUNTIME=1 -DGNUSTEP -fconstant-string-class=NSConstantString -o hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
