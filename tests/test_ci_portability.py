"""Portability of the local/CI checks: versioned targetsets, fresh fixtures, isolated pinned tools."""
import sys
sys.dont_write_bytecode = True
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, root=ROOT):
    spec = importlib.util.spec_from_file_location(name + '_tested', root / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('check_core_contracts')
bootstrap = load('bootstrap_ci')

# Characterization of the scopes the checker formerly read from the ignored plan 004
# (T02-T07, shared plus review-finding.yaml), recorded before the switch.
CHARACTERIZED = {
    'milestones': ['milestone-format.md', 'goal-format.md', 'milestone-index-format.md'],
    'shared': ['SKILL.md', 'workflow-contract.md', 'artifact-contract.md', 'verification.md', 'user-instructions-contract.md', 'workflow-catalog.yaml', 'handoff.md', 'review-finding.yaml'],
    'workflows': ['core-brainstorm', 'core-plan', 'core-execute', 'core-review', 'core-research', 'core-architecture', 'core-refactor', 'core-repo-audit', 'core-milestone', 'goal-prompt.md', 'core-handoff', 'start-prompt.md'],
    'domains': ['core-backend', 'core-database', 'core-frontend', 'core-mobile', 'core-tf-infra', 'core-debug', 'core-docs'],
    'setup': ['core-init-mcps', 'core-init-project', 'core-user2agent-instructions'],
    'docs': ['README.md', 'DESIGN.md'],
}


def source_files():
    listing = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in listing.decode().split('\0') if p and (ROOT / p).is_file()]


def fresh_fixture(directory):
    """Copy only versioned/unignored sources: no .agentic-workflow, no harness projections."""
    root = Path(directory) / 'repo'
    for relative in source_files():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return root


