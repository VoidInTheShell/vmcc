#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Render configuration for a NEW PortalWrt router; never SSH or apply it."""
import argparse,ipaddress,re,shlex
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for key in ['wan-device','lan-device','wan-address','upstream','lan-address','out']:p.add_argument('--'+key,required=True)
a=p.parse_args()
wan=ipaddress.IPv4Interface(a.wan_address);lan=ipaddress.IPv4Interface(a.lan_address);up=ipaddress.IPv4Address(a.upstream)
if lan.network.prefixlen!=24 or wan.network.overlaps(lan.network) or up not in wan.network or up==wan.ip:raise SystemExit('require disjoint networks, LAN /24, usable upstream on WAN')
if any(not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_.-]{0,14}',s) for s in [a.wan_device,a.lan_device]) or a.wan_device==a.lan_device:raise SystemExit('invalid/distinct device names required')
network=f'''config interface 'loopback'
 option device 'lo'
 option proto 'static'
 option ipaddr '127.0.0.1'
 option netmask '255.0.0.0'
config device 'lan_bridge'
 option name 'br-lan'
 option type 'bridge'
 list ports '{a.lan_device}'
config interface 'lan'
 option device 'br-lan'
 option proto 'static'
 option ipaddr '{lan.ip}'
 option netmask '{lan.netmask}'
config interface 'wan'
 option device '{a.wan_device}'
 option proto 'static'
 option ipaddr '{wan.ip}'
 option netmask '{wan.netmask}'
 option gateway '{up}'
 list dns '{up}'
'''
dhcp=f'''config dnsmasq
 option domainneeded '1'
 option boguspriv '1'
 option localservice '1'
 option nonwildcard '1'
 list interface 'br-lan'
 list notinterface '{a.wan_device}'
config dhcp 'lan'
 option interface 'lan'
 option ignore '0'
 option start '100'
 option limit '100'
 option leasetime '12h'
 option dhcpv6 'disabled'
 option ra 'disabled'
 list dhcp_option '3,{lan.ip}'
 list dhcp_option '6,{lan.ip}'
config dhcp 'wan'
 option interface 'wan'
 option ignore '1'
'''
firewall='''config defaults
 option input 'ACCEPT'
 option output 'ACCEPT'
 option forward 'ACCEPT'
 option synflood_protect '1'
config zone
 option name 'lan'
 list network 'lan'
 option input 'ACCEPT'
 option output 'ACCEPT'
 option forward 'ACCEPT'
config zone
 option name 'wan'
 list network 'wan'
 option input 'ACCEPT'
 option output 'ACCEPT'
 option forward 'ACCEPT'
 option masq '1'
 option mtu_fix '1'
config forwarding
 option src 'lan'
 option dest 'wan'
'''
for name,src,dst in [('input','wan',None),('output',None,'wan'),('forward_in','wan','*'),('forward_out','*','wan')]:
 firewall+=f"config rule 'vmcc_dhcp_wan_{name}'\n option name 'Block-WAN-DHCP-{name}'\n option proto 'udp'\n option dest_port '67-68 546-547'\n option target 'DROP'\n option family 'any'\n"
 if src:firewall+=f" option src '{src}'\n"
 if dst:firewall+=f" option dest '{dst}'\n"
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
for name,contents in [('network',network),('dhcp',dhcp),('firewall',firewall)]: (out/name).write_text(contents)
script='''#!/bin/sh
set -eu
test "${1:-}" = --apply || { echo 'Review configs, then run from the new router serial console: sh apply.sh --apply'; exit 2; }
cd -- "$(dirname -- "$0")"
backup="/root/vmcc-network-backup/$(date +%s)"
mkdir -p "$backup"
for name in network dhcp firewall; do
 cp "/etc/config/$name" "$backup/$name"
 uci -c . export "$name" >/dev/null
done
cp /etc/dnsmasq.conf "$backup/dnsmasq.conf"
for name in network dhcp firewall; do cp "$name" "/etc/config/$name"; done
'''
script+="printf '%s\\n' "+shlex.quote('except-interface='+a.wan_device)+' '+shlex.quote('no-dhcp-interface='+a.wan_device)+" >> /etc/dnsmasq.conf\n"
script+="uci set system.@system[0].zonename='America/New_York'\nuci set system.@system[0].timezone='EST5EDT,M3.2.0,M11.1.0'\nuci commit system\nfw4 check\necho 'Config written; network NOT restarted. Reload network/dnsmasq/firewall from serial console, set root password, then verify runtime DHCP exclusions and actual routing.'\n"
(out/'apply.sh').write_text(script)
print(out)
