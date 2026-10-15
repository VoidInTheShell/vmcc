#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Plan/apply a parameterized batch on PVE. Plan is offline; apply creates new resources."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import vmcc

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare',REPO/'tools/prepare-guest.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


def run(*args):
    subprocess.run(list(map(str,args)),check=True)


def normalize(s):
    if s.get('schema')!=1 or not s.get('instances'):raise ValueError('expected schema 1 and nonempty instances')
    for key in ('source_rootfs','runtime','bios'):
        if not Path(s[key]).is_absolute():raise ValueError(key+' must be an absolute host path')
    for key in ('storage','efi_storage','bridge'):
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s[key]):raise ValueError('invalid '+key)
    seen={key:set() for key in ('vmid','name','address','gpu')}
    for i in s['instances']:
        required=('vmid','name','address','gateway','gpu','vcpu_cpus','io_cpus')
        if any(key not in i for key in required):raise ValueError('incomplete instance')
        if not re.fullmatch(r'(?:[0-9a-f]{4}:)?[0-9a-f]{2}:[0-9a-f]{2}',i['gpu']):raise ValueError('invalid GPU slot')
        i['gpu']=i['gpu'] if i['gpu'].count(':')==2 else '0000:'+i['gpu']
        if i.get('onboot',0) not in (0,1):raise ValueError('onboot must be 0 or 1')
        if len(vmcc.cpu_set(i['vcpu_cpus']))!=24 or set(vmcc.cpu_set(i['vcpu_cpus']))&set(vmcc.cpu_set(i['io_cpus'])):
            raise ValueError('24 vCPU CPUs and disjoint I/O CPUs required')
        for key in seen:
            value=i[key].split('/')[0] if key=='address' else i[key]
            if value in seen[key]:raise ValueError('duplicate '+key+' in batch; use one GPU per simultaneously deployable machine')
            seen[key].add(value)
    return s


def plan(a):
    s=normalize(json.loads(Path(a.spec).read_text()))
    out=Path(a.out).resolve()
    if out.exists():raise ValueError('plan output already exists')
    # Validate every identity and render argument in a temporary plan before publishing it.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='vmcc-plan-',dir=out.parent) as temporary:
        stage=Path(temporary)
        for i in s['instances']:
            node=stage/str(i['vmid'])
            vmcc.init(SimpleNamespace(name=i['name'],vmid=i['vmid'],address=i['address'],gateway=i['gateway'],
                timezone=i.get('timezone','America/New_York'),username=i.get('username','user'),uid=i.get('uid',1000),
                mac_prefix=i.get('mac_prefix'),out=str(node)))
            vmcc.render(SimpleNamespace(identity=str(node/'identity.json'),out=str(node/'bundle'),
                disk=f"{s['storage']}:vm-{i['vmid']}-disk-1",efi_storage=s['efi_storage'],bridge=s['bridge'],
                gpu=i['gpu'],bios=s['bios'],audio_backend=i.get('audio_backend','none'),vcpu_cpus=i['vcpu_cpus'],
                io_cpus=i['io_cpus'],prefix='/opt/vmcc',onboot=i.get('onboot',0)))
        vmcc.audit(SimpleNamespace(identities=[str(stage/str(i['vmid'])/'identity.json') for i in s['instances']]))
        vmcc.dump(stage/'spec.json',s)
        sums={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in stage.rglob('*') if p.is_file()}
        vmcc.dump(stage/'plan-sha256.json',sums)
        shutil.copytree(stage,out)
    print('Plan ready: '+str(out)+'; no PVE resources changed.')


def check_plan(directory):
    sums=json.loads((directory/'plan-sha256.json').read_text())
    for relative,digest in sums.items():
        path=(directory/relative).resolve()
        if not path.is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('plan modified after review: '+relative)
    return normalize(json.loads((directory/'spec.json').read_text()))


