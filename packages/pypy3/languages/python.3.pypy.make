identify:
	echo "$(pypy3 --version | head -1 | cut -d" " -f1,2), PyPy $(pypy3 --version | tail -1 | cut -d" " -f2)"

run: %.py
	pypy3 "$<"
