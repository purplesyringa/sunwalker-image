identify:
	echo "$(g++ --version | head -1 | sed "s/ (GCC)//"), C++17"

%: %.cpp
	g++ "$<" -o "$@" -std=c++17

run: %
	"$<"
