#!/bin/bash
# Ubuntu-only. Build a separate review executable; never execute ARM code.
set -euo pipefail
nbt_prep=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$nbt_prep"
sha256sum -c SHA256SUMS
nbt_out=build-qnx
nbt_review="$HOME/nbt-open-handle-reader-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ] || [ -e "$nbt_review" ] || [ -L "$nbt_review" ]; then
    echo "STOP: output already exists; preserve it rather than overwrite." >&2; exit 1
fi
mkdir "$nbt_out"
if python3 -B -m unittest -v test_reader.py > "$nbt_out/host-tests.txt" 2>&1; then
    cat "$nbt_out/host-tests.txt"
else
    cat "$nbt_out/host-tests.txt"; exit 1
fi
nbt_compiler=arm-unknown-nto-qnx6.5.0eabi-gcc
nbt_flags=(-std=gnu99 -O2 -Wall -Wextra -Werror -D_QNX_SOURCE -DNBT_BODY_LENGTH=586
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp)
nbt_docker=(sudo docker run --rm --user "$(id -u):$(id -g)"
    -v "$nbt_prep:/src" -w /src qnx65-armv7-toolchain:4.9)
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" \
    -o "$nbt_out/nbt_hold_reader_586" nbt_hold_reader.c large_body.c
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -E -P \
    -o "$nbt_out/hold_api.i" hold_api.c
"${nbt_docker[@]}" "$nbt_compiler" "${nbt_flags[@]}" -c \
    -o "$nbt_out/hold_api.o" hold_api.c
readelf --symbols --wide "$nbt_out/hold_api.o" > "$nbt_out/hold_api.symbols.txt"
nbt_target="$nbt_out/nbt_hold_reader_586"
readelf -h "$nbt_target" > "$nbt_target.header.txt"
readelf -l "$nbt_target" > "$nbt_target.programs.txt"
readelf -d "$nbt_target" > "$nbt_target.dynamic.txt"
readelf -r --wide "$nbt_target" > "$nbt_target.relocations.txt"
readelf --dyn-syms --wide "$nbt_target" > "$nbt_target.symbols.txt"
readelf --symbols --wide "$nbt_target" > "$nbt_target.all-symbols.txt"
sha256sum nbt_hold_reader.c large_body.c large_body.h hold_api.c "$nbt_target" \
    "$nbt_out/hold_api.i" "$nbt_out/hold_api.o" > "$nbt_out/build-hashes.txt"
cat "$nbt_out/build-hashes.txt"
tar -czf "$nbt_review" nbt_hold_reader.c large_body.c large_body.h hold_api.c \
    test_reader.py test_support/raw_faults.c build_review.sh README.md DESIGN.md \
    PREPARATION.json SHA256SUMS "$nbt_out"
sha256sum "$nbt_review"
echo "Offline review archive ready: $nbt_review"
echo "No endpoint rebuild, milestone-7 edits, BMW connection or ARM execution performed."
