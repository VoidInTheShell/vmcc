#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare an OFFLINE disposable rootfs copy. Never run against a live root."""
import argparse
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

from vmcc import validate

REPO = Path(__file__).resolve().parents[1]
# Source image contents that have no runtime role. This policy also applies at copy time.
EXCLUDES = [
    '/dev/*', '/proc/*', '/sys/*', '/run/*', '/tmp/*', '/var/tmp/*',
    '/boot/efi/*', '/root/*', '/root/.*', '/home/*', '/var/log/*',
    '/build-*', '/opt/acttoolcache', '/opt/hostedtoolcache', '/opt/runner',
    '/github', '/imagegeneration', '/etc/act-image-origin.json', '/etc/profile.d/act-image.sh',
    '/etc/ssh/ssh_host_*', '/var/lib/dhcp/*', '/var/lib/dhcpcd/*',
    '/var/lib/NetworkManager/*', '/etc/NetworkManager/system-connections/*',
    '/var/lib/systemd/random-seed', '/var/lib/systemd/linger/*',
    '/var/lib/sddm/*', '/var/cache/sddm/*', '/var/cache/apt/archives/*.deb',
    '/usr/local/bin/vmaware*', '/var/lib/vmcc', '/etc/pve-emu',
    '/lib/modules/*emu-native*', '/usr/lib/modules/*emu-native*',
    '/boot/*emu-native*', '/usr/src/*emu-native*',
]


def run(root, *args, input=None):
    subprocess.run(['chroot', str(root), *args], input=input, text=True, check=True,
                   env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C',
                        'DEBIAN_FRONTEND': 'noninteractive'})


def safe_root(path):
    root = Path(path).resolve(strict=True)
    if root == Path('/') or not (root/'etc/os-release').is_file():
        raise ValueError('an offline Ubuntu rootfs directory is required')
    if os.path.samefile(root/'etc/passwd', '/etc/passwd'):
        raise ValueError('rootfs is the host root through an alias')
    # Ubuntu usrmerge uses relative links. Absolute directory links can escape the staging tree.
    for relative in ('etc','usr','var','home','root','boot','lib','bin','sbin','lib64'):
        path=root/relative
        if path.exists() and not path.resolve().is_relative_to(root):
            raise ValueError('rootfs directory escapes staging tree: '+relative)
    if root.is_relative_to('/dev') or root.is_relative_to('/proc') or root.is_relative_to('/sys'):
        raise ValueError('unsafe rootfs location')
    if 'VERSION_ID="24.04"' not in (root/'etc/os-release').read_text():
        raise ValueError('this profile requires Ubuntu 24.04')
    if (root/'proc/1').exists() or (root/'run/systemd/private').exists():
        raise ValueError('rootfs appears live; use a fresh offline copy')
    return root


