# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import batch


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


class Factory(unittest.TestCase):
    def test_batch_is_atomic_and_identity_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);spec=json.loads((ROOT/'examples/batch.json').read_text())
            file=base/'spec.json';file.write_text(json.dumps(spec));out=base/'plan'
            p=subprocess.run([sys.executable,str(ROOT/'vmcc'),'batch','plan','--spec',str(file),'--out',str(out)],capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            batch.check_plan(out)
            first=json.loads((out/'200/identity.json').read_text())
            second=json.loads((out/'201/identity.json').read_text())
            self.assertEqual(first['account'],{'username':'user','uid':1000})
            for key in first['clone_disk_identity_plan']:
                self.assertNotEqual(first['clone_disk_identity_plan'][key],second['clone_disk_identity_plan'][key])
            self.assertNotIn('password',json.dumps(first))
            config=(out/'200/create-vm.sh')
            self.assertFalse(config.exists())
            self.assertIn('--onboot 0',(out/'200/bundle/create-vm.sh').read_text())
            (out/'200/identity.json').write_text('{}')
            with self.assertRaises(ValueError):batch.check_plan(out)

    def test_reject_duplicate_gpu_before_publishing_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);spec=json.loads((ROOT/'examples/batch.json').read_text())
            spec['instances'][1]['gpu']=spec['instances'][0]['gpu']
            file=base/'spec.json';file.write_text(json.dumps(spec));out=base/'plan'
            p=subprocess.run([sys.executable,str(ROOT/'vmcc'),'batch','plan','--spec',str(file),'--out',str(out)],capture_output=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(out.exists())

    def test_disk_output_guards_and_live_root_guard(self):
        disk=module('disk',ROOT/'tools/build-boot-disk.py')
        with self.assertRaises(ValueError):disk.output_path('/dev/new-vmcc-test')
        with self.assertRaises(ValueError):disk.prepare.safe_root('/')
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'existing';path.write_text('do not overwrite')
            with self.assertRaises(ValueError):disk.output_path(path)
            self.assertEqual(path.read_text(),'do not overwrite')

    def test_shell_entrypoint_dispatches_to_disk_builder(self):
        result=subprocess.run(['bash',str(ROOT/'tools/build-boot-disk.sh'),'--help'],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('rootfs new_disk identity',result.stdout)

    def test_rom_bar_never_enables_or_overwrites_live_resource(self):
        rom=module('rom',ROOT/'templates/guest/pci-rom-resource.py')
        import struct
        with tempfile.TemporaryDirectory() as temporary:
            dev=Path(temporary)
            (dev/'vendor').write_text('0x10de');(dev/'class').write_text('0x030000')
            (dev/'resource').write_text('0 0 0\n'*6+'81080000 810fffff 46200\n')
            config=bytearray(256);(dev/'config').write_bytes(config)
            result=rom.restore(dev,True)
            self.assertFalse(result['rom_decode_enabled'])
            self.assertEqual(struct.unpack_from('<I',(dev/'config').read_bytes(),0x30)[0],0x81080000)
            for value in (0x81080001,0x90000000):
                struct.pack_into('<I',config,0x30,value);(dev/'config').write_bytes(config)
                with self.assertRaises(ValueError):rom.restore(dev,True)
                self.assertEqual(struct.unpack_from('<I',(dev/'config').read_bytes(),0x30)[0],value)


if __name__=='__main__':unittest.main()
