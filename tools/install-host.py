#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Preflight and register one NEW, stopped VM. Dry run unless --apply is supplied."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]

def checked(cmd):return subprocess.check_output(cmd,text=True).strip()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',required=True);p.add_argument('--runtime',required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args();bundle=Path(a.bundle).resolve();runtime=Path(a.runtime).resolve()
    c=json.loads((bundle/'runtime.json').read_text());vmid=c['vmid']
    if os.geteuid()!=0:raise RuntimeError('run on the target PVE host as root')
    if c['schema']!=1 or not isinstance(vmid,int) or not 100<=vmid<=999999999:raise RuntimeError('invalid VMID/schema')
    if not re.fullmatch(r'/[A-Za-z0-9_/-]+',c['instance_dir']) or '..' in c['instance_dir']:raise RuntimeError('unsafe instance path')
    prefix=Path(c['instance_dir']).parent.parent
    if c['instance_dir']!=str(prefix/'instances'/str(vmid)):raise RuntimeError('instance path mismatch')
    if prefix!=Path('/opt/vmcc'):raise RuntimeError('installer currently requires the default /opt/vmcc prefix')
    for line in (bundle/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        file=(bundle/name).resolve()
        if not file.is_relative_to(bundle) or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('bundle checksum failure')
    if Path(f'/etc/pve/qemu-server/{vmid}.conf').exists():raise RuntimeError('VMID already exists; refusing overwrite')
    if Path(f'/etc/vmcc/instances/{vmid}.json').exists() or Path(c['instance_dir']).exists():raise RuntimeError('instance already registered')
    if not Path('/dev/kvm').exists():raise RuntimeError('/dev/kvm absent')
    if 'vmx' not in Path('/proc/cpuinfo').read_text().split():raise RuntimeError('this profile requires an Intel VMX host')
    if not (set(c['vcpu_cpus'])|set(c['io_cpus'])) <= os.sched_getaffinity(0):raise RuntimeError('host CPU affinity unavailable')
    if not Path('/sys/class/net',c['bridge'],'bridge').exists():raise RuntimeError('Linux bridge absent')
    bios=Path(c['bios_file'])
    if not bios.is_file() or hashlib.sha256(bios.read_bytes()).hexdigest()!=c['bios_sha256']:raise RuntimeError('provide the matching user BIOS file; never included in repository')
    slot=c['gpu_bdf'];slot=slot if slot.count(':')==2 else '0000:'+slot
    for fn in ('0','1'):
        dev=Path('/sys/bus/pci/devices',slot+'.'+fn)
        if not dev.is_dir() or (dev/'driver').resolve().name!='vfio-pci':raise RuntimeError('GPU and HDMI audio must already be bound to vfio-pci')
    for file in Path('/etc/pve/qemu-server').glob('*.conf'):
        text=file.read_text()
        if c['disk_volume'] in text:raise RuntimeError('disk already referenced by another VM')
        for line in text.splitlines():
            if line.startswith('hostpci') and slot.removeprefix('0000:') in line:raise RuntimeError('GPU slot referenced by another VM')
    checked(['pvesm','path',c['disk_volume']])
    for name in ('qemu-system-x86_64','OVMF_CODE_RPL_4M.fd'):
        if not (runtime/name).is_file():raise RuntimeError('missing runtime artifact: '+name)
    env=os.environ|{'LD_LIBRARY_PATH':str(runtime/'lib')}
    help_text=subprocess.check_output([str(runtime/'qemu-system-x86_64'),'-device','help'],env=env,text=True,stderr=subprocess.STDOUT)
    if not all(x in help_text for x in ('i225-v','usb-alc4080','z790-me','z790-gspi')):raise RuntimeError('wrong QEMU runtime')
    if b'VMCC_SPD_FILE' not in (runtime/'qemu-system-x86_64').read_bytes():raise RuntimeError('runtime lacks per-instance SPD patch')
    if Path('/opt/vmcc/runtime').exists():
        for f in runtime.rglob('*'):
            if f.is_file():
                existing=Path('/opt/vmcc/runtime')/f.relative_to(runtime)
                if not existing.is_file() or existing.read_bytes()!=f.read_bytes():raise RuntimeError('installed runtime differs; use a versioned runtime migration')
    print(json.dumps({'preflight':'PASS','vmid':vmid,'apply':a.apply,'creates_vm':False,'starts_vm':False,'network_collision_check':'NOT RUN'},indent=2))
    if not a.apply:return
    # Fail before mutations if the launcher chain is ambiguous.
    kvm=Path('/usr/bin/kvm');original=Path('/usr/bin/kvm.vmcc-original');wrapper=(REPO/'tools/kvm-wrapper.py').read_bytes()
    if original.exists() and kvm.read_bytes()!=wrapper:raise RuntimeError('existing fallback with an unmanaged launcher; inspect manually')
    if not original.exists():shutil.copy2(kvm,original)
    prefix.mkdir(parents=True,exist_ok=True)
    if not (prefix/'runtime').exists():shutil.copytree(runtime,prefix/'runtime')
    shutil.copytree(bundle,c['instance_dir'])
    registry=Path('/etc/vmcc/instances');registry.mkdir(parents=True,exist_ok=True)
    dest=registry/f'{vmid}.json';shutil.copy2(bundle/'runtime.json',dest);dest.chmod(0o600)
    tools=prefix/'tools';tools.mkdir(exist_ok=True)
    shutil.copy2(REPO/'tools/pin-vcpus.py',tools/'pin-vcpus.py');(tools/'pin-vcpus.py').chmod(0o755)
    shutil.copy2(REPO/'templates/vmcc-affinity@.service','/etc/systemd/system/vmcc-affinity@.service')
    temporary=Path('/usr/bin/kvm.vmcc-new');temporary.write_bytes(wrapper);temporary.chmod(0o755);temporary.replace(kvm)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',f'vmcc-affinity@{vmid}.service'],check=True)
    print('Registered only. Review and run '+str(Path(c['instance_dir'])/'create-vm.sh')+' separately, then finalize the cloned guest before its first network boot.')

if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError,subprocess.CalledProcessError) as e:sys.exit('install-host: '+str(e))
