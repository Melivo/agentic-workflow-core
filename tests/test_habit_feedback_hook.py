"""T02 hook tests v2: SDK-verified event mapping, scope, preserved results.

Honest doubles notice: sensor/mapper executables and the pipeline runner used
here are STUB_ doubles; the ShimExecutionTest runs the *real* plugin/index.ts
through the isolated Node runtime (v22.23.3, strip-types transpilation — an
authorised isolated build step) with a fake `ctx` implementing the SDK-pinned
V2 shapes from @opencode/plugin@2.0.25 / @opencode/schema@2.0.25 (registry
tarballs, sha512-verified). The real OpenCode plugin runtime and the real
habit-* binaries remain T03/CK04; nothing here claims that evidence.

Gortex receipt literals are pinned from actual observed mutation results of
this session (status "created"/"would_apply", new_sha, bytes_written,
workspace-prefixed repo path), not invented shapes.
"""
import io
import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CI = Path(os.environ.get('AWC_CI_WORKSPACE', '/tmp/opencode/agentic-workflow-core-ci'))
ASSETS = ROOT / '.apm/skills/core-devops/assets/opencode-habit-feedback'
HOOK = ASSETS / 'hook/habit_feedback_hook.py'
SHIM = ASSETS / 'plugin/index.ts'
NODE = CI / 'node/bin/node'

spec = importlib.util.spec_from_file_location('habit_feedback_hook', HOOK)
hook = importlib.util.module_from_spec(spec)
sys.modules['habit_feedback_hook'] = hook
spec.loader.exec_module(hook)

# Pinned, observed Gortex mutation receipts (this session's real writes).
REAL_WRITE_RECEIPT = {
    "applied_generation": 492, "bytes_written": 25937, "disk_status": "committed",
    "graph_status": "fresh", "mutation_receipt": "commit-248",
    "new_sha": "544ee2e06c1a9fdc64c17d98a8e3e11aa8d1146e",
    "path": "agentic-workflow-core/hook-target.py", "reindex_generation": 491,
    "reindexed": True, "status": "created",
}
REAL_DRYRUN_RECEIPT = {
    "bytes_written": 5712, "diff": "--- a/...\n+++ b/...\n", "dry_run": True,
    "new_sha": "2bee1f82a1c1b90dd7dfeb9fc9a22cb3a3b32fe0",
    "path": "agentic-workflow-core/x.py", "replacements": 1, "status": "would_apply",
}

SENSOR_STUB = '''
    import json, os, sys
    record = os.environ.get("HABIT_FEEDBACK_RECORD_ENV")
    if record:
        open(record, "w").write(json.dumps({
            "HOME": os.environ.get("HOME"),
            "RUFF_CACHE_DIR": os.environ.get("RUFF_CACHE_DIR"),
            "TMPDIR": os.environ.get("TMPDIR")}))
    print(json.dumps([{"smell": "too-many-parameters", "details": {},
                       "issues": [{"key": "big.py", "details": {"file": "big.py", "line": 1}}]}]))
    '''

MAPPER_STUB = 'import sys, json\njson.load(sys.stdin)\nprint("coached: 1")\n'


def write_stub(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text('#!/usr/bin/env python3\n' + textwrap.dedent(body), encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def make_runner(results=None, calls=None):
    """Double for the pipeline runner; records calls, returns canned results."""
    default = SimpleNamespace(complete=True, clean=True, reasons=[],
                              mapper=SimpleNamespace(stdout='clean verdict'), findings=[])
    calls = calls if calls is not None else []

    def runner(scope, rel, *, sensor, mapper, trusted_root, env):
        calls.append({"scope": scope, "file": rel, "trusted_root": trusted_root, "env": env})
        if results is not None:
            return results(rel)
        return default
    return runner


class HookTestBase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix='awc-t02-', dir='/tmp/opencode')
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name).resolve()
        self.state = self.tmp / 'state'
        self.scope = self.tmp / 'proj'
        self.scope.mkdir()
        (self.scope / 'big.py').write_text('def f(a, b, c, d, e):\n    return a\n', encoding='utf-8')
        self.sensor = write_stub(self.tmp, 'STUB_sensor', SENSOR_STUB)
        self.mapper = write_stub(self.tmp, 'STUB_mapper', MAPPER_STUB)

    def process(self, event, runner=None, session='s1', **kwargs):
        return hook.process_event(event, scope_root=self.scope, state_root=self.state,
                                  session=session, sensor=self.sensor, mapper=self.mapper,
                                  runner=runner, trusted_tool_roots=kwargs.pop(
                                      "trusted_tool_roots", [Path(str(CI / 'venv/bin'))]),
                                  **kwargs)

    def before(self, tool='edit', path='big.py', **extra):
        return dict(phase='before', tool=tool, sessionID='s1',
                    input={'path': path, 'oldString': 'x', 'newString': 'y'}, **extra)

    def after(self, tool='edit', status='completed', result=None, **extra):
        # Documented V2 after event: tool, sessionID, id, input, status, result.
        base = dict(phase='after', tool=tool, sessionID='s1', id='call-1',
                    input={'path': 'big.py', 'oldString': 'x', 'newString': 'y'})
        base.update(extra)
        base['status'] = status
        base['result'] = result if result is not None else {
            'content': [{'type': 'text', 'text': 'ok'}]}
        return base


class NativeMutationTest(HookTestBase):
    def test_completed_edit_scans_documented_after_input(self):
        calls = []
        runner = make_runner(calls=calls)
        outcome = self.process(self.after(), runner)
        self.assertEqual(outcome['status'], 'scanned', outcome['reasons'])
        self.assertEqual([c['file'] for c in calls], ['big.py'])
        self.assertIn('habit-feedback', outcome['feedback'])

    def test_before_pairing_fills_a_missing_after_input(self):
        calls = []
        runner = make_runner(calls=calls)
        self.process(self.before(id="call-1"))
        after = self.after()
        after['input'] = None
        outcome = self.process(after, runner)
        self.assertEqual(outcome['status'], 'scanned')
        self.assertEqual([c['file'] for c in calls], ['big.py'])

    def test_write_tool_is_a_documented_mutation(self):
        (self.scope / 'new.py').write_text('x = 1\n', encoding='utf-8')
        calls = []
        runner = make_runner(calls=calls)
        outcome = self.process(self.after(tool='write', input={'path': 'new.py',
                                                               'content': 'x = 1'}), runner)
        self.assertEqual(outcome['status'], 'scanned')
        self.assertEqual(calls[0]['file'], 'new.py')

    def test_failed_tool_call_is_not_a_mutation(self):
        outcome = self.process(self.after(status='error', result=None))
        self.assertEqual(outcome['status'], 'not_mutating')
        self.assertIsNone(outcome['feedback'])

    def test_input_without_documented_path_is_not_scanned(self):
        after = self.after()
        after['input'] = {'oldString': 'x', 'newString': 'y'}
        outcome = self.process(after)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('documented path input', outcome['reasons'][0])

    def test_pairing_without_id_is_ambiguous_not_guessed(self):
        # Two before events without the documented CallID, then one after
        # without a usable input: no unique pairing exists.
        self.process(dict(phase='before', tool='edit', input={'path': 'big.py'}))
        self.process(dict(phase='before', tool='edit', input={'path': 'big.py'}))
        after = self.after()
        after['input'] = None
        after.pop('id')
        outcome = self.process(after)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('ambiguous pairing', outcome['reasons'][0])

    def test_documented_id_pairs_the_right_call(self):
        self.process(self.before(id='A', path='big.py'))
        (self.scope / 'other.py').write_text('y = 2\n', encoding='utf-8')
        self.process(self.before(id='B', path='other.py'))
        calls = []
        runner = make_runner(calls=calls)
        after = self.after(id='B')
        after['input'] = None
        outcome = self.process(after, runner=runner)
        self.assertEqual(outcome['status'], 'scanned')
        self.assertEqual([c['file'] for c in calls], ['other.py'])

    def test_readonly_tools_never_scan(self):
        outcome = self.process(dict(phase='after', tool='read', status='completed',
                                    sessionID='s1',
                                    result={'content': [{'type': 'text', 'text': 'x'}]}))
        self.assertEqual(outcome['status'], 'not_mutating')
        self.assertIsNone(outcome['feedback'])


