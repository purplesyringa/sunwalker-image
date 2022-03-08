#!/usr/bin/env bash
set -e

run node -v >/dev/null

diff <(run node -e "console.log('Hello, world!');") <(echo "Hello, world!")
