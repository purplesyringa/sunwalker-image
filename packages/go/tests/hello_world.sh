#!/usr/bin/env bash
set -e

touch hello_world

run -fhello_world.go -fhello_world go build -o hello_world -buildmode=exe hello_world.go
chmod +x hello_world
diff <(run -fhello_world ./hello_world) <(echo "Hello, world!")
