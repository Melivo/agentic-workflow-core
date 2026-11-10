#!/usr/bin/env python3
"""Synthetic acceptance of one installed component; never an installer.

Only pfo -> leadt3ch@pi-force-one:22 may cycle the receipt/hash-bound unit.
Admin/root and functioning persistence are trusted. Own drills are retained.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'pfo'
NAME = 'typesafe-collection'
CORE_SHA256 = 'd10f0e6a70be329cbbc939a491224c2e26530fd4b1873e425b257926446fd0e2'
UNIT_SHA256 = 'b320ea935b19c5b8368bcc1a8af13ccc5d2d66be63adc94fe5e1a8446e80e930'
PROJECTS = {'synthetic-a', 'synthetic-b'}
TIMEOUT = 25
MAX_OUTPUT = 1024 * 1024
SSH = ('/usr/bin/ssh', '-T', '-oBatchMode=yes', '-oStrictHostKeyChecking=yes',
       '-oUpdateHostKeys=no', '-oConnectTimeout=8', '-oConnectionAttempts=1',
       '-oClearAllForwardings=yes', '-oForwardAgent=no', '-oForwardX11=no',
       '-oControlMaster=no', '-oControlPath=none', '-oProxyCommand=none',
       '-oProxyJump=none', '-oRemoteCommand=none', '-oPermitLocalCommand=no')


class RuntimeFailure(Exception):
    """Fixed diagnostic; no remote payload/log disclosure."""


def require(value, reason):
    if not value:
        raise RuntimeFailure(reason)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(argv, data=b''):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=TIMEOUT, check=False)
    require(len(result.stdout) <= MAX_OUTPUT and len(result.stderr) <= MAX_OUTPUT, 'response_limit')
    require(result.returncode == 0, 'command_failed')
    return result.stdout


def alias_guard(raw):
    config = {}
    for line in raw.decode('utf-8').splitlines():
        key, value = line.split(' ', 1)
        config.setdefault(key, []).append(value)
    require(all(config.get(k) == [v] for k, v in
                {'hostname':'pi-force-one', 'user':'leadt3ch', 'port':'22'}.items()), 'target_mismatch')
    for key in ('proxycommand', 'proxyjump', 'remotecommand', 'localcommand', 'controlpath'):
        require(config.get(key, ['none']) == ['none'], 'alias_wrapper')
    require(config.get('controlmaster', ['false']) in (['false'], ['no'])
            and config.get('permitlocalcommand', ['no']) == ['no'], 'alias_wrapper')


# Fixed probe; stdin contains only a previously observed installation binding.
ROOT_GUARD = r'''
import os, stat, pwd, grp, json, hashlib, platform, subprocess, sys
assert os.geteuid()==0 and platform.node()=='pi-force-one' and platform.machine()=='aarch64'
assert open('/proc/device-tree/model','rb').read().startswith(b'Raspberry Pi ')
expected=json.load(sys.stdin)
n='typesafe-collection'; runtime='/srv/automation/'+n; state='/var/lib/automation/state/'+n
unit='/etc/systemd/system/'+n+'.service'; config='/etc/automation/'+n+'/projects.json'
u=pwd.getpwnam(n); g=grp.getgrnam(n)
assert u.pw_uid!=0 and u.pw_gid==g.gr_gid and u.pw_dir=='/nonexistent' and u.pw_shell=='/usr/sbin/nologin' and not g.gr_mem
def meta(p,uid,mode,directory=False):
 s=os.lstat(p)
 assert (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode))
 assert s.st_uid==uid and stat.S_IMODE(s.st_mode)==mode
 if not directory: assert s.st_nlink==1
 return dict(uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),device=s.st_dev,inode=s.st_ino)
for p in (runtime,'/etc/automation/'+n,state,'/run/'+n,unit):
 q=os.path.dirname(p)
 while True:
  s=os.lstat(q); assert stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_mode&1
  if q=='/': break
  q=os.path.dirname(q)
receipt=runtime+'/install-receipt.jsonl'
meta(receipt,0,0o600)
b=open(receipt,'rb').read(); assert len(b)<65536
rows=[json.loads(x) for x in b.splitlines()]
assert rows[0]['action']=='begin' and rows[-1]=={'action':'complete','activation':'not_performed'}
assert rows[0]['core_sha256']=='d10f0e6a70be329cbbc939a491224c2e26530fd4b1873e425b257926446fd0e2'
assert rows[0]['unit_sha256']=='b320ea935b19c5b8368bcc1a8af13ccc5d2d66be63adc94fe5e1a8446e80e930'
created={r['path']:r['metadata'] for r in rows if r['action']=='created'}
for p,uid,mode,directory in [(runtime,0,0o755,True),('/etc/automation/'+n,0,0o755,True),(state,u.pw_uid,0o700,True),(runtime+'/typesafe_collection.py',0,0o644,False),(config,0,0o644,False),(unit,0,0o644,False)]:
 m=meta(p,uid,mode,directory); assert all(created[p][k]==v for k,v in m.items())
 if not directory: assert hashlib.sha256(open(p,'rb').read()).hexdigest()==created[p]['sha256']
for p,h in [(runtime+'/typesafe_collection.py','d10f0e6a70be329cbbc939a491224c2e26530fd4b1873e425b257926446fd0e2'),(unit,'b320ea935b19c5b8368bcc1a8af13ccc5d2d66be63adc94fe5e1a8446e80e930'),(config,'46f0391c62a9754e7ea4b7a94eb0e3332f95abeef096af44e6c66ac71ccd4f3c')]:
 assert hashlib.sha256(open(p,'rb').read()).hexdigest()==h
def ctl(*a):
 r=subprocess.run(['systemctl',*a],capture_output=True,text=True,timeout=15); assert r.returncode==0 and not r.stderr.strip(); return r.stdout.strip()
assert ctl('show',n+'.service','--property=FragmentPath','--value')==unit
assert not ctl('show',n+'.service','--property=DropInPaths','--value')
assert ctl('show',n+'.service','--property=User','--value')==n
assert ctl('show',n+'.service','--property=Group','--value')==n
assert ctl('is-enabled',n+'.service')=='enabled'
assert meta(state,u.pw_uid,0o700,True)['gid']==g.gr_gid
db=state+'/events.sqlite'; meta(db,u.pw_uid,0o600)
binding={'receipt_sha256':hashlib.sha256(b).hexdigest(),'uid':u.pw_uid,'gid':g.gr_gid,'runtime_inode':os.lstat(runtime).st_ino,'state_inode':os.lstat(state).st_ino,'unit_inode':os.lstat(unit).st_ino}
if expected is not None: assert binding==expected
active=ctl('show',n+'.service','--property=ActiveState','--value')
if active=='active':
 meta('/run/'+n,u.pw_uid,0o700,True)
 s=os.lstat('/run/'+n+'/ingest.sock'); assert stat.S_ISSOCK(s.st_mode) and s.st_uid==u.pw_uid and stat.S_IMODE(s.st_mode)==0o600
 pid=int(ctl('show',n+'.service','--property=MainPID','--value')); assert pid>0 and os.stat('/proc/'+str(pid)).st_uid==u.pw_uid
else: assert active=='inactive'
'''
SERVICE_PREFIX = r'''
import os, sys, json, importlib.util, hashlib, sqlite3, uuid
p='/srv/automation/typesafe-collection/typesafe_collection.py'
assert hashlib.sha256(open(p,'rb').read()).hexdigest()=='d10f0e6a70be329cbbc939a491224c2e26530fd4b1873e425b257926446fd0e2'
s=importlib.util.spec_from_file_location('collection',p); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
projects=c.load_projects('/etc/automation/typesafe-collection/projects.json')
assert projects=={'synthetic-a','synthetic-b'}
db='/var/lib/automation/state/typesafe-collection/events.sqlite'
'''
INVENTORY = SERVICE_PREFIX + r'''
with c.Collection(db,projects=projects) as store:
 events=store.events()
 print(json.dumps({e['event_id']:{'project':e['binding']['project_id'],'sha256':c.payload_hash(c.canonical_wire(e,projects=projects))} for e in events},sort_keys=True))
'''
BACKUP = SERVICE_PREFIX + r'''
from datetime import datetime, timezone
p='/var/lib/automation/state/typesafe-collection/drill-'+uuid.uuid4().hex
os.mkdir(p,0o700)
with c.Collection(db,projects=projects) as store:
 live=store.events()
 store.backup(p+'/snapshot.sqlite')
with c.Collection(p+'/snapshot.sqlite',projects=projects) as store: before=store.events()
c.restore(p+'/snapshot.sqlite',p+'/restored.sqlite',projects=projects)
with c.Collection(p+'/restored.sqlite',projects=projects) as store: after=store.events()
assert live==before==after
for name in ('snapshot.sqlite','restored.sqlite'):
 connection=sqlite3.connect(p+'/'+name)
 try: assert connection.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 finally: connection.close()
canonical=[c.canonical_wire(e,projects=projects) for e in before]
print(json.dumps({'path':p,'events':len(before),'canonical_sha256':hashlib.sha256(b'\n'.join(canonical)).hexdigest(),'integrity':'ok','complete_values_equal':True,'observed_at':datetime.now(timezone.utc).isoformat()}))
'''
DENY_UID = r'''
import socket, errno, json
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(3)
try:
 try: s.connect('/run/typesafe-collection/ingest.sock')
 except PermissionError as e: assert e.errno==errno.EACCES; print(json.dumps({'denied':True}))
 else: raise AssertionError('foreign_uid_reached_socket')
finally: s.close()
'''


class Remote:
    """One pinned host, finite fixed probes, no generic operator interface."""
    def __init__(self, target, *, run=command):
        require(target == TARGET, 'target_not_allowed')
        self.run, self.binding = run, None

    def preflight(self):
        alias_guard(self.run(['/usr/bin/ssh', '-G', '-oBatchMode=yes', TARGET]))
        peers = json.loads(self.run(['tailscale', 'status', '--json']))
        matches = [p for p in peers.get('Peer', {}).values() if p.get('HostName') == 'pi-force-one']
        require(len(matches) == 1 and matches[0].get('Online') is True, 'independent_target_missing')
        self.guard(require_active=True)

    def _probe(self, code, *, user=None, data=b''):
        argv = ['sudo', '-n'] + (['-u', user] if user else []) + ['/usr/bin/python3', '-I', '-c', code]
        return json.loads(self.run([*SSH, TARGET, shlex.join(argv)], data))

    def guard(self, *, require_active=False):
        result = self._probe(ROOT_GUARD + "\nprint(json.dumps({'binding':binding,'active':active}))\n",
                             data=json.dumps(self.binding).encode())
        require(type(result) is dict and set(result) == {'binding', 'active'}, 'invalid_guard')
        b = result['binding']
        require(type(b) is dict and set(b) == {'receipt_sha256','uid','gid','runtime_inode','state_inode','unit_inode'}
                and type(b['receipt_sha256']) is str and len(b['receipt_sha256']) == 64
                and all(type(b[k]) is int and b[k] > 0 for k in b if k != 'receipt_sha256'), 'invalid_binding')
        if self.binding is not None:
            require(b == self.binding, 'installation_drift')
        require(result['active'] in ('active','inactive') and (not require_active or result['active']=='active'), 'not_active')
        self.binding = b
        return result

    def cycle(self, action):
        require(action in ('stop', 'start') and self.binding is not None, 'cycle_not_bound')
        self.inventory()  # Public Collection audit rejects foreign/corrupt DBs before a cycle.
        self.guard(require_active=action == 'stop')
        code = ROOT_GUARD + ("\nassert expected is not None\nctl('stop',n+'.service')\n" if action == 'stop'
                             else "\nassert expected is not None\nctl('start',n+'.service')\n")
        self._probe(code + "print(json.dumps({'cycled':True}))\n", data=json.dumps(self.binding).encode())

    def inventory(self):
        self.guard()
        result = self._probe(INVENTORY, user=NAME)
        require(type(result) is dict, 'invalid_inventory')
        return result

    def deny_uid(self):
        self.guard(require_active=True)
        require(self._probe(DENY_UID, user='nobody') == {'denied':True}, 'uid_not_denied')

    def backup(self):
        self.guard(require_active=True)
        result = self._probe(BACKUP, user=NAME)
        require(result.get('integrity') == 'ok' and result.get('complete_values_equal') is True, 'restore_failed')
        return result


def synthetic_wires(c, nonce):
    pc = load('runtime_comparison', ROOT / '.apm/skills/core-typesafe/scripts/plan_comparison.py')
    result = []
    for project in sorted(PROJECTS):
        plan = ('synthetic T05 ' + nonce + project).encode()
        criteria = {'AC01':'Synthetic criterion, not a real evaluation'}
        binding = pc.bind_plan(project_id=project, plan_ref='synthetic-plan', plan_bytes=plan, criteria=criteria)
        review = pc.fix_review(binding, plan_bytes=plan, criteria=criteria, review_ref='synthetic-review',
                               review_bytes=b'synthetic fixed initial review', verdicts={'AC01':'no_defect_found'},
                               reviewer_role='synthetic-reviewer', recorded_at='2026-11-10T00:00:00Z')
        model = pc.model_event(binding, criterion_id='AC01', selection='eligible', evaluation={
            'profile':'synthetic','outcome':'unresolved','uncertainty':'unassessed',
            'answers':{'synthetic':{'type':'noul','noul':0.5}},'error':None,'http_status':None,
            'request_sent':False,'requested_model':'synthetic','response_model':'synthetic',
            'question_version':'synthetic-v1','question_fingerprint':'a'*64,'core_version':'synthetic-v1',
            'duration_seconds':None,'usage':{'input_tokens':None,'output_tokens':None}})
        comparison = pc.comparison_event(model, review, plan_bytes=plan, criteria=criteria,
                                         review_bytes=b'synthetic fixed initial review', adjudication={
                                             'label':'unresolved','evidence_ref':'synthetic-evidence',
                                             'reviewer_role':'synthetic-reviewer','recorded_at':'2026-11-10T00:00:01Z'})
        result.extend(c.project_event(e, projects=PROJECTS) for e in (model, comparison))
    return result


def expected_events(c, wires):
    return {json.loads(b)['event_id']:{'project':json.loads(b)['binding']['project_id'],
                                      'sha256':c.payload_hash(b)} for b in wires}


def check_added(before, after, expected):
    require(not (set(before) & set(expected)), 'fixture_identity_collision')
    require(after == {**before, **expected}, 'event_values_or_count_mismatch')


def process_reopen(queue):
    """A new interpreter audits the durable queue; no transport in this child."""
    code = """
