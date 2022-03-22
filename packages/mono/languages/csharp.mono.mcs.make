identify:
	echo "Mono C#, MCS $(mcs --version | sed "s/.* version //")"

%.exe: %.cs
	mcs "$<" -out:"$@" -nologo

run: %.exe
	mono "$<"
