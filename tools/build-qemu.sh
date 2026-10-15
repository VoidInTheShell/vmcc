#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cache_dir=${VMCC_BUILD_DIR:-"$repo_dir/.cache/qemu"}
output_dir=${VMCC_OUTPUT_DIR:-"$repo_dir/artifacts/runtime"}
source_tar=${VMCC_QEMU_TARBALL:-"$cache_dir/qemu-10.1.2.tar.xz"}
mkdir -p "$cache_dir" "$output_dir/lib"
if [ ! -f "$source_tar" ]; then
  curl --fail --location --retry 3 https://download.qemu.org/qemu-10.1.2.tar.xz --output "$source_tar"
fi
printf '%s  %s\n' 9d75f331c1a5cb9b6eb8fd9f64f563ec2eab346c822cb97f8b35cd82d3f11479 "$source_tar" | sha256sum --check
test ! -e "$cache_dir/qemu-10.1.2"
tar -xf "$source_tar" -C "$cache_dir"
cd "$cache_dir/qemu-10.1.2"
while IFS= read -r patch_name; do
  patch --batch --fuzz=0 -p1 < "$repo_dir/patches/$patch_name"
done < "$repo_dir/patches/series"
mkdir build
cd build
../configure --target-list=x86_64-softmmu --prefix=/usr --enable-kvm --enable-vnc \
  --enable-gcrypt --disable-werror --disable-docs --disable-gtk --disable-sdl \
  --disable-spice --disable-user --enable-linux-aio --enable-linux-io-uring \
  --audio-drv-list=alsa
ninja -j "${VMCC_BUILD_JOBS:-8}" qemu-system-x86_64
install -m755 qemu-system-x86_64 "$output_dir/qemu-system-x86_64"
# Ubuntu-built QEMU needs libjpeg.so.8 on Debian/PVE; use the build environment's copy.
if [ -f /usr/lib/x86_64-linux-gnu/libjpeg.so.8 ]; then
  cp -L /usr/lib/x86_64-linux-gnu/libjpeg.so.8 "$output_dir/lib/libjpeg.so.8"
fi
(cd "$output_dir" && sha256sum qemu-system-x86_64 > QEMU_SHA256SUMS)
printf 'QEMU build ready: %s\n' "$output_dir"
