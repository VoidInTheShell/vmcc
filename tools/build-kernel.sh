#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${VMCC_KERNEL_BUILD_DIR:-"$repo_dir/.cache/kernel"}
output_dir=${VMCC_KERNEL_OUTPUT_DIR:-"$repo_dir/artifacts/kernel"}
mkdir -p "$build_dir" "$output_dir"
cd "$build_dir"
# Ubuntu noble deb-src must contain this locked source version. dsc hashes are in profiles/.
apt-get source linux=6.8.0-147.147
printf '%s\n' \
  '26512115972bdf017a4ac826cc7d3e9b0ba397d4f85cd330e4e4ff54c78061c8  linux_6.8.0.orig.tar.gz' \
  '370fa76631a470323e92a0b25dca6012287c4ada448c7f2e4954f45a628e936c  linux_6.8.0-147.147.diff.gz' | sha256sum --check
cd linux-6.8.0
sed -i 's/^SUBLEVEL = 0$/SUBLEVEL = 12/' Makefile
cp "$repo_dir/profiles/kernel-6.8.12-generic.config" .config
scripts/config --module UHID
make olddefconfig
# Standard Kbuild provenance overrides; no /proc/version or application hooks.
export KBUILD_BUILD_VERSION=6
export KBUILD_BUILD_USER=builder
export KBUILD_BUILD_HOST=build
export SOURCE_DATE_EPOCH=$(date -d "$(dpkg-parsechangelog -SDate)" +%s)
export KBUILD_BUILD_TIMESTAMP=$(date -u -d "@$SOURCE_DATE_EPOCH" '+%a %b %d %T UTC %Y')
make -j "${VMCC_BUILD_JOBS:-8}" bzImage modules
make INSTALL_MOD_PATH="$output_dir" modules_install
mkdir -p "$output_dir/boot"
for item in System.map .config arch/x86/boot/bzImage; do
  case "$item" in
    System.map) target=System.map-6.8.12-generic;;
    .config) target=config-6.8.12-generic;;
    *) target=vmlinuz-6.8.12-generic;;
  esac
  cp "$item" "$output_dir/boot/$target"
done
headers="$output_dir/usr/src/linux-headers-6.8.12-generic"
mkdir -p "$headers"
tar -cf - --exclude='*.o' --exclude='*.a' --exclude='*.ko' --exclude='*.cmd' \
  --exclude='vmlinux*' --exclude='System.map' --exclude='arch/x86/boot/bzImage' --exclude='.git' . | tar -C "$headers" -xf -
rm -f "$output_dir/lib/modules/6.8.12-generic/build" "$output_dir/lib/modules/6.8.12-generic/source"
ln -s /usr/src/linux-headers-6.8.12-generic "$output_dir/lib/modules/6.8.12-generic/build"
ln -s /usr/src/linux-headers-6.8.12-generic "$output_dir/lib/modules/6.8.12-generic/source"
printf 'Kernel staging: %s; generate initramfs and NVIDIA DKMS on the target guest.\n' "$output_dir"
