#!/bin/sh
# Inert filesystem check only. No plugin files, directory links or execution.
set -eu
for nbt_cmd in ln mkdir cat rm; do command -v "$nbt_cmd" >/dev/null; done
cd /ramdisk/mm
[ "$(pwd -P)" = /ramdisk/mm ]
umask 077
nbt_probe="/ramdisk/mm/.nbt-ram-check.$$"
mkdir "$nbt_probe"
nbt_cleanup() {
    [ ! -L "$nbt_probe" ] || return 1
    if [ ! -d "$nbt_probe" ]; then return 0; fi
    rm -f "$nbt_probe/check"
    for nbt_entry in "$nbt_probe"/* "$nbt_probe"/.[!.]* "$nbt_probe"/..?*; do
        if [ -e "$nbt_entry" ] || [ -L "$nbt_entry" ]; then
            echo "STOP: unexpected entry in temporary directory; leaving it for inspection" >&2
            return 1
        fi
    done
    # rmdir is absent on the target. Use rm only on this owned, empty directory.
    rm -r "$nbt_probe"
}
trap nbt_cleanup 0
trap 'exit 1' 1 2 3 15
echo nbt-ram-check > "$nbt_probe/check"
[ "$(cat "$nbt_probe/check")" = nbt-ram-check ]
nbt_cleanup
trap - 0 1 2 3 15
echo "PASS: RAM directory write/read/delete; ln utility available"
