identify:
	echo "$(python2 --version), CPython"

%.pyc: %.py
	python2 -m compileall -q "$<"

run: %.pyc %.py
	python2 "$<"
