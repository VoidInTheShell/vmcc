# Notices and provenance

This project packages configuration and source changes from the 2026-10-13/14 PVE EMU work. VMCC tooling and new modifications are provided under GPL-2.0-or-later. Existing source files retain their original authors and license notices. Exported modified QEMU sources are represented by patches; modification date: 2026-10-14.

- QEMU 10.1.2: https://www.qemu.org/ and https://download.qemu.org/qemu-10.1.2.tar.xz . QEMU includes code under multiple compatible licenses; see vendor/licenses/QEMU-COPYING, QEMU-COPYING.LIB and original per-file notices.
- Initial EMU changes: AICodo/pve-emu-realpc, forked from zhaodice/qemu-anti-detection. https://github.com/AICodo/pve-emu-realpc . The baseline patch includes those earlier transformations as well as the final project-specific changes; all 98 differences are not claimed as newly authored VMCC code.
- OVMF: TianoCore EDK2 edk2-stable202505. https://github.com/tianocore/edk2/tree/edk2-stable202505 . See vendor/licenses/EDK2-License.txt and upstream component notices. The runtime archive carries the collected upstream license files.
- Guest kernel: Ubuntu linux 6.8.0-147.147; unchanged driver source with a custom configuration. Ubuntu source hashes and dsc are included; the kernel build is GPL-2.0 and retains upstream licensing.
- Runtime libjpeg.so.8 comes from the Ubuntu build environment; the archive includes its copyright and license notices.
- NVIDIA, Sunshine, Ubuntu OCI and PortalWrt are external components. Their binaries, user disk images and user credentials are not part of this source repository. Sunshine is installed from its official, hash-locked release.
- MSI E7E07IMS.MB0 is supplied separately by the user and is not redistributed. PCI/USB/model names identify compatibility targets and do not imply vendor certification.

The Release's unmodified QEMU source archive plus this repository's patch series provide the QEMU source used to build the packaged executable. Build options are in tools/build-qemu.sh. No benchmark source or result was modified.
