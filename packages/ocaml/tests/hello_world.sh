#!/usr/bin/env bash
set -e

run ocaml --version >/dev/null

diff <(run -fhello_world.ocaml ocaml hello_world.ocaml) <(echo "Hello, world!")
