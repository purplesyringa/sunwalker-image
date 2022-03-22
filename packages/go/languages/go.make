identify:
	echo "Go $(go version | sed "s/.* version go//" | cut -d" " -f1)"

%: %.go
	go build -o "$@" -buildmode=exe "$<"

run: %
	"$<"
