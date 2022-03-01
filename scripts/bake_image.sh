#!/usr/bin/env bash
set -e


if [ "$1" != "--unshared" ]; then
	unshare -U -r -m "$0" --unshared
	exit $?
fi


root="$(realpath "$(dirname "$0")/..")"

mount -t tmpfs tmpfs "$root/tmp"

echo "Mounting packages"
mkdir "$root/tmp/packages"
for pkg_path in "$root/packages/"*; do
	pkg="${pkg_path##*/}"
	if [ -f "$pkg_path/$pkg.tar.gz" ]; then
		mkdir "$root/tmp/packages/$pkg"
		ratarmount "$pkg_path/$pkg.tar.gz" "$root/tmp/packages/$pkg"
	fi
done

echo "Building squashfs"
mksquashfs "$root/tmp/packages" "$root/image.sfs" -noappend
