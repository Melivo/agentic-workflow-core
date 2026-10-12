"""Offline regression tests for scripts/check_design_principles.py (G03/M01, T03).

Controlled fixtures in temporary directories prove what the static guard detects.
They never prove how an agent or language model follows the rules.
"""
import sys
sys.dont_write_bytecode = True
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_design_principles.py'
spec = importlib.util.spec_from_file_location('check_design_principles_tested', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

SKILLS = ROOT / guard.SKILLS
TMP_BASE = Path('/tmp/opencode') if Path('/tmp/opencode').is_dir() else None
GOOD_DOCS = {
    'README.md': '# Fixture\n\nDie [S00-Basis](.apm/skills/core-architecture/references/design-baseline.md) beschreibt den verbindlichen Sollzustand.\n',
    'DESIGN.md': '# Fixture\n\nDer [Hintergrund](.apm/skills/core-architecture/references/principles-background.md) erklärt die Prinzipien. '
                 'Statische Prüfungen belegen kein Agentenverhalten. M02 ist nicht Teil dieser Etappe.\n',
}


def digests(paths):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def real_sources():
    relative = {guard.BASELINE, guard.BACKGROUND, guard.ASSET, 'core-architecture/SKILL.md', 'core-shared/SKILL.md', *guard.S00_LINKED}
    relative |= {r for r, _, _ in guard.SKILL_RULES + guard.SKILL_FORBIDDEN}
    return [SKILLS / r for r in sorted(relative)]


class Fixture:
    """A temporary root with a copied skill tree in a chosen layout and controlled docs."""

    def __init__(self, layout='.apm/skills', docs=GOOD_DOCS):
        self.tmp = tempfile.TemporaryDirectory(prefix='design-guard-', dir=TMP_BASE)
        self.root = Path(self.tmp.name)
        self.skills = self.root / layout
        shutil.copytree(SKILLS, self.skills, ignore=shutil.ignore_patterns('__pycache__'))
        for name, text in docs.items():
            (self.root / name).write_text(text.replace('.apm/skills', layout), encoding='utf-8')

    def mutate(self, relative, old, new=''):
        path = self.skills / relative
        text = path.read_text(encoding='utf-8')
        if old not in text:
            raise AssertionError('mutation anchor missing in ' + relative + ': ' + old)
        path.write_text(text.replace(old, new, 1), encoding='utf-8')

    def run(self, group):
        return guard.run(group, self.root, self.skills)

    def main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return guard.main(argv, self.root, self.skills)
            except SystemExit as exc:
                return exc.code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()


class RealSources(unittest.TestCase):
    def test_integration_passes_on_real_sources_and_leaves_them_unchanged(self):
        sources = real_sources()
        before = digests(sources)
        for group in ('background', 'rules', 'integration'):
            with self.subTest(group=group):
                self.assertEqual(guard.run(group), ([], []))
        self.assertEqual(digests(sources), before)

    def test_cli_integration_exit_zero_without_writes(self):
        sources = real_sources()
        before = digests(sources)
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--group', 'integration'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, guard.EXIT_PASS, result.stderr)
        self.assertIn('kein Nachweis von Agentenverhalten', result.stdout)
        self.assertEqual(digests(sources), before)

    def test_guard_source_has_no_network_install_or_write_surface(self):
        source = SCRIPT.read_text(encoding='utf-8')
        for forbidden in ('import socket', 'urllib', 'http.client', 'subprocess', 'write_text', 'write_bytes', "open(", 'shutil', 'pip ', 'os.remove', 'unlink'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class Groups(unittest.TestCase):
    def test_group_composition(self):
        c = guard.CHECKS
        self.assertEqual(c['integration'], (guard.check_background, guard.check_rules, guard.check_linkage))
        self.assertEqual(c['docs'], (guard.check_docs,))
        self.assertEqual(set(c['all']), set(c['background'] + c['rules'] + c['integration'] + c['docs']))
        self.assertNotIn(guard.check_docs, c['integration'])
        self.assertEqual(set(guard.GROUPS), set(c))

    def test_controlled_fixture_passes_every_group(self):
        with Fixture() as f:
            for group in guard.GROUPS:
                with self.subTest(group=group):
                    self.assertEqual(f.run(group), ([], []))
                    self.assertEqual(f.main(['--group', group]), guard.EXIT_PASS)

    def test_cli_usage_errors(self):
        with Fixture() as f:
            for argv in ([], ['--group'], ['--group', 'unknown'], ['--group', 'docs', '--fix']):
                with self.subTest(argv=argv):
                    self.assertEqual(f.main(argv), guard.EXIT_USAGE)

    def test_docs_group_reads_only_docs_and_integration_ignores_docs(self):
        with Fixture() as f:
            (f.root / 'README.md').unlink()
            self.assertEqual(f.run('integration'), ([], []))
            self.assertEqual(f.main(['--group', 'docs']), guard.EXIT_MISSING)
            self.assertEqual(f.main(['--group', 'all']), guard.EXIT_MISSING)
        with Fixture() as f:
            shutil.rmtree(f.skills / 'core-devops')
            self.assertEqual(f.run('docs'), ([], []))
            self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_MISSING)


class Background(unittest.TestCase):
    CASES = {
        'cs50_missing': ('(https://cs50.harvard.edu/x/notes/6/)', '(https://example.org/notes/6/)'),
        'cs50_changed': ('ap/2021/curriculum/x/references/mvc.pdf', 'ap/2021/mvc.pdf'),
        'image_link': ('](../assets/software-design-principles.png)', '](../assets/other.png)'),
        'image_dropped': ('![Übersicht', 'Übersicht'),
        's00_link': ('[S00 – SWE-Basis und Auswahl](design-baseline.md)', 'S00'),
        'principle_heading': ('### 4. Abstraktion und Information Hiding\n', '### 4. Verbergen\n'),
        'image_required': ('keine Voraussetzung', 'die Grundlage'),
        'lazy_load': ('nur bei Auslegungs- oder Erklärungsbedarf', 'bei jeder Aufgabe'),
        'proof_limit': ('Sie zeigen nicht, wie sich ein Agent', 'Sie zeigen, wie sich ein Agent'),
        'appendix_text': ('Zyklische Abhängigkeiten sind zu vermeiden.', 'Zyklische Abhängigkeiten sind erlaubt.'),
        'appendix_removed': ('# Anweisungen zum Schreiben von Code', '# Anweisungen'),
        'broken_relative': ('[core-refactor](../../core-refactor/SKILL.md)', '[core-refactor](../../core-refactor/FEHLT.md)'),
    }

    def test_violations_detected(self):
        for name, (old, new) in self.CASES.items():
            with self.subTest(mutation=name), Fixture() as f:
                f.mutate(guard.BACKGROUND, old, new)
                findings, missing = f.run('background')
                self.assertTrue(findings, name)
                self.assertEqual(missing, [])
                self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_FINDINGS)

    def test_extra_cs50_link_and_copied_pdf_detected(self):
        with Fixture() as f:
            f.mutate(guard.BACKGROUND, '## Quellen\n', '## Quellen\n\n[x](https://cs50.harvard.edu/x/notes/7/)\n')
            self.assertIn('unerwarteter CS50-Link', ' '.join(f.run('background')[0]))
        with Fixture() as f:
            (f.skills / 'core-architecture/assets/principles.pdf').write_bytes(b'%PDF-1.4')
            self.assertIn('PDF', ' '.join(f.run('background')[0]))

    def test_asset_missing_is_prerequisite_not_clean(self):
        with Fixture() as f:
            (f.skills / guard.ASSET).unlink()
            findings, missing = f.run('background')
            self.assertTrue(missing)
            self.assertEqual(f.main(['--group', 'background']), guard.EXIT_MISSING)

    def test_background_missing_is_prerequisite(self):
        with Fixture() as f:
            (f.skills / guard.BACKGROUND).unlink()
            self.assertTrue(f.run('background')[1])
            self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_MISSING)

    def test_corrupt_or_changed_png_is_finding(self):
        original = (SKILLS / guard.ASSET).read_bytes()
        variants = {
            'flipped_byte': original[:-20] + bytes([original[-20] ^ 1]) + original[-19:],
            'truncated': original[:16],
            'not_png': b'GIF89a' + original[6:],
            'other_size': original[:16] + (1000).to_bytes(4, 'big') + original[20:],
        }
        for name, data in variants.items():
            with self.subTest(variant=name), Fixture() as f:
                (f.skills / guard.ASSET).write_bytes(data)
                findings, missing = f.run('background')
                self.assertTrue(findings)
                self.assertEqual(missing, [])
                self.assertEqual(f.main(['--group', 'background']), guard.EXIT_FINDINGS)

    def test_text_explains_all_principles_without_image(self):
        text = (SKILLS / guard.BACKGROUND).read_text(encoding='utf-8')
        plain = guard.IMAGE.sub('', text)
        self.assertNotIn('software-design-principles.png', plain)
        for heading in guard.PRINCIPLE_HEADINGS:
            self.assertRegex(plain, r'(?m)^#+ [^\n]*' + heading)


