#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Create a tiny diskless test initramfs from a static BusyBox and guest modules."""
import argparse,gzip,stat,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--busybox',required=True);p.add_argument('--modules',required=True);p.add_argument('--out',required=True);a=p.parse_args()
init=b'''#!/bin/busybox sh
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
echo VMCC_IDENTITY_SMOKE_BEGIN
modprobe i2c-i801
modprobe ee1004
sleep 1
for p in /sys/bus/i2c/devices/*-005?/eeprom; do
 echo SPD_FILE=$p
 dd if="$p" bs=1 skip=325 count=4 2>/dev/null | od -An -tx1
 sha256sum "$p"
done
for p in /sys/class/dmi/id/product_uuid /sys/class/dmi/id/product_serial /sys/class/dmi/id/board_serial /sys/class/dmi/id/chassis_serial; do echo "$p"; cat "$p"; done
cat /sys/devices/system/cpu/online
echo VMCC_IDENTITY_SMOKE_END
poweroff -f
'''
entries=[('bin/busybox',stat.S_IFREG|0o755,Path(a.busybox).read_bytes()),('init',stat.S_IFREG|0o755,init)]
mods=Path(a.modules)
for f in mods.rglob('*'):
 if not f.is_file() or f.is_symlink():continue
 if f.name.startswith('modules.') or f.name.startswith(('i2c-i801.ko','ee1004.ko','i2c-smbus.ko')):
  entries.append(('lib/modules/'+mods.name+'/'+str(f.relative_to(mods)),stat.S_IFREG|0o644,f.read_bytes()))
parents={str(p) for name,_,_ in entries for p in Path(name).parents if str(p)!='.'}|{'dev','proc','sys','tmp'}
entries=[(n,stat.S_IFDIR|0o755,b'') for n in sorted(parents,key=lambda x:(x.count('/'),x))]+entries
buf=bytearray()
for inode,(name,mode,data) in enumerate(entries+[('TRAILER!!!',0,b'')],1):
 fields=[inode,mode,0,0,1,int(time.time()),len(data),0,0,0,0,len(name)+1,0]
 buf.extend(b'070701'+''.join(f'{n:08x}' for n in fields).encode());buf.extend(name.encode()+b'\0');buf.extend(b'\0'*(-len(buf)%4));buf.extend(data);buf.extend(b'\0'*(-len(buf)%4))
Path(a.out).write_bytes(gzip.compress(buf,compresslevel=1))
