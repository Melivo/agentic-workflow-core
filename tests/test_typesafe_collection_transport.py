"""T02 offline transport: real private Unix sockets/SQLite, SSH only fake children."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


c = load('transport_collection', ROOT / 'scripts/typesafe_collection.py')
pc = load('transport_comparison', ROOT / '.apm/skills/core-typesafe/scripts/plan_comparison.py')
PROJECTS = {'synthetic-a', 'synthetic-b'}
CONFIG = ('batchmode yes\nstricthostkeychecking true\nupdatehostkeys false\n'
          'forwardagent no\nforwardx11 no\nclearallforwardings yes\ncontrolmaster false\n'
          'requesttty false\npermitlocalcommand no\nhostname synthetic-host\nuser synthetic\nport 22\n')


def wire(project='synthetic-a', number=0):
    binding = pc.bind_plan(project_id=project, plan_ref='private.md',
                           plan_bytes=('synthetic-' + str(number)).encode(), criteria={'AC01': 'Synthetic prose'})
    event = pc.model_event(binding, criterion_id='AC01', selection='eligible', evaluation={
        'profile': 'synthetic', 'outcome': 'unresolved', 'uncertainty': 'unassessed',
        'answers': {'q': {'type': 'noul', 'noul': 0.5}}, 'error': None,
        'http_status': None, 'request_sent': True, 'requested_model': 'synthetic',
        'response_model': 'synthetic', 'question_version': 'v1',
        'question_fingerprint': 'a' * 64, 'core_version': 'v1', 'duration_seconds': None,
        'usage': {'input_tokens': None, 'output_tokens': 0}})
    return c.project_event(event, projects=PROJECTS)


def ack(data):
    return json.dumps({'event_id': json.loads(data)['event_id'],
                       'payload_sha256': c.payload_hash(data)}).encode()


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='tc-', dir='/tmp/opencode')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.queue = self.home / 'queue.sqlite'
        self.store = self.home / 'events.sqlite'
        self.sock = self.home / 'ingest.sock'
        self.config = self.home / 'projects.json'
        self.config.write_text(json.dumps({'projects': sorted(PROJECTS)}))
        self.config.chmod(0o600)
        self.data = wire()

    def outbox(self, **kwargs):
        return c.Outbox(self.queue, projects=PROJECTS, **kwargs)

    def cli(self, *args, data=None):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/typesafe_collection.py'),
                               *args, '--projects', str(self.config)], input=data,
                              capture_output=True, timeout=10)

    def fake(self, body):
        path = self.home / 'fake-ssh'
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o700)
        return str(path)

    def test_enqueue_commit_reopen_outage_wrong_and_lost_ack(self):
        with self.outbox(create=True) as box:
            receipt = box.enqueue(self.data)
            self.assertEqual(receipt, json.loads(ack(self.data)))
            box.enqueue(self.data)
            self.assertEqual(box.pending(), [self.data])
        with self.outbox() as box:
            with self.assertRaises(c.CollectionError):
                box.flush(c.UnixSender(self.sock))
            self.assertEqual(box.pending(), [self.data])
            with c.Collection(self.store, projects=PROJECTS, create=True) as db:
                def lost(data, deadline):
                    db.submit(data)
                    return b''
                with self.assertRaises(c.CollectionError):
                    box.flush(lost)
                def wrong(data, deadline):
                    receipt = db.submit(data)
                    receipt['payload_sha256'] = 'b' * 64
                    return json.dumps(receipt).encode()
                with self.assertRaises(c.CollectionError):
                    box.flush(wrong)
                self.assertEqual(box.pending(), [self.data])
                self.assertEqual(len(db.events()), 1)
                self.assertEqual(box.flush(lambda data, deadline: json.dumps(db.submit(data)).encode()), 1)
                self.assertEqual(box.pending(), [])
                self.assertEqual(len(db.events()), 1)

    def test_queue_full_bytes_and_identity_conflict_preserve(self):
        with self.outbox(create=True, max_events=1) as box:
            box.enqueue(self.data)
            box.enqueue(self.data)
            with self.assertRaisesRegex(c.CollectionError, 'outbox_full'):
                box.enqueue(wire('synthetic-b'))
            other = json.loads(self.data)
            other['selection'] = 'unknown'
            with self.assertRaisesRegex(c.CollectionError, 'payload_conflict'):
                box.enqueue(json.dumps(other).encode())
            self.assertEqual(box.pending(), [self.data])
        with c.Outbox(self.home / 'small.sqlite', projects=PROJECTS, create=True,
                      max_bytes=len(self.data) - 1) as box:
            with self.assertRaisesRegex(c.CollectionError, 'outbox_full'):
                box.enqueue(self.data)
            self.assertEqual(box.pending(), [])

    def test_commit_failure_enqueue_and_ack_delete_preserve(self):
        with self.outbox(create=True) as box:
            # Real SQLite authorizer denies COMMIT, as for failed durable commit.
            box._connection.set_authorizer(lambda action, arg, *rest:
                sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg == 'COMMIT' else sqlite3.SQLITE_OK)
            with self.assertRaises(c.CollectionError):
                box.enqueue(self.data)
            box._connection.set_authorizer(None)
            self.assertEqual(box.pending(), [])
            box.enqueue(self.data)
            box._connection.set_authorizer(lambda action, arg, *rest:
                sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg == 'COMMIT' else sqlite3.SQLITE_OK)
            with self.assertRaises(c.CollectionError):
                box.flush(lambda data, deadline: ack(data))
            box._connection.set_authorizer(None)
            self.assertEqual(box.pending(), [self.data])
        with self.outbox() as box:
            self.assertEqual(box.pending(), [self.data])

    def test_concurrent_enqueue_capacity_and_flush_idempotent(self):
        with self.outbox(create=True):
            pass
        def enqueue(data):
            with self.outbox(max_events=1) as box:
                try:
                    box.enqueue(data)
                    return True
                except c.CollectionError:
                    return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(enqueue, (self.data, wire('synthetic-b')))), 1)
        barrier = threading.Barrier(2)
        def flush(_):
            with self.outbox() as box:
                def send(data, deadline):
                    barrier.wait(timeout=2)
                    return ack(data)
                return box.flush(send)
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(list(pool.map(flush, range(2))), [1, 1])
        with self.outbox() as box:
            self.assertEqual(box.pending(), [])

    def test_flush_limits_and_deadline(self):
        with self.outbox(create=True) as box:
            for n in range(102):
                box.enqueue(wire(number=n))
            self.assertEqual(box.flush(lambda data, deadline: ack(data)), 100)
            self.assertEqual(len(box.pending()), 2)
            with self.assertRaises(c.CollectionError):
                box.flush(lambda data, deadline: ack(data), limit=101)
            with self.assertRaises(c.CollectionError):
                box.flush(lambda data, deadline: ack(data), timeout=16)
            with patch.object(c.time, 'monotonic', side_effect=[10, 11]):
                with self.assertRaisesRegex(c.CollectionError, 'transport_timeout'):
                    box.flush(lambda data, deadline: ack(data), timeout=0.1)
            self.assertEqual(len(box.pending()), 2)

    def test_queue_paths_foreign_schema_and_tamper_refused(self):
        with self.outbox(create=True) as box:
            box.enqueue(self.data)
        self.queue.chmod(0o644)
        with self.assertRaises(c.CollectionError):
            self.outbox()
        self.queue.chmod(0o600)
        alias = self.home / 'alias'
        alias.symlink_to(self.queue)
        with self.assertRaises(c.CollectionError):
            c.Outbox(alias, projects=PROJECTS)
        with self.assertRaises(c.CollectionError):
            self.outbox(create=True)
        db = sqlite3.connect(self.queue)
        try:
            with db:
                db.execute("UPDATE queue SET payload_sha256=?", ('b' * 64,))
        finally:
            db.close()
        with self.assertRaises(c.CollectionError):
            self.outbox()
        with c.Collection(self.store, projects=PROJECTS, create=True):
            pass
        with self.assertRaises(c.CollectionError):
            c.Outbox(self.store, projects=PROJECTS)

    def test_real_socket_two_projects_commit_before_ack(self):
        ready, stop = threading.Event(), threading.Event()
        errors = []
        def serve():
            try:
                with c.Collection(self.store, projects=PROJECTS, create=True) as db:
                    with c.UnixServer(db, self.sock) as server:
                        ready.set()
                        while not stop.is_set():
                            server.serve_once(timeout=0.05)
            except BaseException as exc:
                errors.append(exc)
                ready.set()
        thread = threading.Thread(target=serve)
        thread.start()
        self.assertTrue(ready.wait(3))
        try:
            self.assertEqual(errors, [])
            with self.outbox(create=True) as box:
                box.enqueue(self.data)
                box.enqueue(wire('synthetic-b'))
                self.assertEqual(box.flush(c.UnixSender(self.sock)), 2)
                self.assertEqual(box.pending(), [])
            with c.Collection(self.store, projects=PROJECTS) as db:
                self.assertEqual({e['binding']['project_id'] for e in db.events()}, PROJECTS)
            reply = c.UnixSender(self.sock)(self.data, time.monotonic() + 2)
            self.assertEqual(json.loads(reply), json.loads(ack(self.data)))
        finally:
            stop.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(self.sock.exists())

    def test_socket_collision_stale_active_symlink_and_lock_cleanup(self):
        with c.Collection(self.store, projects=PROJECTS, create=True) as db:
            self.sock.write_text('foreign')
            with self.assertRaises(c.CollectionError):
                c.UnixServer(db, self.sock)
            self.assertEqual(self.sock.read_text(), 'foreign')
            self.sock.unlink()
            stale = socket.socket(socket.AF_UNIX)
            stale.bind(str(self.sock))
            self.sock.chmod(0o600)
            stale.close()
            with c.UnixServer(db, self.sock):
                with self.assertRaises(c.CollectionError):
                    c.UnixServer(db, self.sock)
            self.assertFalse(self.sock.exists())
            self.sock.symlink_to(self.store)
            with self.assertRaises(c.CollectionError):
                c.UnixServer(db, self.sock)
            self.assertTrue(self.sock.is_symlink())
            self.sock.unlink()
            # An active own socket without our flock must still never be unlinked.
            with socket.socket(socket.AF_UNIX) as active:
                active.bind(str(self.sock))
                self.sock.chmod(0o600)
                active.listen()
                inode = self.sock.stat().st_ino
                with self.assertRaises(c.CollectionError):
                    c.UnixServer(db, self.sock)
                self.assertEqual(self.sock.stat().st_ino, inode)

    def test_peer_uid_denied_and_server_commit_failure_no_ack(self):
        client, peer = socket.socketpair()
        with client, peer:
            with patch.object(c.os, 'geteuid', return_value=os.geteuid() + 1):
                with self.assertRaisesRegex(c.CollectionError, 'peer_denied'):
                    c._peer(client)
        with c.Collection(self.store, projects=PROJECTS, create=True) as db:
            with c.UnixServer(db, self.sock) as server:
                def request():
                    try:
                        return c.UnixSender(self.sock)(self.data, time.monotonic() + 2)
                    except c.CollectionError:
                        return None
                with ThreadPoolExecutor(1) as pool:
                    future = pool.submit(request)
                    with patch.object(db, 'submit', side_effect=c.CollectionError('storage_unavailable')):
                        self.assertFalse(server.serve_once())
                    self.assertIsNone(future.result(timeout=3))
                self.assertEqual(db.events(), [])

    def test_socket_read_absolute_deadline_and_oversize(self):
        left, right = socket.socketpair()
        with left, right:
            right.sendall(b'x' * 20)
            with self.assertRaisesRegex(c.CollectionError, 'message_too_large'):
                c._receive(left, 10, time.monotonic() + 0.2)
        left, right = socket.socketpair()
        with left, right:
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                c._receive(left, 10, started + 0.05)
            self.assertLess(time.monotonic() - started, 0.5)

    def test_ack_parser_closed_bounded_and_no_raw_error(self):
        for data in (b'', b'[]', b'x' * 257, b'{}', b'{"event_id":NaN}', b'\xff',
                     b'{"event_id":"x","event_id":"y","payload_sha256":"z"}'):
            with self.assertRaises(c.CollectionError):
                c._ack(data)
        self.assertEqual(c._ack(ack(self.data)), json.loads(ack(self.data)))

    def test_fake_ssh_fixed_command_stdin_and_overrides(self):
        log = self.home / 'argv.json'
        stdin = self.home / 'stdin.bin'
        exe = self.fake('import sys,json,hashlib\n'
            'from pathlib import Path\n'
            'if "-G" in sys.argv:\n    print(' + repr(CONFIG) + ')\n'
            'else:\n'
            '    data=sys.stdin.buffer.read()\n'
            '    Path(' + repr(str(log)) + ').write_text(json.dumps(sys.argv[1:]))\n'
            '    Path(' + repr(str(stdin)) + ').write_bytes(data)\n'
            '    print(json.dumps({"event_id":json.loads(data)["event_id"],"payload_sha256":hashlib.sha256(data).hexdigest()}))\n')
        reply = c.SSHSender('synthetic-alias', executable=exe)(self.data, time.monotonic() + 2)
        self.assertEqual(c._ack(reply), json.loads(ack(self.data)))
        argv = json.loads(log.read_text())
        self.assertEqual(argv[-2:], ['synthetic-alias', c.REMOTE_COMMAND])
        self.assertEqual(argv[:-2], list(c.SSH_OPTIONS))
        self.assertEqual(stdin.read_bytes(), self.data)
        self.assertNotIn(self.data.decode(), ' '.join(argv))
        for target in ('-oProxyCommand=x', 'a;b', 'user@host', 'host.example', '', 'a b'):
            with self.assertRaises(c.CollectionError):
                c.SSHSender(target)

    def test_fake_ssh_bad_effective_config_refused_before_send(self):
        exe = self.fake('print(' + repr(CONFIG + 'proxycommand evil\n') + ')\n')
        with self.assertRaises(c.CollectionError):
            c.SSHSender('synthetic', executable=exe)(self.data, time.monotonic() + 1)

    def test_process_timeout_output_limit_and_descendant_cleanup(self):
        pidfile = self.home / 'child.pid'
        exe = self.fake('import os,time\nfrom pathlib import Path\n'
            'pid=os.fork()\n'
            'if pid==0:\n    time.sleep(20)\nelse:\n'
            '    Path(' + repr(str(pidfile)) + ').write_text(str(pid))\n    time.sleep(20)\n')
        started = time.monotonic()
        with self.assertRaises(c.CollectionError):
            c._process([exe], b'x', started + 0.3)
        self.assertLess(time.monotonic() - started, 1)
        pid = int(pidfile.read_text())
        # Killed descendants can be zombies until their OS reaper runs, never senders.
        status = Path('/proc') / str(pid) / 'stat'
        deadline = time.monotonic() + 0.5
        while status.exists() and status.read_text().split()[2] != 'Z' and time.monotonic() < deadline:
            time.sleep(0.005)
        if status.exists():
            self.assertEqual(status.read_text().split()[2], 'Z')
        exe = self.fake('import sys\nsys.stdout.write("x"*4096)\n')
        with self.assertRaisesRegex(c.CollectionError, 'transport_output_limit'):
            c._process([exe], b'', time.monotonic() + 1)
        exe = self.fake('import sys\nsys.exit(1)\n')
        with self.assertRaises(c.CollectionError):
            c._process([exe], b'', time.monotonic() + 1)

    def test_cli_enqueue_flush_submit_snapshot_restore_and_no_adoption(self):
        result = self.cli('enqueue', '--outbox', str(self.queue), '--create', data=self.data)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('enqueue', '--outbox', str(self.queue), '--create', data=self.data)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b'collection_failed\n')
        # CLI receiver is an isolated local child, never a service/host operation.
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'scripts/typesafe_collection.py'),
            'serve', '--projects', str(self.config), '--database', str(self.store),
            '--socket', str(self.sock), '--create'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not self.sock.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertIsNone(process.poll())
            result = self.cli('flush', '--outbox', str(self.queue), '--socket', str(self.sock))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'sent': 1})
            result = self.cli('submit', '--socket', str(self.sock), data=self.data)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), json.loads(ack(self.data)))
            self.assertLessEqual(len(result.stdout), c.MAX_ACK_BYTES)
            snapshot, drill = self.home / 'snapshot.sqlite', self.home / 'drill.sqlite'
            result = self.cli('snapshot', '--database', str(self.store), '--destination', str(snapshot))
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.cli('restore', '--snapshot', str(snapshot), '--destination', str(drill))
            self.assertEqual(result.returncode, 0, result.stderr)
            with c.Collection(drill, projects=PROJECTS) as db:
                self.assertEqual(db.events(), [json.loads(self.data)])
        finally:
            process.terminate()
            process.communicate(timeout=3)

    def test_config_and_cli_input_failure_do_not_create_queue(self):
        self.config.chmod(0o666)
        with self.assertRaises(c.CollectionError):
            c.load_projects(self.config)
        self.config.chmod(0o600)
        self.config.write_text('{"projects":["not-authorized"]}')
        with self.assertRaises(c.CollectionError):
            c.load_projects(self.config)
        self.config.write_text(json.dumps({'projects': sorted(PROJECTS)}))
        result = self.cli('enqueue', '--outbox', str(self.queue), '--create', data=b'x' * 65537)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.queue.exists())

    def test_process_crash_after_durable_enqueue_reopen(self):
        program = ('import importlib.util,os,sys; '
            's=importlib.util.spec_from_file_location("c",sys.argv[1]); '
            'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
            'q=m.Outbox(sys.argv[2],projects={"synthetic-a","synthetic-b"},create=True); '
            'q.enqueue(sys.stdin.buffer.read()); os._exit(9)')
        result = subprocess.run([sys.executable, '-B', '-c', program,
            str(ROOT / 'scripts/typesafe_collection.py'), str(self.queue)], input=self.data,
            capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 9)
        with self.outbox() as box:
            self.assertEqual(box.pending(), [self.data])

    def test_sqlite_full_never_accepts_or_evicts(self):
        with self.outbox(create=True) as box:
            box.enqueue(self.data)
            pages = box._connection.execute('PRAGMA page_count').fetchone()[0]
            box._connection.execute('PRAGMA max_page_count=' + str(pages))
            accepted = [self.data]
            refused = False
            for n in range(1, 20):
                data = wire(number=n)
                try:
                    box.enqueue(data)
                    accepted.append(data)
                except c.CollectionError as exc:
                    self.assertEqual(str(exc), 'outbox_unavailable')
                    refused = True
                    break
            self.assertTrue(refused)
            self.assertEqual(box.pending(), accepted)
        with self.outbox() as box:
            self.assertEqual(box.pending(), accepted)

    def test_crash_after_receiver_commit_before_queue_ack(self):
        with self.outbox(create=True) as box:
            box.enqueue(self.data)
        with c.Collection(self.store, projects=PROJECTS, create=True):
            pass
        program = ('import importlib.util,os,sys; '
            's=importlib.util.spec_from_file_location("c",sys.argv[1]); '
            'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
            'q=m.Outbox(sys.argv[2],projects={"synthetic-a","synthetic-b"}); '
            'db=m.Collection(sys.argv[3],projects={"synthetic-a","synthetic-b"}); '
            'q.flush(lambda data,deadline: (db.submit(data),os._exit(8))[0])')
        result = subprocess.run([sys.executable, '-B', '-c', program,
            str(ROOT / 'scripts/typesafe_collection.py'), str(self.queue), str(self.store)],
            capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 8)
        with self.outbox() as box:
            self.assertEqual(box.pending(), [self.data])
            with c.Collection(self.store, projects=PROJECTS) as db:
                self.assertEqual(db.events(), [json.loads(self.data)])
                self.assertEqual(box.flush(lambda data, deadline: json.dumps(db.submit(data)).encode()), 1)
                self.assertEqual(db.events(), [json.loads(self.data)])

    def test_stdin_deadline_no_queue_and_no_traceback(self):
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'scripts/typesafe_collection.py'),
            'enqueue', '--outbox', str(self.queue), '--create', '--projects', str(self.config)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.wait(timeout=7)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(process.stderr.read(), b'collection_failed\n')
            self.assertFalse(self.queue.exists())
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=2)

    def test_serve_restart_without_create_and_comparison_chain(self):
        binding = pc.bind_plan(project_id='synthetic-a', plan_ref='original.md',
                               plan_bytes=b'synthetic', criteria={'AC01': 'Synthetic'})
        # Use an actual public comparison pipeline, not a handcrafted wire fixture.
        evaluation = {'profile': 'synthetic', 'outcome': 'unresolved', 'uncertainty': 'unassessed',
            'answers': {'q': {'type': 'noul', 'noul': 0.5}}, 'error': None, 'http_status': None,
            'request_sent': True, 'requested_model': 'synthetic', 'response_model': 'synthetic',
            'question_version': 'v1', 'question_fingerprint': 'a' * 64, 'core_version': 'v1',
            'duration_seconds': None, 'usage': {'input_tokens': None, 'output_tokens': 0}}
        model = pc.model_event(binding, criterion_id='AC01', evaluation=evaluation, selection='eligible')
        review = pc.fix_review(binding, plan_bytes=b'synthetic', criteria={'AC01': 'Synthetic'},
            review_ref='review.md', review_bytes=b'synthetic-review', verdicts={'AC01': 'no_defect_found'},
            reviewer_role='reviewer', recorded_at='2026-11-09T12:00:00Z')
        compared = pc.comparison_event(model, review, plan_bytes=b'synthetic', criteria={'AC01': 'Synthetic'},
            review_bytes=b'synthetic-review', adjudication={'label': 'no_material_defect',
            'evidence_ref': 'evidence.md', 'reviewer_role': 'reviewer', 'recorded_at': '2026-11-09T12:00:01Z'})
        data = [c.project_event(e, projects=PROJECTS) for e in (model, compared)]
        for restart in range(2):
            old_inode = self.sock.stat().st_ino if self.sock.exists() else None
            process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'scripts/typesafe_collection.py'),
                'serve', '--projects', str(self.config), '--database', str(self.store), '--socket', str(self.sock)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and process.poll() is None:
                    if self.sock.exists() and (old_inode is None or self.sock.stat().st_ino != old_inode):
                        break
                    # An inode can be reused; a successful fixed submit is also readiness proof.
                    if restart and self.sock.exists():
                        try:
                            c.UnixSender(self.sock)(data[0], time.monotonic() + 0.1)
                            break
                        except (c.CollectionError, OSError):
                            pass
                    time.sleep(0.01)
                self.assertIsNone(process.poll())
                for event in data:
                    self.assertEqual(c._ack(c.UnixSender(self.sock)(event, time.monotonic() + 1)), json.loads(ack(event)))
            finally:
                process.terminate()
                process.communicate(timeout=3)
        with c.Collection(self.store, projects=PROJECTS) as db:
            self.assertEqual(db.events(), [json.loads(d) for d in data])


if __name__ == '__main__':
    unittest.main()
