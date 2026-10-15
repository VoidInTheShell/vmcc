# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline identity and configuration generator. It never calls qm or SSH."""
import argparse
import hashlib
import ipaddress
import json
import re
import secrets
import shlex
import shutil
import struct
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIOS_SHA = 'bf40f12d7d6cfef81622b87183f5d8e2dee3c22e1d3a59ffb398293fa1975954'

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def cpu_set(value):
    cpus = []
    for group in value.split(','):
        bounds = group.split('-')
        if len(bounds) == 1:
            cpus.append(int(group))
        elif len(bounds) == 2:
            first, last = map(int, bounds)
            if first > last:
                raise ValueError('reversed CPU range')
            cpus.extend(range(first, last + 1))
        else:
            raise ValueError('invalid CPU range')
    if not cpus or min(cpus) < 0 or len(set(cpus)) != len(cpus):
        raise ValueError('CPU lists must be nonnegative and contain no duplicates')
    return cpus

def init(args):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,40}', args.name):
        raise ValueError('name must be a lowercase hostname, maximum 41 characters')
    if not 100 <= args.vmid <= 999999999:
        raise ValueError('VMID outside PVE range')
    interface = ipaddress.IPv4Interface(args.address)
    gateway = ipaddress.IPv4Address(args.gateway)
    if (gateway not in interface.network or gateway == interface.ip or
            interface.ip in (interface.network.network_address, interface.network.broadcast_address) or
            gateway in (interface.network.network_address, interface.network.broadcast_address)):
        raise ValueError('address and gateway must be distinct usable addresses in the same subnet')
    if len(args.timezone) > 100 or '..' in args.timezone or not (Path('/usr/share/zoneinfo') / args.timezone).is_file():
        raise ValueError('unknown timezone')
    out = Path(args.out)
    if out.exists():
        raise FileExistsError('identity directory already exists')
    base = secrets.randbelow(0xFFFFFFFC - 0x10000000) + 0x10000000
    eui = '8ce38e' + secrets.token_hex(5)
    sn = secrets.token_hex(6).upper()
    mac = bytearray(secrets.token_bytes(6)); mac[0] = (mac[0] | 2) & 0xFE
    if args.mac_prefix:
        if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){2}[0-9A-Fa-f]{2}',args.mac_prefix) or int(args.mac_prefix[:2],16)&1:
            raise ValueError('MAC prefix must be a three-byte unicast prefix')
        mac[:3]=bytes.fromhex(args.mac_prefix.replace(':',''))
    manifest = {
        'schema': 1, 'name': args.name, 'vmid': args.vmid,
        'profile': '13900k-z790-ddr4-64g-ht-off',
        'system_uuid': str(uuid.uuid4()),
        'system_serial': 'SYS' + secrets.token_hex(6).upper(),
        'board_serial': '07E07' + secrets.token_hex(6).upper(),
        'chassis_serial': 'DT' + secrets.token_hex(6).upper(),
        'dimm_serials': [f'{base+i:08X}' for i in range(4)],
        'nvme': {'serial': sn, 'eui64': eui,
                 'nguid': '0' * 16 + eui,
                 'namespace_uuid': str(uuid.UUID(hex='0' * 16 + eui)),
                 'nqn': 'nqn.2019-10.com.kioxia:KIOXIA-EXCERIA SSD:' + sn},
        'mac': ':'.join(f'{b:02X}' for b in mac),
        'network': {'address': str(interface), 'gateway': str(gateway), 'dns': str(gateway)},
        'timezone': args.timezone,
        'clone_disk_identity_plan': {'gpt_guid': str(uuid.uuid4()),
                                     'efi_partuuid': str(uuid.uuid4()),
                                     'root_partuuid': str(uuid.uuid4()),
                                     'root_ext4_uuid': str(uuid.uuid4())},
        'clone_reset_required': ['machine-id', 'SSH host keys', 'DHCP DUID/client-id and leases',
                                'NetworkManager connection UUID', 'Sunshine state/certificates/pairings',
                                'EFI variable store', 'disk/partition/filesystem UUIDs if cloned'],
    }
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'identity.json', manifest)
    print(out / 'identity.json')

