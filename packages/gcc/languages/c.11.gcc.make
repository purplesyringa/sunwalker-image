identify:
	echo "$(gcc --version | head -1 | sed "s/ (GCC)//"), C11"

%: %.c
	gcc "$<" -o "$@" -std=c11 -O2

run: %
	"$<"
