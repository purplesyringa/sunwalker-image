.NON_EXACT_TARGET_NAMES:

identify:
	javac --version | sed s/javac/Java/

%.class: %.java
	javac "$<"

%.jar: %.class
	jar cf "$(basename "$<")" "$@" "$<"

run: %.jar
	java -jar "$<"
