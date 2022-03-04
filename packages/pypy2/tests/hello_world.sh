#!/usr/bin/env bash
set -e

diff <(run pypy -c "print 'Hello, world!'") <(echo "Hello, world!")