class Rules(unittest.TestCase):
    CASES = {
        'sollzustand': ('**Verbindlicher Sollzustand:**', '**Empfehlungen:**'),
        'principle': ('- **Hohe Kohäsion:**', '- **Zusammenhalt:**'),
        'replaceability': ('ohne Anpassung unabhängiger Verbraucher eingesetzt', 'nach Anpassung der Verbraucher eingesetzt'),
        'contract_errors': ('Ergebnisse, erwartete Fehler und Nebenwirkungen', 'Ergebnisse'),
        'artificial_abstraction': ('Keine künstliche Austauschbarkeit jeder Klasse', 'Austauschbarkeit jeder Klasse ist Pflicht'),
        'constants': ('benannte Konstante oder als eng begrenzte Konfiguration', 'Literal'),
        'global_store': ('nicht in einer globalen Sammelstelle', 'in einer globalen Sammelstelle'),
        'exchange_question': ('**Praktische Austauschfrage:**', '**Frage:**'),
        'exception_recorded': ('halte eine begründete Ausnahme fest', 'ignoriere es'),
        'no_interface_duty': ('Keine Pflicht zu Interfaces', 'Pflicht zu Interfaces'),
        'refactoring_scope': ('nur innerhalb eines dafür bestätigten Tasks', 'jederzeit'),
        'example_authorizes': ('erteilt keine Freigabe', 'erteilt die Freigabe'),
        'review_mutates': ('Review bleibt read-only', 'Review darf korrigieren'),
        'auto_mutation': ('nicht automatisch eine Mutation', 'automatisch eine Mutation'),
        'information_questions': ('Nicht anwendbar auf beliebige Informationsfragen', 'Auch für Informationsfragen'),
        'background_link': ('Lade die [Hintergrundreferenz](principles-background.md)', 'Lade die Hintergrundreferenz'),
        'method_removed': ('[M06 Fehleroberfläche und Wiederherstellung](interface-and-errors.md#m06--fehleroberflache-und-wiederherstellung)', 'M06'),
        'anchor_broken': ('alternatives.md#m10--alternativenvergleich', 'alternatives.md#m10--fehlt'),
    }

    def test_violations_detected(self):
        for name, (old, new) in self.CASES.items():
            with self.subTest(mutation=name), Fixture() as f:
                f.mutate(guard.BASELINE, old, new)
                self.assertTrue(f.run('rules')[0], name)
                self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_FINDINGS)

    def test_reworded_but_equivalent_relation_passes(self):
        with Fixture() as f:
            f.mutate(guard.BASELINE, 'Module sind so zu gestalten, dass', 'Gestalte Module so, dass')
            self.assertEqual(f.run('rules'), ([], []))

    def test_missing_s00_section(self):
        with Fixture() as f:
            f.mutate(guard.BASELINE, '## S00 — ', '## Basis — ')
            self.assertEqual(f.run('rules')[0], ['S00-Abschnitt fehlt'])


