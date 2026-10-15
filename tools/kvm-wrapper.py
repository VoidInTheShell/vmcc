#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Route registered VMIDs; all others chain to the preserved PVE launcher."""
import json
import os
import sys
from pathlib import Path

REGISTRY = Path('/etc/vmcc/instances')
FALLBACK = '/usr/bin/kvm.vmcc-original'

def transform(argv, config):
    result=[];i=0
    nv=config['nvme']
    while i<len(argv):
        key=argv[i]
        if i+1<len(argv) and key in ('-id','-iscsi'):
            i+=2;continue
        if i+1<len(argv) and key in ('-device','-readconfig','-machine','-blockdev'):
            value=argv[i+1]
            if key=='-readconfig' and value.startswith('/usr/share/qemu-server/pve-q35'):
                value=config['q35_config']
            elif key=='-machine':
                value=value.replace('q35+pve0','q35')+',smbios-entry-point-type=64'
            elif key=='-blockdev':
                obj=json.loads(value)
                if obj.get('node-name')=='pflash0':obj['file']['filename']=config['firmware']
                value=json.dumps(obj,separators=(',',':'))
            elif key=='-device':
                if value.startswith('ahci,') and 'id=ahci0' in value:
                    i+=2;continue
                if value.startswith('ide-hd,') and 'id=sata0' in value:
                    result += ['-device','nvme,id=nvme0,serial='+nv['serial']+',bus=ich9-pcie-port-2,addr=0x0',
                               '-device','nvme-ns,id=sata0,drive=drive-sata0,bus=nvme0,nsid=1,bootindex=100,nguid='+nv['nguid']+
                               ',eui64=0x'+nv['eui64']+',uuid='+nv['namespace_uuid']]
                    i+=2;continue
                if value.startswith('e1000,') and 'id=net0' in value:
                    parts=value.split(',');parts[0]='i225-v'
                    value=','.join(p for p in parts if not p.startswith(('bus=','addr=')))+',bus=ich9-pcie-port-10,addr=0x0'
                value=value.replace('bus=pci.0,','bus=pcie.0,')
            result += [key,value];i+=2;continue
        result.append(key);i+=1
    return result+['-L','/usr/share/kvm']

def main():
    argv=sys.argv[1:]
    ids=[argv[i+1] for i in range(len(argv)-1) if argv[i]=='-id']
    path=REGISTRY/(ids[0]+'.json') if len(ids)==1 and ids[0].isdigit() else None
    if path is None or not path.is_file():os.execv(FALLBACK,['kvm']+argv)
    config=json.loads(path.read_text())
    if int(ids[0])!=config['vmid']:raise RuntimeError('VMID registry mismatch')
    spd=Path(config['spd_file'])
    if spd.stat().st_size!=2048:raise RuntimeError('missing/invalid per-instance SPD')
    os.environ['VMCC_SPD_FILE']=str(spd)
    os.environ['LD_LIBRARY_PATH']=config['libdir']
    os.execv(config['qemu'],['kvm']+transform(argv,config))

if __name__=='__main__':main()
