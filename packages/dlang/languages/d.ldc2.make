identify:
	echo "LLVM D Compiler $(ldc2 --version | head -1 | sed "s/.*(//" | sed "s/).*//")"

%: %.d
	ldc2 "$<" -of="$@"

run: %
	"$<"
