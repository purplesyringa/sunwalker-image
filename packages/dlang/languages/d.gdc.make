identify:
	echo "GNU D Compiler $(gdc --version | sed "s/.* ) //")"

%: %.d
	gdc "$<" -o "$@"

run: %
	"$<"
