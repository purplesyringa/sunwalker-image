identify:
	echo "$(python3 --version), CPython"

%.pyc: %.py
	python3 -m compileall -q -b "$<"

run: %.pyc %.py
	python3 "$<"
