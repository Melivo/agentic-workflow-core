"""Positive and deliberately violated fixtures, offline and without source writes."""
import sys
sys.dont_write_bytecode = True
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core_checker_tested', ROOT / 'scripts/check_core_contracts.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def plan_fixture():
    return dict(schema='plan/v1', status='Confirmed', tasks=[dict(id='T01', title='fixture', agent='backend-engineer', task='Do bounded work', context_paths=['schema.yaml'], scope=['api.py'], dependencies=[], required_mcps=['gortex'], optional_mcps=[], acceptance=[dict(id='AC01', description='observed')], checks=[dict(id='CK01', covers=['AC01'], command=['python', '-B', 'check.py'], cwd='.', **{'pass': 'observed relationship'})])])


def examples_fixture():
    goal = dict(schema='goal/v1', id='G01', approval='user-confirmed', goal='observable', non_goals=[], constraints=[], decisions=[], goal_acceptance=[dict(id='GAC01', description='observed')])
    definition = dict(schema='milestone-definition/v1', id='M02', version=2, approval='user-confirmed', goal_path='.agentic-workflow/goals/G01/goal.md', title='fixture', outcome='observed', scope=['src/'], dependencies=[], acceptance=[dict(id='MAC01', description='observed')])
    index = dict(schema='milestone-index/v1', goal_path=definition['goal_path'], revision=1, milestones=[dict(id='M02', version=2, definition_path='.agentic-workflow/goals/G01/milestones/M02-v2.yaml', selected=True, selection_approval='user-confirmed', current=True, current_approval='user-confirmed', plan_paths=[], run_paths=[], completion_refs=[])], goal_completion_refs=[])
    return [goal, definition, index]


def completion_ref(version=2, plan='p01', run='r01'):
    run_dir = '.agentic-workflow/runs/run-G01-M02-v%d-%s-%s/' % (version, plan, run)
    return dict(version=version, definition_path='.agentic-workflow/goals/G01/milestones/M02-v%d.yaml' % version, acceptance_ids=['MAC01'], plan_path='.agentic-workflow/plans/plan-G01-M02-v%d-%s.md' % (version, plan), run_path=run_dir + 'state.yaml', review_path=run_dir + 'review.yaml', evidence_paths=[run_dir + 'tasks/T01/attempt-01.yaml'])


def canonical_examples():
    paths = ['goal-format.md', 'milestone-format.md', 'milestone-index-format.md']
    documents = []
    for name in paths:
        text = (ROOT / '.apm/skills/core-milestone/references' / name).read_text(encoding='utf-8')
        documents.extend(b for b in checker.blocks(text) if isinstance(b, dict) and b.get('schema') != 'milestone/v1')
    return documents


