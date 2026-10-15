#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
import json, os, socket, time, sys, logging
from pathlib import Path
logging.basicConfig(level=logging.INFO)
c=json.loads(Path(sys.argv[1]).read_text());vmid=c['vmid'];last=None
while True:
    try:
        pid=int(Path(f'/run/qemu-server/{vmid}.pid').read_text())
        if pid!=last:
            with socket.socket(socket.AF_UNIX) as s:
                s.settimeout(5);s.connect(f'/run/qemu-server/{vmid}.qmp')
                with s.makefile('rwb') as f:
                    json.loads(f.readline())
                    def request(command):
                        f.write(json.dumps({'execute':command,'id':command}).encode()+b'\n');f.flush()
                        while True:
                            line=f.readline()
                            if not line:raise ConnectionError('QMP closed')
                            obj=json.loads(line)
                            if obj.get('id')==command:
                                if 'error' in obj:raise ValueError(obj['error'])
                                return obj['return']
                    request('qmp_capabilities');cpus=request('query-cpus-fast')
            if len(cpus)!=24:raise ValueError('expected 24 CPUs')
            tids=set()
            for cpu in cpus:
                core=cpu['props']['core-id']
                if not 0<=core<24 or cpu['props']['thread-id']!=0:raise ValueError('unexpected CPU topology')
                tid=cpu['thread-id'];os.sched_setaffinity(tid,{c['vcpu_cpus'][core]});tids.add(tid)
            for task in Path(f'/proc/{pid}/task').iterdir():
                if int(task.name) not in tids:os.sched_setaffinity(int(task.name),set(c['io_cpus']))
            logging.info('VM %s pid %s pinned',vmid,pid);last=pid
    except (OSError,ValueError,KeyError,ConnectionError) as e:
        if last is not None:logging.warning('VM %s retry: %s',vmid,e)
        last=None
    time.sleep(5)
