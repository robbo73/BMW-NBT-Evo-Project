#!/bin/bash
# Ubuntu only. Host fixtures + cross-build/readelf; never execute the ARM binary.
set -eu
nbt_prep_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$nbt_prep_dir"
sha256sum -c SHA256SUMS
nbt_out=build-qnx
nbt_review="$HOME/nbt-ram-lease-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ]; then
    echo "Build output already exists; preserve it before another build." >&2
    exit 1
fi
if [ -e "$nbt_review" ] || [ -L "$nbt_review" ]; then
    echo "Review archive already exists; preserve it before another build." >&2
    exit 1
fi
mkdir "$nbt_out"
if python3 -m unittest -v test_rehearsal.py > "$nbt_out/host-tests.txt" 2>&1; then
    cat "$nbt_out/host-tests.txt"
else
    cat "$nbt_out/host-tests.txt"
    exit 1
fi
sudo docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$nbt_prep_dir:/src" -w /src \
    qnx65-armv7-toolchain:4.9 \
    arm-unknown-nto-qnx6.5.0eabi-gcc \
    -std=gnu99 -O2 -Wall -Wextra -D_QNX_SOURCE \
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
    -o "$nbt_out/nbt_ram_lease_rehearsal" nbt_ram_lease_rehearsal.c
readelf -h "$nbt_out/nbt_ram_lease_rehearsal" > "$nbt_out/elf-header.txt"
readelf -l "$nbt_out/nbt_ram_lease_rehearsal" > "$nbt_out/elf-programs.txt"
readelf -d "$nbt_out/nbt_ram_lease_rehearsal" > "$nbt_out/elf-dynamic.txt"
readelf --dyn-syms --wide "$nbt_out/nbt_ram_lease_rehearsal" > "$nbt_out/elf-symbols.txt"
sha256sum nbt_ram_lease_rehearsal.c "$nbt_out/nbt_ram_lease_rehearsal" > "$nbt_out/build-hashes.txt"
cat "$nbt_out/build-hashes.txt"
tar -czf "$nbt_review" nbt_ram_lease_rehearsal.c test_rehearsal.py \
    build_review.sh README.md SHA256SUMS "$nbt_out"
sha256sum "$nbt_review"
echo "Offline review archive ready: $nbt_review"
echo "No milestone-7 source/binary was edited; no target execution or BMW connection was performed."
