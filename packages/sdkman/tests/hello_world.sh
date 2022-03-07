#!/usr/bin/env bash
set -e

touch hello_world.jar
touch HelloWorld.class
if ! [ -e module ]; then
	mkdir module
fi

run -fhello_world.java -fHelloWorld.class javac hello_world.java
run -fHelloWorld.class -fhello_world.jar jar cf HelloWorld hello_world.jar HelloWorld.class
diff <(run -fhello_world.jar java -jar hello_world.jar) <(echo "Hello, world!")

run -fhello_world.kt -fhello_world.jar kotlinc hello_world.kt -d hello_world.jar
diff <(run -fhello_world.jar kotlin hello_world.jar) <(echo "Hello, world!")

run -fhello_world.scala -fmodule scalac hello_world.scala -d module/hello_world.jar
diff <(run -fhello_world.jar=module/hello_world.jar scala hello_world.jar) <(echo "Hello, world!")
