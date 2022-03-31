identify:
	echo "$(clang --version | head -1 | sed "s/ version/"), Objective C"

%: %.m
	clang "$<" -lobjc -lgnustep-base -DGNUSTEP_BASE_LIBRARY=1 -DGNU_RUNTIME=1 -DGNUSTEP -fconstant-string-class=NSConstantString -o "$@"

run: %
	"$<"
