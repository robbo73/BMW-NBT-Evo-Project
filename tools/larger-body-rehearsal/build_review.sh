#!/bin/bash
# Ubuntu-only: host checks and initial 586-byte QNX build. Never executes ARM.
set -euo pipefail
nbt_prep=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$nbt_prep"
sha256sum -c SHA256SUMS
nbt_out=build-qnx
nbt_review="$HOME/nbt-large-body-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ]; then
    echo "Build output already exists; preserve it before another build." >&2; exit 1
fi
if [ -e "$nbt_review" ] || [ -L "$nbt_review" ]; then
    echo "Review archive already exists; preserve it before another build." >&2; exit 1
fi
mkdir "$nbt_out"
if python3 -B -m unittest -v test_body.py test_callbacks.py test_loop.py test_reader.py \
    > "$nbt_out/host-tests.txt" 2>&1; then
    cat "$nbt_out/host-tests.txt"
else
    cat "$nbt_out/host-tests.txt"; exit 1
fi
for nbt_role in endpoint reader; do
    nbt_target="$nbt_out/nbt_large_${nbt_role}_586"
    nbt_sources=("nbt_large_${nbt_role}.c" large_body.c)
    if [ "$nbt_role" = endpoint ]; then nbt_sources+=(trace_log.c); fi
    sudo docker run --rm --user "$(id -u):$(id -g)" \
        -v "$nbt_prep:/src" -w /src qnx65-armv7-toolchain:4.9 \
        arm-unknown-nto-qnx6.5.0eabi-gcc \
        -std=gnu99 -O2 -Wall -Wextra -D_QNX_SOURCE -DNBT_BODY_LENGTH=586 \
        -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
        -o "$nbt_target" "${nbt_sources[@]}"
    readelf -h "$nbt_target" > "$nbt_target.header.txt"
    readelf -l "$nbt_target" > "$nbt_target.programs.txt"
    readelf -d "$nbt_target" > "$nbt_target.dynamic.txt"
    readelf --dyn-syms --wide "$nbt_target" > "$nbt_target.symbols.txt"
    readelf --symbols --wide "$nbt_target" > "$nbt_target.all-symbols.txt"
done
sha256sum large_body.c large_body.h trace_log.c trace_log.h \
    nbt_large_endpoint.c nbt_large_reader.c \
    "$nbt_out/nbt_large_endpoint_586" "$nbt_out/nbt_large_reader_586" \
    > "$nbt_out/build-hashes.txt"
cat "$nbt_out/build-hashes.txt"
tar -czf "$nbt_review" large_body.c large_body.h trace_log.c trace_log.h \
    nbt_large_endpoint.c nbt_large_reader.c test_body.py test_callbacks.py \
    test_loop.py test_reader.py test_support build_review.sh \
    README.md DESIGN.md PREPARATION.json SHA256SUMS "$nbt_out"
sha256sum "$nbt_review"
echo "Offline larger-body archive ready: $nbt_review"
echo "No milestone-7 changes, BMW connection or ARM execution were performed."
