identify:
	echo "Nim $(nim -v | head -1 | sed "s/.* Version //" | cut -d" " -f1)"

%: %.nim
	nim compile -d:release "$<"

run: %
	"$<"
