identify:
	dmd --version | head -1

%: %.d
	dmd "$<" -of="$@"

run: %
	"$<"
