identify:
	echo "Free Pascal Compiler $(fpc -iW)"

%: %.pas
	fpc -FE. "$<"

run: %
	"$<"