class Linkage(unittest.TestCase):
    CASES = {
        'database_public_contract': ('core-database/SKILL.md', 'Bewusst öffentliche Schemaverträge sind keine Leckage', 'Schemaverträge sind Leckage'),
        'init_mcps_install': ('core-init-mcps/SKILL.md', 'installiert oder konfiguriert nichts', 'installiert fehlende Provider'),
        'init_mcps_fullscan': ('core-init-mcps/SKILL.md', 'Bestandsprüfung ist keine S00-Pflicht, löst keinen Vollscan aus', 'Bestandsprüfung scannt vollständig'),
        'init_mcps_plan_duty': ('core-init-mcps/SKILL.md', 'Ein zusätzlicher Core-Plan wird dadurch nicht pauschal vorgeschrieben', 'Jede Installation verlangt zusätzlich einen Core-Plan'),
        'init_mcps_install_step': ('core-init-mcps/SKILL.md', '3. Wenn Einrichtung gewünscht ist', '3. Installiere fehlende Provider. Wenn Einrichtung gewünscht ist'),
        'init_project_readiness': ('core-init-project/SKILL.md', 'Readiness-Preflight löst keinen Vollscan und keine Installation aus', 'Readiness-Preflight installiert fehlende Werkzeuge'),
        'tf_live_actions': ('core-tf-infra/SKILL.md', 'Keine Ausführung von plan/apply/destroy aus diesen Methoden ableiten', 'Führe plan/apply aus'),
        'tf_authorization': ('core-tf-infra/SKILL.md', 'benötigen jeweils eine passende ausdrückliche Autorisierung', 'sind mit dem Task freigegeben'),
        'devops_install': ('core-devops/SKILL.md', 'Einrichten oder Prüfen autorisiert weder Toolinstallation', 'Einrichten autorisiert Toolinstallation und weder'),
        'devops_residue': ('core-devops/references/development-automation.md', 'ist nur zulässig, wenn diese Restprüfung belegt ist', 'ist immer zulässig'),
        'devops_check_only': ('core-devops/references/development-automation.md', 'Keine Installation, Konfigurationsänderung', 'Installation erlaubt, Konfigurationsänderung'),
        'plan_information': ('core-plan/SKILL.md', 'Reine Informations- oder Bereitschaftsprüfungen lösen diese Pflicht nicht aus.', ''),
        'plan_removal_path': ('core-plan/SKILL.md', 'Abhängigkeiten sowie den Austausch- oder Entfernungspfad', 'Abhängigkeiten'),
        'execute_residue': ('core-execute/SKILL.md', '„rückstandsfrei“ ohne diese Prüfung ist nicht zulässig', '„rückstandsfrei“ ist zulässig'),
        'execute_structural': ('core-execute/SKILL.md', 'Bei schreibenden strukturrelevanten Tasks ergänze', 'Bei allen Tasks ergänze'),
        'debug_minimal_fix': ('core-debug/SKILL.md', 'der minimale Fix hat Vorrang', 'die Strukturänderung hat Vorrang'),
        'coding_fullscan': ('core-backend/SKILL.md', 'nicht als Vollscan', 'als Vollscan'),
        'coding_refactoring': ('core-mobile/SKILL.md', 'erlauben keine ungeplanten Refactorings', 'erlauben Refactorings'),
        'review_s00_link': ('core-review/SKILL.md', '[S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md)', 'S00'),
        'escaping_link': ('core-frontend/SKILL.md', '](../core-architecture/references/design-baseline.md)', '](../../../.apm/apm_modules/x/core-architecture/references/design-baseline.md)'),
        'architecture_background': ('core-architecture/SKILL.md', '[Hintergrundreferenz](references/principles-background.md)', 'Hintergrundreferenz'),
        'shared_background': ('core-shared/SKILL.md', '[Softwaredesign-Prinzipien: Hintergrund](../core-architecture/references/principles-background.md)', 'Softwaredesign-Prinzipien'),
        'shared_duplicates_rule': ('core-shared/SKILL.md', 'nur bei Auslegungsbedarf laden.', 'nur bei Auslegungsbedarf laden. Verbindlicher Sollzustand: fünf Prinzipien.'),
    }

    def test_scope_and_authorization_expansion_detected(self):
        for name, (relative, old, new) in self.CASES.items():
            with self.subTest(mutation=name), Fixture() as f:
                f.mutate(relative, old, new)
                findings, missing = f.run('integration')
                self.assertTrue(findings, name)
                self.assertEqual(missing, [])

    def test_portable_layouts_resolve_relative_links(self):
        for layout in ('producer/.apm/skills', 'consumer/.agents/skills', 'home/.agents/skills'):
            with self.subTest(layout=layout), Fixture(layout) as f:
                self.assertEqual(f.run('all'), ([], []))
                target = (f.skills / 'core-plan/SKILL.md').parent / '../core-architecture/references/design-baseline.md'
                self.assertTrue(target.resolve().is_relative_to(f.skills.resolve()))

    def test_missing_s00_in_layout_is_prerequisite(self):
        with Fixture('home/.agents/skills') as f:
            (f.skills / guard.BASELINE).unlink()
            findings, missing = f.run('integration')
            self.assertTrue(missing)
            self.assertTrue(findings)  # dangling relative S00 links are reported too
            self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_MISSING)


