#!/bin/bash
# Ubuntu host policy checks + QNX cross-build/readelf. Never executes ARM output.
set -eu
nbt_prep=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$nbt_prep"
sha256sum -c SHA256SUMS
nbt_out=build-qnx
nbt_review="$HOME/nbt-endpoint-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ]; then
    echo "Build output already exists; preserve it before another build." >&2
    exit 1
fi
if [ -e "$nbt_review" ] || [ -L "$nbt_review" ]; then
    echo "Review archive already exists; preserve it before another build." >&2
    exit 1
fi
mkdir "$nbt_out"
if python3 -m unittest -v test_policy.py > "$nbt_out/host-policy-tests.txt" 2>&1; then
    cat "$nbt_out/host-policy-tests.txt"
else
    cat "$nbt_out/host-policy-tests.txt"
    exit 1
fi
sudo docker run --rm --user "$(id -u):$(id -g)" \
    -v "$nbt_prep:/src" -w /src qnx65-armv7-toolchain:4.9 \
    arm-unknown-nto-qnx6.5.0eabi-gcc \
    -std=gnu99 -O2 -Wall -Wextra -D_QNX_SOURCE \
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
    -o "$nbt_out/nbt_endpoint_rehearsal" \
    nbt_endpoint_rehearsal.c endpoint_policy.c
readelf -h "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/elf-header.txt"
readelf -l "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/elf-programs.txt"
readelf -d "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/elf-dynamic.txt"
readelf --dyn-syms --wide "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/elf-symbols.txt"
readelf --symbols --wide "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/elf-all-symbols.txt"
sha256sum nbt_endpoint_rehearsal.c endpoint_policy.c endpoint_policy.h \
    "$nbt_out/nbt_endpoint_rehearsal" > "$nbt_out/build-hashes.txt"
cat "$nbt_out/build-hashes.txt"
tar -czf "$nbt_review" nbt_endpoint_rehearsal.c endpoint_policy.c endpoint_policy.h \
    test_policy.py build_review.sh README.md SHA256SUMS "$nbt_out"
sha256sum "$nbt_review"
echo "Offline endpoint review archive ready: $nbt_review"
echo "No milestone-7 changes, BMW connection or ARM execution were performed."