class ContractTests(unittest.TestCase):
    def test_raw_scenarios(self):
        cases = json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']
        self.assertGreaterEqual(len(cases), 140)
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        positive = negative = 0
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertTrue((ROOT / case['source']).is_file())
                if case['expected'] == 'pass':
                    checker.validate_scenario(case['input'])
                    positive += 1
                else:
                    with self.assertRaises(checker.ContractError) as caught:
                        checker.validate_scenario(case['input'])
                    self.assertIn(case['observation'], str(caught.exception))
                    negative += 1
        print('FIXTURES:', positive, 'positive,', negative, 'gezielt verletzte; Namen/Version/Resume/Owner/Scope/Marker/Provider/Index/Prompt/Schreibfolge')

    def test_no_success_defaults(self):
        with self.assertRaises(checker.ContractError):
            checker.validate_scenario({})
        for kind in ('marker', 'handoff', 'result_owner', 'provider', 'version', 'completion', 'name', 'graph', 'progression', 'selection', 'prompt', 'write_sequence', 'goal_change', 'artifacts'):
            with self.subTest(kind=kind), self.assertRaises((KeyError, checker.ContractError)):
                checker.validate_scenario({'kind': kind})

    def test_yaml_safe_and_duplicate_keys(self):
        self.assertEqual(checker.load_yaml('key: [one, two]'), {'key': ['one', 'two']})
        for text in ('key: 1\nkey: 2', '!!python/object/apply:os.system ["touch not-allowed"]', 'a: ['):
            with self.subTest(text=text), self.assertRaises(checker.ContractError):
                checker.load_yaml(text)
        with patch.object(checker, 'yaml', None), self.assertRaisesRegex(checker.ContractError, 'PyYAML fehlt'):
            checker.load_yaml('key: value')

    def test_plan_coverage_registration_and_dependencies(self):
        checker.validate_plan(plan_fixture(), ['backend-engineer'], ['gortex'])
        mutations = [('status', 'Draft'), ('tasks', [])]
        for field, value in mutations:
            data = plan_fixture()
            data[field] = value
            with self.assertRaises(checker.ContractError):
                checker.validate_plan(data)
        for patch_data in ({'agent': 'unknown'}, {'dependencies': ['T02']}, {'checks': []}, {'required_mcps': ['unknown']}):
            data = plan_fixture()
            data['tasks'][0].update(patch_data)
            with self.subTest(patch_data=patch_data), self.assertRaises(checker.ContractError):
                checker.validate_plan(data, ['backend-engineer'], ['gortex'])

    def test_formats_and_exact_relationships(self):
        examples = examples_fixture()
        for data in examples:
            checker.check_format(data['schema'], data)
        checker.check_example_relations(examples)
        for field, value in [('goal_path', '.agentic-workflow/goals/G02/goal.md'), ('definition_path', '.agentic-workflow/goals/G01/milestones/M02-v1.yaml'), ('version', 1)]:
            bad = copy.deepcopy(examples)
            bad[2]['milestones'][0][field] = value
            with self.subTest(field=field), self.assertRaises(checker.ContractError):
                checker.check_example_relations(bad)
        bad = copy.deepcopy(examples)
        bad[1]['run_status'] = 'completed'
        with self.assertRaisesRegex(checker.ContractError, 'Laufzustand'):
            checker.check_format(bad[1]['schema'], bad[1])
        bad = copy.deepcopy(examples)
        bad[2]['milestones'].append(dict(bad[2]['milestones'][0], id='M03', definition_path='.agentic-workflow/goals/G01/milestones/M03-v2.yaml'))
        with self.assertRaisesRegex(checker.ContractError, 'mehrere aktuelle'):
            checker.check_format(bad[2]['schema'], bad[2])
        for field in ('approval', 'title'):
            bad = copy.deepcopy(examples)
            del bad[1][field]
            with self.subTest(missing=field), self.assertRaisesRegex(checker.ContractError, 'Pflichtfeld fehlt: ' + field):
                checker.check_format(bad[1]['schema'], bad[1])
        for field in ('revision', 'goal_completion_refs'):
            bad = copy.deepcopy(examples)
            del bad[2][field]
            with self.subTest(missing=field), self.assertRaisesRegex(checker.ContractError, 'Pflichtfeld fehlt: ' + field):
                checker.check_format(bad[2]['schema'], bad[2])

    def test_dependency_path_and_cycles(self):
        examples = examples_fixture()
        dependency = dict(id='M02', version=1, definition_path='.agentic-workflow/goals/G01/milestones/M02-v1.yaml')
        examples[1]['dependencies'] = [dependency]
        with self.assertRaisesRegex(checker.ContractError, 'fehlende Abhängigkeit'):
            checker.check_example_relations(examples)
        dependency['version'] = 2
        with self.assertRaisesRegex(checker.ContractError, 'widerspricht Inhalt'):
            checker.check_example_relations(examples)
        dependency['definition_path'] = dependency['definition_path'].replace('v1', 'v2')
        with self.assertRaisesRegex(checker.ContractError, 'zyklische'):
            checker.check_example_relations(examples)

    def test_historical_completion_binding(self):
        examples = examples_fixture()
        entry = examples[2]['milestones'][0]
        entry.update(plan_paths=[completion_ref()['plan_path']], run_paths=[completion_ref()['run_path']], completion_refs=[completion_ref()])
        checker.check_format(examples[2]['schema'], examples[2])
        checker.check_example_relations(examples)
        wrong = copy.deepcopy(examples)
        wrong[2]['milestones'][0]['completion_refs'][0]['version'] = 1
        with self.assertRaisesRegex(checker.ContractError, 'historischer Abschluss'):
            checker.check_format(wrong[2]['schema'], wrong[2])
        # An original v1 result is reusable for v2 only with a written revalidation.
        reused = copy.deepcopy(examples)
        old = completion_ref(version=1)
        old.update(version=2, definition_path=entry['definition_path'])
        reused[2]['milestones'][0].update(plan_paths=[], run_paths=[], completion_refs=[old])
        with self.assertRaisesRegex(checker.ContractError, 'automatisch übertragen'):
            checker.check_format(reused[2]['schema'], reused[2])
        old['revalidation_path'] = '.agentic-workflow/runs/run-G01-M02-v2-p01-r01/tasks/T02/attempt-01.yaml'
        checker.check_format(reused[2]['schema'], reused[2])
        old['revalidation_path'] = old['evidence_paths'][0]
        with self.assertRaisesRegex(checker.ContractError, 'automatisch übertragen'):
            checker.check_format(reused[2]['schema'], reused[2])

    def test_rv06_evidence_paths_normalized_to_pinned_run(self):
        cases = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        for case_id, index in (('t08-artifacts-new-structure', 0), ('t08-artifacts-confirmed-replacement', 1)):
            base = cases[case_id]
            checker.validate_scenario(copy.deepcopy(base['input']))
            ref = base['input']['documents'][-1]['milestones'][index]['completion_refs'][0]
            run_dir = ref['run_path'].removesuffix('state.yaml')
            for bad in ('../run-G99-M99-v1-p01-r01/tasks/T01.yaml', './tasks/T01.yaml', 'tasks//T01.yaml', 'tasks\\T01.yaml', 'tasks/../../run-G99-M99-v1-p01-r01/tasks/T01.yaml'):
                mutated = copy.deepcopy(base)
                mutated['input']['documents'][-1]['milestones'][index]['completion_refs'][0]['evidence_paths'] = [run_dir + bad]
                with self.assertRaisesRegex(checker.ContractError, 'Abschlussrun oder ist kein sicherer projektrelativer Pfad'):
                    checker.validate_scenario(mutated['input'])
            for good in ('tasks/T01.yaml', 'tasks/T01/attempt-03.yaml', 'review.yaml'):
                valid = copy.deepcopy(base)
                valid['input']['documents'][-1]['milestones'][index]['completion_refs'][0]['evidence_paths'] = [run_dir + good]
                checker.validate_scenario(valid['input'])
        for path in ('a/./b.md', 'a//b.md', 'a/../../b.md', 'C:/b.md'):
            self.assertFalse(checker.safe_relative(path))
        self.assertTrue(checker.safe_relative('.apm/skills/core-milestone/SKILL.md'))

    def test_rv07_versions_are_positive_integers_not_equal_values(self):
        # Memory-only reproductions of the review: True/1.0 equal 1 but are no version.
        cases = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        base = cases['t08-artifacts-new-structure']['input']
        checker.validate_scenario(copy.deepcopy(base))
        examples = canonical_examples()
        checker.check_example_relations(copy.deepcopy(examples))
        index_pos = next(i for i, d in enumerate(examples) if d['schema'] == 'milestone-index/v1')
        entry_pos = next(i for i, m in enumerate(examples[index_pos]['milestones']) if m['id'] == 'M02')
        dep_pos = next(i for i, d in enumerate(examples) if d['schema'] == 'milestone-definition/v1' and d['id'] == 'M02' and d['dependencies'])
        for bad in (True, 1.0, '1', None, 0, -1):
            with self.subTest(bad=bad):
                scenario = copy.deepcopy(base)
                scenario['documents'][-1]['milestones'][1]['version'] = bad
                with self.assertRaisesRegex(checker.ContractError, 'Indexversion ist keine positive Ganzzahl'):
                    checker.validate_scenario(scenario)
                mutated = copy.deepcopy(examples)
                mutated[index_pos]['milestones'][entry_pos]['version'] = bad
                with self.assertRaisesRegex(checker.ContractError, 'Indexversion ist keine positive Ganzzahl'):
                    checker.check_example_relations(mutated)
                mutated = copy.deepcopy(examples)
                mutated[dep_pos]['dependencies'][0]['version'] = bad
                with self.assertRaisesRegex(checker.ContractError, 'Abhängigkeitsversion ist keine positive Ganzzahl'):
                    checker.check_example_relations(mutated)
                mutated = copy.deepcopy(examples)
                mutated[dep_pos]['version'] = bad
                with self.assertRaisesRegex(checker.ContractError, 'Definitionsversion ist keine positive Ganzzahl'):
                    checker.check_example_relations(mutated)
        # Real index source patched only in memory, as in the review.
        target = ROOT / '.apm/skills/core-milestone/references/milestone-index-format.md'
        original = Path.read_text
        self.assertIn('    version: 1\n', original(target, encoding='utf-8'))
        def injected(value):
            def read(path, *args, **kwargs):
                text = original(path, *args, **kwargs)
                return text.replace('    version: 1\n', '    version: ' + value + '\n') if path == target else text
            return read
        with contextlib.redirect_stdout(io.StringIO()):
            checker.check_group(ROOT, 'milestones')
            for value in ('true', '1.0'):
                with patch.object(Path, 'read_text', injected(value)), self.assertRaisesRegex(checker.ContractError, 'keine positive Ganzzahl'):
                    checker.check_group(ROOT, 'milestones')
        self.assertIn('    version: 1\n', original(target, encoding='utf-8'))
        for value in (1, 2, 10):
            self.assertTrue(checker.positive_int(value))
        for value in (True, False, 1.0, '1', None, 0, -1):
            self.assertFalse(checker.positive_int(value))

    def test_canonical_t02_examples_and_relational_mutations(self):
        documents = canonical_examples()
        self.assertEqual(sorted(d['schema'] for d in documents), ['goal/v1', 'milestone-definition/v1', 'milestone-definition/v1', 'milestone-index/v1'])
        checker.validate_artifacts(documents)
        index = next(d for d in documents if d['schema'] == 'milestone-index/v1')
        # A newer, unselected definition file must not change the selection.
        newer = dict(copy.deepcopy(documents[1]), version=2)
        with_newer = copy.deepcopy(documents) + [newer]
        checker.validate_artifacts(with_newer)
        self.assertEqual({k: v['version'] for k, v in checker.selected_entries(index).items()}, {'M01': 1, 'M02': 1})
        mutations = {
            'Laufzustand': lambda docs: docs[1].update(status='completed'),
            'aktuelle Etappe vor belegtem': lambda docs: docs[3]['milestones'][0].update(completion_refs=[]),
            'falsche Definitionsversion': lambda docs: docs.pop(2),
            'mehrere aktuelle': lambda docs: docs[3]['milestones'][0].update(current=True, current_approval='user-confirmed'),
            'Gesamterfolg': lambda docs: docs[3].update(goal_completion_refs=[dict(goal_path=docs[3]['goal_path'], acceptance_ids=['GAC01'], evidence_paths=['x.yaml'])]),
            'Ersatzplannummer': lambda docs: docs[3]['milestones'][0]['plan_paths'].append(docs[3]['milestones'][0]['plan_paths'][0]),
        }
        for message, mutate in mutations.items():
            docs = copy.deepcopy(documents)
            mutate(docs)
            with self.subTest(message=message), self.assertRaisesRegex(checker.ContractError, message):
                checker.validate_artifacts(docs)

    def test_rv04_design_refs_exist_in_real_sources(self):
        # Inject only in memory; unchanged canonical examples must still pass.
        target = ROOT / '.apm/skills/core-milestone/references/milestone-format.md'
        original = Path.read_text
        def injected(ref):
            def read(path, *args, **kwargs):
                text = original(path, *args, **kwargs)
                return text.replace('schema: milestone-definition/v1\n', 'schema: milestone-definition/v1\ndecision_refs: [' + ref + ']\n') if path == target else text
            return read
        self.assertEqual(original(target, encoding='utf-8').count('schema: milestone-definition/v1\n'), 2)
        with contextlib.redirect_stdout(io.StringIO()):
            checker.check_group(ROOT, 'milestones')
            with patch.object(Path, 'read_text', injected('not-present-design-R004.md')), self.assertRaisesRegex(checker.ContractError, 'Designquelle fehlt'):
                checker.check_group(ROOT, 'milestones')
            with patch.object(Path, 'read_text', injected('../outside.md')), self.assertRaisesRegex(checker.ContractError, 'Designquelle|verlässt Workspace'):
                checker.check_group(ROOT, 'milestones')
            with patch.object(Path, 'read_text', injected('README.md')):
                checker.check_group(ROOT, 'milestones')
        # Illustrative plan/run paths in index examples are no file obligation.
        index = next(d for d in canonical_examples() if d['schema'] == 'milestone-index/v1')
        self.assertFalse((ROOT / index['milestones'][0]['plan_paths'][0]).exists())

    def test_rv04_complete_artifact_set_without_definitions_fails(self):
        documents = canonical_examples()
        docs = [d for d in documents if d['schema'] != 'milestone-definition/v1']
        with self.assertRaisesRegex(checker.ContractError, 'fehlende/falsche Definitionsversion'):
            checker.validate_artifacts(docs)
        with self.assertRaisesRegex(checker.ContractError, 'fehlendes/falsches Ziel'):
            checker.validate_artifacts([d for d in documents if d['schema'] != 'goal/v1'])

    def test_rv01_execute_writes_immutable_attempts_not_legacy(self):
        source = ROOT / '.apm/skills/core-execute/SKILL.md'
        text = source.read_text(encoding='utf-8')
        checker.check_execute_attempts(text)
        shared = (ROOT / '.apm/skills/core-shared/references/artifact-contract.md').read_text(encoding='utf-8')
        self.assertIn('tasks/<task-id>/attempt-<nn>.yaml', shared)
        # Two attempts of one task get distinct sequential paths; the first stays.
        first, second = (checker.NEW_ATTEMPT.replace('<run-id>', 'R01').replace('<task-id>', 'T01').replace('<nn>', n) for n in ('01', '02'))
        checker.validate_scenario(dict(kind='result_owner', writer='core-execute', agent='docs-curator', scope=[], explicit_result_exception=False, attempt_paths=[first, second]))
        with self.assertRaisesRegex(checker.ContractError, 'überschriebener Taskversuch'):
            checker.validate_scenario(dict(kind='result_owner', writer='core-execute', agent='docs-curator', scope=[], explicit_result_exception=False, attempt_paths=[first, first]))
        mutations = (
            text.replace(checker.NEW_ATTEMPT, checker.LEGACY_ATTEMPT, 1),
            text.replace('weder neu beschrieben', 'neu beschrieben'),
            text.replace('Ein Retry erhält die nächste Kennung und überschreibt oder deutet keinen früheren Versuch um.', 'Ein Retry ersetzt den vorigen Versuch.'),
        )
        for mutated in mutations:
            self.assertNotEqual(mutated, text)
            with self.subTest(mutated=mutated[:40]), self.assertRaises(checker.ContractError):
                checker.check_execute_attempts(mutated)

    def test_rv05_catalog_reads_but_never_outputs_legacy(self):
        catalog = checker.load_yaml((ROOT / '.apm/skills/core-shared/assets/workflow-catalog.yaml').read_text(encoding='utf-8'))
        checker.validate_catalog(catalog)
        milestone = next(w for w in catalog['workflows'] if w['id'] == 'core-milestone')
        self.assertIn('milestone/v1', milestone['input_schemas'])
        self.assertNotIn('milestone/v1', milestone['output_schemas'])
        bad = copy.deepcopy(catalog)
        next(w for w in bad['workflows'] if w['id'] == 'core-milestone')['output_schemas'].append('milestone/v1')
        with self.assertRaisesRegex(checker.ContractError, 'Legacy milestone/v1 als Ausgabe'):
            checker.validate_catalog(bad)
        bad = copy.deepcopy(catalog)
        next(w for w in bad['workflows'] if w['id'] == 'core-milestone')['input_schemas'].remove('milestone/v1')
        with self.assertRaisesRegex(checker.ContractError, 'nicht mehr lesbar'):
            checker.validate_catalog(bad)

    def test_coverage_registry_fails_closed(self):
        fixture = json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())
        checker.check_coverage(fixture)
        for key in ('K1-read-only-ergebnisbesitz', 'run-id-resume-review-reparatur', 'nicht-ausgewaehlte-neuere-datei'):
            bad = copy.deepcopy(fixture)
            del bad['coverage'][key]
            with self.subTest(key=key), self.assertRaisesRegex(checker.ContractError, 'Regressionsabdeckung fehlt'):
                checker.check_coverage(bad)
        bad = copy.deepcopy(fixture)
        bad['coverage']['resume'] = dict(cases=['t08-progression-resume-review-repair'])
        with self.assertRaisesRegex(checker.ContractError, 'keine Negativregression'):
            checker.check_coverage(bad)
        bad['coverage']['resume'] = dict(cases=['does-not-exist'])
        with self.assertRaisesRegex(checker.ContractError, 'unbekannte Szenario-ID'):
            checker.check_coverage(bad)

    def test_run_identity_and_plan_progression(self):
        run = '.agentic-workflow/runs/run-G01-M02-v1-p%s-r%s/state.yaml'
        plan = lambda p: dict(action='plan', plan_path='.agentic-workflow/plans/plan-G01-M02-v1-p%s.md' % p)
        same = lambda action, p='01', r='01': dict(action=action, run_path=run % (p, r), previous_run_path=run % (p, r))
        data = dict(kind='progression', goal_id='G01', milestone_id='M02', version=1, events=[plan('01'), dict(action='new', run_path=run % ('01', '01')), same('resume'), same('review'), same('repair'), plan('02'), dict(action='new', run_path=run % ('02', '01')), same('repair', '02')])
        checker.validate_scenario(data)
        # Repair rounds count per Run-ID; resume after a replacement plan is blocked.
        for events, message in (
            (data['events'][:5] + [same('repair')] * 2, 'dritte'),
            (data['events'][:7] + [same('resume')], 'abgelöstem Plan'),
            (data['events'][:2] + [dict(same('resume'), run_path=run % ('01', '02'))], 'Run-ID'),
            (data['events'][:5] + [plan('01')], 'Ersatzplannummer'),
            ([plan('1')], 'Namensschema'),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(checker.ContractError, message):
                checker.validate_scenario(dict(data, events=events))

    def test_ownership_is_a_relation(self):
        schemas = ['goal/v1', 'milestone-definition/v1', 'milestone-index/v1', 'plan/v1', 'review/v1']
        owners = ['core-milestone'] * 3 + ['core-plan', 'core-review']
        table = '\n'.join('| info | ' + s + ' | ' + o + ' |' for s, o in zip(schemas, owners))
        checker.check_owners(table)
        with self.assertRaises(checker.ContractError):
            checker.check_owners(table.replace('| core-plan |', '| core-execute |'))
        with self.assertRaises(checker.ContractError):
            checker.check_owners(' '.join(schemas + owners))

    def test_read_only_guard(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-', dir='/tmp/opencode') as directory:
            path = Path(directory) / 'source.md'
            path.write_text('original')
            checker.guarded_run([path], lambda: path.read_text())
            with self.assertRaisesRegex(checker.ContractError, 'Read-only-Guard'):
                checker.guarded_run([path], lambda: path.write_text('violated'))
            missing = Path(directory) / 'missing.md'
            with self.assertRaisesRegex(checker.ContractError, 'Read-only-Guard'):
                checker.guarded_run([missing], lambda: missing.write_text('created'))

    def test_references_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            source = root / 'source.md'
            target = root / 'target.md'
            target.write_text('reference')
            checker.check_links(root, source, '[ok](target.md) [remote](https://example.invalid)')
            for link in ('[bad](missing.md)', '[escape](../outside.md)', '[glob](*.md)'):
                with self.assertRaises(checker.ContractError):
                    checker.check_links(root, source, link)
            with self.assertRaises(checker.ContractError):
                checker.local_path(root, '../outside.md')

    def test_setup_source_rejects_old_installer_and_unrelated_keywords(self):
        front = {'description': 'Prüft vorhandene MCP-Provider read-only; keine Einrichtung.'}
        text = 'Kein Secretzugriff; Secrets werden nicht gesucht.\n1. Prüfe den Provider read-only.'
        checker.check_setup_source(front, text)
        with self.assertRaisesRegex(checker.ContractError, 'Einrichtung statt'):
            checker.check_setup_source({'description': 'Richtet Provider ein und materialisiert bestätigte Einträge.'}, text)
        for instruction in ('1. Materialisiere bestätigte Einträge.', '1. Installiere den Provider.', '1. Lies apm.lock.yaml.'):
            with self.subTest(instruction=instruction), self.assertRaises(checker.ContractError):
                checker.check_setup_source(front, text + '\n' + instruction)

    def test_catalog_edges_are_bidirectional_and_complete(self):
        edges = [('core-plan', 'core-execute'), ('core-execute', 'core-review'), ('core-execute', 'core-milestone'), ('core-milestone', 'core-plan'), ('core-milestone', 'core-handoff')]
        ids = ['core-plan', 'core-execute', 'core-review', 'core-brainstorm', 'core-milestone', 'core-handoff']
        workflows = [dict(id=i, successors=[b for a, b in edges if a == i], predecessors=[a for a, b in edges if b == i], fresh_context_on_entry=i in ('core-execute', 'core-review'), input_schemas=['milestone/v1'] if i == 'core-milestone' else [], output_schemas=[]) for i in ids]
        catalog = dict(catalog_version=1, max_automatic_review_repair_rounds=2, workflows=workflows, transitions=[dict(**{'from': a, 'to': b}, outcome='conditional') for a, b in edges], known_agent_ids=['backend-engineer'], known_tool_ids=['gortex'])
        checker.validate_catalog(catalog)
        bad = copy.deepcopy(catalog)
        bad['workflows'][4]['predecessors'] = []
        with self.assertRaisesRegex(checker.ContractError, 'predecessors'):
            checker.validate_catalog(bad)
        bad = copy.deepcopy(catalog)
        bad['transitions'].pop()
        with self.assertRaisesRegex(checker.ContractError, 'Workflowübergänge'):
            checker.validate_catalog(bad)

    def test_staged_targetsets(self):
        for group, task in checker.GROUP_TASK.items():
            paths = checker.targets(ROOT, group)
            self.assertTrue(paths)
            self.assertTrue(all(path.is_relative_to(ROOT) for path in paths))
            if group == 'milestones':
                self.assertEqual(len(paths), 3)
                self.assertFalse(any('core-shared' in str(path) for path in paths))
            if group == 'setup':
                self.assertFalse(any('README' in str(path) for path in paths))
        print('STAGING: sechs getrennte explizite Targetsets aus bestätigtem Plan')

    def test_all_cli_groups_and_authoring_switch(self):
        for group in checker.GROUPS:
            with self.subTest(group=group), patch.object(checker, 'check_group') as checked, patch.object(checker, 'selftest') as tested:
                self.assertEqual(checker.main(['--group', group]), 0)
                if group == 'all':
                    self.assertEqual([c.args[1] for c in checked.call_args_list], list(checker.GROUP_TASK))
                elif group == 'selftest':
                    tested.assert_called_once()
                else:
                    checked.assert_called_once_with(ROOT, group, False)
        with patch.object(checker, 'check_group') as checked:
            self.assertEqual(checker.main(['--group', 'shared', '--authoring']), 0)
            checked.assert_called_once_with(ROOT, 'shared', True)
        with patch.object(checker, 'check_group', side_effect=checker.ContractError('missing prerequisite')), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(checker.main(['--group', 'all']), 1)
            self.assertIn('docs: missing prerequisite', output.getvalue())

    def test_missing_authoring_tools_fail(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            path = root / 'target.md'
            path.write_text('read-only')
            with self.assertRaisesRegex(checker.ContractError, 'Authoringtool fehlt'), patch.object(checker.subprocess, 'run') as run:
                checker.authoring(root, [path], root / 'absent-tools')
            run.assert_not_called()
            self.assertEqual(path.read_text(), 'read-only')

    def test_authoring_exact_paths_read_only_and_observation(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            skill = root / 'core-example'
            skill.mkdir()
            path = skill / 'SKILL.md'
            path.write_text('---\nname: core-example\ndescription: fixture\n---\n')
            tools = root / 'tools'
            for relative in ('skill-creator/scripts/quick_validate.py', 'context-debloater/scripts/analyze_markdown.py', 'context-debloater/scripts/consolidate_duplicates.py'):
                tool = tools / relative
                tool.parent.mkdir(parents=True, exist_ok=True)
                tool.write_text('# test double, never executed')
            calls = []
            def run(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 0, 'Skill is valid!' if kwargs['input'] is None else '{"status":"ok"}', '')
            with patch.object(checker.subprocess, 'run', side_effect=run):
                checker.authoring(root, [path], tools)
            self.assertEqual(len(calls), 3)
            for command, kwargs in calls:
                self.assertEqual(command[1], '-B')
                self.assertEqual(kwargs['env']['PYTHONDONTWRITEBYTECODE'], '1')
                self.assertFalse(any(flag in command for flag in ('--apply', '--fix')))
                if kwargs['input'] is not None:
                    payload = json.loads(kwargs['input'])
                    self.assertEqual(payload, {'workspace': str(skill), 'targets': [str(path)]})
            with patch.object(checker.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{"status":"error"}', '')):
                with self.assertRaises(checker.ContractError):
                    checker.authoring(root, [path], tools)
            def malicious_run(command, **kwargs):
                path.write_text('unexpected mutation')
                return subprocess.CompletedProcess(command, 0, 'Skill is valid!' if kwargs['input'] is None else '{"status":"ok"}', '')
            with patch.object(checker.subprocess, 'run', side_effect=malicious_run), self.assertRaisesRegex(checker.ContractError, 'Read-only-Guard'):
                checker.authoring(root, [path], tools)

    def test_real_cli_repository_groups_report_evidence(self):
        paths = list(dict.fromkeys(p for g in checker.GROUP_TASK for p in checker.targets(ROOT, g)))
        before = checker.snapshot(paths)
        observations = []
        for group in (*checker.GROUP_TASK, 'all'):
            command = [sys.executable, '-B', str(ROOT / 'scripts/check_core_contracts.py'), '--group', group]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
            with self.subTest(group=group):
                self.assertIn(result.returncode, (0, 1))
                self.assertNotIn('Traceback', result.stderr)
                if result.returncode == 0:
                    self.assertIn('PASS ' + (group if group != 'all' else 'docs'), result.stdout)
                    self.assertIn('SCENARIOS', result.stdout)
                else:
                    self.assertIn('FAIL:', result.stderr)
                    self.assertTrue(result.stderr.strip().removeprefix('FAIL:').strip())
            observations.append(group + '=' + ('pass' if result.returncode == 0 else 'sichtbare Vertrags-/Voraussetzungslücke'))
        self.assertEqual(checker.snapshot(paths), before)
        print('REPOSITORY CLI (keine Integrationsabnahme):', '; '.join(observations))

    def test_real_cli_missing_phase_visible_no_source_change(self):
        command = [sys.executable, '-B', str(ROOT / 'scripts/check_core_contracts.py'), '--group', 'milestones', '--authoring']
        paths = checker.targets(ROOT, 'milestones')
        before = checker.snapshot(paths)
        # T01 precedes T02. Do not require these future sources to be integrated.
        if any(not path.is_file() for path in paths):
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Phasenvoraussetzung fehlt', result.stderr)
        self.assertEqual(checker.snapshot(paths), before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
