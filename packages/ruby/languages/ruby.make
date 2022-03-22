identify:
	echo "Ruby $(ruby -v | cut -d" " -f2)"

run: %.rb
	ruby "$<"
