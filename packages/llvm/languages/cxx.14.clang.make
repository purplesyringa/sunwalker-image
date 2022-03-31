identify:
	echo "$(clang++ --version | head -1 | sed "s/ version/"), C++14"

%: %.cpp
	clang++ "$<" -o "$@" -std=c++14

run: %
	"$<"
