#!/usr/bin/env bash
set -e

run elixir -v >/dev/null

diff <(run -fhello_world.ex elixir hello_world.ex) <(echo "Hello, world!")
