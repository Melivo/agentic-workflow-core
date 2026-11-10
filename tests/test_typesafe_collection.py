"""Offline T01 storage/import regressions. Only synthetic data and private temp DBs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


c = load('collection', ROOT / 'scripts/typesafe_collection.py')
pc = load('comparison', ROOT / '.apm/skills/core-typesafe/scripts/plan_comparison.py')
PROJECTS = frozenset(('synthetic-a', 'synthetic-b'))


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='collection-', dir='/tmp/opencode')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.path = self.home / 'events.sqlite'
        self.plan = b'Synthetic original plan sentinel'
        self.criteria = {'AC01': 'Synthetic criterion prose sentinel', 'AC02': 'Other synthetic criterion'}
        self.review_bytes = b'Synthetic blind review sentinel'
        self.evaluation = {
            'profile': 'synthetic-profile', 'outcome': 'unresolved', 'uncertainty': 'unassessed',
            'answers': {'synthetic-question': {'type': 'noul', 'noul': 0.5}},
            'error': None, 'http_status': None, 'request_sent': True,
            'requested_model': 'synthetic-request', 'response_model': 'synthetic-response',
            'question_version': 'synthetic-v1', 'question_fingerprint': 'a' * 64,
            'core_version': 'synthetic-core', 'duration_seconds': 0.0,
            'usage': {'input_tokens': None, 'output_tokens': 0},
        }
        self.adjudication = {'label': 'material_defect', 'evidence_ref': 'private-evidence.md#AC01',
                             'reviewer_role': 'synthetic-reviewer', 'recorded_at': '2026-11-09T12:00:01Z'}
        self.binding = pc.bind_plan(project_id='synthetic-a', plan_ref='private-plan.md',
                                    plan_bytes=self.plan, criteria=self.criteria)
        self.review = self.fix(self.binding)
        self.model = self.observe()
        self.compared = self.compare()
        self.db = c.Collection(self.path, projects=PROJECTS, create=True)
        self.addCleanup(self.db.close)

    def fix(self, binding):
        return pc.fix_review(binding, plan_bytes=self.plan, criteria=self.criteria,
                             review_ref='private-review.md', review_bytes=self.review_bytes,
                             verdicts={'AC01': 'no_defect_found', 'AC02': 'defect_found'},
                             reviewer_role='synthetic-reviewer', recorded_at='2026-11-09T12:00:00Z')

    def observe(self, **changes):
        args = dict(criterion_id='AC01', evaluation=self.evaluation, selection='eligible')
        args.update(changes)
        return pc.model_event(self.binding, **args)

    def compare(self, **changes):
        args = dict(plan_bytes=self.plan, criteria=self.criteria, review_bytes=self.review_bytes,
                    adjudication=self.adjudication)
        model = changes.pop('model', self.model)
        review = changes.pop('initial_review', self.review)
        args.update(changes)
        return pc.comparison_event(model, review, **args)

    def wire(self, event):
        return c.project_event(event, projects=PROJECTS)

    def put(self, event):
        return self.db.submit(self.wire(event))

    def mutate(self, event, path, value):
        data = json.loads(self.wire(event))
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return json.dumps(data).encode()

    def rejected(self, data):
        before = self.db.events()
        with self.assertRaises(c.CollectionError) as caught:
            self.db.submit(data)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(self.db.events(), before)
        self.assertNotIn('sentinel', str(caught.exception))
        return str(caught.exception)

    def test_minimized_projection_public_api_and_hash_ack(self):
        original = deepcopy(self.compared)
        self.put(self.model)
        data = self.wire(self.compared)
        result = self.db.submit(data)
        self.assertEqual(result, {'event_id': self.compared['event_id'], 'payload_sha256': hashlib.sha256(data).hexdigest()})
        self.assertEqual(self.compared, original)
        for secret in (self.plan, self.review_bytes, *[v.encode() for v in self.criteria.values()],
                       b'private-plan.md', b'private-review.md', b'private-evidence.md', b'synthetic-reviewer'):
            self.assertNotIn(secret, data)
        value = c.parse_wire(data, projects=PROJECTS)
        self.assertEqual(value['schema'], 'collection/v1')
        self.assertEqual(value['initial_review']['review_ref'], 'ref-' + hashlib.sha256(b'private-review.md').hexdigest())
        self.assertEqual(value['observation']['usage'], {'input_tokens': None, 'output_tokens': 0})
        self.assertEqual(value['observation']['duration_seconds'], 0.0)
        # Formatting is not an identity change: ACK binds canonical payload, not whitespace.
        self.assertEqual(self.db.submit(json.dumps(value, indent=2).encode()), result)
        self.assertEqual(len(self.db.events()), 2)
        value['selection'] = 'excluded'
        self.assertEqual(self.db.events()[-1]['selection'], 'eligible')

    def test_two_projects_persist_reopen_and_exact_replay(self):
        self.put(self.model)
        self.put(self.compared)
        other_binding = pc.bind_plan(project_id='synthetic-b', plan_ref='private-plan.md', plan_bytes=self.plan, criteria=self.criteria)
        other = pc.model_event(other_binding, criterion_id='AC01', evaluation=self.evaluation)
        self.put(other)
        expected = self.db.events()
        self.db.close()
        with c.Collection(self.path, projects=PROJECTS) as reopened:
            for event in expected:
                reopened.submit(c.canonical_wire(event, projects=PROJECTS))
            self.assertEqual(reopened.events(), expected)
            self.assertEqual([e['binding']['project_id'] for e in expected], ['synthetic-a', 'synthetic-a', 'synthetic-b'])
        self.assertNotEqual(self.model['event_id'], other['event_id'])

    def test_conflicts_same_identity_never_weaken_old_values(self):
        self.put(self.model)
        self.put(self.compared)
        for path, value in [(('observation', 'usage', 'input_tokens'), 0),
                            (('selection',), 'unknown'),
                            (('initial_review', 'verdicts', 'AC01'), 'defect_found'),
                            (('adjudication', 'evidence_ref'), 'ref-' + 'b' * 64)]:
            self.rejected(self.mutate(self.compared, path, value))
        self.assertEqual(self.rejected(self.mutate(self.model, ('observation', 'duration_seconds'), 1)), 'payload_conflict')

    def test_strict_json_encoding_depth_duplicates_and_constants(self):
        data = self.wire(self.model)
        cases = [b'\xff', b'\xef\xbb\xbf' + data, b'{', b'null', b'[]',
                 b'{"x":1,"x":2}', data.replace(b'"revision":1', b'"revision":1,"revision":1'),
                 data.replace(b'0.5', b'NaN'), data.replace(b'0.5', b'Infinity'),
                 data.replace(b'0.5', b'-Infinity'), b'[' * 40 + b'0' + b']' * 40,
                 b' ' * (c.MAX_WIRE_BYTES + 1),
                 data.replace(b'synthetic-profile', b'\\ud800'),
                 data.replace(b'0.5', b'1e999')]
        for value in cases:
            with self.subTest(value=value[:32]):
                self.rejected(value)
        # Exactly the input size cap is accepted; beyond is never accepted.
        padded = data + b' ' * (c.MAX_WIRE_BYTES - len(data))
        self.db.submit(padded)
        self.rejected(padded + b' ')

    def test_closed_shapes_every_nested_boundary(self):
        paths = [(), ('binding',), ('observation',), ('observation', 'usage'),
                 ('observation', 'api_error'), ('observation', 'probabilities', 'synthetic-question'),
                 ('initial_review',), ('initial_review', 'binding'), ('adjudication',)]
        for path in paths:
            value = json.loads(self.wire(self.compared))
            node = value
            for key in path:
                node = node[key]
            node['private_text'] = 'sentinel'
            self.rejected(json.dumps(value).encode())
        value = json.loads(self.wire(self.model))
        del value['observation']['usage']['input_tokens']
        self.rejected(json.dumps(value).encode())
        self.rejected(self.mutate(self.model, ('schema',), 'collection/v2'))
        with self.assertRaises(c.CollectionError):
            c.project_event({**self.model, 'payload': 'sentinel'}, projects=PROJECTS)

    def test_numeric_types_domains_and_metadata(self):
        changes = [(('revision',), True), (('revision',), 1.0), (('revision',), 0),
                   (('revision',), 2**63), (('selection',), 'promoted'),
                   (('event_id',), 'pc1-' + '0' * 64),
                   (('binding', 'criteria_ids'), ['AC01', 'AC01']),
                   (('binding', 'plan_sha256'), 'A' * 64),
                   (('binding', 'plan_ref'), 'private-plan.md'),
                   (('observation', 'usage', 'output_tokens'), True),
                   (('observation', 'usage', 'input_tokens'), -1),
                   (('observation', 'usage', 'input_tokens'), 1.0),
                   (('observation', 'duration_seconds'), True),
                   (('observation', 'duration_seconds'), -1),
                   (('observation', 'request_sent'), 1),
                   (('observation', 'api_error', 'occurred'), 0),
                   (('observation', 'api_error', 'http_status'), True),
                   (('observation', 'api_error', 'http_status'), 600),
                   (('observation', 'probabilities', 'synthetic-question', 'noul'), True),
                   (('observation', 'probabilities', 'synthetic-question', 'noul'), 1.1),
                   (('observation', 'question_fingerprint'), 'bad'),
                   (('observation', 'requested_model'), 'sentinel raw text'),
                   (('observation', 'requested_model'), 'a' * 257)]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                self.rejected(self.mutate(self.model, path, value))

    def test_choice_and_unknown_error_are_distinct(self):
        choice = deepcopy(self.model)
        choice['observation']['probabilities'] = {'q': {'probabilities': {'a': 0.2, 'b': 0.8}, 'confidence': 0.8}}
        self.put(choice)
        for change in [{'probabilities': {'a': 0.8}, 'confidence': 0.8},
                       {'probabilities': {'a': True, 'b': 0}, 'confidence': 1},
                       {'probabilities': {'a': 1}, 'confidence': 1, 'text': 'sentinel'}]:
            self.rejected(self.mutate(choice, ('observation', 'probabilities', 'q'), change))
        failure = {**self.evaluation, 'outcome': 'error', 'error': 'sentinel', 'answers': None,
                   'uncertainty': 'no_model_answer', 'usage': None, 'http_status': 503,
                   'duration_seconds': None, 'response_model': None}
        second = self.observe(evaluation=failure, previous=choice)
        self.put(second)
        obs = self.db.events()[-1]['observation']
        self.assertEqual(obs['usage'], {'input_tokens': None, 'output_tokens': None})
        self.assertIsNone(obs['duration_seconds'])
        self.assertEqual(obs['api_error'], {'occurred': True, 'http_status': 503})
        self.assertNotIn(b'sentinel', self.wire(second))

    def test_project_allowlist(self):
        with self.assertRaisesRegex(c.CollectionError, '^project_denied$'):
            c.parse_wire(self.wire(self.model), projects={'synthetic-b'})
        for projects in [[], 'synthetic-a', {'bad token'}, None]:
            with self.assertRaises(c.CollectionError):
                c.parse_wire(self.wire(self.model), projects=projects)

    def test_missing_model_wrong_model_and_observation(self):
        self.assertEqual(self.rejected(self.wire(self.compared)), 'missing_model')
        self.put(self.model)
        wrong = self.observe(criterion_id='AC02')
        self.put(wrong)
        self.rejected(self.mutate(self.compared, ('model_event_id',), wrong['event_id']))
        self.rejected(self.mutate(self.compared, ('model_event_id',), self.compared['event_id']))
        self.rejected(self.mutate(self.compared, ('observation', 'duration_seconds'), 99))
        self.rejected(self.mutate(self.compared, ('initial_review', 'binding', 'criteria_sha256'), 'b' * 64))
        self.rejected(self.mutate(self.compared, ('initial_review', 'verdicts'), {'AC01': 'no_defect_found'}))
        self.put(self.compared)

    def test_linear_history_missing_skip_wrong_predecessor_and_fork(self):
        second = self.observe(previous=self.model)
        third = self.observe(previous=second)
        self.assertEqual(self.rejected(self.wire(second)), 'missing_predecessor')
        self.put(self.model)
        self.rejected(self.wire(third))
        self.rejected(self.mutate(second, ('previous_id',), 'pc1-' + '0' * 64))
        corrupted = deepcopy(second)
        corrupted['previous_id'] = corrupted['supersedes'] = 'pc1-' + '0' * 64
        self.rejected(self.wire(corrupted))
        self.put(second)
        fork = self.observe(previous=self.model, evaluation={**self.evaluation, 'duration_seconds': 2})
        self.assertEqual(self.rejected(self.wire(fork)), 'payload_conflict')
        self.put(third)
        self.assertEqual([e['revision'] for e in self.db.events()], [1, 2, 3])

    def test_frozen_review_and_selection_across_missing_originals(self):
        model = self.observe(selection='excluded')
        first = self.compare(model=model)
        middle = self.compare(model=model, previous=first, review_bytes=None)
        last = self.compare(model=model, previous=middle, review_bytes=None, initial_review=None)
        for event in (model, first, middle, last):
            self.put(event)
        next_event = self.compare(model=model, previous=last)
        for path, value in [(('initial_review',), None),
                            (('initial_review', 'review_ref'), 'ref-' + 'b' * 64),
                            (('initial_review', 'verdicts', 'AC01'), 'defect_found'),
                            (('initial_review', 'recorded_at'), '2026-11-09T12:00:00.1Z'),
                            (('initial_review', 'reviewer_role'), 'ref-' + 'b' * 64),
                            (('selection',), 'unknown')]:
            self.rejected(self.mutate(next_event, path, value))
        # Source private validators do not protect a hand-built imported revision.
        weakened = deepcopy(model)
        weakened['revision'] = 2
        weakened['previous_id'] = weakened['supersedes'] = model['event_id']
        fields = ['plan-comparison/v1', 'synthetic-a', weakened['binding']['plan_sha256'], 'AC01', 'model_observation', 2]
        weakened['event_id'] = 'pc1-' + hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        weakened['selection'] = 'unknown'
        self.assertEqual(self.rejected(self.wire(weakened)), 'history_conflict')
        self.put(next_event)
        self.assertEqual(self.db.events()[-1]['initial_review'], self.db.events()[1]['initial_review'])

    def test_unknown_selection_and_initial_review_may_be_clarified(self):
        model = self.observe(selection='unknown')
        first = self.compare(model=model, initial_review=None, review_bytes=None)
        second = self.compare(model=model, previous=first, selection='eligible')
        for event in (model, first, second):
            self.put(event)
        self.assertIsNone(self.db.events()[1]['initial_review'])
        self.assertEqual(self.db.events()[1]['selection'], 'unknown')
        self.assertEqual(self.db.events()[2]['initial_review']['verdicts']['AC01'], 'no_defect_found')

    def test_decision_labels_and_timestamps_consistency(self):
        self.put(self.model)
        for path, value in [(('initial_review', 'recorded_at'), '2026-02-30T12:00:00Z'),
                            (('adjudication', 'recorded_at'), '2026-11-09T12:00:00Z'),
                            (('adjudication', 'recorded_at'), '2026-11-09T12:00:01+00:00'),
                            (('adjudication', 'reported_label'), 'unresolved'),
                            (('unresolved_reason',), 'raw sentinel'),
                            (('selection',), 'contaminated')]:
            self.rejected(self.mutate(self.compared, path, value))

    def test_private_paths_symlinks_modes_hardlinks_and_sidecars(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        for mode in [0o644, 0o660]:
            self.path.chmod(mode)
            with self.assertRaisesRegex(c.CollectionError, '^unsafe_path$'):
                c.Collection(self.path, projects=PROJECTS)
        self.path.chmod(0o600)
        link = self.home / 'link.sqlite'
        link.symlink_to(self.path)
        with self.assertRaises(c.CollectionError):
            c.Collection(link, projects=PROJECTS)
        hard = self.home / 'hard.sqlite'
        os.link(self.path, hard)
        with self.assertRaises(c.CollectionError):
            c.Collection(self.path, projects=PROJECTS)
        hard.unlink()
        alias = self.home / 'alias'
        alias.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(c.CollectionError):
            c.Collection(alias / 'fresh.sqlite', projects=PROJECTS, create=True)
        journal = Path(str(self.path) + '-journal')
        journal.symlink_to(self.home / 'sentinel')
        with self.assertRaises(c.CollectionError):
            c.Collection(self.path, projects=PROJECTS)
        journal.unlink()
        self.home.chmod(0o755)
        with self.assertRaises(c.CollectionError):
            c.Collection(self.path, projects=PROJECTS)
        self.home.chmod(0o700)
        for name in ['events.sqlite', 'missing/child.sqlite']:
            with self.assertRaises(c.CollectionError):
                c.Collection(self.home / name, projects=PROJECTS, create=True)

    def test_foreign_schema_version_and_data_corruption_refused_without_adoption(self):
        self.db.close()
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA user_version=999')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(c.CollectionError, '^storage_unavailable$') as caught:
            c.Collection(self.path, projects=PROJECTS)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(self.path.read_bytes(), before)
        foreign = self.home / 'foreign.sqlite'
        foreign.touch(mode=0o600)
        with sqlite3.connect(foreign) as db:
            db.execute('CREATE TABLE sentinel(value)')
        before = foreign.read_bytes()
        with self.assertRaises(c.CollectionError):
            c.Collection(foreign, projects=PROJECTS)
        self.assertEqual(foreign.read_bytes(), before)

    def test_full_audit_detects_hash_and_historical_weakening(self):
        self.put(self.model)
        self.put(self.compared)
        self.db.close()
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER events_no_update')
            db.execute("UPDATE events SET payload_sha256=? WHERE event_id=?", ('0' * 64, self.model['event_id']))
            db.execute(c.DDL[2])
        with self.assertRaises(c.CollectionError):
            c.Collection(self.path, projects=PROJECTS)
        self.assertFalse((self.home / 'restore.sqlite').exists())
        with self.assertRaises(c.CollectionError):
            c.restore(self.path, self.home / 'restore.sqlite', projects=PROJECTS)
        self.assertFalse((self.home / 'restore.sqlite').exists())

    def test_constraints_immutable_and_referential(self):
        self.put(self.model)
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA foreign_keys=ON')
            for sql in ['UPDATE events SET revision=3', 'DELETE FROM events']:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)
            row = db.execute('SELECT * FROM events').fetchone()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)', row)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_concurrent_duplicate_and_conflicting_writers(self):
        barrier = threading.Barrier(2)
        good = self.wire(self.model)
        bad = self.mutate(self.model, ('observation', 'duration_seconds'), 9)
        def send(data):
            with c.Collection(self.path, projects=PROJECTS) as db:
                barrier.wait(timeout=5)
                try:
                    return db.submit(data)
                except c.CollectionError as error:
                    return str(error)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(send, (good, good)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.db.events()), 1)
        barrier.reset()
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(send, (good, bad)))
        self.assertIn('payload_conflict', results)
        self.assertEqual(len(self.db.events()), 1)

    def test_lock_timeout_and_commit_failure_no_partial_write_or_ack(self):
        # Runtime fault injection at actual SQLite COMMIT boundary.
        with sqlite3.connect(self.path, isolation_level=None) as blocker:
            blocker.execute('BEGIN IMMEDIATE')
            self.db._connection.execute('PRAGMA busy_timeout=1')
            self.assertEqual(self.rejected(self.wire(self.model)), 'storage_unavailable')
            blocker.execute('ROLLBACK')
        def deny_commit(action, arg1, *_):
            return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg1 == 'COMMIT' else sqlite3.SQLITE_OK
        self.db._connection.set_authorizer(deny_commit)
        self.assertEqual(self.rejected(self.wire(self.model)), 'storage_unavailable')
        self.db._connection.set_authorizer(None)
        self.assertFalse(self.db._connection.in_transaction)
        self.put(self.model)
        self.assertEqual(len(self.db.events()), 1)

    def test_killed_transaction_rolls_back_and_commit_survives_ack_loss(self):
        code = """
