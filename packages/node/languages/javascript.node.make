identify:
	echo "Node $(node -v)"

run: %.js
	node "$<"