class Docs(unittest.TestCase):
    CASES = {
        'background_link': ('README.md', None, 'DESIGN.md', '[Hintergrund](.apm/skills/core-architecture/references/principles-background.md)', 'Hintergrund'),
        'broken_link': ('README.md', None, 'README.md', 'design-baseline.md)', 'design-baseline-fehlt.md)'),
        'sollzustand': ('README.md', None, 'README.md', 'verbindlichen Sollzustand', 'Ziel'),
        'm02': ('DESIGN.md', None, 'DESIGN.md', 'M02 ist nicht Teil dieser Etappe.', 'M02 folgt jetzt automatisch mit.'),
        'proof_limit': ('DESIGN.md', None, 'DESIGN.md', 'Statische Prüfungen belegen kein Agentenverhalten.', 'Statische Prüfungen belegen das Agentenverhalten.'),
    }

    def test_violations_detected(self):
        for name, (_, _, doc, old, new) in self.CASES.items():
            docs = dict(GOOD_DOCS)
            self.assertIn(old, docs[doc])
            docs[doc] = docs[doc].replace(old, new, 1)
            with self.subTest(mutation=name), Fixture(docs=docs) as f:
                self.assertTrue(f.run('docs')[0], name)
                self.assertEqual(f.main(['--group', 'docs']), guard.EXIT_FINDINGS)
                self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_PASS)


