#!/bin/sh
# OMAP only. Dummy alias outside all plugin roots; fixed existing C helper.
nbt_usage() {
    echo "Usage: $0 --deadline | --forced-death"
    echo "Default/help does nothing. Isolated dummy link only; no plugin/HMI operation."
}
case "${1-}" in
    ""|--help) [ "$#" -le 1 ] || exit 2; nbt_usage; exit 0 ;;
    --deadline|--forced-death) [ "$#" -eq 1 ] || exit 2; nbt_mode=$1 ;;
    *) nbt_usage; exit 2 ;;
esac
set -u
ulimit -c 0 || exit 1
for nbt_cmd in cat kill sleep ln mkdir rm; do
    command -v "$nbt_cmd" >/dev/null || exit 1
done
nbt_root=/ramdisk/mm
nbt_binary=/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e
if [ -L "$nbt_root" ] || [ ! -d "$nbt_root" ]; then
    echo "STOP: RAM root unavailable or linked"; exit 1
fi
cd "$nbt_root" || exit 1
[ "$(pwd -P)" = "$nbt_root" ] || exit 1
if [ -L "$nbt_binary" ] || [ ! -f "$nbt_binary" ] || [ ! -x "$nbt_binary" ]; then
    echo "STOP: corrected RAM executable unavailable"; exit 1
fi
umask 077
nbt_base="$nbt_root/.nbt-endpoint-alias.$$"
nbt_alias="$nbt_base/dummy-discovery.txt"
# mkdir must succeed; never reuse a previous fixture, including a symlink.
mkdir "$nbt_base" || exit 1
nbt_server=
nbt_watch=
nbt_pending=0
nbt_cleanup() {
    nbt_code=$?
    trap - 0 1 2 3 15
    if [ "$nbt_pending" -eq 1 ]; then
        kill -15 "$nbt_server" 2>/dev/null || :
        wait "$nbt_server" 2>/dev/null || :
    fi
    if [ -n "$nbt_watch" ]; then
        kill -15 "$nbt_watch" 2>/dev/null || :
        wait "$nbt_watch" 2>/dev/null || :
    fi
    if [ -L "$nbt_root" ] || [ -L "$nbt_base" ] || [ ! -d "$nbt_base" ]; then
        echo "STOP: fixture directory changed; preserving path"; exit 1
    fi
    cd "$nbt_root" || exit 1
    [ "$(pwd -P)" = "$nbt_root" ] || exit 1
    if [ -L "$nbt_alias" ]; then
        rm "$nbt_alias" || exit 1
    elif [ -e "$nbt_alias" ]; then
        echo "STOP: alias replaced by a non-link; preserving fixture"; exit 1
    fi
    for nbt_entry in "$nbt_base"/* "$nbt_base"/.[!.]* "$nbt_base"/..?*; do
        if [ -e "$nbt_entry" ] || [ -L "$nbt_entry" ]; then
            echo "STOP: unexpected fixture entry; preserving directory"; exit 1
        fi
    done
    # QNX has rm but no rmdir utility. Only this owned, checked-empty directory.
    rm -r "$nbt_base" || exit 1
    if [ -e "$nbt_base" ] || [ -L "$nbt_base" ]; then exit 1; fi
    echo "CLEANED: dummy alias and owned fixture directory"
    if [ "$nbt_code" -eq 0 ]; then
        echo "PASS: $nbt_mode dummy discovery-link rehearsal"
    fi
    exit "$nbt_code"
}
trap nbt_cleanup 0
trap 'exit 2' 1 2 3 15
trap '' 13
"$nbt_binary" --serve &
nbt_server=$!
[ "$nbt_server" -gt 1 ] || exit 1
nbt_pending=1
nbt_endpoint="/dev/nbt_endpoint_rehearsal.$nbt_server"
(
    sleep 15 </dev/null >/dev/null 2>&1
    if kill -9 "$nbt_server" 2>/dev/null; then
        echo "WATCHDOG: stopped overrunning inert helper"
    fi
) &
nbt_watch=$!
sleep 1
[ -f "$nbt_endpoint" ] || { echo "STOP: endpoint not ready"; exit 1; }
ln -s "$nbt_endpoint" "$nbt_alias" || exit 1
[ -L "$nbt_alias" ] && [ -f "$nbt_alias" ] || exit 1
if nbt_text=$(cat "$nbt_alias"); then
    echo "ALIAS_READ: $nbt_text"
else
    echo "STOP: dummy alias read failed"; exit 1
fi
[ "$nbt_text" = nbt-endpoint-rehearsal ] || { echo "STOP: unexpected text"; exit 1; }
if [ "$nbt_mode" = --forced-death ]; then
    kill -9 "$nbt_server" || exit 1
    echo "FORCED_STOP: rehearsal child $nbt_server"
fi
if wait "$nbt_server"; then nbt_status=0; else nbt_status=$?; fi
nbt_pending=0
kill -15 "$nbt_watch" 2>/dev/null || :
wait "$nbt_watch" 2>/dev/null || :
nbt_watch=
echo "Endpoint server exit: $nbt_status"
case "$nbt_mode:$nbt_status" in
    --deadline:0|--forced-death:137) : ;;
    *) echo "STOP: unexpected helper exit"; exit 1 ;;
esac
sleep 1
[ -L "$nbt_alias" ] || { echo "STOP: alias changed or disappeared"; exit 1; }
if [ -e "$nbt_endpoint" ] || [ -L "$nbt_endpoint" ] || [ -e "$nbt_alias" ]; then
    echo "STOP: endpoint or alias still resolves"; exit 1
fi
echo "DANGLING: dummy alias remains a link; target unavailable"
# Exit trap removes only this link, checks the directory is empty, then removes it.
exit 0
