"""Static, offline regression tests for the direct S00 integration (G01/M01, T02).

These tests read canonical skill text and check concrete mandatory parts plus
controlled text mutations. They prove text presence and structure only, never
the runtime behaviour of an agent following the text.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import contextlib
import io
import re
import tempfile
import types
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.apm/skills'
BASELINE = SKILLS / 'core-architecture/references/design-baseline.md'
BASELINE_PATH = '.apm/skills/core-architecture/references/design-baseline.md'
CODING_SKILLS = ('core-backend', 'core-frontend', 'core-mobile', 'core-database', 'core-tf-infra', 'core-debug', 'core-refactor')
CHECKER = ROOT / 'scripts/check_core_contracts.py'
CLI_GROUPS = ('selftest', 'milestones', 'shared', 'workflows', 'domains', 'setup', 'docs', 'all')
CLI_DOMAIN_GROUPS = CLI_GROUPS[1:-1]
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
# Former 'Coding-Tasks' anchors, widened to cross-cutting structural work (code, tools, packages, setup, automation).
STRUCTURAL_TASKS = re.compile(r'Coding-Tasks|schreibenden strukturrelevanten Tasks')


def skill_path(name):
    return SKILLS / name / 'SKILL.md'


def read(path):
    return path.read_text(encoding='utf-8')


def section(text, heading):
    """Return the body below an exact Markdown heading up to the next heading of equal or higher level."""
    match = re.search(r'^(#+) ' + re.escape(heading) + r'\s*$', text, re.M)
    if not match:
        return ''
    level = len(match.group(1))
    rest = text[match.end():]
    end = re.search(r'^#{1,%d} ' % level, rest, re.M)
    return rest[:end.start()] if end else rest


def paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n|\n(?=- )', text) if p.strip()]


def links_to_baseline(text, source):
    return any((source.parent / ref.split('#')[0]).resolve() == BASELINE.resolve() for ref in LINK.findall(text))


def slug(heading):
    plain = unicodedata.normalize('NFKD', heading.strip().lower())
    plain = ''.join(c for c in plain if not unicodedata.combining(c))
    plain = re.sub(r'[^a-z0-9 \-]', '', plain)
    return plain.replace(' ', '-')


def anchors(path):
    return {slug(h.replace('\x60', '')) for h in re.findall(r'^#+ (.+?)\s*$', read(path), re.M)}


def link_problems(text, source):
    """Internal links must stay inside the workspace, exist and, for Markdown targets, hit a heading anchor."""
    problems = []
    for ref in LINK.findall(text):
        if re.match(r'^[a-z]+://', ref) or ref.startswith('mailto:'):
            continue
        relative, _, fragment = ref.partition('#')
        target = (source.parent / relative).resolve() if relative else source.resolve()
        if not target.is_relative_to(ROOT.resolve()) or not target.exists():
            problems.append('missing target: ' + ref)
        elif fragment and target.suffix == '.md' and fragment not in anchors(target):
            problems.append('missing anchor: ' + ref)
    return problems


def plan_problems(text, source):
    problems = []
    research = section(text, '3. Research nur bei materieller Wissenslücke')
    s00 = [p for p in paragraphs(research) if links_to_baseline(p, source)]
    if not s00:
        problems.append('plan: direct S00 link missing')
    elif not ('Lösungswahl' in s00[0] and 'Coding' in s00[0]):
        problems.append('plan: S00 not applied at solution choice for coding')
    elif 'kleinen Änderungen' not in s00[0]:
        problems.append('plan: small coding tasks not covered')
    elif 'ungeplantes Refactoring' not in s00[0]:
        problems.append('plan: refactoring boundary missing')
    elif not re.search(r'tatsächlich geladenen[^.]*\x60SKILL\.md\x60', s00[0]) or 'Lesezugriff' not in s00[0]:
        problems.append('plan: S00 link not resolved from loaded skill location')
    elif not re.search(r'fehlend oder nicht lesbar[^.]*\x60blocked\x60', s00[0]):
        problems.append('plan: missing/unreadable S00 source does not block')
    graph = section(text, '4. Einen Taskgraphen zerlegen')
    rule = [p for p in paragraphs(graph) if p.startswith('- \x60context_paths\x60')]
    if not rule or 'aufgelöste exakte S00-Lesepfad' not in rule[0] or not STRUCTURAL_TASKS.search(rule[0]) or 'immer' not in rule[0]:
        problems.append('plan: exact resolved S00 read path in context_paths missing')
    elif BASELINE_PATH in rule[0] or 'nie ein fest codierter' not in rule[0]:
        problems.append('plan: hard-coded producer S00 path required')
    if not re.search(r'S00-Lesepfad[^.]*exakt übernommen[^.]*außerhalb des Projekts', section(text, '5. Statisch validieren und bestätigen')):
        problems.append('plan: exact external S00 read path exception missing')
    if not re.search(r'S00[^\n]*\x60acceptance\x60[^\n]*\x60checks\x60', graph):
        problems.append('plan: S00 results not anchored in acceptance/checks')
    if not section(text, 'Unverändertes \x60plan/v1\x60-Kernformat'):
        problems.append('plan: unchanged plan/v1 core format section missing')
    return problems


def execute_problems(text, source):
    problems = []
    validate = section(text, '1. Plan und Drift validieren')
    step = [p for p in re.split(r'\n(?=\d+\. )', validate) if p.strip().startswith('2. ')]
    if not step or not links_to_baseline(step[0], source):
        problems.append('execute: direct S00 link in validation missing')
    elif '\x60context_paths\x60' not in step[0] or 'kanonische Referenz' not in step[0]:
        problems.append('execute: context_paths S00 validation missing')
    dispatch = section(text, '3. Tasks schedulen und dispatchen')
    bullet = [p for p in paragraphs(dispatch) if 'jeden Task genau einem registrierten Fachagenten' in p]
    if not bullet:
        problems.append('execute: every task to exactly one agent missing')
    else:
        b = bullet[0]
        for part in ('Auftrag', '\x60context_paths\x60', '\x60scope\x60', 'Akzeptanzkriterien', 'Checks', 'Constraints'):
            if part not in b:
                problems.append('execute: dispatch payload lacks ' + part)
        if not links_to_baseline(b, source) or not STRUCTURAL_TASKS.search(b):
            problems.append('execute: S00 handover in dispatch missing')
        if 'vor der ersten Codeänderung' not in b:
            problems.append('execute: pre-change application in handover missing')
        if not re.search(r'read-only Tasks[^.]*einen Fachagenten', b):
            problems.append('execute: read-only tasks no longer bound to one agent')
        if 'kein zusätzlicher Architektur-Dispatch' not in b:
            problems.append('execute: extra architecture dispatch not excluded')
    if 'keinen Subagenten' not in dispatch or 'allein bei \x60core-execute\x60' not in dispatch:
        problems.append('execute: dispatch ownership boundary missing')
    result = section(text, '4. Taskresultat prüfen')
    items = [p for p in paragraphs(result) if p.startswith('- ')]
    acc = [p for p in items if 'Akzeptanz-ID' in p]
    if not acc or 'S00-Befund' not in acc[0] or not STRUCTURAL_TASKS.search(acc[0]):
        problems.append('execute: S00 completion finding in acceptance evidence missing')
    chk = [p for p in items if 'gepinnten Check' in p]
    if not chk or 'unverändertem Kommando' not in chk[0] or 'S00' not in chk[0]:
        problems.append('execute: S00 check evidence missing')
    if not any('vorhandenen Ergebnisfeldern' in p and 'kein neues Schema' in p for p in items):
        problems.append('execute: existing result schema boundary missing')
    if 'task-result/v1' not in result:
        problems.append('execute: task-result/v1 schema missing')
    return problems


def coding_skill_problems(text, source):
    problems = []
    body = section(text, 'Situative Designmethoden')
    pre = [p for p in paragraphs(body) if 'Vor der ersten Codeänderung' in p]
    if not pre:
        return ['coding: pre-change S00 duty missing']
    p = pre[0]
    if not links_to_baseline(p, source):
        problems.append('coding: S00 link missing')
    if 'kleinen Änderungen' not in p:
        problems.append('coding: small changes not covered')
    if not re.search(r'zum Abschluss[^.]*betroffenen', p):
        problems.append('coding: completion check missing')
    if 'nicht als Vollscan' not in p:
        problems.append('coding: full-scan boundary missing')
    if 'keine ungeplanten Refactorings' not in p:
        problems.append('coding: refactoring boundary missing')
    return problems


def mutate(test, text, old, new=''):
    test.assertIn(old, text, 'mutation anchor missing')
    return text.replace(old, new, 1)


def load_checker(source):
    """Execute checker source as an isolated module; its ROOT still resolves to this workspace."""
    module = types.ModuleType('checker_cli_under_test')
    module.__file__ = str(CHECKER)
    exec(compile(source, str(CHECKER), 'exec'), module.__dict__)
    return module


def cli_problems(source):
    """Offline CLI and read-only regression: lost groups/options, swallowed errors and unnoticed source changes."""
    try:
        checker = load_checker(source)
    except Exception as exc:
        return ['load: ' + type(exc).__name__]
    problems = []

    class Guarded(Exception):
        pass

    # Real group and selftest entry points must route their sources through the read-only guard.
    real_guard, guarded = checker.guarded_run, []
    def spy(paths, action):
        guarded.append([Path(p).resolve() for p in paths])
        raise Guarded()
    checker.guarded_run, checker.unittest = spy, types.SimpleNamespace()
    for name, call, expected in (('group', lambda: checker.check_group(ROOT, 'docs'), lambda: checker.targets(ROOT, 'docs')),
                                 ('selftest', lambda: checker.selftest(ROOT), lambda: [CHECKER])):
        guarded.clear()
        try:
            call()
        except Exception:
            pass
        try:
            wanted = {Path(p).resolve() for p in expected()}
        except Exception:
            wanted = None
        if not guarded or wanted is None or not wanted <= set(guarded[0]):
            problems.append('unguarded sources: ' + name)
    checker.guarded_run = real_guard
    with tempfile.TemporaryDirectory(prefix='cli-guard-') as directory:
        source_file, other = Path(directory) / 'source.md', Path(directory) / 'other.md'
        source_file.write_text('stable-1', encoding='utf-8')
        try:
            checker.guarded_run([source_file], lambda: other.write_text('irrelevant', encoding='utf-8'))
        except checker.ContractError:
            problems.append('guard: irrelevant change rejected')
        try:
            checker.guarded_run([source_file], lambda: source_file.write_text('stable-2', encoding='utf-8'))
            problems.append('guard: source change unnoticed')
        except checker.ContractError:
            pass

    calls, failing = [], set()
    def record(group, authoring):
        calls.append((group, authoring))
        if group in failing:
            raise checker.ContractError('injected violation')
    checker.check_group = lambda root, group, with_authoring=False, tool_root=None: record(group, with_authoring)
    checker.selftest = lambda root: record('selftest', False)
    def run(argv, fail=()):
        calls.clear()
        failing.clear()
        failing.update(fail)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return checker.main(argv)
            except SystemExit as exc:
                return exc.code
            except Exception as exc:
                return type(exc).__name__
    def expected(group, authoring):
        return [('selftest', False)] if group == 'selftest' else [(g, authoring) for g in (CLI_DOMAIN_GROUPS if group == 'all' else (group,))]
    for group in CLI_GROUPS:
        for authoring in ((False,) if group == 'selftest' else (False, True)):
            if run(['--group', group] + ['--authoring'] * authoring) != 0 or calls != expected(group, authoring):
                problems.append('group/option lost: ' + group + ' --authoring' * authoring)
    if run(['--group', 'selftest', '--authoring']) != 1:
        problems.append('selftest --authoring accepted')
    for argv in ([], ['--group'], ['--group', 'unknown'], ['--group', 'docs', '--unknown']):
        if run(argv) != 2:
            problems.append('argument error not rejected: ' + ' '.join(argv))
    for group, fail in (('docs', 'docs'), ('selftest', 'selftest'), ('all', 'shared')):
        if run(['--group', group], {fail}) != 1:
            problems.append('violation swallowed: ' + group)
        elif calls != expected(group, False):
            problems.append('groups skipped after violation: ' + group)
    return problems


class DesignPrincipleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_src, cls.exec_src = skill_path('core-plan'), skill_path('core-execute')
        cls.plan, cls.exe = read(cls.plan_src), read(cls.exec_src)
        cls.coding = {name: read(skill_path(name)) for name in CODING_SKILLS}

    def test_baseline_has_s00_with_completion(self):
        text = read(BASELINE)
        s00 = section(text, 'S00 — Proportionale Grund- und Abschlussprüfung')
        self.assertIn('**Abschluss:**', s00)
        self.assertIn('**Ergebnis:**', s00)

    def test_plan_positive(self):
        self.assertEqual(plan_problems(self.plan, self.plan_src), [])

    def test_plan_negative_mutations(self):
        cases = {
            'link': ('](../core-architecture/references/design-baseline.md) bereits', '](missing.md) bereits'),
            'solution': ('Lösungswahl', 'Umsetzung'),
            'small': ('auch bei kleinen Änderungen ohne Architektur-Trigger', ''),
            'producer_hardcode': ('der in Schritt 3 aufgelöste exakte S00-Lesepfad immer dazu, nie ein fest codierter Producer- oder Harness-Pfad', 'die kanonische S00-Referenz \x60' + BASELINE_PATH + '\x60 immer dazu'),
            'hardcode_added': ('nie ein fest codierter Producer- oder Harness-Pfad', 'nie ein fest codierter Pfad außer \x60' + BASELINE_PATH + '\x60'),
            'resolution': ('vom tatsächlich geladenen Verzeichnis dieses \x60SKILL.md\x60', 'vom Projektwurzelverzeichnis'),
            'read_check': ('prüfe mit einem Lesezugriff, dass', 'nimm an, dass'),
            'blocked': ('stoppe mit \x60blocked\x60', 'fahre fort'),
            'external_exception': ('auch wenn er außerhalb des Projekts liegt', ''),
            'acceptance': ('in den vorhandenen \x60acceptance\x60-/\x60checks\x60-Feldern', ''),
            'structural_scope': ('bei schreibenden strukturrelevanten Tasks gehört', 'bei manchen Tasks gehört'),
        }
        for name, (old, new) in cases.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(plan_problems(mutate(self, self.plan, old, new), self.plan_src), [])

    def test_relative_s00_link_resolves_in_producer_consumer_and_home(self):
        # Offline structure check of relative resolution in controlled temp copies; not LLM behaviour.
        ref = next(r for r in LINK.findall(self.plan) if r.endswith('design-baseline.md'))
        base = Path('/tmp/opencode') if Path('/tmp/opencode').is_dir() else None
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            for layout in ('producer/.apm/skills', 'consumer/.agents/skills', 'home/.agents/skills'):
                with self.subTest(layout=layout):
                    skills = Path(tmp) / layout
                    plan = skills / 'core-plan/SKILL.md'
                    plan.parent.mkdir(parents=True)
                    plan.write_text(self.plan, encoding='utf-8')
                    target = (plan.parent / ref).resolve()
                    self.assertTrue(target.is_relative_to(skills.resolve()))
                    self.assertFalse(target.exists())  # missing source stays detectable -> blocked
                    target.parent.mkdir(parents=True)
                    target.write_text(read(BASELINE), encoding='utf-8')
                    self.assertIn('## S00', target.read_text(encoding='utf-8'))
                    self.assertEqual(target, (skills / 'core-architecture/references/design-baseline.md').resolve())

    def test_execute_positive(self):
        self.assertEqual(execute_problems(self.exe, self.exec_src), [])

    def test_execute_negative_mutations(self):
        bullet = next(p for p in paragraphs(section(self.exe, '3. Tasks schedulen und dispatchen')) if 'jeden Task genau' in p)
        cut = bullet[:bullet.index('Fachagenten') + len('Fachagenten')] + '.'
        cases = {
            'validation_link': ('direkt die [S00-Basis](../core-architecture/references/design-baseline.md)', 'direkt die S00-Basis'),
            'truncated_dispatch': (bullet, cut),
            'weakened_assignment': ('jeden Task genau einem', 'Tasks einem'),
            'handover_link': ('[S00-Referenz](../core-architecture/references/design-baseline.md)', 'S00-Referenz'),
            'pre_change': ('wendet S00 vor der ersten Codeänderung an', 'wendet S00 an'),
            'read_only': ('read-only Tasks bleiben ohne diesen Zusatz an ihren einen Fachagenten gebunden', 'read-only Tasks bleiben ohne diesen Zusatz'),
            'subagent': ('**keinen Subagenten**', 'Subagenten'),
            'finding': ('einschließlich des S00-Befunds', ''),
            'schema': ('kein neues Schema', ''),
            'structural_handover': ('Bei schreibenden strukturrelevanten Tasks ergänze', 'Bei Bedarf ergänze'),
            'structural_finding': ('Verträge bei schreibenden strukturrelevanten Tasks,', 'Verträge,'),
        }
        for name, (old, new) in cases.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(execute_problems(mutate(self, self.exe, old, new), self.exec_src), [])

    def test_all_seven_coding_skills_positive(self):
        self.assertEqual(len(self.coding), 7)
        for name, text in self.coding.items():
            with self.subTest(skill=name):
                self.assertEqual(coding_skill_problems(text, skill_path(name)), [])

    def test_coding_skill_negative_mutations(self):
        cases = {
            'pre_change': ('Vor der ersten Codeänderung bei jeder Coding-Arbeit lade', 'Bei Coding-Arbeit lade'),
            'link': ('](../core-architecture/references/design-baseline.md)', '](design-baseline.md)'),
            'completion': ('Prüfe zum Abschluss dieselben tatsächlich betroffenen Bereiche und benenne', 'Benenne'),
            'refactoring': ('erlauben keine ungeplanten Refactorings', 'erlauben Refactorings'),
            'fullscan': ('nicht als Vollscan', 'als Vollscan'),
        }
        for name, text in self.coding.items():
            for mutation, (old, new) in cases.items():
                with self.subTest(skill=name, mutation=mutation):
                    self.assertNotEqual(coding_skill_problems(mutate(self, text, old, new), skill_path(name)), [])

    def test_internal_links_and_anchors(self):
        sources = [skill_path('core-plan'), skill_path('core-execute'), BASELINE] + [skill_path(n) for n in CODING_SKILLS]
        for source in sources:
            with self.subTest(source=str(source.relative_to(ROOT))):
                self.assertEqual(link_problems(read(source), source), [])

    def test_link_checker_negative(self):
        broken = mutate(self, self.exe, 'workflow-contract.md#evidenzbasierte-ersatzplanung', 'workflow-contract.md#nicht-vorhanden')
        self.assertIn('missing anchor', ' '.join(link_problems(broken, self.exec_src)))
        gone = mutate(self, self.plan, '../core-architecture/references/design-baseline.md', '../core-architecture/references/fehlt.md')
        self.assertIn('missing target', ' '.join(link_problems(gone, self.plan_src)))
        outside = '[x](../../../../outside.md)'
        self.assertTrue(link_problems(outside, self.plan_src))

    def test_plan_core_format_has_no_new_fields(self):
        block = re.search(r'\x60\x60\x60yaml\n(schema: plan/v1.*?)\x60\x60\x60', section(self.plan, 'Unverändertes \x60plan/v1\x60-Kernformat'), re.S)
        self.assertIsNotNone(block)
        keys = set(re.findall(r'^    ([a-z_]+):', block.group(1), re.M))
        self.assertEqual(keys, {'title', 'agent', 'task', 'context_paths', 'scope', 'dependencies', 'required_mcps', 'optional_mcps', 'acceptance', 'checks'})
        self.assertNotIn('priority:', block.group(1))
        self.assertNotIn('s00', block.group(1).lower())

    def test_cli_and_read_only_guard_positive(self):
        self.assertEqual(cli_problems(read(CHECKER)), [])

    def test_cli_irrelevant_change_passes(self):
        source = mutate(self, read(CHECKER), '"""Offline report-only contract checks;', '"""Offline report-only contract checks (reworded);')
        self.assertEqual(cli_problems(source + '\n# irrelevant trailing comment\n'), [])

    def test_cli_and_read_only_guard_negative_mutations(self):
        source = read(CHECKER)
        cases = {
            'lost_group': ("'setup', 'docs')", "'setup')"),
            'lost_all': ("*TARGET_GROUPS, 'all')", '*TARGET_GROUPS)'),
            'lost_authoring': ("    parser.add_argument('--authoring', action='store_true')\n", ''),
            'optional_group': ('choices=GROUPS, required=True', "choices=GROUPS, default='selftest'"),
            'authoring_dropped': ('check_group(ROOT, group, args.authoring)', 'check_group(ROOT, group)'),
            'selftest_authoring': ("raise ContractError('selftest besitzt", "print('selftest besitzt"),
            'swallowed_error': ("        print('FAIL:', exc, file=sys.stderr)\n        return 1\n", "        print('FAIL:', exc, file=sys.stderr)\n        return 0\n"),
            'swallowed_all': ("            require(not failures, '\\n'.join(failures))\n", ''),
            'blind_guard': ('require(snapshot(paths) == before,', 'require(True or snapshot(paths) == before,'),
            'unguarded_group': ('    return guarded_run(paths, action)\n\ndef selftest', '    return action()\n\ndef selftest'),
            'unguarded_selftest': ("    return guarded_run([root / 'scripts/check_core_contracts.py', test_path, fixture_path], action)", '    return action()'),
        }
        for name, (old, new) in cases.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(cli_problems(mutate(self, source, old, new)), [])


if __name__ == '__main__':
    unittest.main()