class GortexResultTest(HookTestBase):
    def _receipt_outcome(self, receipt, tool='execute'):
        return self.process(dict(phase='after', tool=tool, status='completed', sessionID='s1',
                                 result={'content': [{'type': 'text',
                                                      'text': json.dumps(receipt)}]}))

    def test_observed_created_receipt_scans_workspace_prefixed_path(self):
        receipt = dict(REAL_WRITE_RECEIPT, path='proj/big.py')
        outcome = self._receipt_outcome(receipt)
        self.assertEqual(outcome['status'], 'scanned', outcome['reasons'])
        self.assertEqual(outcome['scanned'][0]['file'], 'big.py')

    def test_status_applied_receipt_scans(self):
        outcome = self._receipt_outcome({"status": "applied", "path": "big.py",
                                         "new_sha": "a" * 40, "replacements": 1})
        self.assertEqual(outcome['status'], 'scanned')

    def test_mcp_effective_tool_name_is_supported(self):
        outcome = self._receipt_outcome({"status": "applied", "path": "big.py",
                                         "new_sha": "a" * 40, "replacements": 1},
                                        tool='gortex_edit')
        self.assertEqual(outcome['status'], 'scanned')

    def test_observed_dry_run_receipt_is_not_a_mutation(self):
        outcome = self._receipt_outcome(REAL_DRYRUN_RECEIPT)
        self.assertEqual(outcome['status'], 'not_mutating')
        self.assertIn('dry-run', outcome['reasons'][0])

    def test_object_with_path_but_no_receipt_is_not_scanned(self):
        outcome = self._receipt_outcome({"path": "big.py", "status": "indeterminate"})
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('not recognised', outcome['reasons'][0])

    def test_plain_text_result_is_not_guessed_as_paths(self):
        outcome = self.process(dict(phase='after', tool='execute', status='completed',
                                    sessionID='s1',
                                    result={'content': 'wrote something to a file maybe'}))
        self.assertEqual(outcome['status'], 'not_scanned')

    def test_batch_receipts_scan_each_file_up_to_the_limit(self):
        for i in range(6):
            (self.scope / ('f%d.py' % i)).write_text('x = %d\n' % i, encoding='utf-8')
        batch = [{"status": "applied", "path": "proj/f%d.py" % i,
                  "new_sha": "a" * 40, "replacements": 1} for i in range(6)]
        outcome = self._receipt_outcome(batch)
        self.assertEqual(outcome['status'], 'scanned')
        self.assertEqual(len(outcome['scanned']), hook.MAX_FILES_PER_EVENT)
        self.assertEqual(len(outcome['not_scanned']), 2)
        self.assertIn('event file limit', outcome['not_scanned'][0]['reason'])
        self.assertIn('partial', outcome['feedback'])


class ScopeSafetyTest(HookTestBase):
    def test_absolute_path_outside_scope_is_not_scanned(self):
        after = self.after(input={'path': '/etc/passwd'})
        outcome = self.process(after)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertTrue(outcome['not_scanned'])

    def test_symlink_escape_is_not_scanned(self):
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as other:
            victim = Path(other) / 'real.py'
            victim.write_text('x = 1\n', encoding='utf-8')
            (self.scope / 'linked.py').symlink_to(victim)
            receipt = {"status": "applied", "path": "linked.py",
                       "new_sha": "a" * 40, "replacements": 1}
            outcome = self.process(dict(phase='after', tool='execute', status='completed',
                                        sessionID='s1',
                                        result={'content': json.dumps(receipt)}))
            self.assertEqual(outcome['status'], 'not_scanned')
            self.assertIn('no in-scope', outcome['not_scanned'][0]['reason'])

    def test_ambiguous_resolution_is_not_scanned(self):
        nested = self.scope / 'proj'
        nested.mkdir()
        (nested / 'big.py').write_text('x = 1\n', encoding='utf-8')
        receipt = {"status": "applied", "path": "proj/big.py",
                   "new_sha": "a" * 40, "replacements": 1}
        outcome = self.process(dict(phase='after', tool='execute', status='completed',
                                    sessionID='s1',
                                    result={'content': json.dumps(receipt)}))
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('ambiguous', outcome['not_scanned'][0]['reason'])

    def test_too_broad_scope_is_refused(self):
        outcome = hook.process_event(self.after(), scope_root=Path('/'), state_root=self.state,
                                     session='s1', sensor=self.sensor, mapper=self.mapper)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('too broad', outcome['reasons'][0])


class StateRootSafetyTest(HookTestBase):
    def test_default_state_root_is_per_user(self):
        root = hook.default_state_root()
        self.assertIn(str(os.getuid()), root.name)

    def test_foreign_owned_state_root_is_refused(self):
        fake = self.tmp / 'foreign'
        fake.mkdir()
        self.state = fake
        original_getuid = os.getuid
        hook.os.getuid = lambda: original_getuid() + 999  # simulate foreign owner check
        try:
            outcome = self.process(self.after())
        finally:
            hook.os.getuid = original_getuid
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('owned by uid', outcome['reasons'][0])

    def test_symlinked_state_root_is_refused(self):
        target = self.tmp / 'real-state'
        target.mkdir()
        link = self.tmp / 'linked-state'
        link.symlink_to(target)
        outcome = hook.process_event(self.after(), scope_root=self.scope, state_root=link,
                                     session='s1', sensor=self.sensor, mapper=self.mapper)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('not a plain directory', outcome['reasons'][0])


class DedupAndStateTest(HookTestBase):
    def test_unchanged_content_is_not_rescanned(self):
        calls = []
        runner = make_runner(calls=calls)
        self.process(self.after(), runner)
        outcome = self.process(self.after(), runner)
        self.assertEqual(len(calls), 1)
        self.assertEqual(outcome['scanned'][0]['reasons'],
                         ['unchanged since last scan (duplicate suppressed)'])

    def test_changed_content_is_rescanned(self):
        calls = []
        runner = make_runner(calls=calls)
        self.process(self.after(), runner)
        (self.scope / 'big.py').write_text('def f(a):\n    return a\n', encoding='utf-8')
        outcome = self.process(self.after(), runner)
        self.assertEqual(len(calls), 2)
        self.assertEqual(outcome['status'], 'scanned')

    def test_sessions_do_not_share_scan_state(self):
        calls = []
        runner = make_runner(calls=calls)
        for session in ('s1', 's2'):
            self.process(self.after(), runner, session=session)
        self.assertEqual(len(calls), 2)

    def test_corrupt_state_recovers_and_still_scans(self):
        scope_dir = self.state / hook._state_scope_dir(self.state, self.scope.resolve(), 's1').name
        scope_dir.mkdir(parents=True, exist_ok=True)
        (scope_dir / 'state.json').write_text('not json at all', encoding='utf-8')
        calls = []
        runner = make_runner(calls=calls)
        outcome = self.process(self.after(), runner)
        self.assertEqual(outcome['status'], 'scanned')
        reloaded = json.loads((scope_dir / 'state.json').read_text(encoding='utf-8'))
        self.assertIn('ledger', reloaded)


class MissingPrerequisiteTest(HookTestBase):
    def test_missing_sensor_executable_is_visible_not_clean(self):
        outcome = hook.process_event(
            dict(phase='after', tool='execute', status='completed', sessionID='s1',
                 result={'content': json.dumps(dict(REAL_WRITE_RECEIPT, path='proj/big.py'))}),
            scope_root=self.scope, state_root=self.state, session='s1',
            sensor=self.tmp / 'no-such-sensor', mapper=self.mapper)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('habit-sensors executable not usable', outcome['reasons'][0])
        self.assertIn('NOT SCANNED', outcome['feedback'])

    def test_unknown_event_status_is_not_scanned(self):
        outcome = self.process(self.after(status='weird'))
        self.assertEqual(outcome['status'], 'not_scanned')

    def test_unknown_phase_is_not_scanned(self):
        outcome = self.process(dict(phase='during', tool='edit'))
        self.assertEqual(outcome['status'], 'not_scanned')


class IncompleteRunPresentationTest(HookTestBase):
    def test_incomplete_pipeline_is_never_reported_clean(self):
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=False, clean=False, reasons=['sensor exit code 1 means an incomplete run'],
            mapper=SimpleNamespace(stdout=''), findings=None))
        outcome = self.process(self.after(), runner)
        self.assertEqual(outcome['status'], 'scanned')
        self.assertIn('INCOMPLETE', outcome['feedback'])
        self.assertIn('incomplete run', outcome['feedback'])
        self.assertNotIn(': clean', outcome['feedback'])

    def test_coached_verdict_carries_mapper_output(self):
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=True, clean=False, reasons=[],
            mapper=SimpleNamespace(stdout='coached: consider fewer parameters'), findings=[{}, {}]))
        outcome = self.process(self.after(), runner)
        self.assertIn('coached: consider fewer parameters', outcome['feedback'])


