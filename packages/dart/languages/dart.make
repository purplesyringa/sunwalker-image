identify:
	dart --version | sed "s/.*version: //" | cut -d" " -f1

%: %.dart
	dart compile exe "$<" -o "$@"

run: %
	"$<"
