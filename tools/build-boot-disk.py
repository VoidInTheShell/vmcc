#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a fresh 500 GiB regular image from a prepared OFFLINE rootfs and identity."""
import argparse
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

from vmcc import validate

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare-guest.py'))
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)


def run(*args):
    subprocess.run(list(map(str, args)), check=True)


def output_path(value):
    path = Path(value).absolute()
    if path.exists() or path.is_symlink():
        raise ValueError('output already exists; refusing to overwrite')
    parent = path.parent.resolve(strict=True)
    if any(parent == Path(x) or parent.is_relative_to(x) for x in ('/dev', '/proc', '/sys')):
        raise ValueError('a new regular image file is required')
    return parent/path.name


def build(root, disk, m):
    layout = m['clone_disk_identity_plan']
    fd = os.open(disk, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.ftruncate(fd, 500 * 1024**3)
    finally:
        os.close(fd)
    loop = ''
    # A failed build leaves its image for inspection; source media is never overwritten.
    run('sgdisk', '--clear', '--disk-guid='+layout['gpt_guid'],
        '--new=1:2048:+512M', '--typecode=1:ef00', '--change-name=1:EFI',
        '--partition-guid=1:'+layout['efi_partuuid'], '--new=2:0:0', '--typecode=2:8300',
        '--change-name=2:Ubuntu', '--partition-guid=2:'+layout['root_partuuid'], disk)
    loop = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(disk)], text=True).strip()
    mounts = []
    with tempfile.TemporaryDirectory(prefix='vmcc-image-') as directory:
        target = Path(directory)
        try:
            run('mkfs.vfat', '-F32', '-n', 'EFI', '-i', layout['efi_fat_id'], loop+'p1')
            run('mkfs.ext4', '-F', '-L', 'ubuntu-root', '-U', layout['root_ext4_uuid'], loop+'p2')
            run('mount', loop+'p2', target); mounts.append(target)
            (target/'boot/efi').mkdir(parents=True, exist_ok=True)
            run('mount', loop+'p1', target/'boot/efi'); mounts.append(target/'boot/efi')
            run('rsync', '-aHAX', '--numeric-ids', '--exclude=/dev/*', '--exclude=/proc/*',
                '--exclude=/sys/*', '--exclude=/run/*', '--exclude=/boot/efi/*', str(root)+'/', str(target)+'/')
            efi = layout['efi_fat_id']; efi_uuid = efi[:4]+'-'+efi[4:]
            prepare.write(target, 'etc/fstab', 'UUID='+layout['root_ext4_uuid']+' / ext4 defaults,noatime 0 1\nUUID='+efi_uuid+' /boot/efi vfat umask=0077 0 1\n')
            for path in ('dev', 'dev/pts', 'proc', 'sys'):
                (target/path).mkdir(parents=True, exist_ok=True)
                if path in ('dev', 'dev/pts'):
                    run('mount', '--bind', '/'+path, target/path)
                else:
                    fs_type='sysfs' if path=='sys' else 'proc'
                    run('mount', '-t', fs_type, '-o', 'ro', fs_type, target/path)
                mounts.append(target/path)
            prepare.run(target, 'grub-install', '--target=x86_64-efi', '--efi-directory=/boot/efi',
                        '--bootloader-id=ubuntu', '--removable', '--no-nvram')
            for kernel in sorted((target/'boot').glob('vmlinuz-*-generic')):
                release = kernel.name.removeprefix('vmlinuz-')
                prepare.run(target, 'depmod', release)
                action = '-u' if (target/'boot'/('initrd.img-'+release)).exists() else '-c'
                prepare.run(target, 'update-initramfs', action, '-k', release)
            prepare.run(target, 'update-grub')
            for path in (target/'var/log').iterdir():
                prepare.remove(path)
            run('sync')
        finally:
            errors = []
            for mount in reversed(mounts):
                result = subprocess.run(['umount', str(mount)])
                if result.returncode:
                    errors.append(str(mount))
            if not errors:
                run('losetup', '-d', loop)
            else:
                raise RuntimeError('image mounts remain; inspect: '+', '.join(errors))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rootfs'); p.add_argument('new_disk'); p.add_argument('identity')
    a = p.parse_args()
    if os.geteuid() != 0:
        raise ValueError('root required')
    root = prepare.safe_root(a.rootfs); disk = output_path(a.new_disk)
    m = json.loads(Path(a.identity).read_text()); validate(m)
    if 'efi_fat_id' not in m['clone_disk_identity_plan']:
        raise ValueError('identity lacks FAT ID; generate with the current factory')
    if disk.is_relative_to(root):
        raise ValueError('output cannot be inside input rootfs')
    build(root, disk, m)
    print(json.dumps({'image': str(disk), 'size_gib': 500, 'disk_identity': m['clone_disk_identity_plan']}))


if __name__ == '__main__':
    main()