def write(root, relative, text, mode=0o644):
    path = root/relative
    if path.is_symlink():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text); path.chmod(mode)


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def configure(root, m, password):
    """Called only after copying into a new staging directory."""
    validate(m)
    account = m.get('account', {'username': 'user', 'uid': 1000})
    username, uid = account['username'], account['uid']
    for name,major,minor in [('null',1,3),('zero',1,5),('random',1,8),('urandom',1,9),('tty',5,0)]:
        path=root/'dev'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() or path.is_symlink():remove(path)
        os.mknod(path,stat.S_IFCHR|0o666,os.makedev(major,minor))
    inherited=[]
    for row in (root/'etc/passwd').read_text().splitlines():
        fields = row.split(':')
        if 1000 <= int(fields[2]) < 60000:
            inherited.append(fields[0])
            run(root, 'userdel', fields[0])
    for path in (root/'etc/sudoers.d').glob('*'):
        if not path.is_file():continue
        lines=path.read_text().splitlines(keepends=True)
        filtered=[line for line in lines if not any(line.lstrip().startswith(name+' ') for name in inherited)]
        if filtered!=lines:
            if any(line.strip() and not line.lstrip().startswith('#') for line in filtered):
                path.write_text(''.join(filtered))
            else:remove(path)
    # No inherited personal files, credentials, shell histories, validation or build directories.
    for relative in ('root', 'home', 'var/log', 'tmp', 'var/tmp'):
        target = root/relative
        for path in target.iterdir() if target.exists() else []:
            remove(path)
        target.mkdir(parents=True, exist_ok=True)
    (root/'root').chmod(0o700)
    for relative in ('tmp', 'var/tmp'):
        (root/relative).chmod(0o1777)
    for relative in ('etc/vmcc', 'var/lib/vmcc', 'etc/pve-emu',
                     'etc/profile.d/act-image.sh', 'etc/act-image-origin.json', 'github', 'imagegeneration',
                     'opt/acttoolcache','opt/hostedtoolcache','opt/runner',
                     'etc/apparmor.d/sunshine-x11'):
        remove(root/relative)
    for directory, pattern in [('etc/netplan', '*.yaml'), ('etc/default/grub.d', '*.cfg'),
                               ('etc/sudoers.d', '*vmcc*'), ('etc/sudoers.d', '*emu*'),
                               ('var/lib/systemd/linger', '*'),
                               ('etc/ssh', 'ssh_host_*'), ('usr/local/bin', 'vmaware*')]:
        for path in (root/directory).glob(pattern):
            remove(path)
    # Remove the superseded kernel only; keep the active generic kernel and DKMS/headers.
    for directory in ('boot', 'lib/modules', 'usr/src'):
        for path in (root/directory).glob('*emu-native*'):
            remove(path)
    write(root, 'etc/environment', 'PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games"\n')
    for old, new in [('etc/ssh/sshd_config.d/10-emu.conf', 'etc/ssh/sshd_config.d/10-local.conf'),
                     ('etc/modprobe.d/emu-uncore.conf', 'etc/modprobe.d/intel-uncore.conf')]:
        source = root/old
        if source.exists():
            write(root, new, ''.join(line+'\n' for line in source.read_text().splitlines()
                                    if line.strip() and not line.lstrip().startswith('#')))
            source.unlink()
    # Reuse an unoccupied user-private group or create it; refuse system-group collisions.
    groups = [row.split(':') for row in (root/'etc/group').read_text().splitlines()]
    group = next((row for row in groups if row[0] == username), None)
    if group and int(group[2]) < 1000:
        raise ValueError('desktop username collides with system group')
    if not group:
        if any(int(row[2]) == uid for row in groups):
            run(root, 'groupadd', username)
        else:
            run(root, 'groupadd', '-g', str(uid), username)
    run(root, 'useradd', '-m', '-u', str(uid), '-g', username, '-s', '/bin/bash',
        '-G', 'sudo,video,render,input', username)
    run(root, 'usermod', '-L', 'root')
    run(root, 'chpasswd', input=username+':'+password+'\n')
    write(root, 'etc/sudoers.d/90-local-admin', username+' ALL=(ALL:ALL) NOPASSWD: ALL\n', 0o440)
    run(root, 'visudo', '-cf', '/etc/sudoers')
    write(root, 'etc/hostname', m['name']+'\n')
    write(root, 'etc/hosts', '127.0.0.1 localhost\n127.0.1.1 '+m['name']+'\n::1 localhost ip6-localhost ip6-loopback\n')
    write(root, 'etc/timezone', m['timezone']+'\n')
    remove(root/'etc/localtime'); (root/'etc/localtime').symlink_to('/usr/share/zoneinfo/'+m['timezone'])
    n = m['network']
    write(root, 'etc/netplan/90-lan.yaml', 'network:\n  version: 2\n  renderer: networkd\n  ethernets:\n    ethernet:\n      match:\n        macaddress: "'+m['mac'].lower()+'"\n      set-name: enp2s0\n      dhcp4: false\n      dhcp6: false\n      addresses: ["'+n['address']+'"]\n      routes:\n        - to: default\n          via: "'+n['gateway']+'"\n      nameservers:\n        addresses: ["'+n['dns']+'"]\n', 0o600)
    write(root, 'etc/machine-id', '')
    remove(root/'var/lib/dbus/machine-id')
    (root/'var/lib/dbus').mkdir(parents=True, exist_ok=True)
    (root/'var/lib/dbus/machine-id').symlink_to('/etc/machine-id')
    run(root, 'ssh-keygen', '-A')
    write(root, 'etc/default/grub.d/99-desktop.cfg', 'GRUB_TIMEOUT=2\nGRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\nGRUB_CMDLINE_LINUX=""\nGRUB_DISABLE_OS_PROBER=true\nGRUB_TERMINAL="console"\n')
    run(root, 'systemctl', 'disable', 'serial-getty@ttyS0.service')
    for name in ('sunshine-launch', 'sunshine-xauthority'):
        write(root, 'usr/local/libexec/'+name, (REPO/'templates/sunshine'/name).read_text(), 0o755)
    write(root, 'etc/sunshine/streaming-user', username+'\n')
    write(root, 'etc/X11/xorg.conf.d/20-sunshine-headless.conf',
          (REPO/'templates/sunshine/xorg-headless.conf').read_text())
    write(root, 'etc/sudoers.d/91-sunshine', username+' ALL=(root) NOPASSWD: /usr/local/libexec/sunshine-xauthority\n', 0o440)
    home = Path('home')/username
    write(root, home/'.config/sunshine/sunshine.conf', 'sunshine_name = '+m['name']+'\nencoder = nvenc\ncapture = x11\norigin_web_ui_allowed = lan\nupnp = disabled\nav1_mode = 1\naddress_family = ipv4\nbind_address = 0.0.0.0\n', 0o600)
    unit = 'app-dev.lizardbyte.app.Sunshine.service'
    drop = '[Unit]\nStartLimitIntervalSec=0\n[Service]\nEnvironment=DISPLAY=:0\nEnvironment=XDG_RUNTIME_DIR=/run/user/'+str(uid)+'\nEnvironment=PULSE_SERVER=unix:/run/user/'+str(uid)+'/pulse/native\nEnvironment=QT_QPA_PLATFORM=offscreen\nExecStart=\nExecStart=/usr/local/libexec/sunshine-launch\nRestart=always\nRestartSec=5s\n'
    write(root, home/('.config/systemd/user/'+unit+'.d/boot.conf'), drop)
    for target in ('default.target', 'graphical-session.target'):
        link = root/home/('.config/systemd/user/'+target+'.wants')/unit
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to('/usr/lib/systemd/user/'+unit)
    write(root, 'var/lib/systemd/linger/'+username, '')
    run(root, 'chown', '-R', username+':'+username, '/home/'+username)
    run(root, 'setcap', 'cap_sys_nice+p', '/usr/bin/sunshine')
    write(root, 'usr/local/libexec/pci-rom-resource', (REPO/'templates/guest/pci-rom-resource.py').read_text(), 0o755)
    write(root, 'etc/systemd/system/pci-rom-resource.service', (REPO/'templates/guest/pci-rom-resource.service').read_text())
    run(root, 'systemctl', 'enable', 'pci-rom-resource.service', 'sddm.service', 'ssh.service', 'systemd-networkd.service')
    # Rules are persistent even if the inherited firewall is inactive. Do not enable a firewall.
    run(root, 'ufw', 'allow', 'proto', 'tcp', 'from', '0.0.0.0/0', 'to', 'any', 'port', '47984,47989,47990,48010')
    run(root, 'ufw', 'allow', 'proto', 'udp', 'from', '0.0.0.0/0', 'to', 'any', 'port', '47998:48000')
    # These are package state and first-boot runtime state, never an engineering receipt.
    run(root, 'netplan', 'generate')
    for relative in ('run', 'tmp', 'var/tmp', 'var/log'):
        for path in (root/relative).iterdir():
            remove(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True); p.add_argument('--identity', required=True)
    p.add_argument('--password-file', required=True); p.add_argument('--apply', action='store_true')
    a = p.parse_args(); root = safe_root(a.root)
    m = json.loads(Path(a.identity).read_text()); validate(m)
    secret = Path(a.password_file)
    if secret.stat().st_mode & 0o077:
        raise ValueError('password file must have mode 0600 or stricter')
    password = secret.read_text().rstrip('\n')
    if not password or any(c in password for c in '\n\r:'):
        raise ValueError('invalid password file')
    if not a.apply:
        print(json.dumps({'offline_root': str(root), 'identity': m['name'], 'apply': False})); return
    if os.geteuid() != 0:
        raise ValueError('root required for offline preparation')
    configure(root, m, password)
    print('Offline rootfs prepared; no source home, secret, project log or manifest copied.')


if __name__ == '__main__':
    main()
