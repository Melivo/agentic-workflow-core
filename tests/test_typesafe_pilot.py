"""Offline portable IO/policy/calendar regressions; no model, host or scheduler calls."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.apm/skills/core-typesafe/scripts'
sys.path.insert(0, str(SCRIPTS))
import typesafe_collection as c
import typesafe_owner as owner
sys.path.pop(0)
from test_typesafe_integration import pc, ts, fake_response, PLAN, CRITERIA, INPUTS


def wire(identity):
    binding = pc.bind_plan(project_id=c.project_id(identity), plan_ref='local-plan',
                           plan_bytes=PLAN, criteria=CRITERIA)
    result = ts.evaluate('requirement_coverage', INPUTS['requirement_coverage'], model='synthetic',
                         core_version='synthetic', transport=fake_response)
    event = pc.model_event(binding, criterion_id='AC01', evaluation=result.to_dict(), selection='eligible')
    policy = c.ProjectPolicy({'synthetic-a'}, core_project_ids=True)
    return c.project_event(event, projects=policy), event


class PilotOffline(unittest.TestCase):
    def test_fixed_pseudonyms_and_legacy_default(self):
        identity = '/SYNTHETIC/private/project'
        value = c.project_id(identity)
        self.assertRegex(value, r'^core-[0-9a-f]{64}$')
        self.assertEqual(value, c.project_id(identity))
        self.assertNotEqual(value, c.project_id(identity + '-other'))
        data, event = wire(identity)
        self.assertNotIn(identity.encode(), data)
        with self.assertRaisesRegex(c.CollectionError, 'project_denied'):
            c.parse_wire(data, projects={'synthetic-a'})
        policy = c.project_policy({'projects': ['synthetic-a'], 'core_project_ids': True})
        self.assertEqual(c.parse_wire(data, projects=policy)['event_id'], event['event_id'])
        for bad in ('core-', 'core-' + 'A' * 64, 'core-' + 'a' * 63, 'core-' + 'a' * 65,
                    '*', 'real-project', value + '/suffix'):
            self.assertNotIn(bad, policy)
        for identity in ('', None, 1, 'x' * 4097, '\ud800'):
            with self.assertRaises(c.CollectionError):
                c.project_id(identity)

    def test_policy_has_no_wildcard_or_implicit_opt_in(self):
        for flag in (False, True):
            policy = c.project_policy({'projects': ['synthetic-a'], 'core_project_ids': flag})
            self.assertIn('synthetic-a', policy)
            self.assertNotIn('synthetic-b', policy)
            self.assertEqual(c.project_id('one') in policy, flag)
        for bad in ({'projects': ['*']}, {'projects': ['real']}, {'projects': ['synthetic-a'], 'extra': True},
                    *({'projects': ['synthetic-a'], 'core_project_ids': v} for v in (None, 1, 'true', [], {}))):
            with self.subTest(bad=bad), self.assertRaises(c.CollectionError):
                c.project_policy(bad)

    def test_two_projects_queue_outage_reopen_ack_and_unchanged_schema(self):
        policy = c.ProjectPolicy({'synthetic-a'}, core_project_ids=True)
        wires = [wire('SYNTHETIC-A')[0], wire('SYNTHETIC-B')[0]]
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as directory:
            root = Path(directory)
            outbox, database = root / 'outbox.sqlite', root / 'events.sqlite'
            with c.Outbox(outbox, projects=policy, create=True) as box:
                for data in wires:
                    box.enqueue(data)
                def unavailable(*_):
                    raise c.CollectionError('transport_unavailable')
                with self.assertRaises(c.CollectionError):
                    box.flush(unavailable)
                self.assertEqual(box.pending(), wires)
            with c.Collection(database, projects=policy, create=True) as store:
                with c.Outbox(outbox, projects=policy) as box:
                    self.assertEqual(box.pending(), wires)
                    self.assertEqual(box.flush(lambda data, _: json.dumps(store.submit(data)).encode()), 2)
                    self.assertEqual(box.pending(), [])
                self.assertEqual({e['binding']['project_id'] for e in store.events()},
                                 {c.project_id('SYNTHETIC-A'), c.project_id('SYNTHETIC-B')})
                before = store.events()
                for data in wires:
                    store.submit(data)
                self.assertEqual(store.events(), before)
                self.assertEqual(c.SCHEMA_VERSION, 1)
                self.assertEqual(c.WIRE_SCHEMA, 'collection/v1')

    def test_rounded_choice_sum_preserves_originals_end_to_end(self):
        inputs = dict(INPUTS['skill_relevance'], candidates=[
            {'ref': key, 'responsibility': 'SYNTHETIC'} for key in ('a', 'b')])
        prepared = ts.build_request('skill_relevance', inputs, model='synthetic')
        binding = pc.bind_plan(project_id='synthetic-a', plan_ref='local-plan',
                               plan_bytes=PLAN, criteria=CRITERIA)
        self.assertEqual(c.PROBABILITY_SUM_TOLERANCE, ts.PROBABILITY_SUM_TOLERANCE)
        for second in (0.499, 0.451, 0.549):
            with self.subTest(second=second):
                original = {'a': 0.5, 'b': second}
                raw = fake_response(prepared.payload)
                for answer in raw['answers'].values():
                    if answer['type'] == 'choice':
                        answer['probabilities'] = dict(original)
                        answer['choice'] = max(original, key=original.get)
                before = json.dumps(raw, sort_keys=True)
                result = ts.finalize_response(prepared, raw, core_version='synthetic',
                                              duration_seconds=0.1)
                self.assertEqual(result.outcome, 'unresolved')
                self.assertIsNone(result.error)
                event = pc.model_event(binding, criterion_id='AC01', evaluation=result.to_dict(),
                                       selection='eligible')
                self.assertEqual(event['observation']['model_status'], 'uncertain')
                data = c.project_event(event, projects={'synthetic-a'})
                restored = c.parse_wire(data, projects={'synthetic-a'})
                self.assertEqual(restored['observation'], event['observation'])
                choices = [answer['probabilities'] for answer in
                           restored['observation']['probabilities'].values()
                           if 'probabilities' in answer]
                self.assertEqual(choices, [original])
                self.assertEqual(json.dumps(raw, sort_keys=True), before)
                for invalid in (0.449, 0.551):
                    damaged = json.loads(json.dumps(event))
                    for answer in damaged['observation']['probabilities'].values():
                        if 'probabilities' in answer:
                            answer['probabilities']['b'] = invalid
                    with self.assertRaisesRegex(c.CollectionError, 'invalid_wire'):
                        c.project_event(damaged, projects={'synthetic-a'})

    def test_safe_owner_config_is_read_only_and_closed(self):
        value = {'projects': {'projects': ['synthetic-a'], 'core_project_ids': True},
                 'transport': {'ssh_target': 'synthetic-alias',
                               'binding': {'hostname': 'synthetic-host', 'user': 'synthetic-user', 'port': 22},
                               'remote_script': '/synthetic/collection.py'}}
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as directory:
            path = Path(directory) / 'config.json'
            raw = json.dumps(value).encode()
            path.write_bytes(raw)
            with patch.object(c, '_process', side_effect=AssertionError('unexpected process')):
                policy, sender = owner.load_config(path)
            self.assertIn(c.project_id('synthetic'), policy)
            self.assertEqual(sender.binding, value['transport']['binding'])
            self.assertEqual(path.read_bytes(), raw)
            for bad in (dict(value, extra=True), dict(value, transport=None)):
                path.write_text(json.dumps(bad))
                with self.assertRaises(c.CollectionError):
                    owner.load_config(path)
            path.write_bytes(raw)
            path.chmod(0o666)
            with self.assertRaises(c.CollectionError):
                owner.load_config(path)
            with self.assertRaises(c.CollectionError):
                owner.load_config(Path(directory) / 'absent')
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['config.json'])

    def test_pinned_ssh_binding_drift_prevents_delivery(self):
        config = {'batchmode':'yes', 'stricthostkeychecking':'true', 'updatehostkeys':'false',
                  'forwardagent':'no', 'forwardx11':'no', 'clearallforwardings':'yes',
                  'controlmaster':'false', 'requesttty':'false', 'permitlocalcommand':'no',
                  'hostname':'synthetic-host', 'user':'synthetic-user', 'port':'22'}
        raw = ''.join(k + ' ' + v + '\n' for k, v in config.items()).encode()
        sender = c.SSHSender('synthetic-alias', binding={'hostname':'other-host','user':'synthetic-user','port':22},
                             remote_script='/synthetic/collection.py')
        with patch.object(c, '_process', return_value=raw) as run:
            with self.assertRaisesRegex(c.CollectionError, 'ssh_binding_mismatch'):
                sender(b'{}', time.monotonic() + 5)
        self.assertEqual(run.call_count, 1)  # only ssh -G; no event send
        for path in ('relative.py', '/x;touch.py', '/x/../bad.py', '/x\n.py'):
            with self.assertRaises(c.CollectionError):
                c.SSHSender('synthetic-alias', remote_script=path)

    def test_month_end_berlin_leap_year_dst_and_rollover(self):
        for text in ('2026-01-31T21:00:00+00:00', '2026-02-28T21:00:00+00:00',
                     '2028-02-29T21:00:00+00:00', '2026-03-31T20:00:00+00:00',
                     '2026-10-31T21:00:00+00:00', '2026-12-31T21:00:00+00:00'):
            self.assertTrue(owner.month_end_due(datetime.fromisoformat(text)), text)
        for text in ('2028-02-28T21:00:00+00:00', '2026-03-31T21:00:00+00:00',
                     '2026-03-31T20:01:00+00:00', '2027-01-01T21:00:00+00:00'):
            self.assertFalse(owner.month_end_due(datetime.fromisoformat(text)), text)
        with self.assertRaises(c.CollectionError):
            owner.month_end_due(datetime(2026, 1, 31, 22))

    def test_bundle_runs_alone_with_compatibility_wrapper(self):
        spec = importlib.util.spec_from_file_location('pilot_wrapper', ROOT / 'scripts/typesafe_collection.py')
        wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        self.assertEqual(wrapper.project_id('synthetic'), c.project_id('synthetic'))
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as directory:
            target = Path(directory) / 'scripts'
            shutil.copytree(SCRIPTS, target, ignore=shutil.ignore_patterns('__pycache__'))
            code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                    'import typesafe_owner as o, typesafe_collection as c; '
                    'assert c.project_id("synthetic").startswith("core-"); '
                    'assert o.REPORT_ZONE == "Europe/Berlin"')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(target)],
                                    cwd=directory, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
