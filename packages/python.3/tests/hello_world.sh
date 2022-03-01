#!/usr/bin/env bash
set -e
diff <(run python3 -c "print('Hello, world!')") <(echo "Hello, world!")
run python3 -c "import random; print(random.randint(1, 1000))" >/dev/null

if run python3 -c "import sys; sys.exit(123)"; then
	echo "Unexpected success"
	exit 1
else
	[ $? == 123 ]
fi
