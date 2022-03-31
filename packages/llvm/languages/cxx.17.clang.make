identify:
	echo "$(clang++ --version | head -1 | sed "s/ version/"), C++17"

%: %.cpp
	clang++ "$<" -o "$@" -std=c++17

run: %
	"$<"
