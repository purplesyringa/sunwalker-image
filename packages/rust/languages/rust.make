identify:
	echo "Rust $(rust --version | cut -d" " -f2)"

%: %.rs
	rustc "$<" -o "$@"

run: %
	"$<"
