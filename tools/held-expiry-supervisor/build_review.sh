#!/bin/bash
# Run from the standalone preparation root. No ARM execution or car connection.
set -euo pipefail
nbt_tool=$(cd -- "$(dirname -- "$0")" && pwd)
nbt_prep=$(cd -- "$nbt_tool/../.." && pwd)
cd "$nbt_prep"
sha256sum -c SHA256SUMS
nbt_out=build-qnx
nbt_archive="$HOME/nbt-supervisor-r2-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ] || [ -e "$nbt_archive" ] || [ -L "$nbt_archive" ]; then
    echo 'STOP: output already exists; preserve it rather than overwrite.' >&2; exit 1
fi
mkdir "$nbt_out"
if python3 -B tools/held-expiry-supervisor/run_host_checks.py --json "$nbt_out/host-results.json" \
    > "$nbt_out/host-tests.txt" 2>&1; then
    cat "$nbt_out/host-tests.txt"
else
    cat "$nbt_out/host-tests.txt"; exit 1
fi
nbt_compiler=arm-unknown-nto-qnx6.5.0eabi-gcc
nbt_flags=(-std=gnu99 -O2 -Wall -Wextra -Werror -D_QNX_SOURCE
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp)
nbt_docker=(sudo docker run --rm --user "$(id -u):$(id -g)"
    -v "$nbt_prep:/src" -w /src qnx65-armv7-toolchain:4.9)
nbt_source=tools/held-expiry-supervisor/nbt_held_supervisor.c
nbt_api=tools/held-expiry-supervisor/supervisor_api.c
nbt_binary="$nbt_out/nbt_held_supervisor"
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -o "$nbt_binary" "$nbt_source"
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -E -P -o "$nbt_out/supervisor_api.i" "$nbt_api"
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -dM -E "$nbt_api" > "$nbt_out/supervisor_api.macros.txt"
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -c -o "$nbt_out/supervisor_api.o" "$nbt_api"
readelf --symbols --wide "$nbt_out/supervisor_api.o" > "$nbt_out/supervisor_api.symbols.txt"
readelf -h "$nbt_binary" > "$nbt_binary.header.txt"
readelf -l "$nbt_binary" > "$nbt_binary.programs.txt"
readelf -d "$nbt_binary" > "$nbt_binary.dynamic.txt"
readelf -r --wide "$nbt_binary" > "$nbt_binary.relocations.txt"
readelf --dyn-syms --wide "$nbt_binary" > "$nbt_binary.symbols.txt"
readelf --symbols --wide "$nbt_binary" > "$nbt_binary.all-symbols.txt"
sha256sum "$nbt_source" "$nbt_api" "$nbt_binary" "$nbt_out/supervisor_api.i" \
    "$nbt_out/supervisor_api.o" > "$nbt_out/build-hashes.txt"
cat "$nbt_out/build-hashes.txt"
tar -czf "$nbt_archive" README.md PREPARATION.json SHA256SUMS tools "$nbt_out"
sha256sum "$nbt_archive"
echo "Offline supervisor review archive ready: $nbt_archive"
echo 'No endpoint/reader rebuild, milestone-7 edits, BMW connection or ARM execution performed.'