class ReadOnlyGuard(unittest.TestCase):
    def test_changed_source_reported(self):
        with Fixture() as f:
            sources = guard.Sources(f.root, f.skills)
            path = f.skills / guard.BASELINE
            sources.text(path)
            self.assertEqual(sources.changed(), [])
            path.write_text(path.read_text(encoding='utf-8') + '\n', encoding='utf-8')
            self.assertEqual(sources.changed(), [str(path)])

    def test_mutating_check_is_reported_by_run(self):
        def mutating(sources):
            path = sources.skill(guard.BASELINE)
            sources.text(path)
            path.write_text('verändert', encoding='utf-8')
            return []
        with Fixture() as f, unittest.mock.patch.dict(guard.CHECKS, {'rules': (mutating,)}):
            findings, _ = f.run('rules')
            self.assertTrue(any('Read-only-Guard' in x for x in findings))

    def test_non_utf8_source_is_prerequisite(self):
        with Fixture() as f:
            (f.skills / guard.BASELINE).write_bytes(b'\xff\xfe')
            self.assertTrue(f.run('rules')[1])


class Replaceability(unittest.TestCase):
    """Controlled example: same inputs, results, errors and side effects; different internals."""

    @staticmethod
    def table_lookup(effects, kind):
        limits = {'small': 10, 'large': 100}
        if kind not in limits:
            raise ValueError('unknown kind: ' + kind)
        effects.append(('read', kind))
        return limits[kind]

    @staticmethod
    def branching(effects, kind):
        if kind == 'large':
            effects.append(('read', kind))
            return 100
        if kind == 'small':
            effects.append(('read', kind))
            return 10
        raise ValueError('unknown kind: ' + kind)

    @staticmethod
    def reordered_same_branches(effects, kind):
        # Same branch count as table_lookup; only the internal order differs.
        if kind not in ('small', 'large'):
            raise ValueError('unknown kind: ' + kind)
        effects.append(('read', kind))
        return 10 if kind == 'small' else 100

    CASES = [('small',), ('large',), ('other',)]

    def test_contract_conformant_alternatives_accepted(self):
        for candidate in (self.branching, self.reordered_same_branches):
            with self.subTest(candidate=candidate.__name__):
                self.assertEqual(guard.contract_violations(self.table_lookup, candidate, self.CASES), [])

    def test_behaviour_changing_alternatives_rejected(self):
        def other_result(effects, kind):
            effects.append(('read', kind))
            if kind == 'other':
                raise ValueError('unknown kind: ' + kind)
            return 11 if kind == 'small' else 100
        def other_error(effects, kind):
            if kind == 'other':
                raise KeyError(kind)
            effects.append(('read', kind))
            return 10 if kind == 'small' else 100
        def extra_side_effect(effects, kind):
            effects.append(('log', kind))
            return self.table_lookup(effects, kind)
        for candidate in (other_result, other_error, extra_side_effect):
            with self.subTest(candidate=candidate.__name__):
                self.assertTrue(guard.contract_violations(self.table_lookup, candidate, self.CASES))