def preflight(s,a):
    if os.geteuid()!=0:raise ValueError('apply/preflight requires root on PVE')
    prepare.safe_root(s['source_rootfs'])
    if not Path(s['runtime'],'qemu-system-x86_64').is_file():raise ValueError('runtime missing')
    if hashlib.sha256(Path(s['bios']).read_bytes()).hexdigest()!=vmcc.BIOS_SHA:raise ValueError('BIOS checksum mismatch')
    if not Path('/sys/class/net',s['bridge'],'bridge').exists():raise ValueError('bridge missing')
    configs=list(Path('/etc/pve/qemu-server').glob('*.conf'))
    for i in s['instances']:
        vmid=i['vmid']
        if Path(f'/etc/pve/qemu-server/{vmid}.conf').exists():raise ValueError('VMID already exists: '+str(vmid))
        if Path(f'/etc/vmcc/instances/{vmid}.json').exists() or Path(f'/opt/vmcc/instances/{vmid}').exists():
            raise ValueError('instance already registered: '+str(vmid))
        cpus=set(vmcc.cpu_set(i['vcpu_cpus']))|set(vmcc.cpu_set(i['io_cpus']))
        if not cpus<=os.sched_getaffinity(0):raise ValueError('CPU affinity unavailable')
        for fn in ('.0','.1'):
            dev=Path('/sys/bus/pci/devices',i['gpu']+fn)
            if not dev.is_dir() or (dev/'driver').resolve().name!='vfio-pci':raise ValueError('GPU not vfio-bound')
        for conf in configs:
            text=conf.read_text()
            if f'vm-{vmid}-disk-' in text:raise ValueError('disk name already referenced')
            if any(line.startswith('hostpci') and i['gpu'].removeprefix('0000:') in line for line in text.splitlines()):
                stopped=subprocess.check_output(['qm','status',conf.stem],text=True).strip()=='status: stopped'
                if not a.allow_stopped_gpu_sharing or i.get('onboot',0) or not stopped:
                    raise ValueError('GPU belongs to another VM; stop it and explicitly allow sequential sharing with onboot=0')
        # Probe addresses from PVE's routed LAN. A reply is a collision; no reply is not a guarantee.
        probe=subprocess.run(['ping','-c','2','-W','1',i['address'].split('/')[0]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if probe.returncode==0:raise ValueError('address responds; refusing potential collision: '+i['address'])
    status=subprocess.check_output(['pvesm','status'],text=True).splitlines()
    pools={}
    for row in status[1:]:
        fields=row.split()
        if len(fields)>=6:pools[fields[0]]={'type':fields[1],'active':fields[2]=='active','avail':int(fields[5])*1024}
    for pool in (s['storage'],s['efi_storage']):
        if pool not in pools or not pools[pool]['active']:raise ValueError('storage inactive: '+pool)
    if pools[s['storage']]['type']!='lvmthin':raise ValueError('factory disk allocation currently requires PVE lvmthin storage')
    if pools[s['storage']]['avail'] < len(s['instances'])*500*1024**3:
        raise ValueError('less than 500 GiB physical free space per requested instance')
    print('Host preflight passed. IP probe is best effort; ensure the subnet is reserved.')


def apply(a):
    directory=Path(a.plan).resolve();s=check_plan(directory)
    preflight(s,a)
    if not a.apply:return
    secret=Path(a.password_file).resolve(strict=True)
    if secret.stat().st_mode&0o077:raise ValueError('password file must be 0600 or stricter')
    receipt=directory/'apply-state.json'
    if receipt.exists():
        previous=json.loads(receipt.read_text())
        safe=(previous['status']=='FAILED' and all(x['phase'] in ('COPYING','BUILDING') and
              'disk_volume' not in x for x in previous['instances'].values()))
        if not a.retry_before_allocation or not safe:
            raise ValueError('batch already attempted; inspect receipt. Only pre-allocation failures support explicit retry.')
        for vmid in previous['instances']:
            node=directory/vmid
            if (node/'rootfs').is_symlink() or (node/'system.raw').is_symlink():raise ValueError('unexpected staging symlink')
            if (node/'rootfs').exists():shutil.rmtree(node/'rootfs')
            if (node/'system.raw').exists():(node/'system.raw').unlink()
        vmcc.dump(directory/'previous-preallocation-failure.json',previous)
    state={'status':'RUNNING','instances':{},'tool_sha256':{
        str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (REPO/'tools').glob('*.py')},
        'runtime_sha256':hashlib.sha256(Path(s['runtime'],'qemu-system-x86_64').read_bytes()).hexdigest()}
    vmcc.dump(directory/'apply-state.json',state)
    try:
        for i in s['instances']:
            vmid=i['vmid'];node=directory/str(vmid);identity=node/'identity.json'
            current={'phase':'COPYING','vmid':vmid};state['instances'][str(vmid)]=current
            vmcc.dump(directory/'apply-state.json',state)
            stage=node/'rootfs';stage.mkdir(mode=0o700)
            run('rsync','-aHAX','--numeric-ids',*['--exclude='+x for x in prepare.EXCLUDES],
                s['source_rootfs'].rstrip('/')+'/',str(stage)+'/')
            run(sys.executable,REPO/'tools/prepare-guest.py','--root',stage,'--identity',identity,
                '--password-file',secret,'--apply')
            current['phase']='BUILDING';vmcc.dump(directory/'apply-state.json',state)
            image=node/'system.raw'
            run(sys.executable,REPO/'tools/build-boot-disk.py',stage,image,identity)
            current['phase']='ALLOCATING';vmcc.dump(directory/'apply-state.json',state)
            volume=f"{s['storage']}:vm-{vmid}-disk-1"
            # Allocate a NEW thin volume; never format a supplied physical disk.
            run('pvesm','alloc',s['storage'],vmid,f'vm-{vmid}-disk-1','500G')
            current['disk_volume']=volume;vmcc.dump(directory/'apply-state.json',state)
            target=subprocess.check_output(['pvesm','path',volume],text=True).strip()
            lv=json.loads(subprocess.check_output(['lvs','--reportformat','json','-o','segtype,data_percent,origin',target],text=True))['report'][0]['lv'][0]
            if lv['segtype'].strip()!='thin' or lv['origin'].strip() or float(lv['data_percent'])!=0:
                raise ValueError('new thin volume is not empty; refusing zero-target import')
            # This target was just allocated here, has no origin and has no mapped data.
            # Never use target-is-zero on an existing disk or a snapshot.
            run('qemu-img','convert','-p','-n','--target-is-zero','-f','raw','-O','raw',image,target)
            cmd=[sys.executable,REPO/'tools/install-host.py','--bundle',node/'bundle','--runtime',s['runtime'],'--apply']
            if a.allow_stopped_gpu_sharing:cmd.append('--allow-stopped-gpu-sharing')
            run(*cmd)
            run('sh',node/'bundle/create-vm.sh')
            current['phase']='CREATED';vmcc.dump(directory/'apply-state.json',state)
            if a.start:
                run('qm','start',vmid)
                current['phase']='STARTED_UNVERIFIED'
            # Disposable working copies are redundant after successful import. Keep host identity/receipts.
            shutil.rmtree(stage);image.unlink()
            vmcc.dump(directory/'apply-state.json',state)
        state['status']='APPLIED_UNVERIFIED'
    except BaseException as error:
        state['status']='FAILED';state['error']=str(error)
        raise
    finally:
        vmcc.dump(directory/'apply-state.json',state)
    print('Created batch. Run verify against every booted instance; apply alone is not acceptance.')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('plan');a.add_argument('--spec',required=True);a.add_argument('--out',required=True);a.set_defaults(func=plan)
    a=sub.add_parser('apply');a.add_argument('--plan',required=True);a.add_argument('--password-file',required=True)
    a.add_argument('--apply',action='store_true');a.add_argument('--start',action='store_true')
    a.add_argument('--allow-stopped-gpu-sharing',action='store_true');a.set_defaults(func=apply)
    a.add_argument('--retry-before-allocation',action='store_true')
    a=p.parse_args()
    try:a.func(a)
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:p.exit(2,'batch: '+str(error)+'\n')


if __name__=='__main__':main()
