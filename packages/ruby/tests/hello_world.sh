#!/usr/bin/env bash
set -e

diff <(run -fhello_world.rb ruby hello_world.rb) <(echo "Hello, world!")
