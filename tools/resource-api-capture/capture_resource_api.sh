#!/bin/bash
# Ubuntu SDK interface capture only. No target compilation/execution/connection.
set -eu
nbt_prep=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$nbt_prep"
sha256sum -c SHA256SUMS
nbt_out="$HOME/nbt-qnx-resource-api-review"
nbt_archive="$HOME/nbt-qnx-resource-api-review.tar.gz"
if [ -e "$nbt_out" ] || [ -L "$nbt_out" ]; then
    echo "Capture folder already exists; preserve it before another capture." >&2
    exit 1
fi
if [ -e "$nbt_archive" ] || [ -L "$nbt_archive" ]; then
    echo "Capture archive already exists; preserve it before another capture." >&2
    exit 1
fi
mkdir -m 700 "$nbt_out"
cp resource_api.c "$nbt_out/resource_api.c"
nbt_image=qnx65-armv7-toolchain:4.9
nbt_cc=arm-unknown-nto-qnx6.5.0eabi-gcc
sudo docker run --rm --user "$(id -u):$(id -g)" \
    -v "$nbt_out:/out" -w /out "$nbt_image" \
    "$nbt_cc" -std=gnu99 -D_QNX_SOURCE \
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
    -E -P resource_api.c -o resource_api.i
sudo docker run --rm --user "$(id -u):$(id -g)" \
    -v "$nbt_out:/out" -w /out "$nbt_image" \
    "$nbt_cc" -std=gnu99 -D_QNX_SOURCE \
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
    -dM -E resource_api.c -o resource_api.macros.txt
sudo docker run --rm --user "$(id -u):$(id -g)" \
    "$nbt_image" "$nbt_cc" --version > "$nbt_out/compiler-version.txt"
test -s "$nbt_out/resource_api.i"
test -s "$nbt_out/resource_api.macros.txt"
(
    cd "$nbt_out"
    sha256sum resource_api.c resource_api.i resource_api.macros.txt \
        compiler-version.txt > SHA256SUMS
    sha256sum -c SHA256SUMS
)
tar -czf "$nbt_archive" -C "$nbt_out" \
    resource_api.c resource_api.i resource_api.macros.txt compiler-version.txt SHA256SUMS
sha256sum "$nbt_archive"
echo "SDK interface capture ready: $nbt_archive"
echo "Preprocessing only: no target executable, project edits or BMW connection."