import importlib.util,sys,json,hashlib
s=importlib.util.spec_from_file_location('collection',sys.argv[1])
c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
with c.Outbox(sys.argv[2],projects={'synthetic-a','synthetic-b'}) as box:
 print(json.dumps([hashlib.sha256(b).hexdigest() for b in box.pending()]))
"""
    return json.loads(command([sys.executable, '-B', '-I', '-c', code,
                               str(ROOT/'scripts/typesafe_collection.py'), str(queue)]))


def run_acceptance(remote, c, *, directory, nonce):
    remote.preflight()
    baseline = remote.inventory()
    wires = synthetic_wires(c, nonce)
    expected = expected_events(c, wires)
    require(not (set(baseline) & set(expected)), 'fixture_identity_collision')
    queue = Path(directory) / 'outbox.sqlite'
    sender = c.SSHSender(TARGET)
    with c.Outbox(queue, projects=PROJECTS, create=True) as box:
        for wire in wires: box.enqueue(wire)
    # Only the ACK is discarded; the first receiver commit is real.
    ack_received = False
    def lose_ack(data, deadline):
        nonlocal ack_received
        ack = json.loads(sender(data, deadline))
        require(ack == {'event_id':json.loads(data)['event_id'], 'payload_sha256':c.payload_hash(data)}, 'real_ack_mismatch')
        ack_received = True
        raise c.CollectionError('synthetic_ack_lost')
    with c.Outbox(queue, projects=PROJECTS) as box:
        try: box.flush(lose_ack)
        except c.CollectionError: pass
        else: raise RuntimeFailure('lost_ack_not_observed')
        require(ack_received and box.pending() == wires, 'lost_ack_queue_changed')
    check_added(baseline, remote.inventory(), expected_events(c,wires[:1]))
    with c.Outbox(queue, projects=PROJECTS) as box:
        require(box.flush(sender) == len(wires) and not box.pending(), 'flush_incomplete')
    check_added(baseline, remote.inventory(), expected)
    for wire in wires:
        with c.Outbox(queue, projects=PROJECTS) as box:
            box.enqueue(wire); require(box.flush(sender) == 1, 'replay_failed')
    require(remote.inventory() == {**baseline,**expected}, 'duplicate_inserted')
    remote.deny_uid()
    before_invalid = remote.inventory()
    invalid = json.loads(wires[0]); invalid['binding']['project_id'] = 'synthetic-denied'
    conflict = json.loads(wires[0])
    conflict['observation']['probabilities']['synthetic']['noul'] = 0.75
    for payload in (json.dumps(invalid).encode(), b'{"schema":"invalid"}', json.dumps(conflict).encode()):
        try: sender(payload, time.monotonic()+15)
        except c.CollectionError: pass
        else: raise RuntimeFailure('invalid_accepted')
        require(remote.inventory() == before_invalid, 'invalid_mutated_db')
    later = synthetic_wires(c, nonce+'-outage')
    later_expected = expected_events(c, later)
    with c.Outbox(queue, projects=PROJECTS) as box:
        for wire in later: box.enqueue(wire)
    remote.cycle('stop')
    try:
        with c.Outbox(queue, projects=PROJECTS) as box:
            try: box.flush(sender)
            except c.CollectionError: pass
            else: raise RuntimeFailure('stopped_service_accepted')
            require(box.pending() == later, 'outage_queue_changed')
        require(process_reopen(queue) == [c.payload_hash(b) for b in later], 'process_reopen_lost_events')
        with c.Outbox(queue, projects=PROJECTS) as box:
            require(box.pending() == later, 'reopen_lost_events')
    finally:
        remote.cycle('start')
    remote.guard(require_active=True)
    with c.Outbox(queue, projects=PROJECTS) as box:
        require(box.flush(sender) == len(later) and not box.pending(), 'recovery_incomplete')
    check_added({**baseline,**expected}, remote.inventory(), later_expected)
    backup = remote.backup()
    require(backup['events'] == len(baseline)+len(expected)+len(later_expected), 'snapshot_count_mismatch')
    require(remote.inventory() == {**baseline,**expected,**later_expected}, 'backup_mutated_live')
    remote.guard(require_active=True)
    return {'status':'pass','baseline_events':len(baseline),'new_events':len(expected)+len(later_expected),
            'projects':sorted(PROJECTS),'ack_loss_replay':True,'outage_reopen':True,
            'uid_project_payload_denied':True,'backup':backup,'local_outbox':str(queue),
            'binding':remote.binding,'unit':'enabled/active','core_sha256':CORE_SHA256,'unit_sha256':UNIT_SHA256}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ssh-target', required=True, choices=[TARGET])
    parser.add_argument('--allow-own-service-cycle', action='store_true')
    args = parser.parse_args(argv)
    try:
        require(args.allow_own_service_cycle, 'service_cycle_not_authorized')
        source = ROOT / 'scripts/typesafe_collection.py'
        require(hashlib.sha256(source.read_bytes()).hexdigest()==CORE_SHA256, 'local_source_drift')
        c = load('runtime_collection', source)
        directory = tempfile.mkdtemp(prefix='typesafe-collection-T05-', dir='/tmp/opencode')
        print('retained_local_drill='+directory, flush=True)
        result = run_acceptance(Remote(args.ssh_target), c, directory=directory, nonce=uuid.uuid4().hex)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (RuntimeFailure, OSError, ValueError, subprocess.SubprocessError) as error:
        print('runtime_check_failed:'+(str(error) if isinstance(error,RuntimeFailure) else type(error).__name__), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
