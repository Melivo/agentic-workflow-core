"""Static, offline regression tests for the core-devops bundle (G02/M01, T03).

Each rule names concrete protective wording in the current canonical skill
text. Positive tests check the real text; negative tests apply controlled
mutations (dropping a guard or injecting a contrary instruction) to isolated
temporary copies and require the checker to detect the regression. These tests
prove text presence and structure only, never that an agent actually follows
the text, that a package installs, or any token saving.
"""
import sys
sys.dont_write_bytecode = True
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.apm/skills'
DEVOPS = SKILLS / 'core-devops'
REFS = ('git-operations', 'development-automation', 'tooling-profiles',
        'checks-and-hooks', 'ci-and-releases', 'failure-recovery',
        'habit-feedback')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
# Exactly one top-level SemVer core without leading zeros; YAML decides quoting, the value is semantic.
SEMVER = re.compile(r'(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)')

# rule id -> (file relative to the skill dir, required patterns, forbidden patterns)
RULES = {
    'separate_authorizations': ('SKILL.md', [r'Jede Wirkung benötigt ihre eigene passende aktuelle Freigabe'], []),
    'unclear_authorization_no_mutation': ('SKILL.md', [r'Bei unklarer Freigabe bleibt jede Mutation aus'], []),
    'standalone_scm_no_plan': ('SKILL.md', [r'gewöhnliche Git-Aufträge benötigen keinen neuen Implementierungsplan'], []),
    'planned_setup_owned_by_workflows': ('SKILL.md', [r'`core-plan` und `core-execute` bleiben deren Eigentümer'], []),
    'context_paths_not_scope': ('SKILL.md', [r'`context_paths` sind Lesequellen und erweitern keinen'], []),
    'no_deployment': ('SKILL.md', [r'produktives Deployment\? Letzteres liegt außerhalb'], []),
    'commit_only': ('references/git-operations.md',
                    [r'Commit-only endet strikt mit dem lokalen Commit',
                     r'Push oder PR erfolgen ausschließlich bei aktueller ausdrücklicher Freigabe'],
                    [r'(?i)nach dem commit (automatisch|direkt) push']),
    'protected_history': ('references/git-operations.md',
                          [r'Force-Push.*benötigen gesonderte genaue Freigabe',
                           r'Geteilte/publizierte History nicht still umschreiben',
                           r'nicht mit Force wiederholen'],
                          [r'(?i)push --force(?!-with-lease)\b.*(verwenden|ausführen)']),
    'no_hook_bypass': ('SKILL.md', [r'Keine Hook-Umgehung'], [r'(?i)--no-verify (verwenden|nutzen)']),
    'release_inspection_entry': ('SKILL.md',
                                 [r'vor Rückfragen die \[Bestandsaufnahme\]',
                                  r'Diese Angaben sind keine vorab abzufragende Checkliste'], []),
    'release_inspection_first': ('references/ci-and-releases.md',
                                 [r'bevor du nach Releaseart, Veröffentlichungsziel oder Auslöser fragst',
                                  r'prüfe lokale Tags und die Remote-Zuordnung',
                                  r'jüngsten vorhandenen Releases einschließlich Tags, Release Notes und Assetnamen/-typen',
                                  r'bei GitHub `gh`',
                                  r'Ein GitHub-Remote allein belegt weder GitHub Packages noch npm',
                                  r'Übernimm eindeutige bestehende Konventionen',
                                  r'Bestehende Releases allein belegen keine gewünschte neue Auslöse- oder Freigabepolicy',
                                  r'Bereits belegte Angaben werden nicht erneut abgefragt',
                                  r'werte fehlenden Zugriff nicht als fehlende Releases',
                                  r'Die Bestandsaufnahme autorisiert keine Installation'], []),
    'version_not_chosen': ('references/ci-and-releases.md',
                           [r'wähle außerhalb einer freigegebenen Policy keine Version eigenmächtig',
                            r'Versionskollision.*stoppen'], []),
    'zero_x_default': ('references/ci-and-releases.md',
                       [r'Empfiehl bei der Einrichtung einer Releaseautomation standardmäßig',
                        r'Fehlerkorrekturen erhöhen Patch',
                        r'Neue Funktionen und inkompatible Änderungen erhöhen Minor',
                        r'Patch wird dabei auf null gesetzt',
                        r'Bei gemischten Änderungen gilt der höchste erforderliche Sprung',
                        r'Frage ohne solchen Gegenbeleg nicht erneut offen nach einer 0.x-Policy'], []),
    'zero_x_exception': ('references/ci-and-releases.md',
                         [r'sofern keine verbindliche Projektregel oder ein konkreter fachlicher/technischer Grund dagegensteht',
                          r'Benenne und begründe eine Abweichung',
                          r'bewahre bestehende verbindliche Regeln'], []),
    'one_x_explicit': ('references/ci-and-releases.md',
                       [r'Der Wechsel auf `1\.0\.0` benötigt eine gesonderte ausdrückliche Entscheidung',
                        r'leite ihn nicht automatisch aus einer inkompatiblen Änderung ab'], []),
    'recommendation_no_authorization': ('references/ci-and-releases.md',
                                      [r'Die Empfehlung ersetzt keine Einrichtungs- oder Veröffentlichungsfreigabe',
                                       r'Tooldefaults allein belegen die Umsetzung nicht'], []),
    'release_separately_authorized': ('references/ci-and-releases.md',
                                      [r'Paketbau, Installation, Merge, Tag, Upload und Release sind getrennte Wirkungen',
                                       r'Tag oder Push genügt nicht'], []),
    'failed_check_blocks_release': ('references/ci-and-releases.md',
                                    [r'Fehlerhafte oder ausstehende Pflichtchecks blockieren die Veröffentlichung'], []),
    'existing_tools_kept': ('references/development-automation.md',
                            [r'Makefile, package\.json-Skripte',
                             r'Funktionierende vorhandene Werkzeuge und Teamgewohnheiten erhalten'], []),
    'mise_preferred_not_forced': ('references/development-automation.md',
                                  [r'Für neue wiederholbare projektübergreifende Aufgaben mise bevorzugen, falls passend',
                                   r'kein Werkzeugwechsel allein der Einheitlichkeit wegen'],
                                  [r'(?i)immer (nach )?mise (migrieren|verwenden)']),
    'check_only_no_install': ('references/development-automation.md',
                              [r'Nur prüfen: .*Keine Installation, Konfigurationsänderung oder Dependency-Aktualisierung'], []),
    'no_fixed_app_dirs': ('references/development-automation.md',
                          [r'Erfinde keine festen Verzeichnisse wie apps/web oder api'], []),
    'hooks_no_download': ('references/checks-and-hooks.md',
                          [r'Keine Downloads/Toolinstallation beim Commit'], []),
    'hooks_keep_unstaged': ('references/checks-and-hooks.md',
                            [r'Niemals unstaged Änderungen umformatieren, fremde Inhalte stagen'], []),
    'no_false_skip': ('references/checks-and-hooks.md',
                      [r'Root-, Shared- oder unklarer Scope läuft durch den vollen relevanten Check'], []),
    'failed_ci_stays_failed': ('references/failure-recovery.md',
                               [r'fehlgeschlagener Check bleibt fehlgeschlagen'], []),
}
# Fixed monorepo paths presented as given layout would hide repo assumptions.
FIXED_DIR = re.compile(r'(?<![\w/])(apps/(web|api|mobile)|packages/(web|api))/')


