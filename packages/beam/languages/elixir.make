identify:
	echo "Elixir $(elixir --short-version)"

run: %.ex
	elixir "$<"