import importlib.util,json,os,sqlite3,sys
spec=importlib.util.spec_from_file_location('c',sys.argv[1]);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
db=c.Collection(sys.argv[2],projects={'synthetic-a','synthetic-b'})
if sys.argv[3]=='committed':
 db.submit(sys.stdin.buffer.read());os._exit(19)
db._connection.execute('BEGIN IMMEDIATE')
e=c.parse_wire(sys.stdin.buffer.read(),projects=db.projects);data=c.canonical_wire(e,projects=db.projects)
b=e['binding']
db._connection.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',(e['event_id'],b['project_id'],b['plan_sha256'],e['criterion_id'],e['event_type'],e['revision'],e['previous_id'],e['model_event_id'],data.decode(),c.payload_hash(data)))
os._exit(18)
"""
        for mode, exitcode, count in [('uncommitted', 18, 0), ('committed', 19, 1)]:
            p = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT / 'scripts/typesafe_collection.py'), str(self.path), mode],
                               input=self.wire(self.model), capture_output=True, timeout=10)
            self.assertEqual(p.returncode, exitcode, p.stderr.decode())
            self.assertEqual(p.stdout, b'')
            with c.Collection(self.path, projects=PROJECTS) as db:
                self.assertEqual(len(db.events()), count)
        self.put(self.model)
        self.assertEqual(len(self.db.events()), 1)

    def test_backup_restore_complete_values_hashes_and_no_overwrite(self):
        for event in (self.model, self.compared, self.compare(previous=self.compared)):
            self.put(event)
        expected = self.db.events()
        backup = self.home / 'snapshot.sqlite'
        restored = self.home / 'drill.sqlite'
        self.assertEqual(self.db.backup(backup), backup)
        self.put(self.observe(previous=self.model))
        self.assertEqual(c.restore(backup, restored, projects=PROJECTS), restored)
        with c.Collection(restored, projects=PROJECTS) as db:
            self.assertEqual(db.events(), expected)
            for event in expected:
                data = c.canonical_wire(event, projects=PROJECTS)
                self.assertEqual(db.submit(data)['payload_sha256'], hashlib.sha256(data).hexdigest())
        for destination in (self.path, backup, restored):
            before = destination.read_bytes()
            with self.assertRaises(c.CollectionError):
                self.db.backup(destination)
            self.assertEqual(destination.read_bytes(), before)
            with self.assertRaises(c.CollectionError):
                c.restore(backup, destination, projects=PROJECTS)
            self.assertEqual(destination.read_bytes(), before)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(restored.stat().st_nlink, 1)
        with sqlite3.connect(restored) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_recomputed_hash_cannot_launder_historical_selection(self):
        self.put(self.model)
        self.put(self.compared)
        self.db.close()
        changed = json.loads(self.wire(self.model))
        changed['selection'] = 'excluded'
        data = c.canonical_wire(changed, projects=PROJECTS)
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER events_no_update')
            db.execute('UPDATE events SET payload=?,payload_sha256=? WHERE event_id=?',
                       (data.decode(), c.payload_hash(data), changed['event_id']))
            db.execute(c.DDL[2])
        # Every row is individually valid, hashes recomputed, all FKs intact.
        # Full replay must still catch comparison promotion from excluded model.
        with self.assertRaisesRegex(c.CollectionError, '^storage_unavailable$'):
            c.Collection(self.path, projects=PROJECTS)
        target = self.home / 'drill.sqlite'
        with self.assertRaises(c.CollectionError):
            c.restore(self.path, target, projects=PROJECTS)
        self.assertFalse(target.exists())

    def test_snapshot_during_concurrent_commits_is_complete_prefix(self):
        self.put(self.model)
        events = [self.model]
        for _ in range(20):
            events.append(self.observe(previous=events[-1]))
        start = threading.Event()
        def write():
            with c.Collection(self.path, projects=PROJECTS) as db:
                start.set()
                for event in events[1:]:
                    db.submit(self.wire(event))
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(write)
            self.assertTrue(start.wait(timeout=5))
            target = self.home / 'concurrent.sqlite'
            self.db.backup(target)
            future.result(timeout=10)
        with c.Collection(target, projects=PROJECTS) as snapshot:
            stored = snapshot.events()
            self.assertGreaterEqual(len(stored), 1)
            self.assertEqual(stored, [json.loads(self.wire(e)) for e in events[:len(stored)]])
        self.assertEqual(len(self.db.events()), 21)

    def test_malformed_container_types_have_fixed_content_free_errors(self):
        for path in [('binding',), ('observation',), ('observation', 'usage'),
                     ('observation', 'api_error'), ('observation', 'probabilities'),
                     ('initial_review',), ('initial_review', 'verdicts'), ('adjudication',)]:
            for value in [[], 'sentinel', 0, True]:
                self.rejected(self.mutate(self.compared, path, value))
        for timeout in [True, -1, 3, 10**400, float('nan'), float('inf')]:
            with self.assertRaisesRegex(c.CollectionError, '^invalid_configuration$'):
                c.Collection(self.path, projects=PROJECTS, lock_timeout=timeout)
        for path in [None, b'/sentinel', str(self.home) + '/sentinel\x00.db', self.home / '..' / 'sentinel']:
            with self.assertRaisesRegex(c.CollectionError, '^unsafe_path$') as caught:
                c.Collection(path, projects=PROJECTS)
            self.assertIsNone(caught.exception.__context__)
        directory = self.home / 'directory.sqlite'
        directory.mkdir(mode=0o700)
        with self.assertRaises(c.CollectionError):
            c.Collection(directory, projects=PROJECTS)
        with patch.object(c.os, 'geteuid', return_value=os.geteuid() + 1):
            with self.assertRaises(c.CollectionError):
                c.Collection(self.path, projects=PROJECTS)

    def test_backup_failure_does_not_publish_or_lose_original(self):
        self.put(self.model)
        before = self.db.events()
        target = self.home / 'snapshot.sqlite'
        with patch.object(c.os, 'link', side_effect=OSError('sentinel path')):
            with self.assertRaisesRegex(c.CollectionError, '^backup_failed$') as caught:
                self.db.backup(target)
        self.assertIsNone(caught.exception.__context__)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.home.glob('.collection-snapshot-*')))
        self.assertEqual(self.db.events(), before)


if __name__ == '__main__':
    unittest.main()