def read(path):
    return path.read_text(encoding='utf-8')


README_AUDIT_GUARDS = (
    'Fehlt die Methode, meldet der bestehende Skillverfügbarkeitscheck die konkrete Prüflücke statt sie als installiert zu behaupten.',
    'Direkte Dateieingaben und automatische Skripte unterstützen nur Markdown;',
    'übrigen zugänglichen Text nach der geladenen Rubrik manuell beurteilen und',
    'Format-/Extraktionslücken ausdrücklich melden.',
    'Das ist keine universelle Formatgarantie; das Audit bleibt report-only.',
)
INIT_AUDIT = (
    'Die Textprüfungspflicht der [Routingvorlage](assets/core-routing.md) gilt auch für alle hier '
    'erstellten oder inhaltlich bearbeiteten Dateien unabhängig von ihrer Endung. Lade `context-debloater` '
    'und seine Rubrik: Automatische Skripte und direkte Dateieingaben nur für unterstützte Markdownziele '
    'verwenden, übrigen zugänglichen Text manuell nach der Rubrik prüfen. Benenne Formatgrenzen und '
    'unlesbare Inhalte als Prüflücke; das Audit autorisiert weder automatische Kürzung/Mutation noch '
    'Toolinstallation oder Convertereinrichtung. Erhalte diese Pflicht samt Grenzen beim Entwurf und '
    'selektiven Blockabgleich.'
)
INIT_AVAILABILITY = 'Fehlende Skills werden als Einschränkung benannt, nicht installiert oder als verfügbar behauptet.'


