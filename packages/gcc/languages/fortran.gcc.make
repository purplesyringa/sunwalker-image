identify:
	gfortran --version | head -1 | sed "s/ (GCC)//"

%: %.f90
	gfortran "$<" -o "$@"

run: %
	"$<"
