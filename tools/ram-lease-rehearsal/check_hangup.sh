#!/bin/sh
# Vehicle OMAP context. Signal only the inert rehearsal child started here.
# Requires the previously verified RAM executable; never starts/targets HMI.
set -eu
for nbt_cmd in sleep kill; do command -v "$nbt_cmd" >/dev/null; done
ulimit -c 0 || exit 1
nbt_binary=/dev/shmem/nbt_ram_lease_rehearsal_12bcd2379450
[ -f "$nbt_binary" ]
[ ! -L "$nbt_binary" ]
[ -x "$nbt_binary" ]
"$nbt_binary" --rehearse &
nbt_child=$!
[ "$nbt_child" -gt 1 ]
sleep 2
if kill -1 "$nbt_child"; then
    :
else
    echo "STOP: could not signal rehearsal child"
    wait "$nbt_child" || :
    exit 1
fi
if wait "$nbt_child"; then nbt_status=0; else nbt_status=$?; fi
echo "Hangup rehearsal exit: $nbt_status (expected 2)"
[ "$nbt_status" -eq 2 ]
[ ! -e "/ramdisk/mm/.nbt-lease-rehearsal.$nbt_child" ]
[ ! -L "/ramdisk/mm/.nbt-lease-rehearsal.$nbt_child" ]
echo "PASS: signalled child cleaned up"
