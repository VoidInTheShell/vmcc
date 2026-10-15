#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${VMCC_OVMF_BUILD_DIR:-"$repo_dir/.cache/ovmf"}
output_dir=${VMCC_OUTPUT_DIR:-"$repo_dir/artifacts/runtime"}
mkdir -p "$build_dir" "$output_dir"
git clone --depth 1 --branch edk2-stable202505 --recurse-submodules --shallow-submodules https://github.com/tianocore/edk2.git "$build_dir/edk2"
cd "$build_dir/edk2"
test "$(git rev-parse HEAD)" = 6951dfe7d59d144a3a980bd7eda699db2d8554ac
sed -i 's/#define INTEL_Q35_MCH_DEVICE_ID  0x29C0/#define INTEL_Q35_MCH_DEVICE_ID  0xA700/' OvmfPkg/Include/IndustryStandard/Q35MchIch9.h
make -C BaseTools -j "${VMCC_BUILD_JOBS:-8}"
export WORKSPACE="$PWD"
export EDK_TOOLS_PATH="$PWD/BaseTools"
set +u
source edksetup.sh
set -u
build -a X64 -b RELEASE -t GCC5 -p OvmfPkg/OvmfPkgX64.dsc -D FD_SIZE_4MB -D SECURE_BOOT_ENABLE=FALSE -n "${VMCC_BUILD_JOBS:-8}"
install -m644 Build/OvmfX64/RELEASE_GCC5/FV/OVMF_CODE.fd "$output_dir/OVMF_CODE_RPL_4M.fd"
install -m644 Build/OvmfX64/RELEASE_GCC5/FV/OVMF_VARS.fd "$output_dir/OVMF_VARS.clean.fd"
