identify:
	echo "Clozure CL $(ccl -V | cut -d" " -f2)"

run: %.lisp
	ccl -l "$<" -e "(quit)"
