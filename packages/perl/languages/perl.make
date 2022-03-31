identify:
	echo "Perl $(perl -v | grep -m1 perl | sed "s/.*(\(.*\)).*/\1/")"

run: %.pl
	perl "$<"
