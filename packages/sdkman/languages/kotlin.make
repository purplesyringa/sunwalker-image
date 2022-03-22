identify:
	echo "Kotlin $(kotlinc -version | cut -d" " -f3)"

%.jar: %.kt
	kotlinc "$<" -d "$@"

run: %.jar
	kotlin "$<"
