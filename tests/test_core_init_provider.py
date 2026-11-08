"""Integrated provider contract plus the unchanged original safety suite."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'.apm/skills/core-init-project'
LEGACY_SKILL = ROOT/'.apm/skills/gortex-serena-configurator'
# Snapshot at the old source's exact migration revision, not its older import inventory.
# Files not touched since the migration stay pinned to that revision.
SOURCE_HASHES = {
    'scripts/requirements.txt': '3eb0bcd11c478e00ecb6dca8668b5ed32dc5aa273cb278411c1d0d90e6a72584',
}
PROBE_TIMEOUT_SECONDS = 30
# Files revised for Serena 1.7 (`language_servers` next to the legacy `languages` key). Re-pin
# deliberately when one of them changes; migration revision hashes: git history of this test.
REVISED_HASHES = {
    'references/provider-setup.md': '59185cc3cb65b1bcdfa53fbf69b6d5bb220a6a269384690ac277915f5fd9991c',
    'scripts/serena_safety.py': 'e3fd93ecb27a6c8f47a9d19a56b1610c2ec3a59b15d73ed766929941d456b9ea',
    'scripts/test_serena_safety.py': '13ac624a827ec7bdebf6ab9a75861b0cae22f5e7de596a4b723b8edd1570374c',
    'references/configuration-precedence.md': 'a91d7d60a15c62288fc68b3f4a0229b588e981569e9d539f0546a108601e027d',
}


class MigrationBoundary(unittest.TestCase):
    def test_original_instructions_resources_and_scripts_preserved(self):
        for name, expected in {**SOURCE_HASHES, **REVISED_HASHES}.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((SKILL/name).read_bytes()).hexdigest(), expected)

    def test_license_and_explicit_owner_grant_travel_with_skill(self):
        self.assertEqual((SKILL/'LICENSE').read_bytes(), (ROOT/'LICENSE').read_bytes())
        provenance = (SKILL/'PROVENANCE.md').read_text()
        self.assertIn('0c7838d8072dfd70c702cf2d04734a7241550c3e', provenance)
        self.assertIn('explicitly confirmed', provenance)
        self.assertIn('Current package license: MIT', provenance)

    def test_package_has_no_external_private_dependency(self):
        manifest = yaml.safe_load((ROOT/'apm.yml').read_text())
        lock = yaml.safe_load((ROOT/'apm.lock.yaml').read_text())
        self.assertEqual(manifest['dependencies'], {'apm': []})
        self.assertEqual(lock['dependencies'], [])
        self.assertTrue((SKILL/'SKILL.md').is_file())
        self.assertFalse(LEGACY_SKILL.exists())
        self.assertFalse((SKILL/'agents/openai.yaml').exists())
        self.assertFalse((SKILL/'references/provider-setup.md').read_text().startswith('---'))


class PythonRuntimeContract(unittest.TestCase):
    """Static instruction regressions plus the documented probe; no installer or agent proof."""

    @staticmethod
    def runtime_section():
        return (SKILL/'references/provider-setup.md').read_text().split('## Python Runtime', 1)[1].split('\n## ', 1)[0]

    def test_configurator_owns_bounded_probe_first_runtime(self):
        runtime = self.runtime_section()
        for clause in (
            '[REQUIREMENTS.md](../REQUIREMENTS.md)',
            '[scripts/requirements.txt](../scripts/requirements.txt)',
            'führt zum nächsten Kandidaten',
            'Diese vier Quellen sind die gesamte begrenzte Suche',
            'Ein erfolgreicher Import allein',
            'absolute `sys.executable`',
            'Audit-, Apply- und Re-Audit-Aufruf',
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, runtime)

    def test_setup_is_isolated_and_follows_concrete_approval(self):
        runtime = self.runtime_section()
        for clause in (
            'ohne erneute Routinefrage',
            'Eine Serena-Provideraktion allein ist keine',
            'frage einmal gemeinsam mit der Aufrufauswahl',
            '"<base-python>" -m venv "<absolute-env>"',
            '"<env-python>" -m pip install -r "<absolute-skill>/scripts/requirements.txt"',
            'kein System-, Global- oder `--user`-pip',
            'bleibt das Audit ungestartet',
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, runtime)

    def test_workflow_uses_resolved_interpreter(self):
        text = (SKILL/'references/provider-setup.md').read_text()
        self.assertIn('`"<python>" scripts/serena_safety.py --cwd', text)
        self.assertNotIn('`python scripts/serena_safety.py', text)

    def test_init_delegates_without_second_procedure(self):
        init = (ROOT/'.apm/skills/core-init-project/SKILL.md').read_text()
        section = init.split('#### Provider-Laufzeit vorbereiten', 1)[1].split('#### Provideraudit durchführen', 1)[0]
        self.assertIn('(references/provider-setup.md#python-runtime)', section)
        self.assertIn('verifizierten absoluten Interpreterpfad', section)
        for duplicate in ('pip install', 'venv', 'ruamel', 'requirements.txt'):
            with self.subTest(duplicate=duplicate):
                self.assertNotIn(duplicate, section)

    def test_documented_probe_runs_and_reports_interpreter(self):
        line = next(item.strip() for item in self.runtime_section().splitlines() if '"<candidate>"' in item)
        command = [sys.executable, *shlex.split(line)[1:]]
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=PROBE_TIMEOUT_SECONDS)
        self.assertTrue(Path(result.stdout.splitlines()[0]).is_absolute())
        self.assertRegex(result.stdout.splitlines()[-1], r'^0\.\d+')

    def test_mise_runner_probe_disables_install_and_uses_same_interpreter(self):
        runtime = self.runtime_section()
        for clause in (
            'MISE_AUTO_INSTALL=0 MISE_EXEC_AUTO_INSTALL=0 mise exec --',
            'Child-Umgebung',
            'bestehende mise-Einstellungen oder Umgebungsvariablen werden nicht verändert',
            'prozesslokalen `PATH=<existing-env>/bin:$PATH`',
            '`PYTHONPATH` bleibt unverändert',
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, runtime)
        line = next(item.strip() for item in runtime.splitlines() if '"<candidate>"' in item)
        probe = shlex.split(line)[3]
        env = os.environ.copy()
        env.update(MISE_AUTO_INSTALL='0', MISE_EXEC_AUTO_INSTALL='0')
        executable = Path(sys.executable).absolute()
        env['VIRTUAL_ENV'] = str(executable.parent.parent)
        env['PATH'] = str(executable.parent) + os.pathsep + env.get('PATH', '')
        result = subprocess.run(
            ['mise', 'exec', '--', str(executable), '-B', '-c', probe],
            capture_output=True, text=True, check=True, timeout=PROBE_TIMEOUT_SECONDS, env=env,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], str(executable))
        self.assertRegex(lines[-1], r'^0\.\d+')


def load_tests(loader, suite, pattern):
    """Run original skill-local tests in normal CI discovery, not an optional skip."""
    scripts = SKILL/'scripts'
    old_path = sys.path[:]
    previous = sys.modules.get('serena_safety')
    try:
        sys.path.insert(0, str(scripts))
        spec = importlib.util.spec_from_file_location('serena_safety', scripts/'serena_safety.py')
        safety = importlib.util.module_from_spec(spec)
        sys.modules['serena_safety'] = safety
        spec.loader.exec_module(safety)
        spec = importlib.util.spec_from_file_location('core_configurator_original_tests', scripts/'test_serena_safety.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = loader.loadTestsFromModule(module)
        if original.countTestCases() == 0:
            raise AssertionError('migrated safety test suite is empty')
        suite.addTests(original)
    finally:
        sys.path[:] = old_path
        if previous is None:
            sys.modules.pop('serena_safety', None)
        else:
            sys.modules['serena_safety'] = previous
    return suite


if __name__ == '__main__':
    unittest.main()
