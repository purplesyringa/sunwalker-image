identify:
	php -v | head -1 | cut -d" " -f1,2

run: %.php
	php "$<"
