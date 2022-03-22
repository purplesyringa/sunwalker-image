identify:
	lua -v | cut -d" " -f1,2

%.out: %.lua
	luac -o "$@" "$<"

run: %.out
	lua "$<"
