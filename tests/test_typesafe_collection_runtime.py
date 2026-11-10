"""T05 offline guards; no external SSH, accounts or systemd actions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('runtime_check', ROOT/'scripts/check_typesafe_collection_runtime.py')
c = load('runtime_store', ROOT/'scripts/typesafe_collection.py')
ALIAS = b'hostname pi-force-one\nuser leadt3ch\nport 22\ncontrolmaster false\npermitlocalcommand no\n'
BINDING = dict(receipt_sha256='a'*64, uid=991, gid=991, runtime_inode=1, state_inode=2, unit_inode=3)


class FakeSSH:
    def __init__(self):
        self.calls = []
        self.binding = dict(BINDING)
        self.active = 'active'
        self.alias = ALIAS
        self.online = True

    def __call__(self, argv, data=b''):
        self.calls.append((argv,data))
        if '-G' in argv: return self.alias
        if argv[0] == 'tailscale':
            return json.dumps({'Peer':{'one':{'HostName':'pi-force-one','Online':self.online}}}).encode()
        self_check = shlex.split(argv[-1])
        code = self_check[-1]
        if "ctl('stop',n+'.service')" in code: self.active = 'inactive'; return b'{"cycled":true}'
        if "ctl('start',n+'.service')" in code: self.active = 'active'; return b'{"cycled":true}'
        if code == r.INVENTORY: return b'{}'
        return json.dumps({'binding':self.binding,'active':self.active}).encode()


class RuntimeTests(unittest.TestCase):
    def test_target_rejected_before_any_process(self):
        for target in ('pi-force-one','other','pfo;id','pfo -L22'):
            fake = FakeSSH()
            with self.assertRaises(r.RuntimeFailure): r.Remote(target,run=fake)
            self.assertEqual(fake.calls,[])

    def test_alias_exact_endpoint_and_wrappers(self):
        r.alias_guard(ALIAS)
        for raw in (ALIAS.replace(b'leadt3ch',b'root'),ALIAS.replace(b'port 22',b'port 2223'),
                    ALIAS.replace(b'pi-force-one',b'foreign'),ALIAS+b'hostname pi-force-one\n',
                    ALIAS+b'proxycommand wrapper\n',ALIAS+b'remotecommand wrapper\n',
                    ALIAS+b'localcommand wrapper\n',ALIAS+b'controlpath /tmp/mux\n'):
            with self.assertRaises(r.RuntimeFailure): r.alias_guard(raw)

    def test_independent_peer_required_before_remote_probe(self):
        fake = FakeSSH(); fake.online = False
        with self.assertRaises(r.RuntimeFailure): r.Remote('pfo',run=fake).preflight()
        self.assertEqual(len(fake.calls),2)

    def test_cycle_binding_fixed_argv_stdin_and_drift(self):
        fake = FakeSSH(); remote = r.Remote('pfo',run=fake)
        with self.assertRaises(r.RuntimeFailure): remote.cycle('stop')
        remote.preflight(); remote.cycle('stop'); remote.cycle('start')
        for argv,data in fake.calls:
            if argv[0]!='tailscale' and '-G' not in argv:
                self.assertEqual(argv[:-2],list(r.SSH)); self.assertEqual(argv[-2],'pfo')
                self.assertIn('-oStrictHostKeyChecking=yes',argv)
                self.assertIn('-oUpdateHostKeys=no',argv)
                self.assertNotIn(json.dumps(BINDING),argv[-1])
        stop = [(a,d) for a,d in fake.calls if "ctl('stop',n+" in shlex.split(a[-1])[-1]]
        self.assertEqual(len(stop),1); self.assertEqual(json.loads(stop[0][1]),BINDING)
        with self.assertRaises(r.RuntimeFailure): remote.cycle('restart')
        fake.binding['receipt_sha256']='b'*64
        count=len(fake.calls)
        with self.assertRaises(r.RuntimeFailure): remote.cycle('stop')
        self.assertEqual(len(fake.calls),count+1)

    def test_remote_probes_are_syntax_valid_and_hash_bound(self):
        for code in (r.ROOT_GUARD,r.INVENTORY,r.BACKUP,r.DENY_UID): compile(code,'remote','exec')
        self.assertIn(r.CORE_SHA256,r.ROOT_GUARD); self.assertIn(r.UNIT_SHA256,r.ROOT_GUARD)
        for check in ('install-receipt.jsonl',"rows[-1]",'created[p]',"s.st_nlink==1",'DropInPaths',"stat.S_ISSOCK"):
            self.assertIn(check,r.ROOT_GUARD)
        self.assertIn('live==before==after',r.BACKUP)
        self.assertIn('PRAGMA integrity_check',r.BACKUP)
        self.assertNotIn('os.chmod',r.ROOT_GUARD)
        self.assertNotIn('os.chown',r.ROOT_GUARD)

    def test_service_cycle_flag_before_any_process(self):
        with patch.object(r,'command',side_effect=AssertionError('external process')):
            self.assertEqual(r.main(['--ssh-target','pfo']),1)

    def test_synthetic_public_api_two_projects_no_live_answer(self):
        wires=r.synthetic_wires(c,'offline')
        self.assertEqual(len(wires),4)
        self.assertEqual({json.loads(b)['binding']['project_id'] for b in wires},r.PROJECTS)
        self.assertEqual(len(r.expected_events(c,wires)),4)
        for data in wires:
            e=c.parse_wire(data,projects=r.PROJECTS)
            self.assertEqual(e['observation']['response_model'],'synthetic')
            self.assertFalse(e['observation']['request_sent'])
            self.assertNotIn(b'Synthetic criterion',data)

    def test_ack_hash_failure_reopen_and_exact_backup_values(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode',prefix='T05-offline-') as home:
            p=Path(home); wires=r.synthetic_wires(c,'offline-reopen')
            with c.Collection(p/'events.sqlite',projects=r.PROJECTS,create=True) as store:
                with c.Outbox(p/'queue.sqlite',projects=r.PROJECTS,create=True) as box:
                    for wire in wires: box.enqueue(wire)
                    def lose(data,deadline):
                        store.submit(data); raise c.CollectionError('lost')
                    with self.assertRaises(c.CollectionError): box.flush(lose)
                    self.assertEqual(box.pending(),wires)
                self.assertEqual(r.process_reopen(p/'queue.sqlite'),[c.payload_hash(b) for b in wires])
                with c.Outbox(p/'queue.sqlite',projects=r.PROJECTS) as box:
                    def bad(data,deadline):
                        a=store.submit(data); a['payload_sha256']='0'*64; return json.dumps(a).encode()
                    with self.assertRaises(c.CollectionError): box.flush(bad)
                    self.assertEqual(box.pending(),wires)
                    self.assertEqual(box.flush(lambda data,deadline:json.dumps(store.submit(data)).encode()),4)
                    self.assertEqual(box.pending(),[])
                expected=store.events(); store.backup(p/'snapshot.sqlite')
                c.restore(p/'snapshot.sqlite',p/'restored.sqlite',projects=r.PROJECTS)
                with c.Collection(p/'restored.sqlite',projects=r.PROJECTS) as restored:
                    self.assertEqual(expected,restored.events())
                with self.assertRaises(c.CollectionError): c.restore(p/'snapshot.sqlite',p/'events.sqlite',projects=r.PROJECTS)
                self.assertEqual(store.events(),expected)

    def test_baseline_and_full_hash_comparison_not_global_count(self):
        before={'old':{'project':'synthetic-a','sha256':'old'}}
        extra={'new':{'project':'synthetic-b','sha256':'new'}}
        r.check_added(before,{**before,**extra},extra)
        for after in ({**before,'new':{'project':'synthetic-a','sha256':'new'}},extra, before):
            with self.assertRaises(r.RuntimeFailure): r.check_added(before,after,extra)
        with self.assertRaises(r.RuntimeFailure): r.check_added(before,before,before)

    def test_full_acceptance_fake_ssh_real_queue_store_and_second_baseline(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode',prefix='T05-flow-') as home:
            p=Path(home)
            with c.Collection(p/'events.sqlite',projects=r.PROJECTS,create=True) as store:
                class OwnComponent:
                    binding = dict(BINDING)
                    active = True
                    actions = []
                    def preflight(self): pass
                    def guard(self,**kwargs):
                        if kwargs.get('require_active'): self_outer.assertTrue(self.active)
                    def inventory(self):
                        return r.expected_events(c,[c.canonical_wire(e,projects=r.PROJECTS) for e in store.events()])
                    def deny_uid(self): pass  # Only CK08 proves an actual different UID.
                    def cycle(self,action):
                        self.actions.append(action); self.active = action=='start'
                    def backup(self):
                        d=p/('drill-'+str(len(self.actions))); d.mkdir(mode=0o700)
                        store.backup(d/'snapshot.sqlite')
                        c.restore(d/'snapshot.sqlite',d/'restored.sqlite',projects=r.PROJECTS)
                        with c.Collection(d/'restored.sqlite',projects=r.PROJECTS) as restored:
                            self_outer.assertEqual(store.events(),restored.events())
                        return {'events':len(store.events()),'integrity':'ok','complete_values_equal':True}
                self_outer=self
                component=OwnComponent()
                sent=[]
                def sender(data,deadline):
                    sent.append(data)
                    if not component.active: raise c.CollectionError('outage')
                    return json.dumps(store.submit(data)).encode()
                with patch.object(c,'SSHSender',return_value=sender):
                    for i in range(2):
                        d=p/('local-'+str(i)); d.mkdir(mode=0o700)
                        result=r.run_acceptance(component,c,directory=d,nonce='offline-'+str(i))
                        self.assertEqual(result['status'],'pass')
                        self.assertEqual(result['baseline_events'],8*i)
                        self.assertEqual(result['new_events'],8)
                self.assertEqual(component.actions,['stop','start','stop','start'])
                self.assertTrue(component.active)
                self.assertEqual(len(store.events()),16)
                self.assertGreater(len(sent),16)

    def test_failed_remote_hash_or_foreign_resource_cannot_cycle(self):
        fake=FakeSSH(); remote=r.Remote('pfo',run=fake); remote.preflight()
        def refused(argv,data=b''):
            raise r.RuntimeFailure('remote_guard_refused')
        remote.run=refused
        with self.assertRaises(r.RuntimeFailure): remote.cycle('stop')
        self.assertEqual(fake.active,'active')
        with patch.object(r.subprocess,'run',side_effect=AssertionError('external process')):
            with self.assertRaises(r.RuntimeFailure): r.Remote('foreign')

    def test_process_exit_and_size_fail_closed(self):
        for result in (subprocess.CompletedProcess([],1,b'',b''),
                       subprocess.CompletedProcess([],0,b'x'*(r.MAX_OUTPUT+1),b'')):
            with patch.object(r.subprocess,'run',return_value=result):
                with self.assertRaises(r.RuntimeFailure): r.command(['fake'])


if __name__=='__main__': unittest.main()
