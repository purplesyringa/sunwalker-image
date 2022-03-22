identify:
	echo "OCaml $(ocaml --version | sed "s/.*version //")"

run: %.ocaml
	ocaml "$<"