class PortableReferences(unittest.TestCase):
    """RV01: producer-bound absolute links must fail before resolution, even if the target exists."""

    S00 = '(design-baseline.md)'
    IMAGE_REF = '(../assets/software-design-principles.png)'

    def variants(self, f, relative):
        target = f.skills / relative
        return {
            'posix_absolute': str(target),
            'file_uri': target.as_uri(),
            'windows_drive': 'C:/producer/.apm/skills/' + relative,
            'windows_unc': '\\\\host\\skills\\' + relative.replace('/', '\\'),
            'home_tilde': '~/.agents/skills/' + relative,
        }

    def check(self, old, relative):
        for name in ('posix_absolute', 'file_uri', 'windows_drive', 'windows_unc', 'home_tilde'):
            with self.subTest(link=old, variant=name), Fixture() as f:
                f.mutate(guard.BACKGROUND, old, '(' + self.variants(f, relative)[name] + ')')
                findings, missing = f.run('integration')
                self.assertTrue(any('nicht portable' in x for x in findings), findings)
                self.assertEqual(missing, [])
                self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_FINDINGS)

    def test_absolute_s00_link_rejected(self):
        self.check(self.S00, guard.BASELINE)

    def test_absolute_image_link_rejected(self):
        self.check(self.IMAGE_REF, guard.ASSET)

    def test_review_probe_absolute_links_fail_in_producer_layout(self):
        with Fixture() as f:
            f.mutate(guard.BACKGROUND, self.IMAGE_REF, '(' + str(f.skills / guard.ASSET) + ')')
            f.mutate(guard.BACKGROUND, self.S00, '(' + str(f.skills / guard.BASELINE) + ')')
            findings, missing = f.run('integration')
            self.assertIn('Hintergrund bindet das Bild nicht relativ ein', findings)
            self.assertIn('Hintergrund verlinkt S00 nicht', findings)
            self.assertEqual(missing, [])
            self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_FINDINGS)

    def test_helpers_keep_relative_anchor_and_official_links(self):
        for ref in ('design-baseline.md', '../assets/software-design-principles.png', '../../core-refactor/SKILL.md', 'x.md#anker'):
            self.assertTrue(guard.is_portable(ref), ref)
        for ref in CS50_SAMPLE:
            self.assertTrue(guard.is_external(ref), ref)
        for ref in ('/abs/x.md', 'file:///x.md', 'C:/x.md', 'c:\\x.md', '\\\\host\\x.md', '~/x.md'):
            self.assertFalse(guard.is_portable(ref), ref)
            self.assertFalse(guard.is_external(ref), ref)

    def test_relative_links_pass_in_all_layouts(self):
        for layout in ('producer/.apm/skills', 'consumer/.agents/skills', 'home/.agents/skills'):
            with self.subTest(layout=layout), Fixture(layout) as f:
                self.assertEqual(f.run('integration'), ([], []))
                self.assertEqual(f.main(['--group', 'integration']), guard.EXIT_PASS)


CS50_SAMPLE = guard.CS50_LINKS + ('mailto:team@example.org',)


if __name__ == '__main__':
    unittest.main()
