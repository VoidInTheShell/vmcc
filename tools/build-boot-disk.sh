#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Creates ONLY a new regular sparse file, never formats a supplied block device.
set -euo pipefail
test "$#" = 2 || { echo 'usage: sudo tools/build-boot-disk.sh PREPARED_ROOTFS NEW_DISK.raw'; exit 2; }
test "$(id -u)" = 0
rootfs=$(realpath -- "$1")
disk=$(realpath -m -- "$2")
test -d "$rootfs/etc"
test ! -e "$disk"
test ! -L "$disk"
case "$disk" in /dev/*|/proc/*|/sys/*) echo 'regular output file required'; exit 2;; esac
test -f "$rootfs/usr/sbin/grub-install"
compgen -G "$rootfs/boot/vmlinuz-*-generic" >/dev/null
mount_dir=$(mktemp -d /tmp/vmcc-disk.XXXXXXXX)
loop_dev=''
cleanup() {
  for path in sys proc dev/pts dev boot/efi ''; do
    if mountpoint -q "$mount_dir/${path}"; then umount "$mount_dir/${path}" || true; fi
  done
  if [ -n "$loop_dev" ]; then losetup -d "$loop_dev" || true; fi
  rmdir "$mount_dir" 2>/dev/null || true
}
trap cleanup EXIT
# noclobber refuses a racing existing file, including symlinks.
(set -C; : > "$disk")
truncate -s 500G "$disk"
sgdisk --clear --new=1:2048:+512M --typecode=1:ef00 --change-name=1:EFI \
  --new=2:0:0 --typecode=2:8300 --change-name=2:Ubuntu "$disk"
loop_dev=$(losetup --find --show --partscan "$disk")
mkfs.vfat -F32 -n EFI "${loop_dev}p1"
mkfs.ext4 -F -L ubuntu-root "${loop_dev}p2"
mount "${loop_dev}p2" "$mount_dir"
mkdir -p "$mount_dir/boot/efi"
mount "${loop_dev}p1" "$mount_dir/boot/efi"
rsync -aHAX --numeric-ids --exclude='/dev/*' --exclude='/proc/*' --exclude='/sys/*' \
  --exclude='/run/*' --exclude='/boot/efi/*' --exclude='/build-*' \
  --exclude='/etc/ssh/ssh_host_*' --exclude='/home/*/.config/sunshine/*' \
  "$rootfs/" "$mount_dir/"
root_uuid=$(blkid -s UUID -o value "${loop_dev}p2")
efi_uuid=$(blkid -s UUID -o value "${loop_dev}p1")
printf 'UUID=%s / ext4 defaults,noatime 0 1\nUUID=%s /boot/efi vfat umask=0077 0 1\n' "$root_uuid" "$efi_uuid" > "$mount_dir/etc/fstab"
: > "$mount_dir/etc/machine-id"
rm -f "$mount_dir/var/lib/dbus/machine-id"
ln -s /etc/machine-id "$mount_dir/var/lib/dbus/machine-id"
mkdir -p "$mount_dir/etc/default/grub.d"
cat > "$mount_dir/etc/default/grub.d/99-vmcc.cfg" <<'EOF'
GRUB_TIMEOUT=2
GRUB_CMDLINE_LINUX_DEFAULT=""
GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"
GRUB_DISABLE_OS_PROBER=true
GRUB_TERMINAL="console serial"
GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"
EOF
mount --bind /dev "$mount_dir/dev"
mount --bind /dev/pts "$mount_dir/dev/pts"
mount -t proc proc "$mount_dir/proc"
mount -t sysfs -o ro sysfs "$mount_dir/sys"
chroot "$mount_dir" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu --removable --no-nvram
for path in "$mount_dir"/boot/vmlinuz-*-generic; do
  release=${path##*/vmlinuz-}
  chroot "$mount_dir" depmod "$release"
  chroot "$mount_dir" update-initramfs -c -k "$release"
done
chroot "$mount_dir" update-grub
chroot "$mount_dir" systemctl enable serial-getty@ttyS0.service
sync
printf 'New disk ready: %s; fresh GPT, partition and filesystem IDs.\n' "$disk"
