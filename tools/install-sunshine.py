#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Configure the dedicated user on a new guest; requires Xorg, SDDM and NVIDIA."""
import argparse,hashlib,os,pwd,subprocess,shutil
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
DEB_SHA='c38e9c705f650f8705f61702717e99bec34044c5028fcb8f23a08fe041292c21'
def run(*args):subprocess.run(list(args),check=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--deb',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--name',required=True);a=p.parse_args()
 if hashlib.sha256(Path(a.deb).read_bytes()).hexdigest()!=DEB_SHA:raise RuntimeError('wrong Sunshine deb; see locked source in docs')
 user=pwd.getpwnam('user');uid=user.pw_uid
 if not shutil.which('Xorg') or not shutil.which('nvidia-smi') or not Path('/sys/module/uhid').exists():raise RuntimeError('Xorg, NVIDIA driver and UHID must be installed/loaded first')
 if not a.name or any(x in a.name for x in '\n\r='):raise RuntimeError('invalid Sunshine name')
 if not a.apply:print('Preflight passed. --apply installs/configures Sunshine for user, retains SDDM password login, enables linger.');return
 if os.geteuid()!=0:raise RuntimeError('root required')
 if Path('/home/user/.config/sunshine').exists():raise RuntimeError('existing Sunshine state must be reset on the new clone before installation')
 run('apt-get','install','-y',str(Path(a.deb).resolve()))
 def write(path,text,mode=0o644,owner=False):
  f=Path(path);f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text);f.chmod(mode)
  if owner:
   os.chown(f,uid,user.pw_gid)
   for parent in f.parents:
    if parent==Path('/home/user'):break
    os.chown(parent,uid,user.pw_gid)
 write('/etc/X11/xorg.conf.d/20-sunshine-headless.conf',(REPO/'templates/sunshine/xorg-headless.conf').read_text())
 write('/etc/vmcc/streaming-user','user\n',0o644)
 Path('/usr/local/libexec').mkdir(parents=True,exist_ok=True)
 for name in ('sunshine-xauthority','sunshine-launch'):
  shutil.copy2(REPO/'templates/sunshine'/name,'/usr/local/libexec/'+name);Path('/usr/local/libexec/'+name).chmod(0o755)
 write('/etc/sudoers.d/91-vmcc-sunshine','user ALL=(root) NOPASSWD: /usr/local/libexec/sunshine-xauthority\n',0o440)
 run('visudo','-cf','/etc/sudoers.d/91-vmcc-sunshine')
 write('/home/user/.config/sunshine/sunshine.conf','sunshine_name = '+a.name+'\nencoder = nvenc\ncapture = x11\norigin_web_ui_allowed = lan\nupnp = disabled\nav1_mode = 1\n',0o600,True)
 drop='[Unit]\nStartLimitIntervalSec=0\n[Service]\nEnvironment=DISPLAY=:0\nEnvironment=XDG_RUNTIME_DIR=/run/user/'+str(uid)+'\nEnvironment=PULSE_SERVER=unix:/run/user/'+str(uid)+'/pulse/native\nEnvironment=QT_QPA_PLATFORM=offscreen\nExecStart=\nExecStart=/usr/local/libexec/sunshine-launch\nRestart=always\nRestartSec=5s\n'
 write('/home/user/.config/systemd/user/app-dev.lizardbyte.app.Sunshine.service.d/boot.conf',drop,owner=True)
 run('usermod','-aG','input','user');run('loginctl','enable-linger','user')
 run('setcap','cap_sys_nice+p','/usr/bin/sunshine')
 run('systemctl','restart','user@'+str(uid)+'.service')
 for cmd in [('daemon-reload',),('enable','app-dev.lizardbyte.app.Sunshine.service'),('add-wants','default.target','app-dev.lizardbyte.app.Sunshine.service')]:
  run('systemctl','--user','--machine=user@.host',*cmd)
 print('Reboot from the console. Set new web credentials and PIN pairing on this instance; no password or pairing state was copied.')
if __name__=='__main__':main()