class AdvisoryAndCoveragePresentationTest(HookTestBase):
    """RV04: non-blocking mapper verdicts stay model-visible; clean never
    covers smells the narrowed single-file pipeline provably did not check."""

    def test_advisory_findings_are_not_presented_as_clean(self):
        # Original severity decision (e.g. severity='suggest'): mapper exit 0
        # with one finding and the full Core guidance in the verdict.
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=True, clean=True, reasons=[],
            mapper=SimpleNamespace(stdout=(
                'suggest: too-many-parameters\nCore guidance: reduce parameters\n'
                'Wissenseigentum: keep interfaces small')),
            findings=[{'smell': 'too-many-parameters'}], not_scanned=[]))
        outcome = self.process(self.after(), runner)
        self.assertEqual(outcome['status'], 'scanned')
        entry = outcome['scanned'][0]
        self.assertTrue(entry['clean'])      # original decision respected
        self.assertTrue(entry['advisory'])
        self.assertTrue(entry['complete'])
        self.assertIn('no enforced findings', outcome['feedback'])
        self.assertIn('Core guidance', outcome['feedback'])
        self.assertIn('Wissenseigentum', outcome['feedback'])
        self.assertNotIn(': clean', outcome['feedback'])

    def test_clean_zero_finding_verdict_still_names_coverage_gaps(self):
        runner = make_runner()  # findings=[], mapper exit 0
        outcome = self.process(self.after(), runner)
        entry = outcome['scanned'][0]
        self.assertFalse(entry['advisory'])
        self.assertTrue(entry['clean'])
        joined = ' '.join(entry['not_scanned'])
        self.assertIn('duplicated-code', joined)
        self.assertIn('unused-dependency', joined)
        self.assertIn('not scanned', outcome['feedback'])
        self.assertIn('duplicated-code', outcome['feedback'])
        self.assertIn('NOT checked', outcome['feedback'])

    def test_pipeline_reported_gaps_are_carried_without_duplication(self):
        reported = ["duplicated-code not scanned in single-file mode: "
                    "repository-wide sensor 'jscpd' is disabled before spawning "
                    "(no qualified single-file scope)"]
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=True, clean=True, reasons=[],
            mapper=SimpleNamespace(stdout=''), findings=[], not_scanned=reported))
        outcome = self.process(self.after(), runner)
        joined = ' '.join(outcome['scanned'][0]['not_scanned'])
        self.assertEqual(joined.count('duplicated-code'), 1)  # no double listing
        self.assertIn('unused-dependency', joined)            # canonical union

    def test_feedback_truncation_is_named_not_silent(self):
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=True, clean=False, reasons=[],
            mapper=SimpleNamespace(stdout='x' * 9000), findings=[{'smell': 's'}]))
        outcome = self.process(self.after(), runner)
        self.assertLessEqual(len(outcome['feedback']), 4000)
        self.assertIn('truncated', outcome['feedback'])

    def test_mapper_verdict_truncation_is_named(self):
        verdict = 'coached: ' + 'y' * 4000
        runner = make_runner(results=lambda rel: SimpleNamespace(
            complete=True, clean=False, reasons=[],
            mapper=SimpleNamespace(stdout=verdict), findings=[{'smell': 's'}]))
        outcome = self.process(self.after(), runner)
        self.assertIn('mapper verdict truncated', outcome['feedback'])


class UnknownToolVisibilityTest(HookTestBase):
    """RV05: unknown completed forms (bash, unknown patch/MCP tools) are a
    visible not_scanned gap; only proven read-only stock tools stay quiet."""

    def test_completed_bash_with_opaque_command_is_visible_not_scanned(self):
        event = self.after(tool='bash', input={'command': 'some opaque command'},
                           result={'content': [{'type': 'text', 'text': 'done'}]})
        outcome = self.process(event)
        self.assertEqual(outcome['status'], 'not_scanned', outcome)
        self.assertIn('not scanned', outcome['reasons'][0])
        self.assertIn('bash', outcome['reasons'][0])
        # No command parsing or path guessing leaks into the result.
        self.assertNotIn('opaque command', json.dumps(outcome))

    def test_unknown_patch_and_custom_mcp_tools_are_visible_not_scanned(self):
        for tool in ('applypatch', 'mcp_custom_foreign'):
            outcome = self.process(self.after(tool=tool))
            self.assertEqual(outcome['status'], 'not_scanned', tool)
            self.assertIn(tool, outcome['reasons'][0])

    def test_known_readonly_stock_tools_stay_unobtrusive(self):
        for tool in ('read', 'glob', 'grep', 'ls', 'webfetch', 'websearch'):
            outcome = self.process(self.after(tool=tool))
            self.assertEqual(outcome['status'], 'not_mutating', tool)
            self.assertIsNone(outcome['feedback'])

    def test_error_status_of_unknown_tool_stays_untouched(self):
        outcome = self.process(self.after(tool='bash', status='error', result=None))
        self.assertEqual(outcome['status'], 'not_mutating')
        self.assertIsNone(outcome['feedback'])

    def test_gortex_dry_run_does_not_flood_scan_warnings(self):
        receipt = dict(REAL_DRYRUN_RECEIPT, path='big.py')
        outcome = self.process(self.after(tool='execute', result={'output': receipt}))
        self.assertEqual(outcome['status'], 'not_mutating')
        self.assertIsNone(outcome['feedback'])


