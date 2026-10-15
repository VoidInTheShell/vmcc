#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Finalize a new Ubuntu clone from its serial console. Dry run unless --apply."""
import argparse,json,os,pwd,subprocess,uuid,shutil
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--identity',required=True);p.add_argument('--user',default='user');p.add_argument('--apply',action='store_true');p.add_argument('--reset-clone',action='store_true');a=p.parse_args()
 from vmcc import validate
 m=json.loads(Path(a.identity).read_text());validate(m)
 if a.user!='user':raise RuntimeError('this profile currently supports the dedicated account user')
 current=Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()
 if current!=m['system_uuid']:raise RuntimeError('identity UUID does not match this VM; refusing to configure another machine')
 print(json.dumps({'hostname':m['name'],'network':m['network'],'user':a.user,'timezone':m['timezone'],'reset_clone':a.reset_clone,'apply':a.apply,'disk_uuid_rewrite':False},indent=2))
 if not a.apply:return
 if os.geteuid()!=0:raise RuntimeError('root required')
 backup=Path('/root/vmcc-finalize-backup')/m['system_uuid'];backup.mkdir(parents=True,exist_ok=True)
 def write(path,contents,mode=0o644):
  f=Path(path);f.parent.mkdir(parents=True,exist_ok=True)
  if f.exists():
   dest=backup/str(f).lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(f,dest)
  f.write_text(contents);f.chmod(mode)
 subprocess.run(['hostnamectl','set-hostname',m['name']],check=True)
 subprocess.run(['timedatectl','set-timezone',m['timezone']],check=True)
 try:pwd.getpwnam(a.user)
 except KeyError:subprocess.run(['useradd','--create-home','--shell','/bin/bash',a.user],check=True)
 subprocess.run(['usermod','-aG','sudo,video,render,input',a.user],check=True)
 write('/etc/sudoers.d/90-vmcc-user','user ALL=(ALL:ALL) NOPASSWD: ALL\n',0o440)
 subprocess.run(['visudo','-cf','/etc/sudoers.d/90-vmcc-user'],check=True)
 # Only the virtual Ethernet interface is matched; the GPU is physical passthrough.
 n=m['network']
 write('/etc/netplan/90-vmcc.yaml','network:\n  version: 2\n  renderer: networkd\n  ethernets:\n    vmcc-lan:\n      match:\n        macaddress: "'+m['mac'].lower()+'"\n      set-name: lan0\n      dhcp4: false\n      dhcp6: false\n      addresses: ["'+n['address']+'"]\n      routes:\n        - to: default\n          via: "'+n['gateway']+'"\n      nameservers:\n        addresses: ["'+n['dns']+'"]\n',0o600)
 # Remove conflicting inherited network definitions from the clone, preserving rollback copies.
 for f in Path('/etc/netplan').glob('*.yaml'):
  if f.name=='90-vmcc.yaml':continue
  dest=backup/str(f).lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(f,dest)
 subprocess.run(['netplan','generate'],check=True)
 if a.reset_clone:
  write('/etc/machine-id',uuid.uuid4().hex+'\n',0o444)
  dbus=Path('/var/lib/dbus/machine-id')
  if dbus.exists() or dbus.is_symlink():dbus.unlink()
  dbus.symlink_to('/etc/machine-id')
  for f in Path('/etc/ssh').glob('ssh_host_*_key*'):f.unlink()
  subprocess.run(['ssh-keygen','-A'],check=True)
  for directory in ['/var/lib/dhcp','/var/lib/dhcpcd','/var/lib/NetworkManager']:
   if Path(directory).is_dir():
    target=backup/str(Path(directory)).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.move(directory,target);Path(directory).mkdir()
  for directory in ['/etc/NetworkManager/system-connections','/home/user/.config/sunshine']:
   if Path(directory).is_dir():
    target=backup/str(Path(directory)).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.move(directory,target)
  marker=Path('/var/lib/vmcc/clone-reset.json');marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'system_uuid':m['system_uuid'],'disk_identity_applied':False})+'\n')
 print('Set the account password with passwd user. Reconfigure Sunshine credentials/pairing per instance. Reboot from the serial console to apply the network and cloned machine identity; filesystem/GPT UUIDs remain a separate offline step.')

if __name__=='__main__':main()
