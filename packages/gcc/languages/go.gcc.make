identify:
	gccgo --version | head -1 | sed "s/ (GCC)//"

%: %.go
	gccgo "$<" -o "$@"

run: %
	"$<"
