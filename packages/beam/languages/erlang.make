identify:
	echo "Erlang $(erl -version | sed "s/.* version //")"

base_rule: %.erl
	echo "$(cat "$<" | grep -m1 "^-module(" | sed "s/^-module(\(.*\)).*/\1/")"

%.beam: %.erl
	erl -compile "$<"

run: %.erl
	erl -noshell -s "$(basename "$<")" main -s init stop
