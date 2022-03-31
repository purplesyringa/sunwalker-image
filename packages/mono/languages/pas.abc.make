identify:
	echo "PascalABC.NET $(</dev/null mono /pascalabc/pabcnetc.exe | grep -m1 PascalABCCompiler.Core | cut -d" " -f2)"

%.exe: %.pas
	mono /pascalabc/pabcnetc.exe "$<" "$@"

run: %.exe
	mono "$<"
