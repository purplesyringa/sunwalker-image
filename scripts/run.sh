#!/usr/bin/env bash
set -e


if [[ "$1" != "--unshared" ]]; then
	exec unshare -p -f --kill-child -U -r -m "$0" --unshared "$@"
fi
shift


root="$(realpath "$(dirname "$0")/..")"

use_dev=0
files=()
pkg=""
while [[ "$#" -gt 0 ]]; do
	if [[ "$1" =~ ^-.* ]]; then
		if [[ "$1" == "--dev" ]]; then
			use_dev=1
			shift
		elif [[ "$1" == "-f" ]] || [[ "$1" == "--file" ]]; then
			shift
			files+=( "$1" )
			shift
		elif [[ "$1" =~ -f.* ]]; then
			files+=( "${1:2}" )
			shift
		elif [[ "$1" == "--" ]]; then
			shift
			break
		else
			echo "Unknown option $1" >&2
			exit 1
		fi
	else
		if [ -z "$pkg" ]; then
			pkg="$1"
			shift
		else
			break
		fi
	fi
done

if [[ -z "$pkg" ]]; then
	echo "Expected package name as the first unnamed argument" >&2
	exit 1
fi


mount -t tmpfs tmpfs "$root/tmp"

mkdir "$root/tmp/upper"
mkdir "$root/tmp/work"

mkdir "$root/tmp/root"

if [[ "$use_dev" == "1" ]]; then
	# Use package tar image
	mkdir "$root/tmp/package"
	ratarmount "$root/packages/$pkg/$pkg.tar.gz" "$root/tmp/package"
	lowerdir="$root/tmp/package"
else
	# Use common squashfs image
	mkdir "$root/tmp/image"
	squashfuse "$root/image.sfs" "$root/tmp/image"
	lowerdir="$root/tmp/image/$pkg"
fi

mount -t overlay -o "lowerdir=$lowerdir,upperdir=$root/tmp/upper,workdir=$root/tmp/work" overlay "$root/tmp/root"

for name in null full zero urandom random stdin stdout stderr shm mqueue ptmx pts fd; do
	files+=( "/dev/$name" )
done

for file in "${files[@]}"; do
	# If $file does not contain =, no problem--we'll just let $dest == $source == $file
	dest="$(<<<"$file" sed -E "s/=.*//")"
	source="$(<<<"$file" sed -E "s/[^=]*=//")"

	if ! [[ -e "$source" ]]; then
		echo "$source does not exist"
		exit 1
	fi

	if [[ -h "$source" ]]; then
		ln -s $(readlink "$source") "$root/tmp/root/$dest"
	elif [[ -d "$source" ]]; then
		mkdir -p "$root/tmp/root/$dest"
		mount --bind "$source" "$root/tmp/root/$dest"
	else
		mkdir -p "$(dirname "$root/tmp/root/$dest")"
		touch "$root/tmp/root/$dest"
		mount --bind "$source" "$root/tmp/root/$dest"
	fi
done

mkdir "$root/tmp/root/proc"
mount -t proc proc "$root/tmp/root/proc"

mkdir "$root/tmp/root/old-root"

cd "$root/tmp/root"

pivot_root . old-root

export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib
export LANGUAGE=en_US
export LC_ALL=en_US.UTF-8
export LC_ADDRESS=en_US.UTF-8
export LC_NAME=en_US.UTF-8
export LC_MONETARY=en_US.UTF-8
export LC_PAPER=en_US.UTF-8
export LC_IDENTIFIER=en_US.UTF-8
export LC_TELEPHONE=en_US.UTF-8
export LC_MEASUREMENT=en_US.UTF-8
export LC_TIME=en_US.UTF-8
export LC_NUMERIC=en_US.UTF-8
export LANG=en_US.UTF-8

while read -r line; do
	export "$line"
done </.sunwalker/env

exec "$@"
