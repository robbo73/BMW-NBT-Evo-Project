#!/bin/sh
# OMAP only: deliberately stop only the inert helper child started here.
set -u
ulimit -c 0 || exit 1
for nbt_cmd in sleep kill cat; do command -v "$nbt_cmd" >/dev/null || exit 1; done
nbt_binary=/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e
if [ ! -f "$nbt_binary" ] || [ -L "$nbt_binary" ] || [ ! -x "$nbt_binary" ]; then
    echo "STOP: corrected RAM executable unavailable"
    exit 1
fi
"$nbt_binary" --serve &
nbt_server=$!
[ "$nbt_server" -gt 1 ] || exit 1
nbt_endpoint="/dev/nbt_endpoint_rehearsal.$nbt_server"
(
    sleep 15 </dev/null >/dev/null 2>&1
    if kill -9 "$nbt_server" 2>/dev/null; then
        echo "WATCHDOG: stopped overrunning inert helper"
    fi
) &
nbt_watch=$!
sleep 1
nbt_read_ok=1
nbt_kill_ok=1
if nbt_text=$(cat "$nbt_endpoint"); then
    echo "READ: $nbt_text"
    if [ "$nbt_text" = nbt-endpoint-rehearsal ]; then
        nbt_read_ok=0
        if kill -9 "$nbt_server"; then
            nbt_kill_ok=0
            echo "FORCED_STOP: rehearsal child $nbt_server"
        fi
    fi
fi
if wait "$nbt_server"; then nbt_status=0; else nbt_status=$?; fi
kill -15 "$nbt_watch" 2>/dev/null || :
wait "$nbt_watch" 2>/dev/null || :
echo "Forced-stop exit: $nbt_status (expected 137)"
if [ "$nbt_read_ok" -ne 0 ] || [ "$nbt_kill_ok" -ne 0 ] || [ "$nbt_status" -ne 137 ]; then
    echo "STOP: forced-death check did not complete as expected"
    exit 1
fi
sleep 1
if [ -e "$nbt_endpoint" ] || [ -L "$nbt_endpoint" ]; then
    echo "REMAINS: endpoint path"
    exit 1
fi
echo "PASS: endpoint unavailable after forced process death"
