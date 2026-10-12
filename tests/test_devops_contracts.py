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
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.apm/skills'
DEVOPS = SKILLS / 'core-devops'
REFS = ('git-operations', 'development-automation', 'tooling-profiles',
        'checks-and-hooks', 'ci-and-releases', 'failure-recovery')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')

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
    'version_not_chosen': ('references/ci-and-releases.md',
                           [r'Wähle nicht eigenmächtig eine Version oder Policy',
                            r'Versionskollision.*stoppen'], []),
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
    """Isolated copy of core-devops plus its shared targets, for mutation."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='devops-contract-')
        skills = Path(self.tmp.name) / 'skills'
        shutil.copytree(DEVOPS, skills / 'core-devops')
        shutil.copytree(SKILLS / 'core-shared', skills / 'core-shared')
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
        manifest = read(ROOT / 'apm.yml')
        self.assertRegex(manifest, r'(?m)^version: "0\.2\.0"$')
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
            # Provenance may name authoring tools; consumer-loaded instructions must not.
            for path in SKILLS.glob('core-*/SKILL.md'):
                self.assertNotIn(tool, read(path), f'{path} makes {tool} a consumer dependency')
        self.assertIn('keine Paketabhängigkeiten', read(ROOT / 'README.md'))
        self.assertIn('keine APM-Abhängigkeiten und keine Bestandteile eines Verbraucher-Workflows', read(ROOT / 'DESIGN.md'))


# rule -> (file, protective text, replacement simulating the lost guard)
MUTATIONS = {
    'commit_only': ('references/git-operations.md', 'Commit-only endet strikt mit dem lokalen Commit.',
                    'Nach dem Commit automatisch pushen.'),
    'protected_history': ('references/git-operations.md', 'nicht mit Force wiederholen', 'mit Force wiederholen'),
    'separate_authorizations': ('SKILL.md', 'Jede Wirkung benötigt ihre eigene passende aktuelle Freigabe.',
                                'Eine Freigabe deckt alle Folgeschritte ab.'),
    'unclear_authorization_no_mutation': ('SKILL.md', 'Bei unklarer Freigabe bleibt jede Mutation aus.', ''),
    'no_hook_bypass': ('SKILL.md', 'Keine Hook-Umgehung,', 'Bei Hookfehlern --no-verify verwenden,'),
    'version_not_chosen': ('references/ci-and-releases.md', 'Wähle nicht eigenmächtig eine Version oder Policy.',
                           'Wähle eine passende Version.'),
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

    def test_unrelated_edit_keeps_rules_green(self):
        with Fixture() as fx:
            fx.mutate('references/tooling-profiles.md', 'Wähle Prüfwerkzeuge', 'Wähle passende Prüfwerkzeuge')
            self.assertEqual(rule_violations(fx.dir), set())
            self.assertEqual(broken_links(fx.dir), [])


if __name__ == '__main__':
    unittest.main()
