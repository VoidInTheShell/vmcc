#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Restore a disabled ROM BAR to its kernel-assigned resource, never enable ROM."""
import argparse
import json
import os
import struct
from pathlib import Path


def assigned_rom(resource):
    rows = resource.splitlines()
    if len(rows) <= 6:
        raise ValueError('missing ROM resource')
    start, end, flags = (int(x, 16) for x in rows[6].split())
    if not (0 < start <= end < 2**32) or start & 0x7ff or not flags & 0x200:
        raise ValueError('ROM has no aligned, assigned 32-bit memory resource')
    size = end - start + 1
    if size & (size - 1) or size < 2048:
        raise ValueError('unexpected ROM resource size')
    return start


def restore(device, apply=False):
    device = Path(device)
    if device.joinpath('vendor').read_text().strip() != '0x10de':
        raise ValueError('only the NVIDIA display-device quirk is supported')
    if int(device.joinpath('class').read_text().strip(), 16) >> 16 != 3:
        raise ValueError('not a display device')
    base = assigned_rom(device.joinpath('resource').read_text())
    fd = os.open(device / 'config', os.O_RDWR if apply else os.O_RDONLY)
    try:
        value = struct.unpack('<I', os.pread(fd, 4, 0x30))[0]
        if value not in (0, base):
            raise ValueError('ROM BAR is active or differs from assigned resource; refusing to overwrite')
        if apply and value == 0:
            os.pwrite(fd, struct.pack('<I', base), 0x30)
            if struct.unpack('<I', os.pread(fd, 4, 0x30))[0] != base:
                raise RuntimeError('ROM BAR readback failed')
        return {'device': device.name, 'before': hex(value), 'assigned': hex(base),
                'applied': bool(apply and value == 0), 'rom_decode_enabled': False}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    for device in Path('/sys/bus/pci/devices').iterdir():
        if (device.joinpath('vendor').read_text().strip() == '0x10de' and
                int(device.joinpath('class').read_text().strip(), 16) >> 16 == 3):
            print(json.dumps(restore(device, args.apply)))


if __name__ == '__main__':
    main()
