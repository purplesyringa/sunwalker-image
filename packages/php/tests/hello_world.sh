#!/usr/bin/env bash
set -e
run php -v >/dev/null
diff <(run php -r 'echo "Hello, world!\n";') <(echo "Hello, world!")