def validate(m):
    if m.get('schema') != 1 or m.get('profile') != '13900k-z790-ddr4-64g-ht-off':
        raise ValueError('unsupported identity schema/profile')
    uuid.UUID(m['system_uuid'])
    for key in ('name','system_serial','board_serial','chassis_serial'):
        if not re.fullmatch(r'[A-Za-z0-9-]{1,64}', m[key]):
            raise ValueError('unsafe identity string: ' + key)
    serials = m['dimm_serials']
    if len(serials) != 4 or any(not re.fullmatch(r'[0-9A-F]{8}', x) for x in serials):
        raise ValueError('expected four eight-digit DIMM serials')
    if [int(x,16) for x in serials] != list(range(int(serials[0],16), int(serials[0],16)+4)):
        raise ValueError('DIMM serials must be consecutive')
    nv = m['nvme']
    if not re.fullmatch(r'[A-Z0-9]{1,20}', nv['serial']):
        raise ValueError('invalid NVMe serial')
    if not re.fullmatch(r'[0-9a-f]{16}', nv['eui64']) or nv['nguid'] != '0'*16 + nv['eui64']:
        raise ValueError('NVMe identity mismatch')
    if uuid.UUID(nv['namespace_uuid']).hex != nv['nguid']:
        raise ValueError('namespace UUID and NGUID differ')
    if nv['nqn'] != 'nqn.2019-10.com.kioxia:KIOXIA-EXCERIA SSD:' + nv['serial']:
        raise ValueError('NQN and serial differ')
    if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',m['mac']) or int(m['mac'][:2],16) & 1:
        raise ValueError('expected a unicast MAC')

def set_smbios_string(b, offset, value):
    data = bytearray(b)
    strings = bytes(data[data[1]:]).rstrip(b'\0').split(b'\0')
    index = data[offset]
    if not 1 <= index <= len(strings):
        raise ValueError('bad SMBIOS string index')
    strings[index-1] = value.encode('ascii')
    return bytes(data[:data[1]]) + b'\0'.join(strings) + b'\0\0'

