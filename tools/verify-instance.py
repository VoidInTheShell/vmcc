#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Collect over SSH stdin and compare a new instance to actual baseline + identity."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from vmcc import validate,dump

COLLECTOR=Path(__file__).with_name('collect-guest.py')


def assess(actual, baseline, m):
    checks={}
    def check(name,condition):checks[name]=bool(condition)
    check('CPU 24 threads, 8P+16E',len(actual['cpu'])==24 and
          sum(x['hybrid_type']==0x40 for x in actual['cpu'])==8 and
          sum(x['hybrid_type']==0x20 for x in actual['cpu'])==16)
    check('CPU feature leaves match baseline',[x['leaf7'] for x in actual['cpu']]==[x['leaf7'] for x in baseline['cpu']])
    check('PCI devices, BDFs and native drivers match baseline',actual['pci']==baseline['pci'])
    check('SMBIOS types, handles and contents match baseline',actual['smbios']==baseline['smbios'])
    check('Four consecutive DIMM serials',actual['dimm_serials']==m['dimm_serials'])
    check('ACPI OEM tables and static content match baseline',actual['acpi']==baseline['acpi'] and
          all(t['checksum_valid'] for t in actual['acpi'].values()))
    for key in ('sys_vendor','product_name','product_version','board_vendor','board_name','board_version','bios_vendor','bios_version','bios_date'):
        check('DMI '+key,actual['dmi'][key]==baseline['dmi'][key])
    for field,key in [('product_uuid','system_uuid'),('product_serial','system_serial'),('board_serial','board_serial'),('chassis_serial','chassis_serial')]:
        check('Unique '+field,actual['dmi'][field].lower()==m[key].lower() and actual['dmi'][field]!=baseline['dmi'][field])
    check('Generic kernel matches baseline',actual['kernel_sha256']==baseline['kernel_sha256'] and 'builder@build' in actual['version'])
    check('Desktop boot command line','console=ttyS' not in actual['cmdline'] and 'emu' not in actual['cmdline'])
    check('64 GiB memory matches baseline',abs(actual['memtotal_kib']-baseline['memtotal_kib'])<65536)
    check('Physical RTX3080 driver matches baseline',actual['nvidia']==baseline['nvidia'] and actual['nvidia']['code']==0)
    check('NVMe model/firmware and unique serial',len(actual['nvme'])==1 and actual['nvme'][0]['serial']==m['nvme']['serial'] and
          all(actual['nvme'][0][key]==baseline['nvme'][0][key] for key in ('model','firmware_rev')))
    account=m.get('account',{'username':'user','uid':1000})
    check('Only configured desktop account',actual['accounts']==[{'name':account['username'],'uid':account['uid'],'home':'/home/'+account['username']}])
    check('Hostname and timezone',actual['hostname']==m['name'] and actual['timezone']==m['timezone'])
    check('Fresh machine-id',len(actual['machine_id'])==32 and actual['machine_id']!=baseline['machine_id'])
    check('Fresh SSH host keys',len(actual['ssh_public_hashes'])>=3 and not set(actual['ssh_public_hashes'])&set(baseline['ssh_public_hashes']))
    check('No engineering residues',not actual['residues'])
    check('No CI runner environment',not any(x in actual['environment'] for x in ('ACT_','RUNNER_','IMAGE_OS','acttoolcache','DEPLOYMENT_BASEPATH')))
    check('Desktop, SSH and ROM services active',all(x['code']==0 for x in actual['units'].values()))
    sunshine=actual['sunshine'].get(account['username'],{})
    check('Sunshine enabled and listening on IPv4 any',sunshine.get('active') and sunshine.get('linger') and
          'bind_address = 0.0.0.0' in sunshine.get('config','') and
          all('0.0.0.0:'+str(port) in actual['listeners']['stdout'] for port in (47984,47989,47990,48010)))
    net=json.loads(actual['network']['stdout'])
    check('Unique MAC and static IPv4',any(x.get('address','').lower()==m['mac'].lower() and
          any(a.get('local')==m['network']['address'].split('/')[0] for a in x.get('addr_info',[])) for x in net))
    routes=json.loads(actual['routes']['stdout'])
    check('PortalWrt default gateway',any(x.get('dst')=='default' and x.get('gateway')==m['network']['gateway'] for x in routes))
    layout=m['clone_disk_identity_plan'];disks=json.loads(actual['disks']['stdout'])['blockdevices']
    nodes=[]
    def visit(rows):
        for row in rows:nodes.append(row);visit(row.get('children',[]))
    visit(disks)
    check('Planned disk and filesystem identities',any(x.get('ptuuid')==layout['gpt_guid'] for x in nodes) and
          any(x.get('uuid')==layout['root_ext4_uuid'] and x.get('partuuid')==layout['root_partuuid'] for x in nodes) and
          any(x.get('partuuid')==layout['efi_partuuid'] for x in nodes))
    return {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
            'known_limits':{'cpufreq_present':actual['cpufreq_present'],
                'Sunshine HID':'preserved as requested','hypervisor_bit':'preserved as configured',
                'SPD_decode_dimms':'paused by user','Moonlight_streaming':'NOT RUN'},
            'scope':'hardware/configuration parity with current baseline and clean instance state; not proof of indistinguishability'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',required=True);p.add_argument('--ssh-option',action='append',default=[])
    p.add_argument('--out',required=True);p.add_argument('--baseline');p.add_argument('--identity')
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('output already exists')
    out.mkdir(parents=True,mode=0o700)
    cmd=['ssh']
    for option in a.ssh_option:cmd+=['-o',option]
    cmd+=[a.target,'sudo -n python3 -']
    result=subprocess.run(cmd,input=COLLECTOR.read_text(),text=True,capture_output=True)
    (out/'collect.stderr').write_text(result.stderr)
    if result.returncode:raise RuntimeError('guest collection failed: '+result.stderr)
    actual=json.loads(result.stdout);dump(out/'actual.json',actual)
    if a.baseline:
        if not a.identity:raise ValueError('--identity required for comparison')
        m=json.loads(Path(a.identity).read_text());validate(m)
        report=assess(actual,json.loads(Path(a.baseline).read_text()),m)
        dump(out/'acceptance.json',report);print(json.dumps(report,indent=2))
        if report['status']!='PASS':sys.exit(1)
    else:print('Baseline collected: '+str(out/'actual.json'))


if __name__=='__main__':main()
