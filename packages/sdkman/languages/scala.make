identify:
	scalac --version | sed "s/compiler version //" | sed "s/ --.*//"

%.jar: %.scala
	scalac "$<" -d "$@"

run: %.jar
	scala "$<"