def render(args):
    manifest_path = Path(args.identity).resolve()
    m = json.loads(manifest_path.read_text()); validate(m)
    out = Path(args.out).resolve()
    if out.exists():
        raise ValueError('output already exists; use a new directory')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.bridge) or not re.fullmatch(r'[A-Za-z0-9_-]+', args.efi_storage):
        raise ValueError('invalid bridge/storage name')
    if not re.fullmatch(r'[A-Za-z0-9_-]+:[A-Za-z0-9_./-]+', args.disk) or '..' in args.disk:
        raise ValueError('invalid managed PVE disk volume')
    if not re.fullmatch(r'(?:[0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}',args.gpu):
        raise ValueError('GPU must be a whole-slot BDF, e.g. 0000:82:00')
    vcpus, io = cpu_set(args.vcpu_cpus), cpu_set(args.io_cpus)
    if len(vcpus) != 24 or set(vcpus) & set(io):
        raise ValueError('24 vCPU CPUs and disjoint I/O CPUs are required')
    prefix = Path(args.prefix)
    if not prefix.is_absolute() or not re.fullmatch(r'/[A-Za-z0-9_/-]+',str(prefix)) or '..' in str(prefix):
        raise ValueError('prefix must be a safe absolute path')
    bios = Path(args.bios)
    if not bios.is_absolute() or not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(bios)) or '..' in str(bios):
        raise ValueError('BIOS path must be an absolute path without whitespace')
    if args.audio_backend != 'none' and not re.fullmatch(r'[A-Za-z0-9_:.,-]+',args.audio_backend):
        raise ValueError('invalid ALSA backend')
    out.mkdir(parents=True)
    platform = out / 'platform'
    shutil.copytree(ROOT/'templates/platform', platform)
    for p in platform.rglob('*.bin'):
        b = p.read_bytes()
        if b[0] == 2:
            b = set_smbios_string(b,7,m['board_serial'])
        elif b[0] == 17:
            dimm = int(re.search(r'dimm([0-3])',p.name)[1])
            b = set_smbios_string(b,24,m['dimm_serials'][dimm])
        p.write_bytes(b)
    spd = bytearray((ROOT/'templates/spd-template.bin').read_bytes())
    for i, serial in enumerate(m['dimm_serials']):
        spd[i*512+325:i*512+329] = bytes.fromhex(serial)
    (out/'spd.bin').write_bytes(spd)
    instance = str(prefix / 'instances' / str(m['vmid']))
    audio = ('none,id=alc4080' if args.audio_backend == 'none' else
             'alsa,id=alc4080,out.dev='+args.audio_backend.replace(',',',,')+
             ',in.dev='+args.audio_backend.replace(',',',,')+
             ',out.frequency=48000,out.channels=8,out.format=s16,in.frequency=48000,in.channels=2,in.format=s16')
    substitutions = {'@INSTANCE@':instance,'@BOARD_SERIAL@':m['system_serial'],
                     '@CHASSIS_SERIAL@':m['chassis_serial'],'@AUDIODEV@':audio}
    qargs = []
    for item in json.loads((ROOT/'templates/qemu-args.json').read_text()):
        for a,b in substitutions.items(): item=item.replace(a,b)
        item=item.replace(instance+'/platform/@BIOS_NAME@',str(bios))
        if '@' in item: raise ValueError('unresolved placeholder: '+item)
        qargs.append(item)
    common = ['--bios','ovmf','--machine','q35','--cores','24','--sockets','1','--memory','65536',
              '--cpu','host','--balloon','0','--tablet','0','--hotplug','0','--numa','0',
              '--vga','none','--serial0','socket','--vmgenid','0','--ostype','l26','--localtime','0',
              '--affinity',','.join(map(str,vcpus)), '--onboot','1','--startup','order=2,up=20',
              '--name',m['name'],'--boot','order=sata0',
              '--efidisk0',args.efi_storage+':1,efitype=4m,pre-enrolled-keys=0',
              '--hostpci0',args.gpu+',pcie=1,x-vga=1',
              '--net0','e1000='+m['mac']+',bridge='+args.bridge,
              '--smbios1','uuid='+m['system_uuid'],
              '--sata0',args.disk+',cache=directsync,discard=on,ssd=1,serial='+m['nvme']['serial'],
              '--args',shlex.join(qargs)]
    commands = [['qm','create',str(m['vmid']),*common]]
    (out/'create-vm.sh').write_text('#!/bin/sh\nset -eu\n# Creates a new VM, never starts it. Storage/GPU preflight is required.\n'+
                                  '\n'.join(shlex.join(x) for x in commands)+'\n')
    runtime = {'schema':1,'vmid':m['vmid'],'name':m['name'],'instance_dir':instance,
               'qemu':str(prefix/'runtime/qemu-system-x86_64'),
               'libdir':str(prefix/'runtime/lib'),'firmware':str(prefix/'runtime/OVMF_CODE_RPL_4M.fd'),
               'q35_config':instance+'/platform/ubuntu-q35.cfg','spd_file':instance+'/spd.bin',
               'nvme':m['nvme'],'vcpu_cpus':vcpus,'io_cpus':io,
               'bios_file':str(bios),'bios_sha256':BIOS_SHA,
               'disk_volume':args.disk,'bridge':args.bridge,'gpu_bdf':args.gpu,
               'audio_backend':args.audio_backend,
               'network':m['network'],'timezone':m['timezone']}
    dump(out/'runtime.json',runtime); dump(out/'identity.json',m); dump(out/'qemu-args.json',qargs)
    dump(out/'clone-reset-plan.json',{'required':m['clone_reset_required'],'disk_identity':m['clone_disk_identity_plan'],
                                    'automatic_disk_rewrite':False,
                                    'reason':'Disk/partition/filesystem changes require offline boot-reference updates and a clone boot test.'})
    sums=[]
    for p in sorted(out.rglob('*')):
        if p.is_file(): sums.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out)))
    (out/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
    print(out)

def audit(args):
    manifests=[json.loads(Path(p).read_text()) for p in args.identities]
    seen={}
    for m in manifests:
        validate(m)
        fields={k:m[k] for k in ['vmid','name','system_uuid','system_serial','board_serial','chassis_serial','mac']}
        fields.update({'nvme.'+k:v for k,v in m['nvme'].items()})
        fields['network.address']=m['network']['address'].split('/')[0]
        fields.update({'disk.'+k:v for k,v in m['clone_disk_identity_plan'].items()})
        for k,v in fields.items():
            pair=(k,str(v))
            if pair in seen: raise ValueError(f'duplicate {k} in {seen[pair]} and {m["name"]}')
            seen[pair]=m['name']
        for v in m['dimm_serials']:
            pair=('dimm_serial',v)
            if pair in seen: raise ValueError('duplicate DIMM serial across machines')
            seen[pair]=m['name']
    print(json.dumps({'identities':len(manifests),'status':'PASS','scope':'provided manifests only'}))

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('init');a.add_argument('--name',required=True);a.add_argument('--vmid',required=True,type=int)
    a.add_argument('--address',required=True);a.add_argument('--gateway',required=True)
    a.add_argument('--timezone',default='America/New_York');a.add_argument('--out',required=True);a.set_defaults(func=init)
    a.add_argument('--mac-prefix',help='optional assigned three-byte OUI, e.g. D8:FC:93; default is locally administered')
    a=sub.add_parser('render');a.add_argument('--identity',required=True);a.add_argument('--out',required=True)
    a.add_argument('--disk',required=True);a.add_argument('--efi-storage',required=True);a.add_argument('--bridge',required=True)
    a.add_argument('--gpu',required=True);a.add_argument('--bios',required=True);a.add_argument('--audio-backend',default='none')
    a.add_argument('--vcpu-cpus',required=True);a.add_argument('--io-cpus',required=True);a.add_argument('--prefix',default='/opt/vmcc')
    a.set_defaults(func=render)
    a=sub.add_parser('audit');a.add_argument('identities',nargs='+');a.set_defaults(func=audit)
    args=p.parse_args()
    try: args.func(args)
    except (ValueError,KeyError,FileExistsError,FileNotFoundError) as e:p.exit(2,'vmcc: '+str(e)+'\n')
