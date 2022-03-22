identify:
	echo "$(pypy --version | head -1 | cut -d" " -f1,2), PyPy $(pypy --version | tail -1 | cut -d" " -f2)"

run: %.py
	pypy "$<"