class ExplicitInstallationTrustTest(HookTestBase):
    """Actual original CLIs; caller-owned launch env, never global env mutation."""

    def bridge(self, path, *, roots=None, sensor=None, event=None):
        ci = Path(str(CI / 'venv/bin'))
        env = dict(os.environ)
        env.update(PATH=path, HABIT_FEEDBACK_SCOPE=str(self.scope),
                   HABIT_FEEDBACK_STATE_ROOT=str(self.state),
                   HABIT_FEEDBACK_SENSOR=str(sensor or ci / 'habit-sensors'),
                   HABIT_FEEDBACK_MAPPER=str(ci / 'habit-mapper'))
        env.pop('HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS', None)
        if roots is not None:
            env['HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS'] = json.dumps(roots)
        proc = subprocess.run([sys.executable, '-B', str(HOOK), 'event'],
                              input=json.dumps(event or self.after()),
                              text=True, capture_output=True, env=env, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_inherited_project_relative_empty_and_alias_paths_never_execute(self):
        ci = str(CI / 'venv/bin')
        tools = self.scope / 'tools'
        tools.mkdir()
        marker = self.tmp / 'executed'
        write_stub(tools, 'ruff', 'from pathlib import Path\nPath(%r).touch()\nprint("[]")' % str(marker))
        alias = self.tmp / 'alias'
        alias.mkdir()
        (alias / 'ruff').symlink_to(tools / 'ruff')
        variants = [str(tools), 'tools', '', str(alias)]
        for prefix in variants:
            with self.subTest(prefix=prefix):
                result = self.bridge(prefix + ':' + ci + ':/usr/bin:/bin')
                self.assertFalse(marker.exists(), result)
                self.assertFalse(result['scanned'][0]['complete'], result)
                self.assertIn('INCOMPLETE', result['feedback'])
                self.assertNotIn(': clean', result['feedback'])

    def test_explicit_external_original_installation_runs(self):
        ci = str(CI / 'venv/bin')
        result = self.bridge(ci + ':/usr/bin:/bin', roots=[ci])
        self.assertTrue(result['scanned'][0]['complete'], result)
        self.assertIn('duplicated-code', result['feedback'])
        self.assertIn('unused-dependency', result['feedback'])

    def test_separate_owned_detector_installation_needs_explicit_binding(self):
        ci = str(CI / 'venv/bin')
        install = self.tmp / 'owned-detector-install'
        install.mkdir()
        marker = self.tmp / 'owned-executed'
        write_stub(install, 'ruff', 'from pathlib import Path\nPath(%r).touch()\nprint("[]")' % str(marker))
        path = str(install) + ':' + ci + ':/usr/bin:/bin'
        rejected = self.bridge(path)
        self.assertFalse(marker.exists())
        self.assertFalse(rejected['scanned'][0]['complete'])
        accepted = self.bridge(path, roots=[str(install)])
        self.assertTrue(marker.exists(), accepted)
        self.assertTrue(accepted['scanned'][0]['complete'], accepted)

    def test_event_fields_cannot_grant_repository_trust(self):
        ci = str(CI / 'venv/bin')
        tools = self.scope / 'tools'
        tools.mkdir()
        marker = self.tmp / 'executed'
        write_stub(tools, 'ruff', 'from pathlib import Path\nPath(%r).touch()\nprint("[]")' % str(marker))
        event = self.after(trusted_tool_roots=[str(tools)])
        event['input']['trusted_tool_roots'] = [str(tools)]
        event['result']['metadata'] = {'trusted_tool_roots': [str(tools)]}
        result = self.bridge(str(tools) + ':' + ci + ':/usr/bin:/bin', event=event)
        self.assertFalse(marker.exists())
        self.assertFalse(result['scanned'][0]['complete'])

    def test_repository_cli_alias_and_relative_cli_are_refused(self):
        cli = write_stub(self.scope, 'habit-sensors', 'raise RuntimeError("MUST NOT RUN")')
        alias = self.tmp / 'cli-alias'
        alias.symlink_to(cli)
        for sensor in (cli, alias, Path('habit-sensors')):
            result = self.bridge('/usr/bin:/bin', sensor=sensor)
            self.assertEqual(result['status'], 'not_scanned', result)
            self.assertTrue(result['feedback'], result)

    def test_path_discovery_alone_never_qualifies_original_clis(self):
        env = dict(os.environ)
        env.update(PATH=str(CI / 'venv/bin') + ':/usr/bin:/bin',
                   HABIT_FEEDBACK_SCOPE=str(self.scope),
                   HABIT_FEEDBACK_STATE_ROOT=str(self.state))
        for key in ('HABIT_FEEDBACK_SENSOR', 'HABIT_FEEDBACK_MAPPER',
                    'HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS'):
            env.pop(key, None)
        proc = subprocess.run([sys.executable, '-B', str(HOOK), 'event'],
                              input=json.dumps(self.after()), text=True,
                              capture_output=True, env=env, timeout=30)
        result = json.loads(proc.stdout)
        self.assertEqual(result['status'], 'not_scanned', result)
        self.assertIn('binding required', result['feedback'])
        sensor, mapper, reasons = hook._locate_executables('relative-sensor', 'relative-mapper')
        self.assertIsNone(sensor)
        self.assertIsNone(mapper)
        self.assertTrue(reasons)


class RealAdapterIntegrationTest(HookTestBase):
    """Real T01 adapter with STUB executables: config, env, repo cleanliness."""

    def _real_scan(self):
        return self.process(self.after())

    def test_scan_runs_real_pipeline_with_runtime_config(self):
        outcome = self._real_scan()
        self.assertEqual(outcome['status'], 'scanned', outcome['reasons'])
        self.assertEqual(outcome['scanned'][0]['file'], 'big.py')
        self.assertTrue(outcome['scanned'][0]['complete'], outcome['scanned'][0]['reasons'])
        runtime_cfg = list((self.state).rglob('config.toml'))
        self.assertEqual(len(runtime_cfg), 1)
        config_text = runtime_cfg[0].read_text(encoding='utf-8')
        self.assertIn('plugins = ["generic", "python"]', config_text)
        # Narrowed single-file pipeline: repository-wide sensors are disabled
        # explicitly in the first-run default config, and the coverage gap is
        # still surfaced per scanned entry (never presented as passed).
        self.assertIn('[sensors.jscpd]', config_text)
        self.assertIn('[sensors.deptry]', config_text)
        self.assertIn('disabled = true', config_text)
        gaps = ' '.join(outcome['scanned'][0]['not_scanned'])
        self.assertIn('duplicated-code', gaps)
        self.assertIn('unused-dependency', gaps)
        self.assertIn('not scanned: duplicated-code', outcome['feedback'])
        self.assertIn('not scanned: unused-dependency', outcome['feedback'])

    def test_repository_is_never_mutated_by_a_scan(self):
        before = sorted(p.relative_to(self.scope).as_posix()
                        for p in self.scope.rglob('*'))
        before_bytes = (self.scope / 'big.py').read_bytes()
        self._real_scan()
        after = sorted(p.relative_to(self.scope).as_posix()
                       for p in self.scope.rglob('*'))
        self.assertEqual(before, after)
        self.assertEqual(before_bytes, (self.scope / 'big.py').read_bytes())

    def test_detector_side_effects_are_redirected_into_state_root(self):
        record = self.state / 'env-record.json'
        wrapper = self.tmp / 'STUB_recording_sensor'
        wrapper.write_text('#!/usr/bin/env python3\nimport os, runpy\n'
                           'os.environ["HABIT_FEEDBACK_RECORD_ENV"] = %r\n'
                           'runpy.run_path(%r, run_name="__main__")\n'
                           % (str(record), str(self.sensor)), encoding='utf-8')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        hook.process_event(self.after(), scope_root=self.scope, state_root=self.state,
                           session='s1', sensor=wrapper, mapper=self.mapper,
                           trusted_tool_roots=[Path(str(CI / 'venv/bin'))])
        (self.scope / "big.py").write_text("x = 2\n", encoding="utf-8")
        outcome = hook.process_event(self.after(), scope_root=self.scope,
                                     state_root=self.state, session='s1',
                                     sensor=wrapper, mapper=self.mapper,
                           trusted_tool_roots=[Path(str(CI / 'venv/bin'))])
        self.assertEqual(outcome['status'], 'scanned', outcome['reasons'])
        recorded = json.loads(record.read_text(encoding='utf-8'))
        self.assertTrue(str(recorded['HOME']).startswith(str(self.state)), recorded)
        self.assertTrue(str(recorded['RUFF_CACHE_DIR']).startswith(str(self.state)), recorded)
        self.assertTrue(str(recorded['TMPDIR']).startswith(str(self.state)), recorded)

    def test_symlinked_runtime_config_is_refused(self):
        scope_dir = hook._state_scope_dir(self.state, self.scope.resolve(), 's1')
        runtime = scope_dir / 'runtime'
        runtime.mkdir(parents=True)
        outside = self.tmp / 'evil-config.toml'
        outside.write_text('plugins = ["generic", "python"]\nfiles = ["**/*.py"]\n',
                           encoding='utf-8')
        (runtime / 'config.toml').symlink_to(outside)
        outcome = self._real_scan()
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('symlink', outcome['reasons'][0] + str(outcome['not_scanned']))

    def test_dangerous_runtime_config_content_is_refused(self):
        scope_dir = hook._state_scope_dir(self.state, self.scope.resolve(), 's1')
        runtime = scope_dir / 'runtime'
        runtime.mkdir(parents=True)
        (runtime / 'config.toml').write_text(
            'plugins = ["generic", "python"]\nfiles = ["**/*.py"]\n[runners]\npy = "python"\n',
            encoding='utf-8')
        outcome = self._real_scan()
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('runtime config rejected', outcome['reasons'][0])

    def test_project_plugin_override_is_visible_and_incomplete(self):
        plugin = self.scope / '.habit-hooks' / 'generic'
        (plugin / 'sensors').mkdir(parents=True)
        (plugin / 'sensors' / 'evil.toml').write_text('command = "x"\n', encoding='utf-8')
        outcome = self._real_scan()
        self.assertEqual(outcome['status'], 'scanned')
        entry = outcome['scanned'][0]
        self.assertFalse(entry['complete'])
        self.assertFalse(entry['clean'])
        self.assertIn('config rejected', entry['reasons'][0])
        self.assertIn('INCOMPLETE', outcome['feedback'])

    def test_project_config_wins_over_trusted_runtime_root(self):
        (self.scope / '.habit-hooks').mkdir()
        (self.scope / '.habit-hooks' / 'config.toml').write_text(
            'plugins = ["generic", "python"]\nfiles = ["**/*.py"]\n[sensors.jscpd]\n'
            'disabled = true\n', encoding='utf-8')
        outcome = self._real_scan()
        self.assertEqual(outcome['status'], 'scanned', outcome['reasons'])


class ParallelismTest(HookTestBase):
    def test_busy_state_lock_times_out_visibly(self):
        scope_dir = hook._state_scope_dir(self.state, self.scope.resolve(), 's1')
        scope_dir.mkdir(parents=True, exist_ok=True)
        import fcntl
        fd = os.open(scope_dir / 'state.lock', os.O_WRONLY | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            original_wait = hook.STATE_LOCK_WAIT_S
            hook.STATE_LOCK_WAIT_S = 0.2
            try:
                outcome = self.process(self.after())
            finally:
                hook.STATE_LOCK_WAIT_S = original_wait
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('state lock busy', outcome['reasons'][0])

    def test_concurrent_events_serialise_without_corruption(self):
        for i in range(4):
            (self.scope / ('c%d.py' % i)).write_text('x = %d\n' % i, encoding='utf-8')
        lock = threading.Lock()
        runner_calls = []

        def runner(scope, rel, *, sensor, mapper, trusted_root, env):
            with lock:
                runner_calls.append(rel)
            return SimpleNamespace(complete=True, clean=True, reasons=[],
                                   mapper=SimpleNamespace(stdout='clean'), findings=[])

        errors = []

        def work(i):
            try:
                receipt = {"status": "applied", "path": "proj/c%d.py" % i,
                           "new_sha": "a" * 40, "replacements": 1}
                self.process(dict(phase='after', tool='execute', status='completed',
                                  sessionID='s1',
                                  result={'content': json.dumps(receipt)}), runner=runner)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertFalse(errors, errors)
        self.assertEqual(len(runner_calls), 4)
        scope_dir = hook._state_scope_dir(self.state, self.scope.resolve(), 's1')
        data = json.loads((scope_dir / 'state.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['ledger']), 4)


class CliTransportTest(HookTestBase):
    def _run_cli(self, event, env_extra=None, payload=None):
        env = {'HABIT_FEEDBACK_SCOPE': str(self.scope),
               'HABIT_FEEDBACK_STATE_ROOT': str(self.state),
               'HABIT_FEEDBACK_SESSION': 'cli',
               'HABIT_FEEDBACK_SENSOR': str(self.sensor),
               'HABIT_FEEDBACK_MAPPER': str(self.mapper),
               'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        env.update(env_extra or {})
        data = payload if payload is not None else json.dumps(event)
        proc = subprocess.run([sys.executable, '-B', str(HOOK), 'event'],
                              input=data, capture_output=True, text=True, env=env,
                              timeout=60)
        return proc

    def test_main_transports_json_both_ways(self):
        receipt = dict(REAL_WRITE_RECEIPT, path='proj/big.py')
        proc = self._run_cli(dict(phase='after', tool='execute', status='completed',
                                  sessionID='cli',
                                  result={'content': json.dumps(receipt)}))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload['status'], 'scanned')
        self.assertIn('feedback', payload)

    def test_missing_scope_env_is_a_json_error_not_a_crash(self):
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        proc = subprocess.run([sys.executable, '-B', str(HOOK), 'event'],
                              input='{}', capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)['status'], 'error')

    def test_oversized_event_payload_is_rejected(self):
        proc = self._run_cli({}, payload='x' * (hook.MAX_EVENT_BYTES + 1))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)['status'], 'error')
        self.assertIn('exceeds', json.loads(proc.stdout)['reasons'][0])


class BridgeSignalTest(HookTestBase):
    def test_sigterm_kills_pipeline_process_groups_no_orphans(self):
        pid_file = self.tmp / 'sensor.pid'
        sleeping = write_stub(self.tmp, 'STUB_sleeping_sensor', '''
            import os, time
            open(%r, "w").write(str(os.getpid()))
            time.sleep(60)
            ''' % str(pid_file))
        env = {'HABIT_FEEDBACK_SCOPE': str(self.scope),
               'HABIT_FEEDBACK_STATE_ROOT': str(self.state),
               'HABIT_FEEDBACK_SESSION': 'sig',
               'HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS': json.dumps([
                   str(CI / 'venv/bin')]),
               'HABIT_FEEDBACK_SENSOR': str(sleeping),
               'HABIT_FEEDBACK_MAPPER': str(self.mapper),
               'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        receipt = json.dumps(dict(REAL_WRITE_RECEIPT, path='proj/big.py'))
        event = json.dumps(dict(phase='after', tool='execute', status='completed',
                                sessionID='sig', result={'content': receipt}))
        proc = subprocess.Popen([sys.executable, '-B', str(HOOK), 'event'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env)
        proc.stdin.write(event.encode())
        proc.stdin.close()
        deadline = time.time() + 10
        while not pid_file.exists() and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(pid_file.exists(), 'sensor never started')
        sensor_pid = int(pid_file.read_text())
        proc.terminate()  # SIGTERM to the bridge
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail('bridge did not exit on SIGTERM')
        proc.stdout.close()
        proc.stderr.close()
        self.assertNotEqual(code, 0)
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                os.kill(sensor_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        with self.assertRaises(ProcessLookupError):
            os.kill(sensor_pid, 0)  # no orphan sensor survives the bridge


class ShimExecutionTest(unittest.TestCase):
    """Run the REAL plugin/index.ts through the isolated Node runtime.

    The shim is executed (not regex-checked) with an in-memory `ctx` double
    that implements the SDK-pinned V2 shapes; the bridge runs the real Python
    module with STUB sensor/mapper executables.
    """

    HARNESS = r'''
        import { pathToFileURL } from "node:url"
        const assert = (cond, msg) => { if (!cond) { console.error("ASSERT: " + msg); process.exit(1) } }
        const mod = await import(pathToFileURL(process.env.HABIT_SHIM).href)
        const hooks = {}
        const sessions = JSON.parse(process.env.HABIT_SESSIONS)
        const ctx = {
          session: {
            get: async ({ sessionID }) => {
              const hit = sessions[sessionID]
              if (hit && hit.error) throw new Error(hit.error)
              if (!hit) throw new Error("no such session: " + sessionID)
              return hit.info
            },
          },
          tool: {
            hook: async (name, cb) => { hooks[name] = cb; return { dispose: async () => {} } },
          },
          location: { directory: "/plugin/instance/dir", project: { id: "p", directory: "/x", canonical: "/x" } },
        }
        const cleanup = await mod.default.setup(ctx)
        const scenario = process.env.HABIT_SCENARIO
        const after = { tool: "edit", sessionID: "sA", agent: "build", messageID: "m1",
                        id: "call-1", input: { path: "big.py", oldString: "a", newString: "b" },
                        status: "completed",
                        result: { content: [{ type: "text", text: "ORIGINAL" }],
                                  metadata: { keep: 1 }, output: "structured" } }
        if (scenario === "basic") {
          assert(typeof hooks["execute.before"] === "function", "before hook missing")
          assert(typeof hooks["execute.after"] === "function", "after hook missing")
          await hooks["execute.after"](after)
          const content = after.result.content
          assert(Array.isArray(content) && content.length === 2, "content not extended: " + JSON.stringify(content))
          assert(content[0].text === "ORIGINAL", "original content part lost")
          assert(content[1].type === "text" && content[1].text.includes("habit-feedback"), "feedback not appended")
          assert(after.result.output === "structured", "output changed")
          assert(after.result.metadata.keep === 1, "metadata lost")
        } else if (scenario === "error-untouched") {
          const errEvent = { tool: "edit", sessionID: "sA", agent: "build", messageID: "m2",
                             id: "call-2", input: { path: "big.py" }, status: "error",
                             error: { message: "tool failed" } }
          await hooks["execute.after"](errEvent)
          assert(!("result" in errEvent), "error result must not be created")
        } else if (scenario === "string-content") {
          after.result = { content: "plain output", metadata: {} }
          await hooks["execute.after"](after)
          assert(typeof after.result.content === "string" && after.result.content.startsWith("plain output"),
                 "string content not preserved: " + JSON.stringify(after.result))
          assert(after.result.content.includes("habit-feedback"), "feedback missing on string content")
        } else if (scenario === "no-session-dir") {
          after.sessionID = "sNoDir"
          await hooks["execute.after"](after)
          const text = JSON.stringify(after.result)
          assert(text.includes("NOT RUN"), "missing scope must be visible: " + text)
          assert(!text.includes("process.cwd") && !text.includes("/plugin/instance/dir"),
                 "no fallback scope allowed: " + text)
        } else if (scenario === "session-lookup-fails") {
          after.sessionID = "sFail"
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("session lookup failed"),
                 "lookup failure must be visible")
        } else if (scenario === "two-checkouts-one-instance") {
          // Two sessions, two different checkout directories, one plugin instance.
          const inA = JSON.parse(JSON.stringify(after)); inA.sessionID = "sA"
          const inB = JSON.parse(JSON.stringify(after)); inB.sessionID = "sB"
          await hooks["execute.after"](inA)
          await hooks["execute.after"](inB)
          assert(JSON.stringify(inA.result).includes("habit-feedback"), "scope A not scanned")
          assert(JSON.stringify(inB.result).includes("habit-feedback"), "scope B not scanned")
        } else if (scenario === "file-content") {
          after.result.content.push({type:"file",uri:"file:///tmp/evidence.txt",mime:"text/plain",name:"evidence"})
          const original = JSON.stringify(after.result.content)
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result.content.slice(0,2)) === original, "original file/text content lost")
          assert(after.result.content[2].type === "text", "feedback content missing")
        } else if (scenario === "bridge-spawn-failure") {
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("spawn failed"), "spawn failure invisible")
        } else if (scenario === "bridge-invalid-json") {
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("not JSON"), "invalid output invisible")
        } else if (scenario === "bridge-input-limit") {
          after.input.content = "x".repeat(9 * 1024 * 1024)
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("input limit"), "oversized payload invisible")
        } else if (scenario === "bridge-crash") {
          await hooks["execute.after"](after)
          const text = JSON.stringify(after.result)
          assert(text.includes("exit code"), "crash must be visible: " + text)
          assert(text.includes("ORIGINAL"), "original result must survive a crash")
        } else if (scenario === "bridge-overrun") {
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("output exceeded"),
                 "overrun must be a visible failure, not a partial result")
        } else if (scenario === "bridge-timeout") {
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("timed out"),
                 "timeout must be visible")
        } else if (scenario === "trust-refused") {
          const before = JSON.stringify(after.result)
          await hooks["execute.after"](after)
          const content = after.result.content
          assert(content[0].text === "ORIGINAL", "original text lost")
          assert(after.result.output === "structured", "output changed")
          assert(after.result.metadata.keep === 1, "metadata lost")
          assert(content[1].text.includes("INCOMPLETE") || content[1].text.includes("NOT RUN"),
                 "trust refusal must be model-visible: " + JSON.stringify(after.result))
          assert(!content[1].text.includes(": clean"), "unsafe clean claim")
        } else if (scenario === "unknown-tool-warning") {
          // RV05: completed bash/unknown MCP forms must warn in the next
          // model-visible content without touching the original output.
          const bashEvent = { tool: "bash", sessionID: "sA", agent: "build", messageID: "m3",
                              id: "call-3", input: { command: "opaque command" },
                              status: "completed",
                              result: { content: [{ type: "text", text: "done" }] } }
          await hooks["execute.after"](bashEvent)
          const text = JSON.stringify(bashEvent.result)
          assert(text.includes("NOT RUN"), "unknown completed tool must warn visibly: " + text)
          assert(text.includes("bash"), "warning must name the unknown tool: " + text)
          assert(bashEvent.result.content[0].text === "done", "original content lost")
          assert(!text.includes("opaque command"), "command text must not be echoed: " + text)
          const mcpEvent = { tool: "mcp_custom_foreign", sessionID: "sA", agent: "build",
                             messageID: "m4", id: "call-4", input: {}, status: "completed",
                             result: { content: [{ type: "text", text: "ok" }] } }
          await hooks["execute.after"](mcpEvent)
          const mcpText = JSON.stringify(mcpEvent.result)
          assert(mcpText.includes("NOT RUN"), "unknown MCP tool must warn visibly: " + mcpText)
          assert(mcpEvent.result.content[0].text === "ok", "original MCP content lost")
        } else if (scenario === "module-missing") {
          // setup with a nonexistent module: hooks stay registered and report.
          assert(typeof hooks["execute.after"] === "function", "hooks must still register")
          await hooks["execute.after"](after)
          assert(JSON.stringify(after.result).includes("hook module missing"),
                 "missing module must be visible")
        } else {
          console.error("unknown scenario: " + scenario)
          process.exit(2)
        }
        if (typeof cleanup === "function") await cleanup()
        console.log("SCENARIO-OK " + scenario)
    '''

    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix='awc-t02-shim-', dir='/tmp/opencode')
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name).resolve()
        self.state = self.tmp / 'state'
        self.scopeA = self.tmp / 'projA'
        self.scopeB = self.tmp / 'projB'
        for scope in (self.scopeA, self.scopeB):
            scope.mkdir()
            (scope / 'big.py').write_text('def f(a, b, c, d, e):\n    return a\n',
                                          encoding='utf-8')
        self.sensor = write_stub(self.tmp, 'STUB_sensor', SENSOR_STUB)
        self.mapper = write_stub(self.tmp, 'STUB_mapper', MAPPER_STUB)
        self.harness = self.tmp / 'harness.mjs'
        self.harness.write_text(self.HARNESS, encoding='utf-8')
        self.assertTrue(NODE.is_file(), 'isolated node runtime missing: %s' % NODE)
        self.assertTrue(SHIM.is_file())

    def run_shim(self, scenario, sessions=None, env_extra=None, shim_path=None, timeout=120):
        sessions = sessions if sessions is not None else {
            'sA': {'info': {'id': 'sA', 'location': {'directory': str(self.scopeA)}}},
            'sB': {'info': {'id': 'sB', 'location': {'directory': str(self.scopeB)}}},
            'sNoDir': {'info': {'id': 'sNoDir'}},
            'sFail': {'error': 'boom'},
        }
        env = dict(os.environ)
        env.update({
            'HABIT_SHIM': str(shim_path or SHIM),
            'HABIT_SCENARIO': scenario,
            'HABIT_SESSIONS': json.dumps(sessions),
            'HABIT_FEEDBACK_STATE_ROOT': str(self.state),
            'HABIT_FEEDBACK_SENSOR': str(self.sensor),
            'HABIT_FEEDBACK_MAPPER': str(self.mapper),
            # Explicit qualification of the existing owned test installation;
            # not a grant derived from PATH or any event/fixture project.
            'HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS': json.dumps([
                str(CI / 'venv/bin')]),
        })
        env.update(env_extra or {})
        proc = subprocess.run(
            [str(NODE), '--experimental-strip-types', str(self.harness)],
            capture_output=True, text=True, env=env, timeout=timeout)
        return proc

    def assert_scenario_ok(self, scenario, **kwargs):
        proc = self.run_shim(scenario, **kwargs)
        self.assertEqual(proc.returncode, 0, 'scenario %s failed\nstdout:%s\nstderr:%s'
                         % (scenario, proc.stdout, proc.stderr))
        self.assertIn('SCENARIO-OK ' + scenario, proc.stdout)

    def test_shim_runs_and_appends_feedback_preserving_result(self):
        self.assert_scenario_ok('basic')

    def test_error_result_is_never_touched(self):
        self.assert_scenario_ok('error-untouched')

    def test_string_content_is_preserved_and_extended(self):
        self.assert_scenario_ok('string-content')

    def test_missing_session_directory_is_visible_not_scanned(self):
        self.assert_scenario_ok('no-session-dir')

    def test_session_lookup_failure_is_visible(self):
        self.assert_scenario_ok('session-lookup-fails')

    def test_two_sessions_in_different_checkouts_one_instance(self):
        self.assert_scenario_ok('two-checkouts-one-instance')
        # Two scope dirs under the state root: one per session checkout.
        scope_dirs = [p for p in self.state.iterdir() if p.is_dir()]
        self.assertEqual(len(scope_dirs), 2, scope_dirs)

    def test_bridge_crash_is_visible_and_original_survives(self):
        crasher = self.tmp / 'STUB_crashing_python'
        crasher.write_text('#!/usr/bin/env python3\nimport sys\n'
                           'sys.stderr.write("boom inside bridge\n")\nsys.exit(3)\n',
                           encoding='utf-8')
        crasher.chmod(crasher.stat().st_mode | stat.S_IEXEC)
        self.assert_scenario_ok('bridge-crash',
                                env_extra={'HABIT_FEEDBACK_PYTHON': str(crasher)})

    def test_bridge_output_overrun_is_a_visible_failure(self):
        loud = self.tmp / 'STUB_loud_python'
        loud.write_text('#!/usr/bin/env python3\nprint("x" * 4 * 1024 * 1024)\n',
                        encoding='utf-8')
        loud.chmod(loud.stat().st_mode | stat.S_IEXEC)
        self.assert_scenario_ok('bridge-overrun',
                                env_extra={'HABIT_FEEDBACK_PYTHON': str(loud)})

    def test_bridge_timeout_kills_group_and_is_visible(self):
        sleepy = self.tmp / 'STUB_sleepy_python'
        sleepy.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(60)\n',
                          encoding='utf-8')
        sleepy.chmod(sleepy.stat().st_mode | stat.S_IEXEC)
        self.assert_scenario_ok('bridge-timeout',
                                env_extra={'HABIT_FEEDBACK_PYTHON': str(sleepy),
                                           'HABIT_FEEDBACK_BRIDGE_TIMEOUT_MS': '800'})

    def test_file_content_parts_survive_feedback_append(self):
        self.assert_scenario_ok('file-content')

    def test_spawn_failure_is_visible(self):
        self.assert_scenario_ok('bridge-spawn-failure',
            env_extra={'HABIT_FEEDBACK_PYTHON': str(self.tmp / 'absent-python')})

    def test_invalid_json_is_visible(self):
        invalid = write_stub(self.tmp, 'STUB_invalid_python', 'print("not-json")')
        self.assert_scenario_ok('bridge-invalid-json',
            env_extra={'HABIT_FEEDBACK_PYTHON': str(invalid)})

    def test_input_limit_prevents_bridge_spawn(self):
        self.assert_scenario_ok('bridge-input-limit')

    def test_shim_timeout_reaps_real_sensor_group(self):
        pidfile = self.tmp / 'timeout-sensor.pid'
        sensor = write_stub(self.tmp, 'STUB_timeout_sensor',
            '''import os, time
open(%r, "w").write(str(os.getpid()))
time.sleep(60)''' % str(pidfile))
        self.assert_scenario_ok('bridge-timeout', env_extra={
            'HABIT_FEEDBACK_SENSOR': str(sensor), 'HABIT_FEEDBACK_BRIDGE_TIMEOUT_MS': '1200'})
        self.assertTrue(pidfile.exists(), 'sensor must actually start')
        pid = int(pidfile.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_repository_trust_grant_refused_in_actual_sdk_shim_content(self):
        self.assert_scenario_ok('trust-refused', env_extra={
            'HABIT_FEEDBACK_SENSOR': str(CI / 'venv/bin/habit-sensors'),
            'HABIT_FEEDBACK_MAPPER': str(CI / 'venv/bin/habit-mapper'),
            'HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS': json.dumps([str(self.scopeA)])})

    def test_invalid_launch_trust_shape_warns_without_content_loss(self):
        self.assert_scenario_ok('trust-refused', env_extra={
            'HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS': '{"unknown":"policy"}'})

    def test_unknown_completed_tools_warn_in_model_visible_content(self):
        self.assert_scenario_ok('unknown-tool-warning')

    def test_missing_module_stays_registered_and_reports(self):
        fake_dir = self.tmp / 'empty-plugin'
        fake_dir.mkdir()
        broken_shim = fake_dir / 'index.ts'
        # Same shim source, but placed where ../hook does not exist.
        broken_shim.write_text(SHIM.read_text(encoding='utf-8'), encoding='utf-8')
        self.assert_scenario_ok('module-missing', shim_path=broken_shim)


class PluginOptionsTransportTest(unittest.TestCase):
    # Reuse fixture helpers, not the inherited test suite.
    setUp = ShimExecutionTest.setUp
    run_shim = ShimExecutionTest.run_shim
    HARNESS = r'''
        import { pathToFileURL } from "node:url"
        const mod = await import(pathToFileURL(process.env.HABIT_SHIM).href)
        const assert = (ok, msg) => { if (!ok) throw new Error(msg) }
        const sessions = JSON.parse(process.env.HABIT_SESSIONS)
        const configs = JSON.parse(process.env.HABIT_OPTIONS)
        const beforeEnv = JSON.stringify(process.env)
        const instances = await Promise.all(configs.map(async (options, i) => {
          const hooks = {}
          const ctx = { options, tool: {hook: async (name, cb) => {
            hooks[name] = cb; return {dispose: async () => {}}
          }}, session: {get: async ({sessionID}) => sessions[sessionID].info} }
          const dispose = await mod.default.setup(ctx)
          return {hooks, dispose, i}
        }))
        const results = await Promise.all(instances.map(async ({hooks, i}) => {
          const event = {tool:"edit",sessionID:i === 0 ? "sA" : "sB",agent:"build",
            messageID:"m"+i,id:"call"+i,input:{path:"big.py",oldString:"a",newString:"b"},
            status:"completed", result:{content:[{type:"text",text:"ORIGINAL"},
              {type:"file",uri:"file:///evidence",mime:"text/plain"}],
              metadata:{keep:42},output:{keep:"output"}}}
          await hooks["execute.after"](event)
          assert(event.result.content[0].text === "ORIGINAL", "original text lost")
          assert(event.result.content[1].type === "file", "file part lost")
          assert(event.result.metadata.keep === 42 && event.result.output.keep === "output", "data lost")
          return event.result.content[2].text
        }))
        assert(JSON.stringify(process.env) === beforeEnv, "global environment mutated")
        await Promise.all(instances.map(x => x.dispose()))
        console.log(JSON.stringify(results))
    '''

    def options_run(self, options, **env_extra):
        proc = self.run_shim('options', env_extra={
            'HABIT_OPTIONS': json.dumps(options), **env_extra})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def bindings(self, **overrides):
        ci = str(CI / 'venv/bin')
        values = dict(sensor=str(self.sensor), mapper=str(self.mapper),
                      python=sys.executable, trustedToolRoots=[ci],
                      stateRoot=str(self.state))
        values.update(overrides)
        return values

    def test_options_only_real_original_installation_and_no_environment_grant(self):
        (self.scopeA / 'big.py').write_text(
            'def f(a, b, c, d, e, f, g, h):\n    return a\n')
        ci = str(CI / 'venv/bin')
        result = self.options_run([self.bindings(sensor=ci+'/habit-sensors',
            mapper=ci+'/habit-mapper')], HABIT_FEEDBACK_SENSOR='', HABIT_FEEDBACK_MAPPER='',
            PATH='/usr/bin:/bin')
        self.assertIn('coaching', result[0])
        self.assertIn('Core guidance', result[0])
        self.assertTrue(self.state.is_dir())

    def test_two_instances_spawn_with_isolated_options_and_child_environment(self):
        configs = []
        records = []
        for label in ('A', 'B'):
            record = self.tmp / ('child-'+label+'.json')
            records.append(record)
            python = write_stub(self.tmp, 'python-'+label,
                'import os,sys,json\n'
                'open(%r,"w").write(json.dumps({k:os.environ.get(k) for k in '
                '["HABIT_FEEDBACK_SENSOR","HABIT_FEEDBACK_MAPPER",'
                '"HABIT_FEEDBACK_STATE_ROOT","HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS",'
                '"HABIT_FEEDBACK_SESSION"]}))\n'
                'os.execv(%r,[%r]+sys.argv[1:])' % (str(record), sys.executable, sys.executable))
            mapper = write_stub(self.tmp, 'mapper-'+label,
                'import json,sys\njson.load(sys.stdin)\nprint("INSTANCE-%s")' % label)
            configs.append(self.bindings(python=str(python), mapper=str(mapper),
                                         stateRoot=str(self.tmp / ('state-'+label))))
        feedback = self.options_run(configs, HABIT_FEEDBACK_SENSOR='/absent/fallback')
        for i, label in enumerate(('A', 'B')):
            self.assertIn('INSTANCE-'+label, feedback[i])
            self.assertNotIn('INSTANCE-'+('B' if label == 'A' else 'A'), feedback[i])
            child = json.loads(records[i].read_text())
            self.assertEqual(child['HABIT_FEEDBACK_MAPPER'], configs[i]['mapper'])
            self.assertEqual(child['HABIT_FEEDBACK_STATE_ROOT'], configs[i]['stateRoot'])
            self.assertEqual(json.loads(child['HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS']), configs[i]['trustedToolRoots'])
            self.assertEqual(child['HABIT_FEEDBACK_SESSION'], 'sA' if i == 0 else 'sB')

    def test_invalid_option_shapes_fail_visibly_without_echoing_values(self):
        for name, value in [('sensor','relative-secret'), ('mapper', 42),
                            ('python', None), ('trustedToolRoots','SECRET-VALUE'),
                            ('trustedToolRoots',['/']), ('stateRoot','relative-secret')]:
            with self.subTest(name=name, value=value):
                feedback = self.options_run([self.bindings(**{name:value})])[0]
                self.assertIn('NOT RUN', feedback)
                self.assertIn(name, feedback)
                self.assertNotIn('SECRET-VALUE', feedback)
                self.assertNotIn('relative-secret', feedback)

    def test_options_do_not_bypass_state_or_root_guards(self):
        for overrides in [dict(trustedToolRoots=[str(self.scopeA)]),
                          dict(stateRoot=str(self.scopeA / 'state'))]:
            feedback = self.options_run([self.bindings(**overrides)])[0]
            self.assertTrue('NOT RUN' in feedback or 'INCOMPLETE' in feedback)
            self.assertNotIn(': clean', feedback)

    def test_repository_python_alias_never_executes(self):
        marker = self.tmp / 'python-executed'
        python = write_stub(self.scopeA, 'python',
                            'open(%r,"w").write("BAD")' % str(marker))
        alias = self.tmp / 'python-alias'
        alias.symlink_to(python)
        feedback = self.options_run([self.bindings(python=str(alias))])[0]
        self.assertIn('NOT RUN', feedback)
        self.assertFalse(marker.exists())

    def test_no_explicit_cli_bindings_is_not_scanned(self):
        feedback = self.options_run([{}], HABIT_FEEDBACK_SENSOR='', HABIT_FEEDBACK_MAPPER='')[0]
        self.assertIn('NOT RUN', feedback)
        self.assertNotIn(': clean', feedback)


class ResultShapeContractTest(unittest.TestCase):
    """SDK-pinned result shapes in both halves (source-level guards only for
    shapes that the executed shim test above cannot reach)."""

    def test_shim_uses_documented_v2_event_fields(self):
        source = SHIM.read_text(encoding='utf-8')
        for field in ('event.tool', 'event.sessionID', 'event.id', 'event.input',
                      'event.status', 'event.result'):
            self.assertIn(field, source)
        self.assertIn('ctx.tool.hook("execute.before"', source)
        self.assertIn('ctx.tool.hook("execute.after"', source)
        self.assertIn('ctx.session.get({ sessionID: event.sessionID })', source)

    def test_shim_is_esm_native_no_dirname(self):
        source = SHIM.read_text(encoding='utf-8')
        self.assertNotIn('__dirname', source)
        self.assertIn('fileURLToPath(import.meta.url)', source)

    def test_shim_uses_v2_content_result_form(self):
        source = SHIM.read_text(encoding='utf-8')
        self.assertIn('{type:"text", text}', source)
        # V1 tool-result fields must not drive the append path
        self.assertNotIn('result.output +', source)

    def test_no_v1_alias_dependency(self):
        source = SHIM.read_text(encoding='utf-8')
        self.assertNotIn('from "@opencode-ai/plugin"', source)
        self.assertNotIn("require('@opencode-ai/plugin'", source)

    def test_python_bridge_transports_only_json(self):
        source = HOOK.read_text(encoding='utf-8')
        for forbidden in ('eval(', 'exec(', 'os.system', 'shell=True', 'subprocess'):
            self.assertNotIn(forbidden, source, forbidden)


class MapperRuntimeGuideTest(HookTestBase):
    def test_real_original_mapper_uses_runtime_core_guide_without_project_writes(self):
        mapper = Path(str(CI / 'venv/bin/habit-mapper'))
        self.assertTrue(mapper.is_file(), 'qualified mapper required, no skip')
        before = {p.relative_to(self.scope).as_posix(): p.read_bytes()
                  for p in self.scope.rglob('*') if p.is_file()}
        result = hook.process_event(self.after(), scope_root=self.scope, state_root=self.state,
            session='s1', sensor=self.sensor, mapper=mapper)
        self.assertEqual(result['status'], 'scanned', result)
        self.assertTrue(result['scanned'][0]['complete'], result)
        self.assertIn('Core guidance', result['scanned'][0]['verdict'])
        self.assertIn('Wissenseigentum', result['scanned'][0]['verdict'])
        after = {p.relative_to(self.scope).as_posix(): p.read_bytes()
                 for p in self.scope.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_mapper_workdir_cannot_leave_trusted_root(self):
        adapter = hook._load_adapter()
        trusted = self.tmp / 'trusted'
        trusted.mkdir()
        (trusted / 'config.toml').write_text(hook.CANONICAL_RUNTIME_CONFIG)
        with self.assertRaises(adapter.ConfigRejected):
            adapter.run_pipeline(self.scope, file='big.py', sensor_executable=self.sensor,
                mapper_executable=self.mapper, trusted_config_root=trusted,
                mapper_project_root=self.tmp)

    def test_structured_codemode_receipt_and_mixed_batch_are_explicit(self):
        receipt = dict(REAL_WRITE_RECEIPT, path='proj/big.py')
        event = self.after(tool='execute', result={'output': [receipt, {'unknown': 'data'}]})
        result = self.process(event)
        self.assertEqual(result['status'], 'scanned')
        self.assertEqual(len(result['not_scanned']), 1)
        self.assertIn('partial', result['feedback'])


class BoundedEventRegressionTest(HookTestBase):
    def test_large_file_is_not_scanned_not_clean(self):
        target = self.scope / 'large.py'
        with target.open('wb') as handle:
            handle.truncate(hook.MAX_SCAN_FILE_BYTES + 1)
        result = self.process(self.after(input={'path': 'large.py'}))
        self.assertEqual(result['status'], 'not_scanned')
        self.assertIn('file size', result['not_scanned'][0]['reason'])

    def test_too_many_receipts_are_not_walked(self):
        receipt = dict(REAL_WRITE_RECEIPT, path='proj/big.py')
        result = self.process(self.after(tool='execute', result={
            'output': [receipt] * (hook.MAX_RECEIPTS_PER_EVENT + 1)}))
        self.assertEqual(result['status'], 'not_scanned')
        self.assertIn('count exceeds', result['reasons'][0])

    def test_concurrent_file_change_prevents_a_clean_claim_or_cache(self):
        def runner(scope, rel, **kwargs):
            (scope / rel).write_text('changed while scan ran')
            return SimpleNamespace(complete=True, clean=True, reasons=[], findings=[],
                mapper=SimpleNamespace(stdout='clean'))
        result = self.process(self.after(), runner)
        self.assertFalse(result['scanned'][0]['complete'])
        self.assertFalse(result['scanned'][0]['clean'])
        self.assertIn('changed during scan', result['scanned'][0]['reasons'][0])

    def test_project_config_symlink_cannot_escape_scope(self):
        config = self.scope / '.habit-hooks'
        config.mkdir()
        outside = self.tmp / 'external.toml'
        outside.write_text(hook.CANONICAL_RUNTIME_CONFIG)
        (config / 'config.toml').symlink_to(outside)
        result = self.process(self.after())
        self.assertFalse(result['scanned'][0]['complete'])
        self.assertIn('outside project', result['scanned'][0]['reasons'][0])

    def test_state_root_inside_project_is_refused_without_writes(self):
        state = self.scope / 'runtime-state'
        result = hook.process_event(self.after(), scope_root=self.scope, state_root=state,
            session='s1', sensor=self.sensor, mapper=self.mapper)
        self.assertEqual(result['status'], 'not_scanned')
        self.assertFalse(state.exists())

    def test_runtime_directory_symlink_does_not_receive_writes(self):
        scope_dir = hook._state_scope_dir(self.state, self.scope, 's1')
        scope_dir.mkdir(parents=True, mode=0o700)
        outside = self.tmp / 'outside-runtime'
        outside.mkdir()
        (scope_dir / 'runtime').symlink_to(outside)
        result = self.process(self.after())
        self.assertEqual(result['status'], 'not_scanned')
        self.assertEqual(list(outside.iterdir()), [])


class SDKTypecheckTest(unittest.TestCase):
    def test_actual_shim_typechecks_against_exact_sdk_2_0_25(self):
        runtime = Path(os.environ.get('AWC_HABIT_SDK', '/tmp/opencode/opencode-plugin-sdk')) / 'runtime'
        modules = runtime / 'node_modules'
        for name in ('@opencode/plugin', '@opencode/schema', '@opencode/client'):
            manifest = json.loads((modules / name / 'package.json').read_text())
            self.assertEqual(manifest['version'], '2.0.25')
        source = runtime / 'index.ts'
        source.write_text(SHIM.read_text(), encoding='utf-8')
        command = [str(NODE), str(modules / 'typescript/bin/tsc'), '--noEmit', '--strict',
                   '--skipLibCheck', '--target', 'es2022', '--module', 'nodenext',
                   '--moduleResolution', 'nodenext', '--typeRoots', str(modules / '@types'),
                   '--types', 'node', str(source)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class AdditionalStateSafetyTest(HookTestBase):
    def test_state_files_and_scope_dirs_refuse_symlinks(self):
        for filename in ('state.json', 'state.lock', 'scope-directory'):
            with self.subTest(filename=filename):
                state = self.tmp / ('state-' + filename)
                state.mkdir(mode=0o700)
                scope_dir = hook._state_scope_dir(state, self.scope, 's1')
                victim = self.tmp / ('victim-' + filename)
                if filename == 'scope-directory':
                    victim.mkdir()
                    scope_dir.symlink_to(victim)
                else:
                    scope_dir.mkdir(mode=0o700)
                    victim.write_text('DO NOT CHANGE')
                    (scope_dir / filename).symlink_to(victim)
                outcome = hook.process_event(self.after(), scope_root=self.scope, state_root=state,
                    session='s1', sensor=self.sensor, mapper=self.mapper)
                self.assertEqual(outcome['status'], 'not_scanned', outcome)
                self.assertIn('unsafe state path', outcome['reasons'][0])
                if filename != 'scope-directory':
                    self.assertEqual(victim.read_text(), 'DO NOT CHANGE')

    def test_symlink_ancestor_is_refused(self):
        actual = self.tmp / 'ancestor-real'
        actual.mkdir()
        link = self.tmp / 'ancestor-link'
        link.symlink_to(actual)
        outcome = hook.process_event(self.after(), scope_root=self.scope, state_root=link / 'state',
            session='s1', sensor=self.sensor, mapper=self.mapper)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('symlink', outcome['reasons'][0])

    def test_incomplete_scan_is_retried_not_cached_clean(self):
        calls = []
        runner = make_runner(calls=calls, results=lambda rel: SimpleNamespace(
            complete=False, clean=False, reasons=['missing detector'], findings=None,
            mapper=SimpleNamespace(stdout='')))
        self.process(self.after(), runner)
        self.process(self.after(), runner)
        self.assertEqual(len(calls), 2)

    def test_input_limit_applies_to_direct_events(self):
        event = self.after(input={'path': 'big.py', 'content': 'x' * hook.MAX_EVENT_BYTES})
        outcome = self.process(event)
        self.assertEqual(outcome['status'], 'not_scanned')
        self.assertIn('input limit', outcome['reasons'][0])


if __name__ == '__main__':
    unittest.main()
