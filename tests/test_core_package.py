"""Package verification: archive and fresh installation are checked against the canonical sources.

Fixtures mirror the APM 0.31 bundle layout built from the real .apm sources; a fake apm binary proves
that exit code 0 alone never yields a verified package. The real producer build runs in acceptance.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('build_core_package_tested', ROOT / 'scripts/build_core_package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
import release_guard  # noqa: E402

VERSION = json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))['.']
TOP = 'agentic-workflow-core-%s/' % VERSION
# Built at runtime so no secret-shaped literal is stored in the repository.
FAKE_TOKEN = 'gh' + 'p_' + 'A1b2C3d4' * 4 + 'E5f6'


def canonical_sources():
    files = {p: (ROOT / p).read_bytes() for p in ('apm.yml', 'apm.lock.yaml', 'LICENSE')}
    files.update({p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted((ROOT / '.apm').rglob('*')) if p.is_file()})
    return files


SOURCES = canonical_sources()


def archive_entries(sources=SOURCES, version=VERSION):
    """Entries as apm pack --target agent-skills lays them out, with a matching embedded inventory."""
    files = {'plugin.json': json.dumps({'name': 'agentic-workflow-core', 'version': version}).encode()}
    files.update({'agents/' + k[len('.apm/agents/'):]: v for k, v in sources.items() if k.startswith('.apm/agents/')})
    files.update({'skills/' + k[len('.apm/skills/'):]: v for k, v in sources.items() if k.startswith('.apm/skills/')})
    return with_inventory(files, version)


def with_inventory(files, version=VERSION):
    files = {k: v for k, v in files.items() if k != 'apm.lock.yaml'}
    lock = {'pack': {'format': 'claude-plugin', 'bundle_files': {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}}
    files['apm.lock.yaml'] = yaml.safe_dump(lock).encode()
    return {'agentic-workflow-core-%s/' % version + k: v for k, v in files.items()}


def installation(sources=SOURCES):
    files = {'.agents/skills/' + k[len('.apm/skills/'):]: v for k, v in sources.items() if k.startswith('.apm/skills/')}
    files['apm.lock.yaml'] = b'lockfile_version: "1"\n'
    return files


def first(mapping, prefix):
    return next(k for k in sorted(mapping) if k.startswith(prefix))


class ArchiveInspection(unittest.TestCase):
    def inspect(self, entries, name=None):
        return package.inspect_archive(name or TOP[:-1] + '.zip', entries, SOURCES, VERSION)

    def assertFlags(self, entries, fragment, name=None):
        _, violations = self.inspect(entries, name)
        self.assertTrue(any(fragment in v for v in violations), (fragment, violations[:5]))

    def test_complete_archive_passes_with_all_core_bundles(self):
        summary, violations = self.inspect(archive_entries())
        self.assertEqual(violations, [])
        self.assertEqual(summary['core_bundles'], release_guard.CORE_BUNDLES)
        self.assertEqual(summary['core_files'], len([k for k in SOURCES if k.startswith('.apm/skills/core-')]))

    def test_source_inventory_has_exactly_22_core_bundles(self):
        self.assertEqual(len(package.bundles(package.core_files(SOURCES, '.apm/skills/'))), 22)

    def test_missing_bundle_is_incomplete(self):
        entries = {k: v for k, v in archive_entries().items() if '/skills/core-devops/' not in k}
        self.assertFlags(entries, 'Core-Bundles weichen ab')

    def test_changed_or_missing_core_file_is_detected(self):
        entries = archive_entries()
        key = first(entries, TOP + 'skills/core-plan/')
        entries[key] += b'\nmanipuliert\n'
        self.assertFlags(with_inventory({k[len(TOP):]: v for k, v in entries.items()}), 'verändert')
        entries = archive_entries()
        del entries[first(entries, TOP + 'skills/core-review/')]
        self.assertFlags(entries, 'fehlt')

    def test_run_artifacts_projections_and_secrets_are_blocked(self):
        for extra, fragment in ((('.agentic-workflow/runs/r/state.yaml', b'x'), 'verbotener Pfad'),
                                (('skills/core-plan/.env', b'A=1'), 'verbotener Pfad'),
                                (('skills/core-plan/references/notes.md', ('token ' + FAKE_TOKEN).encode()), 'mögliches Secret'),
                                (('apm_modules/x/SKILL.md', b'x'), 'verbotener Pfad'),
                                (('README.md', b'x'), 'unerwarteter Archivinhalt')):
            with self.subTest(extra=extra[0]):
                files = {k[len(TOP):]: v for k, v in archive_entries().items()}
                files[extra[0]] = extra[1]
                self.assertFlags(with_inventory(files), fragment)

    def test_version_binding(self):
        self.assertFlags(archive_entries(version='0.9.9'), 'Einträge außerhalb')
        files = {k[len(TOP):]: v for k, v in archive_entries().items()}
        files['plugin.json'] = json.dumps({'name': 'agentic-workflow-core', 'version': '0.9.9'}).encode()
        self.assertFlags(with_inventory(files), 'plugin.json nennt')
        self.assertFlags(archive_entries(), 'Archivname', name='agentic-workflow-core-0.9.9.zip')

    def test_embedded_inventory_must_match(self):
        entries = archive_entries()
        entries[TOP + 'plugin.json'] = json.dumps({'name': 'agentic-workflow-core', 'version': VERSION, 'x': 1}).encode()
        self.assertFlags(entries, 'eingebettetes Inventar')

    def test_license_notices_and_bundled_configurator_required(self):
        files = {k[len(TOP):]: v for k, v in archive_entries().items()}
        files['skills/core-shared/LICENSE'] = b'other'
        self.assertFlags(with_inventory(files), 'core-shared/LICENSE')
        files = {k[len(TOP):]: v for k, v in archive_entries().items() if 'gortex-serena-configurator' not in k}
        self.assertFlags(with_inventory(files), 'Begleitskill-Datei fehlt')

    def test_migrated_scripts_and_license_are_source_bound(self):
        for rel in ('scripts/serena_safety.py', 'scripts/test_serena_safety.py', 'LICENSE'):
            files = {k[len(TOP):]: v for k, v in archive_entries().items()}
            key = 'skills/gortex-serena-configurator/' + rel
            files[key] += b'changed'
            self.assertFlags(with_inventory(files), 'Begleitskill-Datei verändert')


class InstallationInspection(unittest.TestCase):
    def assertFlags(self, files, fragment):
        _, violations = package.inspect_installation(files, SOURCES)
        self.assertTrue(any(fragment in v for v in violations), (fragment, violations[:5]))

    def test_fresh_installation_passes_with_resolvable_links(self):
        summary, violations = package.inspect_installation(installation(), SOURCES)
        self.assertEqual(violations, [])
        self.assertEqual(summary['core_bundles'], 22)
        self.assertGreaterEqual(summary['internal_links'], 217)

    def test_broken_or_cache_bound_link_is_detected(self):
        for target in ('references/missing.md', '../../../apm_modules/x/SKILL.md'):
            with self.subTest(target=target):
                files = installation()
                key = '.agents/skills/core-backend/SKILL.md'
                files[key] = files[key] + ('\n[kaputt](%s)\n' % target).encode()
                self.assertFlags(files, 'nicht auflösbar')

    def test_incomplete_or_foreign_installation_is_detected(self):
        files = {k: v for k, v in installation().items() if '/core-handoff/' not in k}
        self.assertFlags(files, 'Core-Bundles weichen ab')
        files = installation()
        files['.opencode/agents/x.md'] = b'x'
        self.assertFlags(files, 'unerwartete Installationsdatei')
        files = {k: v for k, v in installation().items() if not k.endswith('THIRD_PARTY_NOTICES.md')}
        self.assertFlags(files, 'THIRD_PARTY_NOTICES')


class ReportBinding(unittest.TestCase):
    def report(self, **change):
        report = {'schema': 'core-package-report/v1', 'verified': True, 'version': '0.3.0', 'source_commit': 'c' * 40,
                  'source_clean': True, 'core_bundles': 22, 'bundled_skills': [release_guard.BUNDLED_SKILL], 'archive': {'name': 'agentic-workflow-core-0.3.0.zip', 'sha256': 'd' * 64}}
        report.update(change)
        return release_guard.package_report(report, '0.3.0', 'c' * 40, 'd' * 64)

    def test_exact_report_passes(self):
        self.assertEqual(self.report(), [])

    def test_wrongly_bound_or_unverified_package_blocks(self):
        for change in ({'verified': False}, {'version': '0.2.9'}, {'source_commit': 'e' * 40}, {'source_clean': False},
                       {'core_bundles': 21}, {'bundled_skills': []}, {'archive': {'name': 'agentic-workflow-core-0.3.0.zip', 'sha256': 'f' * 64}},
                       {'archive': {'name': 'other.zip', 'sha256': 'd' * 64}}, {'schema': 'x'}):
            with self.subTest(change=change):
                self.assertNotEqual(self.report(**change), [])


class ProducerIsolation(unittest.TestCase):
    def test_exact_producer_commands(self):
        self.assertEqual(package.PRODUCER_COMMANDS, (
            ('install', '--only', 'apm', '--frozen'), ('audit', '--ci'),
            ('pack', '--offline', '--target', 'agent-skills', '--archive', '--output', 'dist')))

    def test_environment_is_scratch_only_and_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.dict(os.environ, {
                'GITHUB_TOKEN': 'x', 'APP_PRIVATE_KEY': 'x', 'GITHUB_APM_PAT': 'x', 'APM_HOME': '/real', 'XDG_CONFIG_HOME': '/real'}):
            scratch = Path(tmp)
            env = package.isolated_env(scratch)
            for key in ('GITHUB_TOKEN', 'APP_PRIVATE_KEY', 'GITHUB_APM_PAT'):
                self.assertNotIn(key, env)
            for key in ('HOME', 'APM_HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'TMPDIR'):
                self.assertTrue(Path(env[key]).is_relative_to(scratch), key)
            self.assertEqual(env['APM_NO_SCRIPTS'], '1')

    def test_package_sources_exclude_projections_and_run_artifacts(self):
        self.assertEqual(package.PACKAGE_SOURCES, ('apm.yml', 'apm.lock.yaml', 'LICENSE', '.apm'))
        self.assertEqual(package.leaks(SOURCES), [])


FAKE_APM = r'''#!{python}
import sys, zipfile, json, pathlib, shutil
args = sys.argv[1:]
mode = {mode!r}
cwd = pathlib.Path.cwd()
if args[0] == 'pack':
    out = cwd / 'dist'; out.mkdir()
    version = {version!r}
    with zipfile.ZipFile(out / ('agentic-workflow-core-%s.zip' % version), 'w') as z:
        z.writestr('agentic-workflow-core-%s/plugin.json' % version, json.dumps({{'name': 'agentic-workflow-core', 'version': version}}))
        for p in sorted((cwd / '.apm/skills').rglob('*')):
            if p.is_file() and (mode != 'incomplete' or 'core-devops' not in str(p)):
                z.write(p, 'agentic-workflow-core-%s/skills/' % version + p.relative_to(cwd / '.apm/skills').as_posix())
elif args[0] == 'install' and args[1].endswith('.zip'):
    with zipfile.ZipFile(args[1]) as z:
        for name in z.namelist():
            if '/skills/' in name:
                target = cwd / '.agents/skills' / name.split('/skills/', 1)[1]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
elif mode == 'audit-fails' and args[0] == 'audit':
    sys.exit(1)
'''


class ExitCodeIsNeverEnough(unittest.TestCase):
    """A fake apm exits 0 throughout yet produces an incomplete bundle: verify must not pass."""

    def run_fake(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir, out = Path(tmp) / 'bin', Path(tmp) / 'out'
            bin_dir.mkdir()
            fake = bin_dir / 'apm'
            fake.write_text(FAKE_APM.format(python=sys.executable, mode=mode, version=VERSION), encoding='utf-8')
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ.get('PATH', ''), TMPDIR=tmp)
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/build_core_package.py'), 'verify', '--output', str(out)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
            report = json.loads((out / 'package-report.json').read_text()) if (out / 'package-report.json').is_file() else None
            return result, report

    def test_incomplete_bundle_with_exit_zero_fails(self):
        result, report = self.run_fake('incomplete')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(report['verified'])
        self.assertTrue(any('core-devops' in v for v in report['violations']))
        self.assertTrue(all(c['exit_code'] == 0 for c in report['commands']))

    def test_failing_producer_step_stops_without_report(self):
        result, report = self.run_fake('audit-fails')
        self.assertEqual(result.returncode, 1)
        self.assertIn('apm audit --ci scheiterte', result.stderr)
        self.assertIsNone(report)


if __name__ == '__main__':
    unittest.main()
