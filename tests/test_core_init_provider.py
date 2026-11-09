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
# Files revised for Serena 1.7 and bounded discovery/readiness instructions. Re-pin
# deliberately when one of them changes; earlier revision hashes: git history of this test.
REVISED_HASHES = {
    'references/provider-setup.md': '0496c80a28183193f7c1c99767f57c884da8a455c817ef64e5a402a4cf09befc',
    'scripts/serena_safety.py': '72ab9b4326a52654e0b0357b69f6602928545f3aab1441d6508385ca7655a246',
    'scripts/test_serena_safety.py': '7136a6fe27cfa58d36395fa9c6467fdb6db8c655367aa394f3476e8ce10d7eaa',
    'references/configuration-precedence.md': '8fc5a919922c1678f79bca2add6f2a2cb4b41c419058833c8cbec6da2426a53c',
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


class RoutingAndReadinessContract(unittest.TestCase):
    """Static source/consumer contracts; mutations never write files or call models."""

    CONTRACTS = {
        'README.md': (
            ('separat bereitzustellende Inhaltsprüfmethode',
             'keine neue APM-Paketabhängigkeit', 'wird nicht automatisch installiert',
             'bestehende Skillverfügbarkeitscheck die konkrete Prüflücke',
             'Direkte Dateieingaben und automatische Skripte unterstützen nur Markdown',
             'übrigen zugänglichen Text nach der geladenen Rubrik manuell beurteilen',
             'Format-/Extraktionslücken ausdrücklich melden',
             'keine universelle Formatgarantie', 'das Audit bleibt report-only'),
            ('`skill-creator` und `context-debloater` sind Werkzeuge für die Paketentwicklung, keine zusätzlichen Verbraucherabhängigkeiten',),
        ),
        '.apm/skills/core-init-project/scripts/serena_safety.py': (
            ('Before project assignment only', 'native path/name discovery',
             'do not search contents or symbols', 'An unknown file within a known project is not an exception',
             'When the CWD is the user home (`Path.home()`)',
             'Readiness checks are read-only', 'only when explicitly authorized for that concrete project'),
            ('If the target location is unknown, use narrow native discovery',
             'Keep Serena initialized for each concrete project'),
        ),
        '.apm/skills/core-shared/references/tool-routing.md': (
            ('Vor Projektzuordnung ist ausschließlich eng begrenzte native Pfad-/Namenssuche',
             'keine Inhalts- oder Symbolsuche',
             'Eine unbekannte Datei innerhalb eines bekannten Projekts begründet keine Ausnahme',
             'Bei CWD `Path.home()`', 'Readiness ist rein lesend',
             'benötigen jeweils ausdrückliche Autorisierung für das konkrete Projekt'),
            ('die normale Wahl außerhalb eines indexierten Projekts',),
        ),
        '.apm/skills/core-init-project/assets/core-routing.md': (
            ('Vor Projektzuordnung ist ausschließlich eng begrenzte native Pfad-/Namenssuche',
             'keine Inhalts- oder Symbolsuche',
             'Eine unbekannte Datei innerhalb eines bekannten Projekts begründet keine Ausnahme',
             'Bei CWD `Path.home()`', 'Serena-Readiness bleibt rein lesend',
             'benötigen jeweils ausdrückliche Autorisierung für das konkrete Projekt',
             'Prüfe beim Erstellen oder inhaltlichen Bearbeiten von Dateien deren Textinhalt mit context-debloater',
             'README, AGENTS.md, Markdown, TXT, PDF, DOCX, HTML, JSON, YAML/YML, TOML, CONF, SUDOERS, LOCK, IN, TEMPLATE, TMPL, TPL, JS/MJS/CJS, PY, SH, PHP, SQL, CSS, SERVICE, TIMER, MOUNT, DOCKERFILE, SVG, DIFF, PATCH, OUT, RC, BACKUP, ORIGINAL, Dateien ohne Endung und weitere',
             'Die Pflicht gilt unabhängig von der Endung',
             'Direkte Dateieingaben und automatische Skripte des vorhandenen Skills sind auf Markdown begrenzt',
             'prüfe übrigen zugänglichen Text anhand seiner geladenen Rubrik manuell',
             'Melde nicht unterstützte oder unlesbare Textinhalte ausdrücklich als Prüflücke',
             'Das Audit bleibt report-only: keine automatische Kürzung oder Mutation',
             'keine Toolinstallation oder Convertereinrichtung daraus ableiten'),
            ('Prüfe nur Markdowndateien', 'Übergebe alle Dateiformate direkt an die Audit-Skripte',
             'Kürze Dateien automatisch nach dem Audit'),
        ),
        '.apm/skills/core-init-project/SKILL.md': (
            ('vor Projektzuordnung', 'native Pfad-/Namenssuche', 'keine Inhalts- oder Symbolsuche',
             'Eine unbekannte Datei im bekannten Projekt hebt die Providerfolge nicht auf',
             'Home-Ausnahme', 'Readiness bleibt rein lesend',
             'benötigen jeweils ausdrückliche Autorisierung für dieses konkrete Projekt',
             'Weder normales Init noch fehlende Bereitschaft erteilen diese Freigabe',
             '(references/configuration-precedence.md#markdownlint-konfiguration)',
             'Textprüfungspflicht', 'Dateien unabhängig von ihrer Endung',
             'Automatische Skripte und direkte Dateieingaben nur für unterstützte Markdownziele',
             'übrigen zugänglichen Text manuell nach der Rubrik prüfen',
             'Benenne Formatgrenzen und unlesbare Inhalte als Prüflücke'),
            ('Prüfe nur Markdowndateien', 'Übergebe alle Dateiformate direkt an die Audit-Skripte'),
        ),
        '.apm/skills/core-init-project/references/provider-setup.md': (
            ('Vor Projektzuordnung ist ausschließlich eng begrenzte native',
             'keine Inhalts-/Symbolsuche', 'eine unbekannte Datei ist keine',
             'Home-Ausnahme bleibt erhalten', 'Readiness bleibt rein lesend',
             'benötigen jeweils ausdrückliche Autorisierung für das konkrete',
             'normales Init oder ein fehlender Fallback erteilen diese nicht'),
            (),
        ),
        '.apm/skills/core-init-project/references/configuration-precedence.md': (
            ('Before project assignment only', 'never content or symbol search',
             'An unknown file within a known project is not an exception',
             'CWD is `Path.home()`', 'read-only readiness check',
             'each require explicit authorization for the concrete project',
             'normal init or a missing fallback grants none',
             'Projektkonfiguration hat Vorrang', '`mise exec`',
             '`<home>/.markdownlint-cli2.jsonc`', 'bestätigter Zuordnung zur Benutzeranweisung',
             'lesendem Nachweis der Datei', '`--config <absolute-config>`',
             'melde die Konfigurationslücke', 'Benutzeranweisungen werden nicht automatisch geändert'),
            ('Maintain Serena initialization, project languages, and MCP exposure',),
        ),
    }

    def assert_contract(self, text, required, forbidden):
        for clause in required:
            self.assertIn(clause, text)
        for clause in forbidden:
            self.assertNotIn(clause, text)

    def test_sources_cover_positive_and_negative_boundaries(self):
        for path, (required, forbidden) in self.CONTRACTS.items():
            with self.subTest(path=path):
                text = (ROOT/path).read_text()
                self.assert_contract(text, required, forbidden)
                self.assertNotIn('/home/visimeos/', text)
                self.assertNotIn('C:\\Users\\', text)

    def test_in_memory_mutations_reject_lost_guards_and_old_instructions(self):
        for path, (required, forbidden) in self.CONTRACTS.items():
            text = (ROOT/path).read_text()
            for clause in required:
                with self.subTest(path=path, removed=clause), self.assertRaises(AssertionError):
                    self.assert_contract(text.replace(clause, ''), required, forbidden)
            for clause in forbidden:
                with self.subTest(path=path, inserted=clause), self.assertRaises(AssertionError):
                    self.assert_contract(text + '\n' + clause, required, forbidden)

    def test_generated_root_routing_retains_template_boundaries(self):
        required, forbidden = self.CONTRACTS['.apm/skills/core-init-project/assets/core-routing.md']
        root = (ROOT/'AGENTS.md').read_text().split('<!-- CORE-INIT-PROJECT:START -->', 1)[1].split(
            '<!-- CORE-INIT-PROJECT:END -->', 1)[0]
        self.assert_contract(root, required, forbidden)
        template = (SKILL/'assets/core-routing.md').read_text()
        # The project fact/routing boundary is literal, not a semantic rewrite.
        self.assertIn(template.split('- **Einstieg:**', 1)[0], root)


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
