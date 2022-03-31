identify:
	echo "$(clang++ --version | head -1 | sed "s/ version/"), C++11"

%: %.cpp
	clang++ "$<" -o "$@" -std=c++11

run: %
	"$<"
