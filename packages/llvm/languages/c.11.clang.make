identify:
	echo "$(clang --version | head -1 | sed "s/ version/"), C11"

%: %.c
	clang "$<" -o "$@" -std=c11

run: %
	"$<"
