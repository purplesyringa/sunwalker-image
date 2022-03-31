identify:
	echo "$(clang++ --version | head -1 | sed "s/ version/"), C++20"

%: %.cpp
	clang++ "$<" -o "$@" -std=c++20

run: %
	"$<"