def authoring_tools_are_not_dependencies(text):
    """Require split roles and audit guards in one README declaration paragraph."""
    paragraphs = [' '.join(p.split()) for p in text.split(chr(10) * 2)]
    named = [p for p in paragraphs if re.search(r'\b(?:skill-creator|context-debloater)\b', p)]
    if len(named) != 1:
        return False
    declarations = [s.strip() for s in re.split(r'[.!?]', named[0])
                    if re.search(r'\b(?:skill-creator|context-debloater)\b', s)]
    patterns = (
        r'`skill-creator` ist ein Werkzeug für die Paketentwicklung',
        r'`context-debloater` ist eine separat bereitzustellende Inhaltsprüfmethode, '
        r'die auch die Init-Ausgabe für erstellte oder inhaltlich bearbeitete Dateien verlangt; '
        r'sie ist keine (?:neue|zusätzliche) APM-Paketabhängigkeit und wird nicht automatisch installiert',
    )
    return (len(declarations) == len(patterns)
            and all(re.fullmatch(p, s) for p, s in zip(patterns, declarations))
            and all(guard in named[0] for guard in README_AUDIT_GUARDS))


def consumer_authoring_tools_are_bounded(text, *, init=False):
    """Only the complete, guarded Init audit paragraph is consumer-facing."""
    normalized = ' '.join(text.split())
    if init:
        if normalized.count(INIT_AUDIT) != 1 or INIT_AVAILABILITY not in normalized:
            return False
        normalized = normalized.replace(INIT_AUDIT, '', 1)
    return all(tool not in normalized for tool in ('skill-creator', 'context-debloater'))


def frontmatter(text):
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    return dict(re.findall(r'^(\w+): (.+)$', match.group(1), re.M)) if match else {}


def rule_violations(skill_dir):
    found = set()
    for rule, (rel, required, forbidden) in RULES.items():
        text = ' '.join(read(skill_dir / rel).split())
        if any(not re.search(p, text) for p in required) or any(re.search(p, text) for p in forbidden):
            found.add(rule)
    for path in sorted(skill_dir.rglob('*.md')):
        if FIXED_DIR.search(read(path)):
            found.add('no_fixed_app_dirs')
    return found


def package_version(manifest):
    try:
        data = yaml.safe_load(manifest)
    except yaml.YAMLError as exc:
        raise ValueError('apm.yml ist kein gültiges YAML') from exc
    # PyYAML keeps the last duplicate key silently, so top-level occurrences are counted on the text.
    version = data.get('version') if isinstance(data, dict) else None
    if len(re.findall(r'(?m)^version:', manifest)) != 1 or not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError('apm.yml braucht genau eine gültige Paketversion')
    return version


# Unmodified release-please YAML updater, as configured for apm.yml ($.version).
UPDATER = """
const root = process.argv[1];
const {GenericYaml} = require(root + '/build/src/updaters/generic-yaml.js');
const {Version} = require(root + '/build/src/version.js');
let text = '';
process.stdin.on('data', chunk => text += chunk).on('end', () =>
  process.stdout.write(new GenericYaml('$.version', Version.parse(process.argv[2])).updateContent(text)));
"""


