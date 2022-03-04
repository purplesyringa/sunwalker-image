#!/usr/bin/env bash
set -e

diff <(run pypy3 -c "print('Hello, world!')") <(echo "Hello, world!")