class Targetsets(unittest.TestCase):
    def test_versioned_targetsets_preserve_characterized_sets(self):
        data = json.loads((ROOT / 'scripts/ci_contract_targets.json').read_text(encoding='utf-8'))
        groups = checker.validate_targetsets(data)
        self.assertEqual(list(groups), list(CHARACTERIZED))
        for group, markers in CHARACTERIZED.items():
            with self.subTest(group=group):
                self.assertEqual(len(groups[group]), len(markers))
                for path, marker in zip(groups[group], markers):
                    self.assertIn(marker, path)
                self.assertTrue(all((ROOT / p).is_file() for p in groups[group]))

    def test_checker_no_longer_reads_private_plans(self):
        source = (ROOT / 'scripts/check_core_contracts.py').read_text(encoding='utf-8')
        for legacy in ('004-core-goals-milestones-and-synergies', 'GROUP_TASK', 'PLAN ='):
            self.assertNotIn(legacy, source)

    def test_broken_targetsets_fail(self):
        good = json.loads((ROOT / 'scripts/ci_contract_targets.json').read_text(encoding='utf-8'))
        def variant(change):
            data = json.loads(json.dumps(good))
            change(data)
            return data
        broken = {
            'schema': variant(lambda d: d.update(schema='ci-contract-targets/v0')),
            'missing group': variant(lambda d: d['groups'].pop('docs')),
            'extra group': variant(lambda d: d['groups'].update(extra=['README.md'])),
            'reordered': variant(lambda d: d.update(groups=dict(reversed(list(d['groups'].items()))))),
            'empty': variant(lambda d: d['groups'].update(docs=[])),
            'duplicate': variant(lambda d: d['groups']['docs'].append('README.md')),
            'escape': variant(lambda d: d['groups']['docs'].append('../outside.md')),
            'absolute': variant(lambda d: d['groups']['docs'].append('/etc/passwd')),
            'not a list': variant(lambda d: d['groups'].update(docs='README.md')),
        }
        for label, data in broken.items():
            with self.subTest(label=label), self.assertRaises(checker.ContractError):
                checker.validate_targetsets(data)

    def test_missing_or_invalid_targetset_file_and_missing_source_fail(self):
        with tempfile.TemporaryDirectory(prefix='targetsets-') as directory:
            root = Path(directory)
            with self.assertRaises(OSError):
                checker.targets(root, 'docs')
            (root / 'scripts').mkdir()
            (root / checker.TARGETS).write_text('{not json', encoding='utf-8')
            with self.assertRaisesRegex(checker.ContractError, 'ungültige Targetsets'):
                checker.targets(root, 'docs')
            shutil.copyfile(ROOT / checker.TARGETS, root / checker.TARGETS)
            with self.assertRaisesRegex(checker.ContractError, 'Phasenvoraussetzung fehlt'):
                checker.check_group(root, 'docs')
        with tempfile.TemporaryDirectory(prefix='targetsets-') as directory:
            root = fresh_fixture(directory)
            (root / 'DESIGN.md').unlink()
            result = subprocess.run([sys.executable, '-B', str(root / 'scripts/check_core_contracts.py'), '--group', 'all'], cwd=root, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Phasenvoraussetzung fehlt: DESIGN.md', result.stderr)


class FreshFixture(unittest.TestCase):
    def test_checks_pass_without_private_plans_or_installed_authoring_skills(self):
        with tempfile.TemporaryDirectory(prefix='fresh-fixture-') as directory:
            root = fresh_fixture(directory)
            self.assertFalse((root / '.agentic-workflow').exists())
            self.assertFalse((root / '.agents').exists())
            home = Path(directory) / 'empty-home'
            home.mkdir()
            # An empty HOME hides installed authoring skills; PyYAML stays importable from its real location.
            yaml_site = str(Path(checker.yaml.__file__).resolve().parents[1])
            env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=yaml_site)
            # Every existing suite; this module itself is excluded to avoid recursion.
            commands = [[sys.executable, '-B', 'scripts/check_core_contracts.py', '--group', 'all']]
            commands += [[sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-t', 'tests', '-p', name] for name in ('test_core_contracts.py', 'test_devops_contracts.py', 'test_design_principles.py')]
            for command in commands:
                result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=900)
                with self.subTest(command=command[2:]):
                    self.assertEqual(result.returncode, 0, result.stderr[-3000:] + result.stdout[-2000:])
                    self.assertNotIn('skipped', result.stderr)
            self.assertFalse((root / '.agentic-workflow').exists())


class Toolchain(unittest.TestCase):
    def test_pins_are_exact_and_consistent(self):
        tc = bootstrap.load_toolchain()
        self.assertEqual((tc['mise']['version'], tc['python']['version'], tc['node']['version'], tc['apm']['version'], tc['actionlint']['version'], tc['shellcheck']['version']), ('2026.10.6', '3.13.14', '22.23.3', '0.31.0', '1.7.12', '0.11.0'))
        self.assertEqual(tc['python']['packages'], {'PyYAML': '6.0.3'})
        self.assertEqual(tc['npm']['packages'], {'release-please': '17.11.2'})
        bootstrap.check_pins(tc)

    def test_pin_drift_and_missing_integrity_fail(self):
        mutations = {
            'scripts/requirements-ci.txt': ('PyYAML==6.0.3', 'PyYAML==6.0.2'),
            'scripts/package.json': ('"release-please": "17.11.2"', '"release-please": "^17.11.2"'),
            'scripts/package-lock.json': ('"integrity"', '"integrityX"'),
        }
        for relative, (old, new) in mutations.items():
            with self.subTest(file=relative), tempfile.TemporaryDirectory(prefix='toolchain-') as directory:
                root = Path(directory)
                shutil.copytree(ROOT / 'scripts', root / 'scripts')
                path = root / relative
                path.write_text(path.read_text(encoding='utf-8').replace(old, new, 1), encoding='utf-8')
                module = load('bootstrap_ci', root)
                with self.assertRaises(module.ToolchainError):
                    module.check_pins(module.load_toolchain())
        with tempfile.TemporaryDirectory(prefix='toolchain-') as directory:
            path = Path(directory) / 'toolchain.json'
            for change in (lambda d: d['node'].update(sha256=''), lambda d: d['apm'].update(url='http://example.invalid/apm'), lambda d: d['actionlint'].update(sha256='abc'), lambda d: d.pop('actionlint'), lambda d: d['shellcheck'].update(sha256=''), lambda d: d['shellcheck'].update(version='0.11'), lambda d: d.pop('shellcheck'), lambda d: d['python'].update(version='3.13'), lambda d: d.pop('npm')):
                data = json.loads((ROOT / 'scripts/ci_toolchain.json').read_text(encoding='utf-8'))
                change(data)
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises((bootstrap.ToolchainError, KeyError)):
                    bootstrap.load_toolchain(path)

    def test_wrong_runtime_versions_fail_without_substitution(self):
        tc = bootstrap.load_toolchain()
        with patch.object(bootstrap.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '2026.10.7 linux-x64\n', '')), self.assertRaisesRegex(bootstrap.ToolchainError, 'mise 2026.10.6'):
            bootstrap.check_runtime(tc)
        with patch.object(bootstrap.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '2026.10.6 linux-x64\n', '')), patch.object(bootstrap.sys, 'version_info', (3, 13, 13)), self.assertRaisesRegex(bootstrap.ToolchainError, 'keine Ersatzversion'):
            bootstrap.check_runtime(tc)

    def test_workspace_must_be_isolated(self):
        for bad in (str(ROOT / 'ci'), str(Path.home()), '/'):
            with self.subTest(workspace=bad), patch.dict(os.environ, AWC_CI_WORKSPACE=bad), self.assertRaises(bootstrap.ToolchainError):
                bootstrap.workspace()
        env = bootstrap.isolated_env(Path('/tmp/ws'))
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'TMPDIR', 'PIP_CACHE_DIR', 'npm_config_cache', 'npm_config_userconfig', 'npm_config_prefix'):
            self.assertTrue(env[key].startswith('/tmp/ws'), key)
        self.assertEqual(env['PIP_CONFIG_FILE'], os.devnull)

    def test_checks_never_install_and_report_missing_tools(self):
        with tempfile.TemporaryDirectory(prefix='empty-ws-') as directory:
            with patch.object(bootstrap, 'run') as run, self.assertRaisesRegex(bootstrap.ToolchainError, 'tools:setup'):
                bootstrap.tool_versions(bootstrap.load_toolchain(), Path(directory), {})
            run.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_shellcheck_blocks_and_isolated_path_comes_first(self):
        with tempfile.TemporaryDirectory(prefix='partial-ws-') as directory:
            ws = Path(directory)
            for relative in ('venv/bin/python', 'node/bin/node', 'apm/apm', 'actionlint/actionlint'):
                (ws / relative).parent.mkdir(parents=True)
                (ws / relative).write_text('', encoding='utf-8')
            with patch.object(bootstrap, 'run') as run, self.assertRaisesRegex(bootstrap.ToolchainError, 'shellcheck/shellcheck'):
                bootstrap.tool_versions(bootstrap.load_toolchain(), ws, {})
            run.assert_not_called()
            self.assertFalse((ws / 'shellcheck').exists())
        with patch.dict(os.environ, PATH='/usr/bin'):
            parts = bootstrap.isolated_env(Path('/tmp/ws'))['PATH'].split(os.pathsep)
        self.assertLess(parts.index('/tmp/ws/shellcheck'), parts.index('/usr/bin'))
        self.assertLess(parts.index('/tmp/ws/actionlint'), parts.index('/usr/bin'))

    def test_actionlint_binds_pinned_shellcheck_without_disabling(self):
        command = [str(c) for c in bootstrap.step_command(('actionlint', '.github/workflows/ci.yaml'), Path('/tmp/ws'))]
        self.assertEqual(command[:2], ['/tmp/ws/actionlint/actionlint', '-shellcheck=/tmp/ws/shellcheck/shellcheck'])
        self.assertEqual([c for c in command if c.startswith('-shellcheck')], ['-shellcheck=/tmp/ws/shellcheck/shellcheck'])

    def test_integrity_violation_discards_download(self):
        with tempfile.TemporaryDirectory(prefix='download-') as directory:
            ws = Path(directory)
            tool = dict(url='https://example.invalid/tool.tar.gz', sha256='0' * 64)
            with patch.object(bootstrap.urllib.request, 'urlopen', return_value=io.BytesIO(b'tampered')), self.assertRaisesRegex(bootstrap.ToolchainError, 'Integritätswert verletzt'):
                bootstrap.download(tool, ws)
            self.assertEqual(list((ws / 'downloads').iterdir()), [])


