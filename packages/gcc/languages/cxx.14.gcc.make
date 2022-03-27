identify:
	echo "$(g++ --version | head -1 | sed "s/ (GCC)//"), C++14"

%: %.cpp
	g++ "$<" -o "$@" -std=c++14 -O2 -I/usr/local/include/c++14

run: %
	"$<"
