#!/bin/bash
set -eu

nbt_prep_dir=$(cd -- "$(dirname -- "$0")" && pwd)
nbt_project_root=$(cd -- "${1:-$HOME/milestone-7}" && pwd)
nbt_check_binary="$nbt_project_root/rhmiapp/libNbtAadInitCheck.so"
nbt_review_archive="$HOME/nbt-init-check-review.tar.gz"

if [ -e "$nbt_check_binary" ] || [ -L "$nbt_check_binary" ]; then
    echo "Initialization-check binary already exists; preserve it before another build." >&2
    exit 1
fi
if [ -e "$nbt_review_archive" ] || [ -L "$nbt_review_archive" ]; then
    echo "Review archive already exists; preserve it before another build." >&2
    exit 1
fi

python3 "$nbt_prep_dir/prepare_init_check.py" "$nbt_project_root" --write-copy

sudo docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$nbt_project_root:/src" \
    -w /src \
    qnx65-armv7-toolchain:4.9 \
    qcc -Vgcc_ntoarmv7le_gpp \
    -O2 -Wall -Wno-unused-function -D_QNX_SOURCE \
    -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp -fPIC -I./plugin \
    -std=gnu++0x -shared -Wl,-soname,libNbtAadInitCheck.so \
    -o rhmiapp/libNbtAadInitCheck.so \
    rhmiapp/nbt_aad_app_init_check.cpp rhmiapp/b58/b58_rhmi_bridge.cpp \
    ./rhmiapp/lib/libAppFramework.A.so ./rhmiapp/lib/libCoreFramework.A.so \
    -Wl,--allow-shlib-undefined -lang-c++

cd -- "$nbt_project_root"
tar -czf "$nbt_review_archive" \
    rhmiapp/libNbtAadInitCheck.so rhmiapp/nbt_aad_app_init_check.cpp
sha256sum rhmiapp/nbt_aad_app.cpp rhmiapp/libNbtAad.so \
    rhmiapp/nbt_aad_app_init_check.cpp rhmiapp/libNbtAadInitCheck.so "$nbt_review_archive"
echo "Offline review archive ready: $nbt_review_archive"
echo "No installation or BMW execution was performed."