class MiseTasks(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8'))
        self.tasks = self.config['tasks']

    def test_required_tasks_and_no_auto_install(self):
        self.assertEqual(set(self.tasks), {'tools:setup', 'check', 'version:check', 'release:test', 'workflows:check', 'docs:check', 'acceptance'})
        self.assertEqual(self.config['min_version'], '2026.10.6')
        self.assertIs(self.config['settings']['auto_install'], False)
        self.assertNotIn('tools', self.config)

    def test_setup_and_checks_are_separate(self):
        self.assertEqual(self.tasks['tools:setup']['run'], 'python3 -B scripts/bootstrap_ci.py setup')
        for name, task in self.tasks.items():
            if name != 'tools:setup':
                self.assertNotIn(' setup', task['run'], name)
                self.assertNotIn('depends', task, name)

    def test_followups_dispatch_to_contracted_steps(self):
        for name in ('version:check', 'release:test', 'workflows:check', 'docs:check', 'acceptance'):
            self.assertEqual(self.tasks[name]['run'], 'python3 -B scripts/bootstrap_ci.py run ' + name)
        self.assertEqual(set(bootstrap.STEPS), {'version:check', 'release:test', 'workflows:check', 'docs:check', 'acceptance'})


WS = Path('/fake-ws')
PY = str(WS / 'venv/bin/python')


def unittest_call(root, name):
    return [PY, '-B', '-m', 'unittest', 'discover', '-s', str(root / 'tests'), '-t', str(root / 'tests'), '-p', name, '-v']


class FollowupDispatch(unittest.TestCase):
    """Fake follow-up sources prove the exact pinned calls without implementing T02-T04."""

    def run_task(self, task, present=None, results=None, snapshots=None):
        with tempfile.TemporaryDirectory(prefix='dispatch-') as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'scripts', root / 'scripts')
            module = load('bootstrap_ci', root)
            present = list(module.OWNERS if present is None else present)
            # Declared-missing sources really are absent, even where the real follow-up already exists.
            for relative in set(module.OWNERS) - set(present):
                (root / relative).unlink(missing_ok=True)
            for relative in present:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text('fake fixture\n', encoding='utf-8')
            calls, events = [], []
            def call(command, env):
                calls.append([str(c) for c in command])
                return (results or {}).get(Path(str(command[-2] if command[-1] == '-v' else command[-1])).name, subprocess.CompletedProcess(command, 0, '', 'Ran 2 tests\n\nOK\n'))
            output, error = io.StringIO(), io.StringIO()
            with patch.object(module, 'verify', side_effect=lambda: events.append('verify') or ({}, WS, {'HOME': str(WS / 'home')}, {})), \
                 patch.object(module, 'source_snapshot', side_effect=snapshots or (lambda: {})), \
                 patch.object(module, 'call', side_effect=call), patch.object(module, 'check', side_effect=lambda: events.append('check')), \
                 patch.object(module, 'setup') as setup, patch.object(module, 'download') as download, patch.object(module, 'extract') as extract, \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                code = module.main(['run', task])
            for installer in (setup, download, extract):
                installer.assert_not_called()
            return code, calls, events, output.getvalue(), error.getvalue(), root

    def test_exact_pinned_calls(self):
        expected = {
            'version:check': lambda r: [[PY, '-B', str(r / 'scripts/release_guard.py'), 'version-check']],
            'release:test': lambda r: [unittest_call(r, 'test_release_automation.py'), unittest_call(r, 'test_core_package.py')],
            'workflows:check': lambda r: [[str(WS / 'actionlint/actionlint'), '-shellcheck=' + str(WS / 'shellcheck/shellcheck'), str(r / '.github/workflows/ci.yaml'), str(r / '.github/workflows/release.yaml')], unittest_call(r, 'test_ci_workflows.py')],
            'docs:check': lambda r: [[PY, '-B', str(r / 'scripts/check_core_contracts.py'), '--group', 'docs']],
        }
        for task, build in expected.items():
            with self.subTest(task=task):
                code, calls, events, output, _, root = self.run_task(task)
                self.assertEqual((code, calls, events), (0, build(root), ['verify']))
                self.assertNotIn('PACKAGE-EFFECT', output)
                self.assertFalse(any('install' in part or part == 'ci' for command in calls for part in command))
        code, calls, events, output, _, root = self.run_task('acceptance')
        self.assertEqual((code, events), (0, ['verify', 'check']))
        steps = [c for t in ('version:check', 'release:test', 'workflows:check', 'docs:check') for c in expected[t](root)]
        self.assertEqual(calls, steps + [[PY, '-B', str(root / 'scripts/build_core_package.py'), 'verify']])
        self.assertIn('PACKAGE-EFFECT erlaubt (nur acceptance)', output)

    def test_missing_sources_block_before_tools_or_calls(self):
        for task, missing, owner in (('version:check', 'scripts/release_guard.py', 'T02'), ('release:test', 'tests/test_core_package.py', 'T02'),
                                     ('workflows:check', '.github/workflows/release.yaml', 'T03'), ('acceptance', 'scripts/build_core_package.py', 'T02')):
            with self.subTest(task=task):
                present = [p for p in bootstrap.OWNERS if p != missing]
                code, calls, events, _, error, _ = self.run_task(task, present)
                self.assertEqual((code, calls, events), (1, [], []))
                self.assertIn(missing + ' (' + owner + ')', error)
                code, calls, events, _, _, root = self.run_task(task, present + [missing])
                self.assertEqual((code, events[0]), (0, 'verify'))
                self.assertTrue(any(str(root / missing) in command or missing.endswith(command[-2]) for command in calls))
                self.assertIn('kein grüner Skip', error)

    def test_failing_steps_zero_tests_and_unknown_task_block(self):
        cases = {
            'version:check': {'version-check': subprocess.CompletedProcess([], 3, '', '')},
            'release:test': {'test_core_package.py': subprocess.CompletedProcess([], 0, '', 'Ran 0 tests\n\nNO TESTS RAN\n')},
            'workflows:check': {'release.yaml': subprocess.CompletedProcess([], 1, '', 'actionlint finding')},
            'docs:check': {'docs': subprocess.CompletedProcess([], 1, '', 'FAIL')},
        }
        for task, results in cases.items():
            with self.subTest(task=task):
                code, _, _, _, error, _ = self.run_task(task, results=results)
                self.assertEqual(code, 1)
                self.assertRegex(error, 'Schritt fehlgeschlagen|keine Tests ausgeführt')
        code, _, _, _, error, _ = self.run_task('acceptance', results={'test_ci_workflows.py': subprocess.CompletedProcess([], 0, '', '')})
        self.assertEqual(code, 1)
        self.assertIn('keine Tests ausgeführt', error)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bootstrap.main(['run', 'unknown']), 1)

    def test_source_change_during_dispatch_fails(self):
        snapshots = iter([{'a': '1'}, {'a': '2'}])
        code, _, _, _, error, _ = self.run_task('docs:check', snapshots=lambda: next(snapshots))
        self.assertEqual(code, 1)
        self.assertIn('hat Quellbestand verändert', error)

    def test_missing_isolated_tool_blocks_without_install(self):
        with tempfile.TemporaryDirectory(prefix='empty-ws-') as directory, patch.dict(os.environ, AWC_CI_WORKSPACE=directory), \
             patch.object(bootstrap, 'check_runtime'), patch.object(bootstrap, 'setup') as setup, patch.object(bootstrap, 'download') as download, \
             contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(bootstrap.main(['run', 'docs:check']), 1)
            setup.assert_not_called()
            download.assert_not_called()
            self.assertIn('tools:setup', error.getvalue())
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
