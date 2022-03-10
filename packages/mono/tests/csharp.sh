#!/usr/bin/env bash
set -e

touch hello_world.exe

run -fhello_world.cs -fhello_world.exe csc hello_world.cs -out:hello_world.exe -nologo
diff <(run -fhello_world.exe mono hello_world.exe) <(echo "Hello, world!")

run -fhello_world.cs -fhello_world.exe mcs hello_world.cs -out:hello_world.exe -nologo
diff <(run -fhello_world.exe mono hello_world.exe) <(echo "Hello, world!")
