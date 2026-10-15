#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read actual guest state. Run over stdin; save stdout ONLY on the management host."""
import ctypes
import hashlib
import json
import mmap
import os
import pwd
import struct
import subprocess
from pathlib import Path


def read(path):
    try:return Path(path).read_text().strip()
    except (FileNotFoundError,PermissionError,OSError):return None


def command(*args):
    p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {'code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}


def main():
    dmi={key:read('/sys/class/dmi/id/'+key) for key in
         ('sys_vendor','product_name','product_version','product_serial','product_uuid',
          'board_vendor','board_name','board_version','board_serial','chassis_serial',
          'bios_vendor','bios_version','bios_date')}
    smbios=[]; dimm_serials=[]
    raw=Path('/sys/firmware/dmi/tables/DMI').read_bytes(); pos=0
    while pos+4<=len(raw):
        kind,length=raw[pos],raw[pos+1]
        if length<4 or pos+length>len(raw):raise ValueError('invalid SMBIOS structure')
        end=raw.find(b'\0\0',pos+length)
        if end<0:raise ValueError('unterminated SMBIOS structure')
        header=bytearray(raw[pos:pos+length]);strings=raw[pos+length:end].split(b'\0')
        offsets={1:7,2:7,3:7,17:24}
        if kind in offsets and len(header)>offsets[kind]:
            index=header[offsets[kind]]
            if index and index<=len(strings):
                if kind==17:dimm_serials.append(strings[index-1].decode(errors='replace'))
                strings[index-1]=b'INSTANCE-SERIAL'
        if kind==1 and len(header)>=24:header[8:24]=b'\0'*16
        normalized=bytes(header)+b'\0'.join(strings)+b'\0\0'
        smbios.append({'type':kind,'handle':int.from_bytes(header[2:4],'little'),
                       'sha256_without_instance_identity':hashlib.sha256(normalized).hexdigest()})
        pos=end+2
        if kind==127:break
    acpi={}
    for table in Path('/sys/firmware/acpi/tables').iterdir():
        if not table.is_file() or table.name=='FACS':continue
        data=table.read_bytes()
        if len(data)>=36:
            acpi[table.name]={'oem_id':data[10:16].decode(errors='replace'),'table_id':data[16:24].decode(errors='replace'),
                              'checksum_valid':sum(data)%256==0}
            if table.name.startswith(('DSDT','SSDT','APIC','HPET')):
                acpi[table.name]['sha256']=hashlib.sha256(data).hexdigest()
    pci=[]
    for dev in sorted(Path('/sys/bus/pci/devices').iterdir()):
        row={'bdf':dev.name,**{key:read(dev/key) for key in
             ('vendor','device','class','subsystem_vendor','subsystem_device','revision')}}
        row['driver']=(dev/'driver').resolve().name if (dev/'driver').exists() else None
        if row['vendor']=='0x10de' and int(row['class'],16)>>16==3:
            try:
                fd=os.open(dev/'config',os.O_RDONLY)
                try:row['rom_bar']=hex(struct.unpack('<I',os.pread(fd,4,0x30))[0])
                finally:os.close(fd)
            except OSError:row['rom_bar']=None
        pci.append(row)
    # Native CPUID instructions, pinned one vCPU at a time; no modified detection application.
    code=bytes.fromhex('534989d089f889f10fa241890041895804418948084189500c5bc3')
    memory=mmap.mmap(-1,len(code),prot=mmap.PROT_READ|mmap.PROT_WRITE|mmap.PROT_EXEC)
    memory.write(code)
    call=ctypes.CFUNCTYPE(None,ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32))(
        ctypes.addressof(ctypes.c_char.from_buffer(memory)))
    def cpuid(leaf,sub=0):
        result=(ctypes.c_uint32*4)();call(leaf,sub,result);return list(result)
    affinity=os.sched_getaffinity(0);cores=[]
    try:
        for cpu in sorted(affinity):
            os.sched_setaffinity(0,{cpu})
            cores.append({'cpu':cpu,'hybrid_type':cpuid(0x1a)[0]>>24,
                          'leaf1':cpuid(1),'leaf7':cpuid(7),'topology':cpuid(0x1f,1)})
    finally:os.sched_setaffinity(0,affinity)
    kernel=os.uname().release
    kernel_file=Path('/boot/vmlinuz-'+kernel)
    account=[{'name':x.pw_name,'uid':x.pw_uid,'home':x.pw_dir} for x in pwd.getpwall() if 1000<=x.pw_uid<60000]
    fingerprints=[]
    for key in Path('/etc/ssh').glob('ssh_host_*_key.pub'):
        fingerprints.append(hashlib.sha256(key.read_bytes()).hexdigest())
    nvme=[]
    for dev in Path('/sys/class/nvme').glob('nvme[0-9]*'):
        nvme.append({key:read(dev/key) for key in ('model','serial','firmware_rev','subsysnqn')})
    units={unit:command('systemctl','is-active',unit) for unit in ('display-manager','pci-rom-resource','ssh')}
    sunshine={}
    for a in account:
        unit='app-dev.lizardbyte.app.Sunshine.service'
        p=subprocess.run(['runuser','-u',a['name'],'--','env','XDG_RUNTIME_DIR=/run/user/'+str(a['uid']),
                          'systemctl','--user','is-active',unit],text=True,capture_output=True)
        sunshine[a['name']]={'active':p.returncode==0,'config':read(Path(a['home'])/'.config/sunshine/sunshine.conf'),
                              'linger':Path('/var/lib/systemd/linger',a['name']).exists()}
    residues=[]
    for pattern in ('/var/log/emu-validation','/root/*emu*','/root/*vmaware*','/root/*audit*',
                    '/root/*kernel*','/root/*validate*','/root/*collect*','/boot/*emu-native*',
                    '/lib/modules/*emu-native*','/etc/vmcc','/etc/pve-emu','/opt/acttoolcache',
                    '/github','/imagegeneration','/etc/act-image-origin.json',
                    '/etc/profile.d/act-image.sh','/etc/default/grub.d/*emu*','/etc/default/grub.d/*vmcc*',
                    '/etc/sudoers.d/*vmcc*','/usr/local/bin/vmaware*'):
        import glob
        residues.extend(glob.glob(pattern))
    state={'schema':1,'dmi':dmi,'smbios':smbios,'dimm_serials':dimm_serials,'acpi':acpi,
           'pci':pci,'cpu':cores,'kernel':kernel,'version':read('/proc/version'),
           'cmdline':read('/proc/cmdline'),'kernel_sha256':hashlib.sha256(kernel_file.read_bytes()).hexdigest(),
           'memtotal_kib':int(read('/proc/meminfo').splitlines()[0].split()[1]),
           'nvme':nvme,'accounts':account,'hostname':read('/etc/hostname'),'timezone':read('/etc/timezone'),
           'machine_id':read('/etc/machine-id'),'ssh_public_hashes':sorted(fingerprints),
           'environment':read('/etc/environment'),'units':units,'sunshine':sunshine,
           'nvidia':command('nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'),
           'usb':command('lsusb','-t'),'network':command('ip','-j','address'),'routes':command('ip','-j','route'),
           'disks':command('lsblk','-J','-o','NAME,SIZE,UUID,PARTUUID,PTUUID,TYPE'),
           'listeners':command('ss','-H','-lnt'),'residues':sorted(set(residues)),
           'cpufreq_present':Path('/sys/devices/system/cpu/cpu0/cpufreq').exists()}
    print(json.dumps(state,indent=2))


if __name__=='__main__':main()
