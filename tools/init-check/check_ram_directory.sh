#!/bin/sh
# Inert filesystem check only. No plugin files, directory links or execution.
set -eu
command -v ln >/dev/null
cd /ramdisk/mm
[ "$(pwd -P)" = /ramdisk/mm ]
umask 077
nbt_probe="/ramdisk/mm/.nbt-ram-check.$$"
mkdir "$nbt_probe"
trap 'rm -f "$nbt_probe/check"; rmdir "$nbt_probe"' 0
trap 'exit 1' 1 2 3 15
echo nbt-ram-check > "$nbt_probe/check"
[ "$(cat "$nbt_probe/check")" = nbt-ram-check ]
rm "$nbt_probe/check"
rmdir "$nbt_probe"
trap - 0 1 2 3 15
echo "PASS: RAM directory write/read/delete; ln utility available"
