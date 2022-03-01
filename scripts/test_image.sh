#!/usr/bin/env bash
set -e

export SUNWALKER_ROOT="$(realpath "$(dirname "$0")/..")"


use_dev=0
packages=()
while [[ "$#" -gt 0 ]]; do
	if [[ "$1" =~ ^-.* ]]; then
		if [[ "$1" == "--dev" ]]; then
			use_dev=1
			shift
		elif [[ "$1" == "--" ]]; then
			shift
			break
		else
			echo "Unknown option $1" >&2
			exit 1
		fi
	else
		packages+=( "$1" )
		shift
	fi
done


if [[ "${#packages}" -eq 0 ]]; then
	for pkg_path in "$SUNWALKER_ROOT/packages/"*; do
		pkg="${pkg_path##*/}"
		packages+=( "$pkg" )
	done
fi


opts=()
if [[ "$use_dev" == "1" ]]; then
	opts+=( "--dev" )
fi

export SUNWALKER_RUN_OPTS="${opts[@]}"

run() {
	"$SUNWALKER_ROOT/scripts/run.sh" $SUNWALKER_RUN_OPTS "$SUNWALKER_PACKAGE" "$@"
}
export -f run


for pkg in "${packages[@]}"; do
	export SUNWALKER_PACKAGE="$pkg"
	pkg_path="$SUNWALKER_ROOT/packages/$pkg"

	if [[ -d "$pkg_path/tests" ]]; then
		echo "$pkg"
		for test_path in "$pkg_path/tests/"*".sh"; do
			test_name="${test_path##*/}"
			echo "- $test_name"
			pushd "$(dirname "$test_path")" >/dev/null
			"$test_path"
			popd >/dev/null
		done
	else
		echo "$pkg has no tests"
	fi
done
