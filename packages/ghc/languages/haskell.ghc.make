identify:
	echo "Glasgow Haskell Compiler $(ghc | sed "s/.* version //")"

%: %.hs
	ghc -dynamic "$<" -o "$@"

run: %
	"$<"
