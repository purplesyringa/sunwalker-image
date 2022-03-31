identify:
	echo "Mono C#, CSC $(csc -version | sed "s/ (.*//")"

%.exe: %.cs
	csc "$<" -out:"$@" -nologo

run: %.exe
	mono "$<"