def release_please_update(manifest, version):
    """Run the pinned isolated release-please updater; a missing toolchain fails instead of skipping."""
    spec = importlib.util.spec_from_file_location('bootstrap_ci_devops', ROOT / 'scripts/bootstrap_ci.py')
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    _, ws, env, _ = bootstrap.verify(Path(os.environ.get('AWC_CI_WORKSPACE') or Path(sys.prefix).parent))
    result = subprocess.run([str(ws / 'node/bin/node'), '-e', UPDATER, str(ws / 'npm/node_modules/release-please'), version],
                            input=manifest, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise AssertionError('release-please updater: ' + result.stderr[-2000:])
    return result.stdout


def broken_links(skill_dir):
    broken = []
    for path in sorted(skill_dir.rglob('*.md')):
        for ref in LINK.findall(read(path)):
            if '://' in ref or ref.startswith('#'):
                continue
            if not (path.parent / ref.split('#')[0]).exists():
                broken.append((path.name, ref))
    return broken


class Fixture:
    """Isolated copy of core-devops plus its shared and S00 link targets, for mutation."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='devops-contract-')
        skills = Path(self.tmp.name) / 'skills'
        shutil.copytree(DEVOPS, skills / 'core-devops')
        shutil.copytree(SKILLS / 'core-shared', skills / 'core-shared')
        # core-devops links S00 directly; copy only that file, not the whole architecture skill.
        baseline = 'core-architecture/references/design-baseline.md'
        (skills / baseline).parent.mkdir(parents=True)
        shutil.copy2(SKILLS / baseline, skills / baseline)
        # habit-feedback.md links four workflow skill sources; copy those real
        # files so link checks stay effective, not whole skills.
        for name in ('core-plan', 'core-execute', 'core-refactor', 'core-review'):
            target = skills / name / 'SKILL.md'
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SKILLS / name / 'SKILL.md', target)
        self.dir = skills / 'core-devops'
        return self

    def mutate(self, rel, old, new):
        path = self.dir / rel
        text = read(path)
        if old not in text:
            raise AssertionError(f'mutation anchor missing in {rel}: {old!r}')
        path.write_text(text.replace(old, new, 1), encoding='utf-8')

    def __exit__(self, *exc):
        self.tmp.cleanup()


class CurrentText(unittest.TestCase):
    def test_frontmatter_names_and_descriptions(self):
        meta = frontmatter(read(DEVOPS / 'SKILL.md'))
        self.assertEqual(meta.get('name'), 'core-devops')
        self.assertIn('nicht für Produktimplementierung', meta.get('description', ''))

    def test_every_reference_is_linked_from_skill_and_exists(self):
        skill = read(DEVOPS / 'SKILL.md')
        for ref in REFS:
            self.assertTrue((DEVOPS / f'references/{ref}.md').is_file(), ref)
            self.assertIn(f'(references/{ref}.md)', skill, ref)
        self.assertEqual(sorted(p.stem for p in (DEVOPS / 'references').glob('*.md')), sorted(REFS))

    def test_links_resolve(self):
        self.assertEqual(broken_links(DEVOPS), [])

    def test_all_rules_hold(self):
        self.assertEqual(rule_violations(DEVOPS), set())

    def test_package_inventory_and_version(self):
        package_version(read(ROOT / 'apm.yml'))
        bundles = sorted(p.parent.name for p in SKILLS.glob('core-*/SKILL.md'))
        self.assertEqual(len(bundles), 22)
        self.assertIn('core-devops', bundles)
        self.assertNotIn('core-scm', bundles)

    def test_no_stale_core_scm_routing(self):
        for path in [ROOT / 'README.md', ROOT / 'DESIGN.md', *SKILLS.glob('core-*/SKILL.md')]:
            self.assertNotIn('core-scm', read(path), path)
        for name in ('core-refactor', 'core-repo-audit'):
            self.assertIn('core-devops', read(SKILLS / name / 'SKILL.md'), name)

    def test_authoring_tools_are_not_consumer_dependencies(self):
        deps = read(ROOT / 'apm.yml').split('dependencies:', 1)[1]
        for tool in ('skill-creator', 'context-debloater'):
            self.assertNotIn(tool, deps)
        for path in SKILLS.glob('core-*/SKILL.md'):
            self.assertTrue(consumer_authoring_tools_are_bounded(
                read(path), init=path.parent.name == 'core-init-project'), path)
        self.assertTrue(authoring_tools_are_not_dependencies(read(ROOT / 'README.md')))
        design = read(ROOT / 'DESIGN.md')
        self.assertIn('`skill-creator` bleibt ein Authoring-Werkzeug der Paketentwicklung.', design)
        self.assertIn('separat verfügbare, report-only Inhaltsprüfmethode für die Init-Ausgabe', design)
        self.assertIn('Beide sind keine APM-Abhängigkeiten und werden weder durch dieses Paket installiert noch mit ihm ausgeliefert.', design)


# rule -> (file, protective text, replacement simulating the lost guard)
MUTATIONS = {
    'commit_only': ('references/git-operations.md', 'Commit-only endet strikt mit dem lokalen Commit.',
                    'Nach dem Commit automatisch pushen.'),
    'protected_history': ('references/git-operations.md', 'nicht mit Force wiederholen', 'mit Force wiederholen'),
    'separate_authorizations': ('SKILL.md', 'Jede Wirkung benötigt ihre eigene passende aktuelle Freigabe.',
                                'Eine Freigabe deckt alle Folgeschritte ab.'),
    'unclear_authorization_no_mutation': ('SKILL.md', 'Bei unklarer Freigabe bleibt jede Mutation aus.', ''),
    'no_hook_bypass': ('SKILL.md', 'Keine Hook-Umgehung,', 'Bei Hookfehlern --no-verify verwenden,'),
    'release_inspection_entry': ('SKILL.md', 'vor Rückfragen die [Bestandsaufnahme]',
                                 'nach Rückfragen die [Bestandsaufnahme]'),
    'release_inspection_first': ('references/ci-and-releases.md',
                                 'bevor du nach Releaseart, Veröffentlichungsziel oder Auslöser fragst',
                                 'nachdem du Releaseart, Veröffentlichungsziel und Auslöser erfragt hast'),
    'version_not_chosen': ('references/ci-and-releases.md', 'wähle außerhalb einer freigegebenen Policy keine Version eigenmächtig.',
                           'Wähle eine passende Version.'),
    'zero_x_default': ('references/ci-and-releases.md', 'Neue Funktionen und inkompatible Änderungen erhöhen Minor',
                       'Inkompatible Änderungen erhöhen Major'),
    'zero_x_exception': ('references/ci-and-releases.md', 'bewahre bestehende verbindliche Regeln',
                         'ersetze bestehende Regeln durch den Default'),
    'one_x_explicit': ('references/ci-and-releases.md',
                       'Der Wechsel auf `1.0.0` benötigt eine gesonderte ausdrückliche Entscheidung',
                       'Inkompatible Änderungen wechseln automatisch auf `1.0.0`'),
    'recommendation_no_authorization': ('references/ci-and-releases.md',
                                      'Die Empfehlung ersetzt keine Einrichtungs- oder Veröffentlichungsfreigabe',
                                      'Die Empfehlung autorisiert Einrichtung und Veröffentlichung'),
    'release_separately_authorized': ('references/ci-and-releases.md', 'Tag oder Push genügt nicht', 'Tag genügt'),
    'failed_check_blocks_release': ('references/ci-and-releases.md', 'Fehlerhafte oder ausstehende Pflichtchecks blockieren',
                                    'Fehlerhafte Pflichtchecks verzögern'),
    'existing_tools_kept': ('references/development-automation.md',
                            'Funktionierende vorhandene Werkzeuge und Teamgewohnheiten erhalten', 'Alles auf mise umstellen'),
    'mise_preferred_not_forced': ('references/development-automation.md', 'mise bevorzugen, falls passend',
                                  'immer mise verwenden'),
    'check_only_no_install': ('references/development-automation.md',
                              'Keine Installation, Konfigurationsänderung oder Dependency-Aktualisierung ableiten.',
                              'Fehlende Tools dabei installieren.'),
    'hooks_no_download': ('references/checks-and-hooks.md', 'Keine Downloads/Toolinstallation beim Commit',
                          'Tools beim Commit herunterladen'),
    'hooks_keep_unstaged': ('references/checks-and-hooks.md', 'Niemals unstaged Änderungen umformatieren',
                            'Auch unstaged Änderungen umformatieren'),
    'no_false_skip': ('references/checks-and-hooks.md', 'Root-, Shared- oder unklarer Scope läuft durch den vollen relevanten Check.',
                      'Root-Änderungen dürfen übersprungen werden.'),
    'failed_ci_stays_failed': ('references/failure-recovery.md', 'fehlgeschlagener Check bleibt fehlgeschlagen',
                               'bei Bedarf Check deaktivieren'),
    'standalone_scm_no_plan': ('SKILL.md', 'gewöhnliche Git-Aufträge benötigen keinen neuen Implementierungsplan',
                               'jeder Git-Auftrag benötigt einen Implementierungsplan'),
    'context_paths_not_scope': ('SKILL.md', '`context_paths` sind Lesequellen und erweitern keinen dieser Scopes.',
                                '`context_paths` sind ebenfalls Schreibscope.'),
}


class AuthoringDependencyText(unittest.TestCase):
    """Frozen text mutations; CurrentText separately checks the mutable README."""

    DECLARATION = (
        '`skill-creator` ist ein Werkzeug für die Paketentwicklung. '
        '`context-debloater` ist eine separat bereitzustellende Inhaltsprüfmethode, '
        'die auch die Init-Ausgabe für erstellte oder inhaltlich bearbeitete Dateien verlangt; '
        'sie ist keine neue APM-Paketabhängigkeit und wird nicht automatisch installiert. '
        + ' '.join(README_AUDIT_GUARDS)
    )
    TEXT = '## Lizenz' + chr(10) * 2 + DECLARATION

    def test_both_valid_dependency_phrasings(self):
        text = self.TEXT
        anchor = 'keine neue APM-Paketabhängigkeit'
        self.assertIn(anchor, text)
        for phrase in ('keine zusätzliche APM-Paketabhängigkeit', anchor):
            with self.subTest(phrase=phrase):
                self.assertTrue(authoring_tools_are_not_dependencies(text.replace(anchor, phrase)))

    def test_missing_contrary_and_misleading_declarations_fail(self):
        text = self.TEXT
        declaration = self.DECLARATION
        self.assertEqual(text.count(declaration), 1)
        variants = {
            'removed': text.replace(declaration, ''),
            'no negation': text.replace('keine neue APM-Paketabhängigkeit', 'eine neue APM-Paketabhängigkeit'),
            'auto install': text.replace('wird nicht automatisch installiert', 'wird automatisch installiert'),
            'unrelated negation': text.replace(declaration,
                '`skill-creator` und `context-debloater` sind Paketabhängigkeiten. '
                'Andere Werkzeuge sind keine Paketabhängigkeiten.'),
            'detached tool names': text.replace(declaration,
                '`skill-creator` und `context-debloater` werden verwendet. '
                'Andere Werkzeuge sind keine zusätzlichen Verbraucherabhängigkeiten.'),
            'one tool missing': text.replace('`skill-creator` ist ein Werkzeug für die Paketentwicklung.', ''),
            'different tool': text.replace('`context-debloater`', '`other-tool`'),
            'qualified denial': text.replace('keine neue APM-Paketabhängigkeit',
                                             'keine neue APM-Paketabhängigkeit nur im Test'),
            'quoted claim': text.replace(declaration, 'Ein Beispiel lautet: ' + declaration),
            'contradiction': text + """
`skill-creator` ist eine Paketabhängigkeit.""",
        }
        for label, mutated in variants.items():
            with self.subTest(label=label):
                self.assertNotEqual(mutated, text)
                self.assertFalse(authoring_tools_are_not_dependencies(mutated))
        for guard in README_AUDIT_GUARDS:
            with self.subTest(removed_guard=guard):
                self.assertFalse(authoring_tools_are_not_dependencies(text.replace(guard, '')))
        self.assertFalse(authoring_tools_are_not_dependencies(''))
        self.assertFalse(authoring_tools_are_not_dependencies('keine Paketabhängigkeiten'))

    def test_irrelevant_text_and_line_wrapping_keep_contract_green(self):
        text = self.TEXT
        self.assertIn('## Lizenz', text)
        self.assertTrue(authoring_tools_are_not_dependencies(text.replace('## Lizenz', '## Paketlizenz')))
        self.assertTrue(authoring_tools_are_not_dependencies(text.replace(
            'keine neue APM-Paketabhängigkeit', 'keine neue\nAPM-Paketabhängigkeit')))

    def test_consumer_audit_is_scoped_and_requires_every_guard(self):
        text = INIT_AVAILABILITY + '\n\n' + INIT_AUDIT
        self.assertTrue(consumer_authoring_tools_are_bounded(text, init=True))
        self.assertTrue(consumer_authoring_tools_are_bounded('# Other consumer'))
        self.assertTrue(consumer_authoring_tools_are_bounded(text.replace('Rubrik:', 'Rubrik:\n'), init=True))
        self.assertFalse(consumer_authoring_tools_are_bounded(text))
        for old in (INIT_AVAILABILITY, 'unabhängig von ihrer Endung',
                    'nur für unterstützte Markdownziele', 'manuell nach der Rubrik prüfen',
                    'als Prüflücke', 'weder automatische Kürzung/Mutation',
                    'noch Toolinstallation oder Convertereinrichtung'):
            with self.subTest(removed=old):
                self.assertFalse(consumer_authoring_tools_are_bounded(text.replace(old, ''), init=True))
        for contrary in ('Lade `skill-creator`.', 'Installiere `context-debloater` automatisch.',
                         'Lade `context-debloater` als zusätzliche Voraussetzung.'):
            with self.subTest(injected=contrary):
                self.assertFalse(consumer_authoring_tools_are_bounded(text + '\n\n' + contrary, init=True))


class PackageVersion(unittest.TestCase):
    def test_valid_versions_accepted(self):
        for version in ('0.2.1', '0.10.0', '1.0.0', '12.34.56'):
            for scalar in (version, f'"{version}"', f"'{version}'"):
                with self.subTest(scalar=scalar):
                    self.assertEqual(package_version(f'name: x\nversion: {scalar}\n'), version)

    def test_invalid_versions_rejected(self):
        for manifest in ('name: x\n', 'version: "v0.2.1"\n', 'version: "0.2"\n', 'version: 0.2\n', 'version: 1\n', 'version: "01.2.3"\n',
                         'version: "0.2.1-rc.1"\n', 'version: [0.2.1]\n', 'version:\n', 'version: "0.2.1\'\n', "version: '0.2.1\"\n",
                         'version: "0.2.1"\nversion: "0.2.2"\n', 'version: "0.2.1"\nversion: 0.2.2\n', '  version: "0.2.1"\n',
                         'version: "0.2.1"\n  bad: [\n', '- version: 0.2.1\n'):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                package_version(manifest)

    def test_real_release_please_updater_output_is_accepted(self):
        manifest = read(ROOT / 'apm.yml')
        current = package_version(manifest)
        major, minor, patch = map(int, current.split('.'))
        bumped = '%d.%d.%d' % (major, minor, patch + 1)
        updated = release_please_update(manifest, bumped)
        self.assertEqual(package_version(updated), bumped)
        before, after = yaml.safe_load(manifest), yaml.safe_load(updated)
        self.assertEqual(after.pop('version'), bumped)
        before.pop('version')
        self.assertEqual(after, before)


class Mutations(unittest.TestCase):
    def test_each_lost_guard_is_detected_in_isolation(self):
        self.assertTrue(set(MUTATIONS) <= set(RULES))
        for rule, (rel, old, new) in MUTATIONS.items():
            with self.subTest(rule=rule), Fixture() as fx:
                self.assertEqual(rule_violations(fx.dir), set())
                fx.mutate(rel, old, new)
                self.assertIn(rule, rule_violations(fx.dir))

    def test_injected_contrary_instruction_is_detected(self):
        with Fixture() as fx:
            fx.mutate('references/git-operations.md', '## History und Remote',
                      'Bei abgelehntem Push git push --force ausführen.\n\n## History und Remote')
            self.assertIn('protected_history', rule_violations(fx.dir))

    def test_hidden_fixed_repo_layout_is_detected(self):
        with Fixture() as fx:
            fx.mutate('references/tooling-profiles.md', '| Python |', '| Python (apps/api/) |')
            self.assertIn('no_fixed_app_dirs', rule_violations(fx.dir))

    def test_removed_reference_breaks_links(self):
        with Fixture() as fx:
            (fx.dir / 'references/failure-recovery.md').unlink()
            self.assertIn(('SKILL.md', 'references/failure-recovery.md'), broken_links(fx.dir))

    def test_removed_core_link_target_breaks_fixture_links(self):
        with Fixture() as fx:
            (fx.dir.parent / 'core-plan' / 'SKILL.md').unlink()
            self.assertIn(('habit-feedback.md', '../../core-plan/SKILL.md'), broken_links(fx.dir))

    def test_unrelated_edit_keeps_rules_green(self):
        with Fixture() as fx:
            fx.mutate('references/tooling-profiles.md', 'Wähle Prüfwerkzeuge', 'Wähle passende Prüfwerkzeuge')
            self.assertEqual(rule_violations(fx.dir), set())
            self.assertEqual(broken_links(fx.dir), [])


if __name__ == '__main__':
    unittest.main()
