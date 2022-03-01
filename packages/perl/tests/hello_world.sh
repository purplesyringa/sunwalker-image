#!/usr/bin/env bash
set -e
run perl -v >/dev/null
diff <(run perl -e 'print "Hello, world!\n";') <(echo "Hello, world!")
