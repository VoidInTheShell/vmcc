# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from vmcc import set_smbios_string,validate
spec=importlib.util.spec_from_file_location('wrapper',ROOT/'tools/kvm-wrapper.py')
wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)

def cli(*args,ok=True):
    p=subprocess.run([sys.executable,str(ROOT/'vmcc'),*map(str,args)],capture_output=True,text=True)
    if ok and p.returncode:raise AssertionError(p.stderr)
    return p

class Instances(unittest.TestCase):
    def test_independent_instances_and_binary_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); identities=[]
            for i in range(1,101):
                node=base/f'node-{i}'
                cli('init','--name',f'node-{i}','--vmid',200+i,'--address',f'10.20.1.{i+1}/24','--gateway','10.20.1.1','--out',node)
                identities.append(node/'identity.json')
            self.assertEqual(cli('audit',*identities).returncode,0)
            for i in (1,2):
                out=base/f'render-{i}'
                cli('render','--identity',identities[i-1],'--out',out,'--disk',f'pool:vm-{200+i}-disk-1',
                    '--efi-storage','pool','--bridge','vmbr2','--gpu','0000:82:00','--bios','/opt/firmware/E7E07IMS.MB0',
                    '--vcpu-cpus','0-23','--io-cpus','28-31')
                m=json.loads(identities[i-1].read_text());validate(m)
                spd=(out/'spd.bin').read_bytes()
                self.assertEqual(len(spd),2048)
                template=(ROOT/'templates/spd-template.bin').read_bytes()
                for n,sn in enumerate(m['dimm_serials']):
                    b=(out/f'platform/smbios-13900k/type17-dimm{n}.bin').read_bytes()
                    self.assertIn(sn.encode()+b'\0',b)
                    self.assertEqual(spd[n*512+325:n*512+329],bytes.fromhex(sn))
                    self.assertEqual(spd[n*512:n*512+325],template[n*512:n*512+325])
                    self.assertEqual(spd[n*512+329:(n+1)*512],template[n*512+329:(n+1)*512])
                args=json.loads((out/'qemu-args.json').read_text())
                self.assertIn('24,sockets=1,dies=1,cores=24,threads=1,maxcpus=24',args)
                self.assertTrue(any('serial='+m['system_serial'] in x for x in args))
                self.assertTrue(any('image=/opt/firmware/E7E07IMS.MB0' in x for x in args))
                self.assertIn(m['board_serial'].encode(),(out/'platform/smbios-13900k/peripherals-v5/type2-board.bin').read_bytes())
                config=json.loads((out/'runtime.json').read_text())
                transformed=wrapper.transform(['-id',str(m['vmid']),'-readconfig','/usr/share/qemu-server/pve-q35.cfg',
                    '-device','ide-hd,id=sata0,drive=drive-sata0','-device','e1000,id=net0,mac='+m['mac']],config)
                self.assertTrue(any('serial='+m['nvme']['serial'] in x for x in transformed))
                self.assertTrue(any('nguid='+m['nvme']['nguid'] in x for x in transformed))
                self.assertTrue(any(x.startswith('i225-v,') for x in transformed))
                self.assertEqual(sum(x.startswith('nvme,id=nvme0,serial='+m['nvme']['serial']+',') for x in transformed),1)
                self.assertNotEqual(cli('render','--identity',identities[i-1],'--out',out,
                    '--disk','pool:vm-201-disk-1','--efi-storage','pool','--bridge','vmbr2','--gpu','82:00',
                    '--bios','/opt/bios.bin','--vcpu-cpus','0-23','--io-cpus','28-31',ok=False).returncode,0)
            duplicate=base/'duplicate.json';duplicate.write_bytes(identities[0].read_bytes())
            self.assertNotEqual(cli('audit',identities[0],duplicate,ok=False).returncode,0)

    def test_unregistered_vm_uses_original_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            entry=Path(d)/'fallback.py';output=Path(d)/'argv.json'
            entry.write_text('#!/usr/bin/python3\nimport sys,json\nfrom pathlib import Path\nPath('+repr(str(output))+').write_text(json.dumps(sys.argv[1:]))\n')
            entry.chmod(0o755)
            wrapper.FALLBACK=str(entry);wrapper.REGISTRY=Path(d)/'absent'
            pid=os.fork()
            if pid==0:
                sys.argv=['kvm','-id','999','-device','e1000,id=net0'];wrapper.main();os._exit(1)
            _,status=os.waitpid(pid,0)
            self.assertEqual(status,0)
            self.assertEqual(json.loads(output.read_text()),['-id','999','-device','e1000,id=net0'])

    def test_rejects_invalid_network_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(cli('init','--name','bad','--vmid','200','--address','10.20.1.1/24',
                '--gateway','10.20.1.1','--out',Path(d)/'bad',ok=False).returncode,0)
            self.assertFalse((Path(d)/'bad').exists())

if __name__=='__main__':unittest.main()
