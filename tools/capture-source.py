#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Copy runtime files from a STOPPED source VM using a read-only, no-replay mount."""
import argparse
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare-guest.py'))
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vmid',type=int,required=True);p.add_argument('--out',required=True)
    p.add_argument('--disk',default='sata0');p.add_argument('--shutdown',action='store_true')
    a=p.parse_args()
    if os.geteuid()!=0 or not 100<=a.vmid<=999999999:
        raise ValueError('run as root on PVE with a valid source VMID')
    dest=Path(a.out).absolute()
    if dest.exists() or dest.is_symlink():raise ValueError('capture output already exists')
    conf=dict(line.split(': ',1) for line in subprocess.check_output(['qm','config',str(a.vmid)],text=True).splitlines() if ': ' in line)
    volume=conf[a.disk].split(',')[0]
    if ':' not in volume:raise ValueError('managed PVE disk required')
    status=lambda: subprocess.check_output(['qm','status',str(a.vmid)],text=True).strip()
    if status()!='status: stopped':
        if not a.shutdown:raise ValueError('stop source VM or explicitly use --shutdown')
        subprocess.run(['qm','shutdown',str(a.vmid),'--timeout','120'],check=True)
    if status()!='status: stopped':raise ValueError('source did not stop; refusing live filesystem copy')
    source=subprocess.check_output(['pvesm','path',volume],text=True).strip()
    loop=subprocess.check_output(['losetup','--find','--show','--read-only','--partscan',source],text=True).strip()
    mounted=False
    with tempfile.TemporaryDirectory(prefix='vmcc-source-') as mount:
        try:
            subprocess.run(['mount','-o','ro,noload',loop+'p2',mount],check=True);mounted=True
            prepare.safe_root(mount)
            dest.mkdir(parents=True,mode=0o700,exist_ok=False)
            subprocess.run(['rsync','-aHAX','--numeric-ids',
                            *['--exclude='+x for x in prepare.EXCLUDES],mount+'/',str(dest)+'/'],check=True)
        finally:
            if mounted:subprocess.run(['umount',mount],check=True)
            subprocess.run(['losetup','-d',loop],check=True)
    # Receipt is a sibling, never inserted in the guest filesystem.
    dest.with_name(dest.name+'.capture.json').write_text(json.dumps({'source_vmid':a.vmid,
        'source_volume':volume,'source_stopped':True,'mount_options':'ro,noload',
        'excluded':prepare.EXCLUDES},indent=2)+'\n')
    print(dest)


if __name__=='__main__':main()
