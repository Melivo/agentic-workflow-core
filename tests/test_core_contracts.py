"""Positive and deliberately violated fixtures, offline and without source writes."""
import sys
sys.dont_write_bytecode = True
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import re
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
        for kind in ('marker', 'handoff', 'result_owner', 'provider', 'version', 'completion', 'name', 'graph', 'progression', 'selection', 'prompt', 'write_sequence', 'goal_change', 'artifacts', 'docs', 'authorization', 'safety', 'delegation'):
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

    def test_completion_original_sources_and_prior_runs(self):
        index = examples_fixture()[2]
        ref = completion_ref()
        originals = ['.apm/skills/core-milestone/SKILL.md',
                     '.agentic-workflow/runs/run-G01-M02-v1-p01-r01/tasks/T01/attempt-01.yaml']
        ref['evidence_paths'].extend(originals)
        entry = index['milestones'][0]
        entry.update(plan_paths=[ref['plan_path']], run_paths=[ref['run_path']], completion_refs=[ref])
        checker.check_index(index)
        # Historical originals still need explicit revalidation for the new version.
        reused = completion_ref(version=1)
        reused.update(version=2, definition_path=entry['definition_path'])
        reused['evidence_paths'].extend(originals)
        entry['completion_refs'] = [reused]
        with self.assertRaisesRegex(checker.ContractError, 'revalidation_path fehlt'):
            checker.check_index(index)
        reused['revalidation_path'] = ref['evidence_paths'][0]
        checker.check_index(index)

    def test_completion_original_paths_do_not_relax_bindings(self):
        index = examples_fixture()[2]
        ref = completion_ref()
        ref['evidence_paths'].append('.apm/skills/core-milestone/SKILL.md')
        index['milestones'][0].update(plan_paths=[ref['plan_path']], run_paths=[ref['run_path']], completion_refs=[ref])
        for field in ('version', 'definition_path', 'acceptance_ids', 'plan_path', 'run_path', 'review_path', 'evidence_paths'):
            bad = copy.deepcopy(index)
            del bad['milestones'][0]['completion_refs'][0][field]
            with self.subTest(missing=field), self.assertRaisesRegex(checker.ContractError, 'Abschluss ohne Originalnachweise/Kriterien'):
                checker.check_index(bad)
        for paths in ([], None, 'source.md', [''], [None], ['/source.md'], ['../source.md'],
                      ['./source.md'], ['src//source.md'], ['src/../source.md'],
                      ['C:/source.md'], ['src\\source.md'], ref['evidence_paths'] + ['../bad.md']):
            bad = copy.deepcopy(index)
            bad['milestones'][0]['completion_refs'][0]['evidence_paths'] = paths
            with self.subTest(paths=paths), self.assertRaises(checker.ContractError):
                checker.check_index(bad)
        mutations = [
            ('version', 1, 'historischer Abschluss'),
            ('definition_path', '.agentic-workflow/goals/G01/milestones/M02-v1.yaml', 'historischer Abschluss'),
            ('plan_path', completion_ref(plan='p02')['plan_path'], 'Abschlussrun gehört nicht'),
            ('run_path', completion_ref(plan='p02')['run_path'], 'Abschlussrun gehört nicht'),
            ('review_path', completion_ref(run='r02')['review_path'], 'Review gehört nicht'),
            ('revalidation_path', ref['evidence_paths'][0], 'Revalidierung ohne Versionswechsel'),
        ]
        for field, value, message in mutations:
            bad = copy.deepcopy(index)
            bad['milestones'][0]['completion_refs'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(checker.ContractError, message):
                checker.check_index(bad)
        for field in ('plan_paths', 'run_paths'):
            bad = copy.deepcopy(index)
            bad['milestones'][0][field] = []
            with self.subTest(unlinked=field), self.assertRaises(checker.ContractError):
                checker.check_index(bad)

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
                with self.assertRaisesRegex(checker.ContractError, 'Evidenz ist kein sicherer projektrelativer Pfad'):
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
        # Illustrative plan/run paths in index examples are no file obligation:
        # the index check must pass whether those files are absent or present, independent of ROOT.
        index = next(d for d in canonical_examples() if d['schema'] == 'milestone-index/v1')
        illustrative = {p for m in index['milestones'] for p in m['plan_paths'] + m['run_paths']}
        self.assertTrue(illustrative)
        real_exists = Path.exists
        for present in (False, True):
            seen = []
            def exists(path, *args, **kwargs):
                if any(str(path).endswith(p) for p in illustrative):
                    seen.append(str(path))
                    return present
                return real_exists(path, *args, **kwargs)
            with self.subTest(present=present), patch.object(Path, 'exists', exists):
                self.assertEqual({p for p in illustrative if (ROOT / p).exists()}, illustrative if present else set())
                checker.check_format('milestone-index/v1', copy.deepcopy(index))
                self.assertTrue(seen)

    def test_rv04_complete_artifact_set_without_definitions_fails(self):
        documents = canonical_examples()
        docs = [d for d in documents if d['schema'] != 'milestone-definition/v1']
        with self.assertRaisesRegex(checker.ContractError, 'fehlende/falsche Definitionsversion'):
            checker.validate_artifacts(docs)
        with self.assertRaisesRegex(checker.ContractError, 'fehlendes/falsches Ziel'):
            checker.validate_artifacts([d for d in documents if d['schema'] != 'goal/v1'])

    def test_execute_identifies_session_plan_without_reconfirmation(self):
        text = (ROOT / ".apm/skills/core-execute/SKILL.md").read_text(encoding="utf-8")
        activation = text.split("## Aktivierung und Eingaben", 1)[1].split("## Verbindliche Verträge", 1)[0]
        # Static instruction regression, not evidence of live model behavior.
        for requirement in (
            "Plan- und Direktmodus sind exklusiv",
            "ein Direktlauf wird ausschließlich über `mode: direct` und `request_path` wiederaufgenommen",
            "Legacy-Zustände mit `plan_path` ohne `mode` bleiben Planmodus",
            "aktuell vom Benutzer genannten Pfad",
            "Kontext der laufenden Sitzung eindeutig zugeordneten aktiven Planpfad",
            "auch wenn du ihn selbst erstellt hast",
            "frisch gelesenes `state.yaml` den `plan_path`",
            "verlange weder die erneute Nennung des Pfads noch eine Bestätigungsformel",
            "nicht das Alter der Sitzung",
            "Fehlt im Planmodus eine eindeutige Zuordnung",
            "fehlende/verlorene Planartefakte werden nicht in Direktmodus umgedeutet",
            "Ein aktiver gebundener Plan, eine gepinnte Etappe oder Milestone-Arbeit bleibt im Planweg",
            "mehrere Pläne beziehungsweise Runs",
            "frage gezielt nach dem Plan oder Run",
            "Suche niemals nach dem vermeintlich neuesten Plan",
            "nicht anhand von Dateidatum, Versionsnummer oder Provider-Memory",
            "`status: Confirmed` nicht validierbar, stoppe Produktmutationen",
            "Route die Erweiterung zu `core-plan`",
            "nur den bestätigten Ersatzplan",
            "den exakt identifizierten Plan",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, activation)
        self.assertNotIn("expliziten Pfad", activation)
        self.assertIn("eindeutig identifizierten bestätigten plan/v1", text.split("---", 2)[1])
        self.assertIn("Ein Chatverlauf oder Provider-Memory ersetzt kein Run-Artefakt.", text)
        shared = (ROOT / ".apm/skills/core-shared/references/workflow-contract.md").read_text(encoding="utf-8")
        self.assertIn("../../core-execute/SKILL.md#aktivierung-und-eingaben", shared)
        self.assertIn("ersetzt aber weder frisch gelesene Artefakte noch Freigabe, Runzustand oder Evidenz", shared)

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
        bad = copy.deepcopy(catalog)
        bad['max_automatic_review_repair_rounds'] = 2
        with self.assertRaisesRegex(checker.ContractError, 'Reparaturlimit'):
            checker.validate_catalog(bad)
        bad = copy.deepcopy(catalog)
        next(w for w in bad['workflows'] if w['id'] == 'core-execute')['max_automatic_review_repair_rounds'] = 2
        with self.assertRaisesRegex(checker.ContractError, 'Reparaturlimit'):
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
        repair = lambda p='01', r='01', b='': dict(action='repair', run_path=run % (p, r), previous_run_path=run % (p, r), basis=b)
        data = dict(kind='progression', goal_id='G01', milestone_id='M02', version=1, events=[plan('01'), dict(action='new', run_path=run % ('01', '01')), same('resume'), same('review'), repair(b='neue Evidenz A'), plan('02'), dict(action='new', run_path=run % ('02', '01')), repair('02', '01', 'Hypothese B')])
        checker.validate_scenario(data)
        # More than two justified, distinct attempts are allowed; unjustified or
        # repeated repairs fail closed. Resume after a replacement plan is blocked.
        checker.validate_scenario(dict(data, events=data['events'][:5] + [repair(b='Hypothese B'), repair(b='Hypothese C')]))
        for events, message in (
            (data['events'][:5] + [same('repair')], 'Reparatur ohne neue Erkenntnis'),
            (data['events'][:5] + [repair(b='neue Evidenz A')], 'Reparatur wiederholt dieselbe Begründung'),
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
        with tempfile.TemporaryDirectory(prefix='core-contract-') as directory:
            path = Path(directory) / 'source.md'
            path.write_text('original')
            checker.guarded_run([path], lambda: path.read_text())
            with self.assertRaisesRegex(checker.ContractError, 'Read-only-Guard'):
                checker.guarded_run([path], lambda: path.write_text('violated'))
            missing = Path(directory) / 'missing.md'
            with self.assertRaisesRegex(checker.ContractError, 'Read-only-Guard'):
                checker.guarded_run([missing], lambda: missing.write_text('created'))

    def test_references_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-') as directory:
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

    def test_init_project_checks_provider_runtime_before_audit(self):
        # Static instruction regression, not a live agent or installation test.
        skill = ROOT / '.apm/skills/core-init-project/SKILL.md'
        text = skill.read_text(encoding='utf-8')
        runtime = text.split('#### Provider-Laufzeit vorbereiten', 1)[1].split('#### Provideraudit durchführen', 1)[0]
        self.assertIn('references/provider-setup.md#python-runtime', runtime)
        self.assertIn('verifizierten absoluten Interpreterpfad für alle Audit- und ausgewählten Apply-Aufrufe', runtime)
        self.assertIn('Bei erneutem Init wird er neu geprüft', runtime)
        self.assertIn('führe das Audit-Skript nicht aus', runtime)
        # One internal source owns the complete runtime procedure.
        provider = (ROOT / '.apm/skills/core-init-project/references/provider-setup.md').read_text(encoding='utf-8')
        canonical_runtime = provider.split('## Python Runtime', 1)[1].split('## Workflow', 1)[0]
        self.assertIn('[Python Runtime](#python-runtime)', provider)
        for requirement in (
            '[REQUIREMENTS.md](../REQUIREMENTS.md)',
            '[scripts/requirements.txt](../scripts/requirements.txt)',
            'besitzen das',
            'from ruamel.yaml import YAML, YAMLError',
            "version('ruamel.yaml')",
            'Ein erfolgreicher Import allein',
            'PyYAML ersetzt `ruamel.yaml` nicht',
            'frage einmal gemeinsam mit der Aufrufauswahl',
            'Netzwerk-/Dateiwirkungen und Entfernungspfad',
            'Eine konkrete Freigabe, die genau diese Laufzeiteinrichtung benannt',
            '"<env-python>" -m pip install -r',
            'kein System-, Global- oder `--user`-pip',
            'keine App-Abhängigkeitsänderung',
            'Eine Serena-Provideraktion allein ist keine',
            'ausgegebene absolute `sys.executable`',
            'stoppe beim ersten erfolgreichen',
            'MISE_AUTO_INSTALL=0 MISE_EXEC_AUTO_INSTALL=0 mise exec --',
            'tatsächlichen Runner',
            'bleibt das Audit ungestartet',
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, canonical_runtime)
        self.assertIn('Readiness-Preflight löst keinen Vollscan und keine Installation aus', text)
        self.assertIn('**completed:** Provider-Laufzeit und Preflight sind belegt', text)
        self.assertIn('**partial:** Der Harness oder Block ist gültig, aber die Provider-Laufzeit', text)

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
        edges = [('core-plan', 'core-review'), ('core-review', 'core-plan'), ('core-plan', 'core-execute'), ('core-execute', 'core-review'), ('core-execute', 'core-plan'), ('core-execute', 'core-milestone'), ('core-milestone', 'core-plan'), ('core-milestone', 'core-handoff')]
        ids = ['core-plan', 'core-execute', 'core-review', 'core-brainstorm', 'core-milestone', 'core-handoff']
        workflows = [dict(id=i, successors=[b for a, b in edges if a == i], predecessors=[a for a, b in edges if b == i], fresh_context_on_entry=i in ('core-execute', 'core-review'), input_schemas={'core-milestone': ['milestone/v1'], 'core-execute': ['text', 'plan/v1']}.get(i, []), output_schemas=['text'] if i == 'core-review' else []) for i in ids]
        catalog = dict(catalog_version=1, workflows=workflows, transitions=[dict(**{'from': a, 'to': b}, outcome='conditional') for a, b in edges], known_agent_ids=['backend-engineer'], known_tool_ids=['gortex'])
        checker.validate_catalog(catalog)
        bad = copy.deepcopy(catalog)
        bad['workflows'][4]['predecessors'] = []
        with self.assertRaisesRegex(checker.ContractError, 'predecessors'):
            checker.validate_catalog(bad)
        bad = copy.deepcopy(catalog)
        bad['transitions'].pop()
        with self.assertRaisesRegex(checker.ContractError, 'Workflowübergänge'):
            checker.validate_catalog(bad)
        bad = copy.deepcopy(catalog)
        bad['max_automatic_review_repair_rounds'] = 2
        with self.assertRaisesRegex(checker.ContractError, 'Reparaturlimit'):
            checker.validate_catalog(bad)

    def test_scope_guardrail_clauses_accept_minimal_work_and_reject_violations(self):
        # Fixture sentences per clause; text matches show contract wording, not live model compliance.
        cases = {
            'Dateiscope ist keine Funktionsfreigabe': ('Ein Dateiscope autorisiert keine neuen Verantwortlichkeiten.', 'Ein neuer Harness im erlaubten Verzeichnis ist durch den Dateiscope gedeckt.'),
            'kumulativer Scope gegen Originalbezug': ('Ersatzpläne prüfen den kumulativen Scope gegen den ursprünglichen Auftrag.', 'Ersatzpläne prüfen nur den direkten Vorgänger.'),
            'Vereinfachungsstopp': ('Ohne neue Erkenntnis oder neu belegtes fachliches Ergebnis stoppt der Ersatzplanzyklus früh.', 'Jeder Ersatzplan startet automatisch den nächsten.'),
            'Aufwand allein keine Rückfrage': ('Mehr Arbeitsaufwand begründet allein keine erneute Rückfrage.', 'Mehr Aufwand erfordert stets eine neue Freigabe.'),
            'unklare Wirkung stoppt': ('Materiell unklare oder ungedeckte Wirkung stoppt.', 'Ungedeckte Wirkung wird toleriert.'),
            'monetäre Kosten brauchen Zustimmung': ('Zusätzliche monetäre Kosten brauchen vorherige Zustimmung.', 'Geringe KI-Kosten sind automatisch gedeckt.'),
            'evidenzbasierte Fortsetzung statt starrer Rundenzahl': ('Der nächste Versuch benennt neue Erkenntnis oder eine unterscheidbare prüfbare Hypothese, kleinste Prüfung, realistische Reparierbarkeit, Aufwand/Risiko/Restnutzen und sichere Abbruchbedingungen.', 'Nach der zweiten Runde stoppt der Lauf starr.'),
            'Planreviewfortsetzung evidenzbasiert': ('Ohne tragfähigen Korrekturansatz folgt die Nutzerentscheidung statt weiterer blinder Korrektur.', 'Ohne Korrekturansatz läuft die Schleife weiter.'),
            'entscheidende Sicherheitsannahme': ('Benenne die entscheidende Sicherheitsannahme der Änderung.', 'Sicherheitsannahmen bleiben implizit.'),
            'indirekte Folgen jenseits Aufrufer': ('Prüfe indirekte Folgen jenseits direkter Aufrufer.', 'Nur direkte Aufrufer zählen.'),
            'Evidenzstärke klassifizieren': ('Trenne die Evidenzstärke in belegt, widerlegt oder offen.', 'Alle Risiken gelten gleich.'),
            'delegierte Testbedienung beim Agenten': ('Delegierte Sandbox- und Testbedienung bleibt beim Agenten.', 'Delegierte Tests bedient wieder der Nutzer.'),
            'keine unbestätigte persönliche Wiederholung': ('Eine persönliche Wiederholung erfolgt nur nach bestätigter Anforderung.', 'Der Nutzer wiederholt jeden Test persönlich.'),
            'keine neue Startformel': ('Bestehende Freigaben bleiben erhalten, ohne neue Startformel und ohne automatische Folgeetappe.', 'Jede Sitzung verlangt eine neue Startformel.'),
            'keine Zeitbudget- oder Bereitschaftsschleifen': ('Es entstehen keine neuen Zeitbudget- oder Bereitschaftsschleifenregeln.', 'Jeder Schritt wartet auf Bereitschaftsbestätigung.'),
            'evidenzbasierte Review-Reparatur': ('Starte die nächste automatische `execute ↔ review`-Reparatur nur gemäß evidenzbasierte Fortsetzung.', 'Die dritte automatische Runde ist stets verboten.'),
            'Umbenennung setzt nicht zurück': ('Eine Umbenennung des Findings setzt die Zählung nicht zurück.', 'Ein neuer Findingname beginnt eine neue Zählung.'),
            'Planreview ohne Run': ('Das Planreview erzeugt keinen Run.', 'Das Planreview legt einen Run mit review.yaml an.'),
            'Planreview-pass ist keine Bestätigung': ('Ein Planreview-pass bedeutet nur bestätigungsfähig, nicht vom Nutzer bestätigt.', 'Ein Planreview-pass startet die Ausführung.'),
            'schmale Planreview-Dispatchausnahme': ('Ausschließlich für das Planreview darf core-plan einen qa-reviewer beauftragen.', 'core-plan darf Implementierungsagenten und einen qa-reviewer beauftragen.'),
            'Legacy-Kompatibilitätsprüfung': ('Für Runs ohne historisches Planreview gilt eine Kompatibilitätsprüfung.', 'Fehlt das Planreview, wird es rückwirkend als bestanden eingetragen.'),
            'Bloat verwerfen statt ausbauen': ('Ist Bloat belegt, empfiehl dessen Verwerfen.', 'Ist ein Zusatzfeature unnötig, empfiehl mehr Tests und Härtung.'),
            'Standard vor unbegründeter Eigenentwicklung': ('Standardlösung plus kleiner Regressionstest genügt; eine Eigenentwicklung braucht eine belegte Lücke.', 'Ein eigener Runner ist technisch attraktiver als der vorhandene Standard.'),
            'kein präventiver Zusatz': ('Notwendige Voraussetzungen sind zulässig, aber keine präventiven Optimierungen.', 'Zur Zukunftssicherheit ergänzen wir präventiv ein Cache-Framework.'),
            'übernommene Voraussetzung neu begründen': ('Übernommene technische Voraussetzungen werden neu begründet, sobald sie Blocker erzeugen.', 'Der Ersatzplan übernimmt den Runner als Nutzerpflicht.'),
            'Vereinfachen statt kompensieren': ('Unnötige Komplexität wird entfernt, nicht durch weitere Mechanismen ausgeglichen.', 'Gegen den selbst erzeugten Blocker bauen wir ein weiteres Gate.'),
            # Behavior requirements: plan scenarios 1-8 as fixture sentences, not evidence of agent compliance.
            'Verhalten getrennt von Lösung': ('Der Plan beschreibt beobachtbares Verhalten samt Fehlerfällen getrennt von technischen Entscheidungen.', 'Der Plan beschreibt die Datenbanktabellen als Anforderung.'),
            'Agentenpräferenz keine Nutzeranforderung': ('Die vom Agenten vorgeschlagene Datenbank ist eine Agentenpräferenz und wird nicht zur Nutzeranforderung.', 'Der Agent schlägt eine Datenbank vor; sie ist damit Nutzer-Muss.'),
            'Nutzerconstraint bleibt verbindlich': ('Schreibt der Nutzer die Datenbank vor, bleiben bestätigte technische Nutzerconstraints verbindlich.', 'Der Agent ersetzt die vorgeschriebene Datenbank durch eine bessere Wahl.'),
            'schlanker Kleinfix': ('Ein Kleinfix nennt nur Fehler, erwartetes Ergebnis und Regressionstest.', 'Auch ein Kleinfix braucht eine eigene Verhaltensspezifikation.'),
            'vollständige Originalabdeckung': ('Jede ursprüngliche Anforderung samt Fehlerfall führt zu Task und Check.', 'Alle Tasks haben grüne Checks.'),
            'grüne Eigenkriterien genügen nicht': ('Grüne selbst gewählte Kriterien genügen nicht, solange ein ursprünglicher Fehlerfall ungedeckt ist.', 'Alle Tasktests sind grün, also ist der Auftrag erfüllt.'),
            'keine ungefragten Zusätze': ('Unbegründete Zusätze entfallen, auch in Spezifikationsprosa.', 'Die Spezifikationsprosa ergänzt ein ungefragtes Exportfeature.'),
            'Abdeckung ohne neue Felder': ('Dafür gibt es keine zusätzlichen YAML-Felder.', 'Jeder Task erhält ein Feld requirement_refs.'),
            'Verhaltensänderung über Ersatzplanung': ('Ändert sich bestätigtes Verhalten, nennt der Ersatzplan Vorher/Nachher.', 'Eine neue Anforderung wird still in den bestätigten Plan editiert.'),
            'technische Alternative ohne neue Freigabe': ('Eine technische Alternative ohne Verhaltensänderung ist keine neue Nutzeranforderung.', 'Jede andere Bibliothek braucht eine neue Planfreigabe.'),
            'Plan trennt Anforderung und Lösung': ('Trenne Verhalten, Fehlergrenzen und Anforderungsherkunft von technischen Entscheidungen.', 'Übernimm die Lösung des Agenten als Anforderung.'),
            'Plan prüft Originalabdeckung': ('Alle ursprünglichen Anforderungen sind gedeckt, und unbegründete Zusätze fehlen.', 'Jeder Task hat mindestens einen Check.'),
        }
        policies = {label: pattern for group in ('shared', 'workflows') for pattern, label in checker.POLICIES[group]}
        self.assertLessEqual(set(cases), set(policies))
        for label, (allowed, violated) in cases.items():
            with self.subTest(label=label):
                self.assertRegex(allowed, '(?i)' + policies[label])
                self.assertNotRegex(violated, '(?i)' + policies[label])
        catalog = checker.load_yaml((ROOT / '.apm/skills/core-shared/assets/workflow-catalog.yaml').read_text(encoding='utf-8'))
        checker.validate_catalog(catalog)
        bad = copy.deepcopy(catalog)
        bad['transitions'] = [t for t in bad['transitions'] if (t['from'], t['to']) != ('core-plan', 'core-review')]
        with self.assertRaisesRegex(checker.ContractError, 'Planreviewübergang'):
            checker.validate_catalog(bad)

    def test_scope_guardrail_mutations_of_canonical_clauses_fail(self):
        # Controlled in-memory removal of canonical workflow-contract bullets; sources stay untouched.
        contract = ROOT / '.apm/skills/core-shared/references/workflow-contract.md'
        original_read = Path.read_text
        mutations = {'Kleinste hinreichende Lösung': 'Standard vor unbegründeter Eigenentwicklung|kein präventiver Zusatz', 'Keine vererbten Anforderungen': 'übernommene Voraussetzung neu begründen', 'Vereinfachen statt kompensieren': 'Vereinfachen statt kompensieren',
                     'Anforderung und Lösung trennen': 'Verhalten getrennt von Lösung', 'Vollständige Originalabdeckung': 'vollständige Originalabdeckung', 'Verhaltensänderung': 'Verhaltensänderung über Ersatzplanung'}
        for heading, label in mutations.items():
            text, count = re.subn(r'^- \*\*' + re.escape(heading) + r':\*\*.*\n', '', original_read(contract, encoding='utf-8'), flags=re.M)
            self.assertEqual(count, 1)
            def read_text(path, *args, _text=text, **kwargs):
                return _text if Path(path) == contract else original_read(path, *args, **kwargs)
            with self.subTest(heading=heading), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                checker.check_group(ROOT, 'shared')
        # core-plan keeps only short references; removing them fails the workflows group.
        plan = ROOT / '.apm/skills/core-plan/SKILL.md'
        for pattern, label in ((r'Trenne Verhalten[^.]*technischen Entscheidungen', 'Plan trennt Anforderung und Lösung'), (r'^11\. .*\n', 'Plan prüft Originalabdeckung')):
            text, count = re.subn(pattern, '', original_read(plan, encoding='utf-8'), flags=re.M)
            self.assertEqual(count, 1)
            def read_text(path, *args, _text=text, **kwargs):
                return _text if Path(path) == plan else original_read(path, *args, **kwargs)
            with self.subTest(label=label), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                checker.check_group(ROOT, 'workflows')

    def test_g04_authorization_safety_delegation_scenarios(self):
        # Z01/Z02: technical scope adjustment in frame vs. goal change, money, unclear impact.
        base = dict(kind='authorization', frame_confirmed=True, goal_changed=False, technical_change=True, within_frame=True, coverage_known=True, extra_monetary_cost=False, consent_given=False, uncovered_usage=False, production_effect=False, impact_clear=True, recovery_safe=True)
        checker.validate_scenario(base)
        checker.validate_scenario(dict(base, production_effect=True))
        checker.validate_scenario(dict(base, extra_monetary_cost=True, consent_given=True))
        for mutation, message in (
            (dict(frame_confirmed=False), 'bestätigungspflichtig'),
            (dict(goal_changed=True), 'Nutzerentscheidung'),
            (dict(within_frame=False), 'außerhalb des Rahmens'),
            (dict(extra_monetary_cost=True), 'vorherige Zustimmung'),
            (dict(coverage_known=False), 'unbekannte Deckung'),
            (dict(uncovered_usage=True), 'ungedeckte KI'),
            (dict(production_effect=True, impact_clear=False), 'Produktionswirkung stoppt'),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(checker.ContractError, message):
                checker.validate_scenario(dict(base, **mutation))
        # Z04: decisive assumption with explicit evidence strength, no external duty.
        safety = dict(kind='safety', assumption_named=True, indirect_effects_considered=True, evidence_strength='belegt', checked_or_marked_open=True, external_skill_duty=False)
        checker.validate_scenario(safety)
        checker.validate_scenario(dict(safety, evidence_strength='offen'))
        for mutation, message in (
            (dict(assumption_named=False), 'unbenannt'),
            (dict(evidence_strength='vermutet'), 'Evidenzstärke nicht klassifiziert'),
            (dict(checked_or_marked_open=False), 'weder geprüft noch offen markiert'),
            (dict(external_skill_duty=True), 'Blast-Radius'),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(checker.ContractError, message):
                checker.validate_scenario(dict(safety, **mutation))
        # Z06: agent operates delegated tests; only personal consent is handed over.
        delegation = dict(kind='delegation', personal_repetition=False, requirement_confirmed=True, personal_action=True, handed_over=True, sandbox_delegated=True, agent_operates=True, session_artifacts_exact=True, drift_checked=True, new_start_formula=False, auto_follow_up=False, time_budget_loop=False)
        checker.validate_scenario(delegation)
        for mutation, message in (
            (dict(personal_repetition=True, requirement_confirmed=False), 'persönliche Wiederholung'),
            (dict(handed_over=False), 'nicht übergeben'),
            (dict(agent_operates=False), 'delegierte Testbedienung'),
            (dict(drift_checked=False), 'Driftprüfung'),
            (dict(new_start_formula=True), 'Startformel'),
            (dict(auto_follow_up=True), 'automatische Folgeetappe'),
            (dict(time_budget_loop=True), 'Bereitschaftsschleife'),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(checker.ContractError, message):
                checker.validate_scenario(dict(delegation, **mutation))
        domain_pattern = next(p for p, l in checker.POLICIES['domains'] if l == 'Domain-Kostenklausel')
        self.assertRegex('Zusätzliche monetäre Kosten brauchen vorherige Zustimmung.', '(?i)' + domain_pattern)
        self.assertNotRegex('Kosten werden ohne Zustimmung akzeptiert.', '(?i)' + domain_pattern)

    def test_rv05_replacement_chain_and_authorization_countercases(self):
        sources = {p: (ROOT / p).read_text() for p in checker.REPLACEMENT_SOURCES}
        checker.check_replacement_sources(sources)
        cases = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        # Existing deterministic fixtures cover the frame boundary; source checks
        # connect that boundary to the complete plan/review/execute/prompt path.
        covered = cases['g04-authorization-positive']['input']
        self.assertFalse(covered['consent_given'])
        checker.validate_scenario(covered)
        for case_id in ('g04-authorization-first-plan-without-frame', 'g04-authorization-goal-change', 'g04-authorization-extra-cost', 'g04-authorization-technical-outside-frame', 'g04-authorization-unknown-coverage'):
            case = cases[case_id]
            with self.subTest(case=case_id), self.assertRaisesRegex(checker.ContractError, case['observation']):
                checker.validate_scenario(case['input'])
        # Every source-local obligation is necessary, including derived evidence,
        # independent review, new path/run, unchanged old plan and no implicit start.
        for path, patterns in checker.REPLACEMENT_SOURCES.items():
            for pattern in patterns:
                mutated, count = re.subn(pattern, '', sources[path], count=1, flags=re.I)
                self.assertEqual(count, 1, (path, pattern))
                with self.subTest(path=path, clause=pattern), self.assertRaisesRegex(checker.ContractError, 'RV05 Ersatzplan-Ablaufklausel'):
                    checker.check_replacement_sources(dict(sources, **{path: mutated}))

    def test_handoff_first_plan_clauses_and_in_memory_mutations(self):
        sources = {p: (ROOT / p).read_text(encoding='utf-8') for p in checker.HANDOFF_SOURCES}
        checker.check_handoff_sources(sources)
        original_read = Path.read_text
        def run_group(relative, text):
            def read_text(path, *args, **kwargs):
                return text if Path(path) == ROOT / relative else original_read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()):
                checker.check_group(ROOT, 'workflows')
        mutations = 0
        for relative, patterns in checker.HANDOFF_SOURCES.items():
            for pattern in patterns:
                text, count = re.subn(pattern, '', sources[relative])
                with self.subTest(source=relative, clause=pattern):
                    self.assertGreater(count, 0)
                    with self.assertRaisesRegex(checker.ContractError, 'Handoff-Klausel fehlt'):
                        checker.check_handoff_sources(dict(sources, **{relative: text}))
                    with self.assertRaises(checker.ContractError):
                        run_group(relative, text)
                mutations += 1
        widenings = ('Mit M01 beginnen bedeutet Gesamtfreigabe.',
                     'Die Gesamtfreigabe wählt weitere Etappen automatisch aus.',
                     'Ausdrückliches Nur-Planen erlaubt Umsetzung.',
                     'Handoff erlaubt sofortige Ausführung.', 'Draft ist ausführbar.',
                     'handoff-planning ersetzt selection_approval.', 'Anzeige gilt als Nutzerfreigabe.',
                     'Ein Dateipfad genügt als vollständige Anzeige.',
                     'Handoff-Sperre gilt auch für technische Ersatzpläne.',
                     'goal-covered ersetzt user-confirmed.', 'goal-covered ersetzt selection_approval.',
                     'Qualitäts-pass genügt als Deckung.', 'Der Indexwert beweist die Ausführungsdeckung.',
                     'Eine Schreibfreigabe gilt rückwirkend als Gesamtfreigabe.',
                     'Die Gesamtfreigabe deckt jede spätere Definitionsversion.',
                     'Die gedeckte Etappe startet automatisch die nächste Etappe.',
                     'Für Erstpläne gilt der [Erstplan-Ablauf des Workflowvertrags].',
                     'Für Erstpläne im Etappenmodus gilt der [Erstplan-Ablauf des Workflowvertrags].')
        for relative in sources:
            for clause in widenings:
                with self.subTest(source=relative, widening=clause), self.assertRaisesRegex(checker.ContractError, 'Handoff-Ausweitung'):
                    run_group(relative, sources[relative] + '\n' + clause)
                mutations += 1
        # The old mandatory single-plan halt is replaced by coverage criteria; reinserting it fails.
        legacy = ('Mit M01 beginnen bedeutet nur M01 freigegeben.',
                  'Die erste Indexauswahl begrenzt die Gesamtfreigabe.',
                  'Handoffs geben nur die aktuelle Etappenfreigabe weiter.',
                  'Gedeckte Umsetzung braucht eine zusätzliche persönliche Einzelbestätigung.',
                  'Erst eine neue ausdrückliche Nutzerfreigabe macht dieselbe Datei `Confirmed`; bis dahin ist sie nicht ausführbar.',
                  'Der Erstplan bleibt bis zur ausdrücklichen neuen Nutzerfreigabe Draft.',
                  '`core-plan` muss auf die ausdrückliche neue Nutzerfreigabe warten, bevor dieselbe Datei Confirmed wird.',
                  'Neue Ziele, Scopeänderungen, Folgeetappen und gesondert freigabepflichtige Aktionen benötigen eigene ausdrückliche Autorisierung.')
        for relative in sources:
            for clause in legacy:
                with self.subTest(source=relative, legacy=clause), self.assertRaisesRegex(checker.ContractError, 'Handoff-Einzelplanhalt ohne Deckungskriterien'):
                    run_group(relative, sources[relative] + '\n' + clause)
                mutations += 1
        print('HANDOFF source mutations:', mutations, 'rejected; static evidence only')

    def test_initial_frame_and_handoff_repair_mutations(self):
        # Alter clauses in place, retaining the surrounding positive prose. These
        # regressions were missed by the pre-repair source-local checks. Include
        # the handoff owner even when replaying the old checker's smaller source set.
        paths = set(checker.HANDOFF_SOURCES) | {'.apm/skills/core-handoff/SKILL.md'}
        sources = {p: (ROOT / p).read_text() for p in paths}
        checker.check_handoff_sources(sources)
        mutations = (
            ('.apm/skills/core-milestone/SKILL.md',
             'Vor dem Schreiben kläre bei unklarer Reichweite gezielt, welche Etappen-ID-Versionen zur Umsetzung mitbestätigt werden.',
             'Die Reichweite kann nach dem Schreiben offenbleiben.'),
            ('.apm/skills/core-milestone/SKILL.md',
             '„Mit M01 beginnen“ allein bedeutet weder „nur M01 freigegeben“ noch Gesamtdeckung',
             '„Mit M01 beginnen“ allein bedeutet „nur M01 freigegeben“'),
            ('.apm/skills/core-milestone/references/goal-format.md',
             'die erste Auswahl im Index bezeichnet nur die aktuelle Etappe und verengt sie nicht',
             'die erste Auswahl im Index begrenzt die Gesamtfreigabe'),
            ('.apm/skills/core-handoff/SKILL.md',
             'den vollständigen ursprünglichen Rahmen', 'nur den aktuellen Etappenrahmen'),
            ('.apm/skills/core-handoff/assets/start-prompt.md',
             'alle gedeckten Etappen-IDs/Versionen und Ausschlüsse', 'nur die aktuelle Etappen-ID/Version'),
            ('.apm/skills/core-shared/references/workflow-contract.md',
             'ohne zusätzliches persönliches Einzelgate zulässig', 'erst nach zusätzlichem persönlichem Einzelgate zulässig'),
            ('.apm/skills/core-handoff/assets/start-prompt.md',
             'Explizite Einschränkungen, fehlende Deckung, Konflikte, Abbruch, Resume-Grenzen und ungedeckte Wirkungen bleiben bindend',
             'Explizite Einschränkungen werden durch Gesamtdeckung aufgehoben'),
            ('.apm/skills/core-shared/references/workflow-contract.md',
             'Ausdrückliche Einschränkungen, fehlende Deckung, Konflikte, Abbruch, Resume-Grenzen und ungedeckte Wirkungen bleiben unverändert bindend',
             'Ausdrückliche Einschränkungen treten hinter belegte Gesamtdeckung zurück'),
            ('.apm/skills/core-shared/references/workflow-contract.md',
             'Die Gesamtfreigabe wählt umgekehrt keine weitere Etappe automatisch aus und ersetzt nicht die bestehende Auswahl- und Planungsaktivierung',
             'Die Gesamtfreigabe aktiviert jede weitere gedeckte Etappe unmittelbar'),
            ('.apm/skills/core-milestone/SKILL.md',
             'Der Rahmen deckt genau die im Freigabebeleg benannten Etappen-IDs und Versionen',
             'Der Rahmen deckt alle Etappen des Ziels'),
            ('.apm/skills/core-milestone/SKILL.md',
             'eine solche Planungserlaubnis ist keine Ausführungsfreigabe',
             'eine solche Planungserlaubnis erlaubt auch die Ausführung'),
            *((relative, old, new)
              for relative in ('.apm/skills/core-init-project/assets/core-routing.md', 'AGENTS.md')
              for old, new in (
                  ('Eine Gesamtfreigabe deckt nur die im sichtbaren Freigabebeleg genannten Etappen',
                   'Eine Gesamtfreigabe deckt alle Etappen des Ziels'),
                  ('fehlt diese Reichweite, klärt `core-milestone` gezielt nach',
                   'fehlt diese Reichweite, gilt nur die aktuelle Etappe'),
                  ('Die erste Indexauswahl begrenzt die bestätigte Gesamtdeckung nicht',
                   'Die erste Indexauswahl begrenzt die bestätigte Gesamtdeckung'),
                  ('keine Etappe wird automatisch ausgewählt', 'gedeckte Etappen werden automatisch ausgewählt'),
                  ('nicht gedeckte Folgeetappen', 'Folgeetappen nach Wahl'),
                  ('ein ausdrücklicher Nur-Planen-Auftrag erlaubt keine Umsetzung',
                   'ein ausdrücklicher Nur-Planen-Auftrag erlaubt bei Deckung die Umsetzung'),
                  ('evidenzbasierten Reparatur- und Stopgrenzen des zuständigen Skills statt starrer Rundenzahlen',
                   'starren Rundenzahlen'),
              )),
        )
        for relative in ('.apm/skills/core-init-project/assets/core-routing.md', 'AGENTS.md'):
            # Re-tightening in place is a separate reversal: every further stage needs approval again.
            self.assertEqual(sources[relative].count('nicht gedeckte Folgeetappen'), 1)
            changed = sources[relative].replace('nicht gedeckte Folgeetappen', 'Folgeetappen')
            with self.subTest(source=relative, mutation='pauschales Folgeetappengate'), self.assertRaisesRegex(checker.ContractError, 'Handoff-Einzelplanhalt'):
                checker.check_handoff_sources(dict(sources, **{relative: changed}))
        for relative, old, new in mutations:
            self.assertEqual(sources[relative].count(old), 1, old)
            changed = sources[relative].replace(old, new)
            with self.subTest(source=relative, mutation=new), self.assertRaisesRegex(checker.ContractError, 'Handoff-Klausel fehlt'):
                checker.check_handoff_sources(dict(sources, **{relative: changed}))
        print('FRAME:', len(mutations) + 2, 'source alterations rejected (static only)')

    def test_initial_frame_to_covered_execute_and_real_stops(self):
        # Reuse the existing full chain: initial two-version frame, first stage,
        # handoff order, separate reviews, display, Confirmed, index and Execute.
        cases = {c['id']: c['input'] for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        handoff = cases['handoff-covered-handoff-goal-covered']
        first = cases['handoff-covered-stage-first-user-confirmed']
        self.assertEqual(first['coverage']['frame_definitions'], handoff['coverage']['frame_definitions'])
        self.assertEqual(len(handoff['coverage']['frame_definitions']), 2)
        for data in (first, handoff):
            before = copy.deepcopy(data)
            self.assertTrue(data['execute'])
            self.assertFalse(data['new_user_approval'])
            checker.validate_scenario(data)
            self.assertEqual(data, before)
            # Coverage may not be silently narrowed to an unnecessary Draft halt.
            narrowed = copy.deepcopy(data)
            narrowed.update(final_plan=copy.deepcopy(data['draft']), final_index=copy.deepcopy(data['index']), execute=False)
            with self.assertRaisesRegex(checker.ContractError, 'bestätigte Datei/Inhalt verändert'):
                checker.validate_scenario(narrowed)
        for name, fields, gap in (
            ('write-only', {'source_kind': 'write-only'}, 'keine belegte Gesamtfreigabe: write-only'),
            ('content-only', {'source_kind': 'content-only'}, 'keine belegte Gesamtfreigabe: content-only'),
            ('not-shown', {'frame_explained_before_question': False}, 'Ausführungsrahmen nicht sichtbar'),
            ('G06-like-M01-only', {'frame_definitions': handoff['coverage']['frame_definitions'][:1]}, 'Gesamtfreigabe deckt diese Definitionsversion nicht'),
            ('only-plan', {'deviations': ['planning_only']}, 'ausdrücklicher Nur-Planen-Auftrag'),
            ('drift', {'deviations': ['stale_originals']}, 'veraltete Originale'),
            ('cost', {'deviations': ['uncovered_cost']}, 'ungedeckte Geld-/Usagekosten'),
        ):
            halted = copy.deepcopy(handoff)
            halted['coverage'].update(fields)
            halted.update(final_plan=copy.deepcopy(halted['draft']), final_index=copy.deepcopy(halted['index']), execute=False)
            with self.subTest(stop=name):
                checker.validate_scenario(halted)
                for change in ({'execute': True}, {'final_plan': handoff['final_plan']}):
                    with self.assertRaisesRegex(checker.ContractError, gap):
                        checker.validate_scenario(dict(halted, **change))
        print('FRAME: covered first-stage/handoff Execute; 7 real halts with forced execution/confirmation rejected (static only)')

    def test_handoff_draft_keeps_execute_gate_and_task_validation(self):
        cases = {c['id']: c['input'] for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        data = cases['handoff-draft-native']
        before = copy.deepcopy(data)
        checker.validate_prompt(data)
        self.assertEqual(data, before, 'static Draft validation must not confirm the input')
        with self.assertRaisesRegex(checker.ContractError, 'Plan nicht bestätigt'):
            checker.validate_plan(data['draft'])
        # Index syntax accepts the planning marker, but a normal execution/resume prompt does not.
        checker.check_index(data['index'])
        resume = dict(data, purpose='resume')
        with self.assertRaisesRegex(checker.ContractError, 'keine freigegebene aktuelle Etappe'):
            checker.validate_prompt(resume)
        for change in ({'tasks': []}, {'tasks': [dict(data['draft']['tasks'][0], dependencies=['T99'])]},
                       {'tasks': [dict(data['draft']['tasks'][0], checks=[])]}):
            invalid = copy.deepcopy(data)
            invalid['draft'].update(change)
            with self.subTest(change=change), self.assertRaises(checker.ContractError):
                checker.validate_prompt(invalid)
        # Missing observed facts must fail, never acquire success defaults.
        for field in data:
            invalid = copy.deepcopy(data)
            del invalid[field]
            if field in ('kind', 'purpose', 'approval_after_display', 'execution_order', 'link_owner', 'link_recheck', 'execute_checks'):
                continue
            with self.subTest(missing=field), self.assertRaises((checker.ContractError, KeyError)):
                checker.validate_handoff_first_plan(invalid)

    def test_direct_covered_transition_cannot_stop_after_confirmed_link(self):
        cases = {c['id']: c['input'] for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        # Existing first-stage and follow-handoff originals: no new fixture/schema.
        for name in ('handoff-covered-stage-first-user-confirmed', 'handoff-covered-handoff-goal-covered'):
            data = copy.deepcopy(cases[name])
            self.assertFalse(data['new_user_approval'])
            checker.validate_scenario(data)
            data['execute'] = False
            with self.subTest(case=name), self.assertRaisesRegex(checker.ContractError, 'gedeckter Übergang wartet grundlos'):
                checker.validate_scenario(data)
        completion = copy.deepcopy(cases['completion-positive'])
        checker.validate_scenario(completion)
        # Even historical coverage does not permit a same-session completion cascade.
        completion.update(next_started=True, next_authorized=True)
        with self.assertRaisesRegex(checker.ContractError, 'Handoff und Halt'):
            checker.validate_scenario(completion)

    def test_direct_transition_rejects_prompt_gate_wait_and_completion_cascade(self):
        sources = {p: (ROOT / p).read_text() for p in checker.HANDOFF_SOURCES}
        checker.check_handoff_sources(sources)
        for path, text in sources.items():
            for clause in ('Fülle den Goal-Prompt aus.',
                           'Verlange das Asset assets/goal-prompt.md.',
                           'Gedeckte Arbeit wartet auf eine neue Nutzerantwort.',
                           'Nach Etappenabschluss plane unmittelbar die nächste Etappe.',
                           'Nach Etappenabschluss ist Handoff optional.'):
                with self.subTest(path=path, clause=clause), self.assertRaisesRegex(checker.ContractError, 'direkter Etappenübergang verletzt'):
                    checker.check_handoff_sources(dict(sources, **{path: text + '\n' + clause}))
        self.assertFalse((ROOT / '.apm/skills/core-milestone/assets/goal-prompt.md').exists())
        fixture = json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())
        inventory = json.loads((ROOT / checker.TARGETS).read_text())
        self.assertTrue(all('assets/goal-prompt.md' not in c['source'] for c in fixture['cases']))
        self.assertTrue(all('assets/goal-prompt.md' not in p for paths in inventory['groups'].values() for p in paths))

    def test_handoff_coverage_and_display_paths_use_existing_scenarios(self):
        fixture = json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())
        checker.check_coverage(fixture)
        for key in ('handoff-planungsbefugnis', 'handoff-erstplan-halt', 'handoff-sichtbare-anzeige', 'handoff-gesamtdeckung'):
            ids = fixture['coverage'][key]['cases']
            self.assertTrue({'pass', 'fail'} <= {c['expected'] for c in fixture['cases'] if c['id'] in ids})
            missing = copy.deepcopy(fixture)
            del missing['coverage'][key]
            with self.assertRaisesRegex(checker.ContractError, 'Regressionsabdeckung fehlt'):
                checker.check_coverage(missing)
        # A foreign harness takes the same capability route without installing a viewer.
        by_id = {c['id']: c for c in fixture['cases']}
        for name in ('draft-native', 'draft-other-harness', 'draft-os-fallback', 'draft-headless', 'draft-display-failure', 'confirmed-same-version', 'execute-after-new-order'):
            checker.validate_scenario(by_id['handoff-' + name]['input'])
        # Existing independent replacement-plan controls must still pass without a new personal approval.
        checker.check_replacement_sources({p: (ROOT / p).read_text() for p in checker.REPLACEMENT_SOURCES})
        checker.validate_scenario(by_id['g04-authorization-positive']['input'])

    def test_goal_coverage_scenarios_separate_activation_review_and_link(self):
        # Static relationship model only: no live reviewer, harness display or model compliance.
        by_id = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        handoff = by_id['handoff-covered-handoff-goal-covered']['input']
        stage = by_id['handoff-covered-stage-first-user-confirmed']['input']
        for data in (handoff, stage):
            checker.validate_scenario(data)
            # Draft stays unexecutable even when coverage is later proven.
            with self.assertRaisesRegex(checker.ContractError, 'Plan nicht bestätigt'):
                checker.validate_plan(data['draft'])
        current = lambda ix: next(e for e in ix['milestones'] if e['current'])
        self.assertEqual(current(handoff['index'])['current_approval'], 'handoff-planning')
        self.assertEqual(current(handoff['final_index'])['current_approval'], 'goal-covered')
        # A real first-stage activation is never rewritten to goal-covered.
        self.assertEqual(current(stage['index'])['current_approval'], 'user-confirmed')
        self.assertEqual(current(stage['final_index'])['current_approval'], 'user-confirmed')
        # The positive covered fixture needs no own approval sentence and no new single-plan confirmation.
        self.assertFalse(handoff['new_user_approval'])
        # Every coverage criterion is necessary on its own: in-memory one-field mutations of the
        # covered fixture with the exact expected message (replaces former full-copy fixtures).
        goal, index, definition = (handoff['prompt'][k] for k in ('goal_path', 'index_path', 'definition_path'))
        def cov(**fields):
            return lambda d: d['coverage'].update(fields)
        def top(**fields):
            return lambda d: d.update(fields)
        def unlinked(d):
            current(d['final_index'])['plan_paths'] = []
        mutations = [(f'source_kind={kind}', cov(source_kind=kind), 'keine belegte Gesamtfreigabe: ' + kind)
                     for kind in ('write-only', 'historical-approval-field', 'previous-stage-execution', 'content-only')]
        mutations += [
            ('frame_explained', cov(frame_explained_before_question=False), 'Ausführungsrahmen nicht sichtbar vorgelegt und bestätigt'),
            ('frame_confirmed', cov(frame_confirmed=False), 'Ausführungsrahmen nicht sichtbar vorgelegt und bestätigt'),
            ('foreign_source', cov(source_path='.agentic-workflow/goals/G02/goal.md'), 'Gesamtfreigabequelle nicht im aktuellen Original belegt'),
            ('new_definition_version', cov(frame_definitions=[d for d in handoff['coverage']['frame_definitions'] if d != definition]), 'Gesamtfreigabe deckt diese Definitionsversion nicht'),
            ('expected_verdict', cov(expected_verdict_given=True), 'Deckungsreview ohne neutrale vollständige Originalbelege'),
            ('review_without_handoff', cov(review_inputs=[goal, index, definition]), 'Deckungsreview ohne neutrale vollständige Originalbelege'),
            ('quality_pass_only', cov(review_verdict='nicht geprüft'), 'Deckungsreview: nicht geprüft'),
            ('unknown_deviation', cov(deviations=['unbekannt']), 'unbekannte Deckungsabweichung: unbekannt'),
            ('unconfirmed_security_measure', cov(confirmed_security_measures=['Neue öffentliche Erreichbarkeit ohne bestätigten Rahmen']), 'Nutzerentscheidung nötig: Sicherheitsmaßnahme ohne Rahmenbeleg: Neue öffentliche Erreichbarkeit ohne bestätigten Rahmen'),
            ('no_plan_text', cov(plan_text_evidence=False), 'Deckungsbeleg fehlt im Planreviewabschnitt'),
            ('without_plan_link', unlinked, 'Confirmed-Link verändert ID-Version/Auswahl/Aktivierung'),
            ('draft_linked', lambda d: d.update(final_plan=copy.deepcopy(d['draft'])), 'bestätigte Datei/Inhalt verändert'),
            ('link_without_recheck', top(link_recheck=False), 'Planlink ohne erneute Original-/Index-/Konkurrenzprüfung'),
            ('execute_without_own_checks', top(execute_checks=False), 'Execute ohne eigene Original-/Review-/Indexprüfung'),
            ('without_review', top(review_pass=False), 'statische Validierung/unabhängiges Planreview fehlt'),
        ]
        mutations += [(f'deviation={key}', cov(deviations=[key]), 'Nutzerentscheidung nötig: ' + text)
                      for key, text in checker.COVERAGE_DEVIATIONS.items()]
        for name, mutate, message in mutations:
            invalid = copy.deepcopy(handoff)
            mutate(invalid)
            with self.subTest(criterion=name), self.assertRaisesRegex(checker.ContractError, '(?:^|: )' + re.escape(message) + '$'):
                checker.validate_scenario(invalid)
        # A concretely confirmed security measure passes only when the confirmed frame names exactly it.
        secured = by_id['handoff-covered-confirmed-security-measure']['input']
        checker.validate_scenario(secured)
        self.assertTrue(secured['coverage']['confirmed_security_measures'])
        for name, frame in (('measure_missing_in_frame', []), ('other_measure_in_frame', ['Anderer Rahmen'])):
            invalid = copy.deepcopy(secured)
            invalid['coverage']['frame_security_measures'] = frame
            with self.subTest(security=name), self.assertRaisesRegex(checker.ContractError, 'Sicherheitsmaßnahme ohne Rahmenbeleg'):
                checker.validate_scenario(invalid)
        # The index value alone never proves coverage for an execution/resume prompt.
        prompt = {'goal_path': handoff['prompt']['goal_path'], 'index_path': handoff['prompt']['index_path'],
                  'definition_path': handoff['prompt']['definition_path'], 'milestone_id': 'M02', 'version': 1,
                  'plan_path': handoff['prompt']['plan_path']}
        resume = {'kind': 'prompt', 'purpose': 'resume', 'index': handoff['final_index'], 'prompt': prompt}
        with self.assertRaisesRegex(checker.ContractError, 'goal-covered ohne Originalbelege'):
            checker.validate_prompt(resume)
        resume['prompt'] = dict(prompt, coverage_refs=[prompt['goal_path'], prompt['index_path'], prompt['definition_path'], prompt['plan_path']])
        checker.validate_prompt(resume)
        bare = copy.deepcopy(handoff['final_index'])
        current(bare)['plan_paths'] = []
        with self.assertRaisesRegex(checker.ContractError, 'goal-covered ohne verknüpften Confirmed-Plan'):
            checker.check_index(bare)

    def test_rv07_situational_user_confirmation_stays_valid(self):
        # RV07 rejects only blanket gates; situational confirmation remains allowed.
        sources = {p: (ROOT / p).read_text() for p in checker.REPLACEMENT_SOURCES}
        situational = '\nBei neuem Ziel, ungedeckten Geldkosten, ungedeckter Wirkung oder ohne bestätigten Rahmen bleibt eine Nutzerbestätigung vor Schreiben und Ausführung erforderlich.\n'
        for path in ('.apm/skills/core-review/SKILL.md', '.apm/skills/core-plan/SKILL.md'):
            with self.subTest(path=path):
                checker.check_replacement_sources(dict(sources, **{path: sources[path] + situational}))

    def test_rv05_reintroduced_gates_fail_in_real_workflow_group(self):
        original_read = Path.read_text
        old_gates = {
            '.apm/skills/core-shared/references/workflow-contract.md': (
                'Erst nach ausdrücklicher Bestätigung wird der Ersatzplan geschrieben.',
                'Die bisherige Planfreigabe bestätigt keinen unbekannten Ersatzplan.',
                'Ein Planreview-pass bedeutet nur bestätigungsfähig, nicht vom Nutzer bestätigt; ohne Nutzerbestätigung wird nichts ausgeführt.',
            ),
            '.apm/skills/core-plan/SKILL.md': ('Präsentiere den Entwurf zur Bestätigung, sofern die aktuelle Benutzeranweisung nicht bereits genau diesen Plan autorisiert.', 'Nutze anschließend denselben Validierungs-, Planreview- und Bestätigungsschritt wie bei Erstplanung.', 'Prüfe vor der Bestätigung:'),
            '.apm/skills/core-execute/SKILL.md': ('die Bestätigung des Ersatzplans bleibt erforderlich.',),
            '.apm/skills/core-review/SKILL.md': (
                'Prüft einen vollständigen Planentwurf vor der Nutzerbestätigung (Planreview, Textergebnis).',
                'Zwei Modi: Planreview vor der Nutzerbestätigung und Umsetzungsreview nach core-execute.',
            ),
            '.apm/skills/core-milestone/SKILL.md': ('Ziel-/Definitionsbestätigung und aktuelle Etappenfreigabe sind weder Planbestätigung noch Ausführungsfreigabe.', 'Der Nutzer aktiviert ihn erst nach Bestätigung des eigenen Plans, ab core-execute.', 'Ausführung beginnt erst nach Planbestätigung und ausdrücklicher Execute-Autorisierung.'),
            '.apm/skills/core-handoff/assets/start-prompt.md': ('die Planbestätigung bleibt erforderlich.', 'Execute beginnt erst nach bestätigtem Plan und ausdrücklicher Ausführungsautorisierung.'),
            'README.md': (
                'Planreview vor deiner Bestätigung.',
                'Ein unabhängiges Planreview prüft den Entwurf vor deiner Bestätigung.',
                'Planreview → deine Freigabe → core-execute',
                'erst deine ausdrückliche Bestätigung erlaubt die Umsetzung.',
            ),
            'DESIGN.md': (
                'Planreview → Nutzerbestätigung → core-execute',
                'Planung, Planreview vor Nutzerbestätigung und read-only Umsetzungsreview.',
                'unabhängiges Planreview vor Bestätigung und read-only Umsetzungsreview.',
                'core-plan → core-execute (erst nach Nutzerbestätigung)',
                'core-plan → core-review (Planreview; Textantwort vor Bestätigung)',
                'Nach vollständigem Entwurf und vor Nutzerbestätigung.',
            ),
        }
        for relative, clauses in old_gates.items():
            source = ROOT / relative
            for clause in clauses:
                # Keep every positive clause: the contradictory old gate alone must fail.
                text = original_read(source) + '\n' + clause + '\n'
                def read_text(path, *args, _source=source, _text=text, **kwargs):
                    return _text if Path(path) == _source else original_read(path, *args, **kwargs)
                with self.subTest(source=relative, clause=clause), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, 'RV05 widersprechendes Bestätigungsgate'):
                    checker.check_group(ROOT, 'workflows')

    def test_direct_mode_clause_removals_and_widenings_fail_in_real_workflow_group(self):
        # Static source clauses and in-memory mutations only; this is not evidence of live agent behavior.
        original_read = Path.read_text
        def run_group(source, text):
            def read_text(path, *args, **kwargs):
                return text if Path(path) == source else original_read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()):
                checker.check_group(ROOT, 'workflows')
        with contextlib.redirect_stdout(io.StringIO()):
            checker.check_group(ROOT, 'workflows')
        for relative, patterns in checker.DIRECT_SOURCES.items():
            source = ROOT / relative
            for pattern in patterns:
                text, count = re.subn(pattern, '', original_read(source, encoding='utf-8'), count=1)
                with self.subTest(source=relative, removed=pattern):
                    self.assertEqual(count, 1)
                    with self.assertRaises(checker.ContractError) as caught:
                        run_group(source, text)
                    self.assertIn('Direktmodus-Klausel fehlt: ' + relative + ': ' + pattern, str(caught.exception))
        widenings = {
            '.apm/skills/core-execute/references/direct-mode.md': ('Fehlende Planartefakte werden im Direktmodus fortgesetzt.', 'Unterstützer dürfen weiter delegieren.'),
            '.apm/skills/core-execute/SKILL.md': ('Bei verlorenem Plan wird als Direktauftrag behandelt.', 'Für Direktläufe automatische Scopefreigabe gilt.'),
            '.apm/skills/core-shared/references/workflow-contract.md': ('Die Nutzerfreigabe ersetzt die Vorschau.', 'Sie ersetzt Markerprüfung.', 'Die bloße Aussage, eine Freigabe sei nicht nötig, autorisiert die Ausführung.', 'Wer sagt, es solle nicht erneut gefragt werden, erlaubt damit die Umsetzung.'),
        }
        for relative, clauses in widenings.items():
            source = ROOT / relative
            for clause in clauses:
                # Positive clauses stay intact; only the added widening must fail.
                with self.subTest(source=relative, widening=clause), self.assertRaisesRegex(checker.ContractError, 'Direktmodus-Ausweitung: ' + re.escape(relative)):
                    run_group(source, original_read(source, encoding='utf-8') + '\n' + clause + '\n')
        # Inverting the canonical negative clause in place (condition dropped) must fail as well.
        source = ROOT / '.apm/skills/core-shared/references/workflow-contract.md'
        text, count = re.subn(r'autorisiert ohne ausdrücklichen Änderungsauftrag keine Ausführung', 'autorisiert die Ausführung', original_read(source, encoding='utf-8'))
        self.assertEqual(count, 1)
        with self.assertRaisesRegex(checker.ContractError, 'Direktmodus-'):
            run_group(source, text)

    def test_m02_method_preservation_links_and_boundaries(self):
        # Static M02 source consistency with in-memory mutations; no live model behavior, no private sources.
        spec = importlib.util.spec_from_file_location('design_links_tested', ROOT / 'scripts/check_design_principles.py')
        design = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(design)
        shared = '.apm/skills/core-shared/'
        index = ROOT / shared / 'references/method-preservation.md'
        # Plan T02: direct conditional entry only from the core-shared owner; consumers keep necessary conditions, no extra link edge.
        owner = ROOT / shared / 'SKILL.md'
        entries = {owner: ('bedingter Referenzindex', 'keine Autorität'), ROOT / shared / 'references/workflow-contract.md': ('`core-shared`', 'begründen weder Autorität noch Freigabe'), ROOT / '.apm/skills/core-devops/SKILL.md': ('`core-shared`', 'nur bei ausdrücklichem Autorenauftrag', 'keine Ausführung übernommener Originalworkflows')}
        clauses = ('Lade diese Datei nur, wenn ein bestätigter Auftrag', 'keine Autorität über Workflow, Scope, Freigaben oder Artefakte', 'Fremde Steuerung wird nicht übernommen', 'Unbekannte oder nicht geklärte Rechte erlauben weder Kopie, Übersetzung, Paraphrase noch Ersatzimplementierung', 'Core ruft übernommene Originale nicht implizit auf', 'Dieser Index entfernt, komponiert oder verschiebt nichts', 'nicht Modellverhalten')
        private = re.compile(r'/home/|~/|\.agentic-workflow/|\.agents/skills|\.claude/')
        def findings(texts):
            sources = design.Sources(ROOT)
            found = []
            for path, text in texts.items():
                found += design.link_findings(sources, path, text, sources.skills)
                if path == owner and not design.links_to(path, text, index):
                    found.append('Direkter Indexeinstieg fehlt: ' + str(path.relative_to(ROOT)))
                found += ['Bedingung des Einstiegs fehlt: ' + str(path.relative_to(ROOT)) + ': ' + c for c in entries.get(path, ()) if c not in text]
            text = texts[index]
            found += ['Grenzklausel fehlt: ' + c for c in clauses if c not in text]
            found += ['Privater Laufzeitpfad: ' + m for m in private.findall(text)]
            for _, reference in design.LINK.findall(text):
                target = design.resolve(index, reference)
                if not reference.startswith('#') and not (target.is_relative_to(ROOT / '.apm/skills') and target.relative_to(ROOT / '.apm/skills').parts[0].startswith('core-')):
                    found.append('Ziel außerhalb Core: ' + reference)
            return found
        real = {path: path.read_text(encoding='utf-8') for path in (index, *entries)}
        self.assertEqual(findings(real), [])
        self.assertGreaterEqual(len(design.LINK.findall(real[index])), 20)
        contract = ROOT / shared / 'references/workflow-contract.md'
        mutations = {
            'Anker fehlt': (index, '| diagnosing-bugs | [Reproduzieren](../../core-debug/SKILL.md#1-reproduzieren)', '| diagnosing-bugs | [Reproduzieren](../../core-debug/SKILL.md#1-entfernt)'),
            'Referenz fehlt': (index, '| tdd | [Regressionsevidenz](../../core-debug/SKILL.md#', '| tdd | [Regressionsevidenz](../../core-debug/MISSING.md#'),
            'Ziel außerhalb Core': (index, '| architect | [Proportionale Methode]', '| architect | [Original](../../gortex-serena-configurator/SKILL.md); [Proportionale Methode]'),
            'nicht portable absolute Referenz': (index, '| architect | [Proportionale Methode]', '| architect | [Original](/home/user/.agents/skills/architect/SKILL.md); [Proportionale Methode]'),
            'Privater Laufzeitpfad': (index, '## Grenzen\n', '## Grenzen\n\nNachweis: .agentic-workflow/runs/run-G05-M01-v1-p01-r01/state.yaml\n'),
            'Grenzklausel fehlt: keine Autorität': (index, 'keine Autorität über Workflow', 'die Autorität über Workflow'),
            'Grenzklausel fehlt: Unbekannte': (index, 'erlauben weder Kopie, Übersetzung, Paraphrase noch', 'erlauben Kopie, Übersetzung, Paraphrase und'),
            'Grenzklausel fehlt: Lade': (index, 'Lade diese Datei nur, wenn ein bestätigter Auftrag', 'Lade diese Datei immer, wenn ein Auftrag'),
            'Grenzklausel fehlt: Core ruft': (index, 'Core ruft übernommene Originale nicht implizit auf', 'Core ruft übernommene Originale implizit auf'),
            'Direkter Indexeinstieg fehlt: .apm/skills/core-shared/SKILL.md': (owner, '[Methodenerhalt](references/method-preservation.md)', 'Methodenerhalt'),
            'Bedingung des Einstiegs fehlt: .apm/skills/core-shared/SKILL.md: bedingter': (owner, 'bedingter Referenzindex', 'verbindlicher Referenzindex'),
            'Bedingung des Einstiegs fehlt: .apm/skills/core-shared/SKILL.md: keine Autorität': (owner, 'keine Fachmethodik und keine Autorität', 'keine Fachmethodik und volle Autorität'),
            'Bedingung des Einstiegs fehlt: .apm/skills/core-shared/references/workflow-contract.md: begründen': (contract, 'begründen weder Autorität noch Freigabe', 'begründen Autorität und Freigabe'),
            'Bedingung des Einstiegs fehlt: .apm/skills/core-devops/SKILL.md: nur bei': (ROOT / '.apm/skills/core-devops/SKILL.md', 'nur bei ausdrücklichem Autorenauftrag', 'bei jedem Auftrag'),
            'Bedingung des Einstiegs fehlt: .apm/skills/core-devops/SKILL.md: keine Ausführung': (ROOT / '.apm/skills/core-devops/SKILL.md', 'keine Ausführung übernommener Originalworkflows', 'Ausführung übernommener Originalworkflows'),
        }
        for expected, (path, old, new) in mutations.items():
            with self.subTest(expected=expected):
                self.assertEqual(real[path].count(old), 1)
                mutated = {**real, path: real[path].replace(old, new)}
                self.assertTrue(any(expected in f for f in findings(mutated)), findings(mutated))

    def test_m04_selection_clauses_and_negative_mutations(self):
        # Frozen text fixtures and actual source mutations; no agent-behavior oracle.
        routing = ROOT / '.apm/skills/core-shared/references/tool-routing.md'
        text = routing.read_text(encoding='utf-8').split('## Fachmethoden ergänzend auswählen\n', 1)[1].split('\n## ', 1)[0]
        cases = (
            ('verbindliche Core-Methode ein', 'Core-Methode ist optional'),
            ('deren fachlicher Nutzen den gezielten Einsatz rechtfertigt', 'deren bloße Existenz den Einsatz rechtfertigt'),
            ('Aufgabe und Stack', 'Aufgabe ohne Stackprüfung'),
            ('relevante Querschnittsthemen', 'keine Querschnittsthemen'),
            ('Voraussetzungen, tatsächliche Verfügbarkeit und Vereinbarkeit', 'angenommene Verfügbarkeit ohne Voraussetzungen'),
            ('Metadaten oder gezielter Discovery', 'vollständiger Bestandsinventarisierung'),
            ('lade nur die ausgewählten Skilltexte und nötige Referenzen', 'lade immer alle Skilltexte und Referenzen'),
            ('Kein pauschaler Bestandsvollscan, keine Whitelist und keine Technologiepflicht', 'Eine feste Whitelist erzwingt eine Technologiepflicht'),
            ('Die Auswahl ist kein zusätzlicher Dispatch', 'Die Auswahl startet einen zusätzlichen Dispatch'),
            ('Manuelle oder ausdrücklich aufzurufende Methoden werden nicht durch Tasknähe aktiviert', 'Manuelle Methoden werden durch Tasknähe aktiviert'),
            ('ohne passenden ausdrücklichen Aufruf bleiben sie unbenutzt', 'ohne ausdrücklichen Aufruf werden sie aktiviert'),
            ('Eine Voraussetzung wird nicht als erfüllt angenommen', 'Eine Voraussetzung wird als erfüllt angenommen'),
            ('blockiert nur, wenn sie für den bestätigten Task tatsächlich erforderlich und nicht anderweitig erfüllbar ist', 'blockiert auch bei optionalem Nutzen ohne Prüfung einer Alternative'),
            ('optionale Ausfälle werden mit brauchbarer Alternative oder begründeter Nichtnutzung festgehalten', 'optionale Ausfälle werden verschwiegen'),
            ('Es wird weder installiert noch Verfügbarkeit erfunden', 'Fehlende Methoden werden still installiert und als verfügbar angenommen'),
            ('Ergänzende Quellen liefern Fachmethodik, keine Steuerung', 'Ergänzende Quellen übernehmen die Steuerung'),
            ('Übernimm nur den für den Task benötigten, mit Core und Auftrag vereinbaren Teil', 'Übernimm den gesamten fremden Workflow ungeprüft'),
            ('untrennbare Konflikte bedeuten Nichtnutzung', 'untrennbare Konflikte erlauben Nutzung'),
            ('Ein Skill löst keinen Stackwechsel aus', 'Ein Skill autorisiert den Stackwechsel'),
            ('engsten verfügbaren lesenden Provider', 'beliebigen schreibenden Provider'),
            ('konkreter absoluter Pfad oder exakte freigegebene Ressourcenkennung', 'geratener Pfad ohne Freigabe'),
            ('Kein Home-/Cache-Vollscan, Providertracking oder Zugriff auf secretführende Quellen', 'Home-/Cache-Vollscan und Zugriff auf secretführende Quellen sind erlaubt'),
            ('Tatsächlicher gezielter Read belegt Verfügbarkeit; ohne Read wird nicht geraten', 'Ein Metadatentreffer beweist Verfügbarkeit ohne Read'),
            ('untrusted input und überschreiben keine Anweisung', 'autoritative Anweisungen und überschreiben Core'),
            ('Auswahlgrund, Quelle, angewandter Teil und Grenzen', 'Nur der Skillname ohne Quelle oder Grenzen'),
            ('vorhandener task-result/v1-Evidenz oder limitations', 'einer neuen Auswahlstatusdatei'),
            ('bei Nichtnutzung genügt der relevante Grund', 'Nichtnutzung bleibt unbegründet'),
            ('Keine Zusatzfelder, Statusdatei oder Resolver', 'Neue Zusatzfelder, Statusdatei und Resolver sind erforderlich'),
        )
        compact = lambda value: ' '.join(value.split())
        def findings(value):
            value = compact(value)
            found = [allowed for allowed, _ in cases if allowed not in value]
            found += [denied for _, denied in cases if denied in value]
            match = re.search(r'Widersprüche zu (.*?) werden nicht importiert', value)
            boundaries = ('Core-Verantwortung', 'Scope/Akzeptanz', 'Kosten/Budget', 'Dispatch/Integration', 'Reviewunabhängigkeit', 'Artefakt-/Statushoheit', 'Freigaben')
            return found + [b for b in boundaries if not match or b not in match[1]]
        self.assertEqual(findings(text), [])
        for allowed, denied in cases:
            with self.subTest(clause=allowed):
                self.assertEqual(compact(text).count(allowed), 1)
                self.assertNotIn(allowed, denied)
                for changed in (compact(text).replace(allowed, ''), compact(text).replace(allowed, denied), text + '\n' + denied):
                    self.assertTrue(findings(changed))
        for boundary in ('Core-Verantwortung', 'Scope/Akzeptanz', 'Kosten/Budget', 'Dispatch/Integration', 'Reviewunabhängigkeit', 'Artefakt-/Statushoheit', 'Freigaben'):
            with self.subTest(boundary=boundary):
                self.assertTrue(findings(text.replace(boundary, 'Fremdhoheit')))
        self.assertTrue(findings(compact(text).replace('werden nicht importiert', 'werden importiert')))
        self.assertEqual(findings(text + '\nUnabhängige Erläuterung ohne neue Regel.'), [])

    def test_m04_profiles_shared_entry_and_local_link_drift(self):
        spec = importlib.util.spec_from_file_location('m04_design_links_tested', ROOT / 'scripts/check_design_principles.py')
        design = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(design)
        shared = ROOT / '.apm/skills/core-shared'
        routing, workflow, index = (shared / p for p in ('references/tool-routing.md', 'references/workflow-contract.md', 'SKILL.md'))
        owners = {'architecture-reviewer': 'core-architecture', 'backend-engineer': 'core-backend', 'db-engineer': 'core-database', 'debug-investigator': 'core-debug', 'docs-curator': 'core-docs', 'frontend-engineer': 'core-frontend', 'mobile-engineer': 'core-mobile', 'pm-planner': 'core-plan', 'qa-reviewer': 'core-review', 'refactor-engineer': 'core-refactor', 'research-explorer': 'core-research', 'tf-infra-engineer': 'core-tf-infra'}
        profiles = {ROOT / '.apm/agents' / (name + '.agent.md'): owner for name, owner in owners.items()}
        self.assertEqual(set(profiles), set((ROOT / '.apm/agents').glob('*.agent.md')))
        guide = ROOT / '.apm/skills/AGENTS.md'
        real = {p: p.read_text(encoding='utf-8') for p in (routing, workflow, index, guide, *profiles)}
        def findings(texts):
            sources, found = design.Sources(ROOT), []
            original_read = Path.read_text
            def read(path, *args, **kwargs):
                return texts[Path(path)] if Path(path) in texts else original_read(path, *args, **kwargs)
            with patch.object(sources, 'text', side_effect=read):
                for path, text in texts.items():
                    if path in profiles:
                        # Expand this single known reference for the existing inline-link helper.
                        target = re.search(r'^\[method-choice\]: (\S+)$', text, re.M)
                        if not target or '[gemeinsamen Auswahlregel][method-choice]' not in text:
                            found.append('Auswahlverweis fehlt')
                        else:
                            text = text.replace('[gemeinsamen Auswahlregel][method-choice]', '[gemeinsamen Auswahlregel](' + target[1] + ')')
                        if not design.links_to(path, text, routing):
                            found.append('Auswahlziel fehlt')
                        owner_clause = 'Eigentümer-Skill: ' + chr(96) + profiles[path] + chr(96) + '; nutze ihn als verbindliche Core-Methode.'
                        clauses = (owner_clause, 'Ergänze bei Tasknutzen verfügbare Fachmethoden', '- Eingang:', '- Ausgang:', '- Scope:', 'erweitere den Auftrag nicht', 'verwalte keinen Workflowzustand', 'Starte keine eigenen Subagenten.')
                        found += [c for c in clauses if c not in text]
                        if 'alleinige Fachmethodik' in text:
                            found.append('alte Ausschließlichkeit')
                    found += design.link_findings(sources, path, text, ROOT / '.apm')
                if not design.links_to(index, texts[index], routing):
                    found.append('Shared-Indexeinstieg fehlt')
                compact = ' '.join(texts[workflow].split())
                for clause in ('zusätzlich zum verbindlichen Eigentümer-Skill', 'sofern sie tatsächlich verfügbar und mit diesem Vertrag vereinbar sind', 'manuelle Aufrufgrenzen', 'Statushoheit bleiben bindend', 'weder Whitelist noch neuen Dispatch oder Workflow'):
                    if clause not in compact:
                        found.append(clause)
                if not design.links_to(workflow, texts[workflow], routing):
                    found.append('Workfloweinstieg fehlt')
            return found
        actual_findings = findings(real)
        # Exercise mutations even when the real entry is broken; keep its failure below.
        entry = real[workflow].replace('[gemeinsame Auswahlregel]\n(', '[gemeinsame Auswahlregel](')
        actual_findings += findings({**real, workflow: entry})
        real = {**real, workflow: entry.replace('#fachmethoden-erg-nzend-ausw-hlen', '#' + design.slug('Fachmethoden ergänzend auswählen'))}
        self.assertEqual(findings(real), [])
        for path, owner in profiles.items():
            for old, new in ((owner, 'core-wrong-owner'), ('[gemeinsamen Auswahlregel][method-choice]', 'keine Auswahlregel'), ('../skills/core-shared/references/tool-routing.md', '../skills/core-shared/references/MISSING.md'), ('../skills/core-shared/references/tool-routing.md', '../skills/core-shared/references/tool-routing.md#missing'), ('verbindliche Core-Methode', 'alleinige Fachmethodik'), ('Starte keine eigenen Subagenten.', 'Starte eigene Subagenten.'), ('verwalte keinen Workflowzustand', 'verwalte den Workflowzustand'), ('erweitere den Auftrag nicht', 'erweitere den Auftrag')):
                with self.subTest(profile=path.name, mutation=old):
                    self.assertIn(old, real[path])
                    self.assertTrue(findings({**real, path: real[path].replace(old, new)}))
        mutations = ((index, '(references/tool-routing.md)', '(references/MISSING.md)'), (workflow, '#' + design.slug('Fachmethoden ergänzend auswählen'), '#missing'), (routing, '## Fachmethoden ergänzend auswählen', '## Auswahl entfernt'), (workflow, 'Statushoheit bleiben bindend', 'Statushoheit wird übertragen'), (workflow, 'zusätzlich zum verbindlichen Eigentümer-Skill', 'anstelle des Eigentümer-Skills'))
        for path, old, new in mutations:
            with self.subTest(path=path.name, mutation=old):
                self.assertEqual(real[path].count(old), 1)
                self.assertTrue(findings({**real, path: real[path].replace(old, new)}))

        # RV01: the owning guide must reject precisely the historical bad anchor.
        old = 'core-shared/references/tool-routing.md#' + design.slug('Fachmethoden ergänzend auswählen')
        bad = 'core-shared/references/tool-routing.md#fachmethoden-erg-nzend-ausw-hlen'
        self.assertEqual(real[guide].count(old), 1)
        changed = findings({**real, guide: real[guide].replace(old, bad)})
        self.assertEqual(changed, ['AGENTS.md: Anker fehlt: ' + bad])

        self.assertEqual(actual_findings, [])

    def test_habit_core_snapshot_links_close_without_sdk(self):
        # Source-only producer link check; never main/package/stage, no SDK or TypeScript.
        spec = importlib.util.spec_from_file_location('habit_producer_links_tested', ROOT / 'scripts/check_habit_feedback.py')
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        files = {'core/' + name: producer.source_bytes(ROOT, name) for name in producer.CORE_FILES}
        producer.check_links(files)
        self.assertEqual(files, {'core/' + name: (ROOT / name).read_bytes() for name in producer.CORE_FILES})
        for relative in ('core-execute/references/direct-mode.md',
                         'core-typesafe/assets/evaluation-directory-AGENTS.md',
                         'core-typesafe/scripts/typesafe_collection.py',
                         'core-typesafe/scripts/typesafe_owner.py',
                         'core-typesafe/examples/images/image_probe.py',
                         'core-typesafe/examples/images/cases.json'):
            missing = 'core/.apm/skills/' + relative
            self.assertIn(missing, files)
            with self.subTest(missing=missing), self.assertRaisesRegex(producer.CheckError, 'unresolved Core snapshot link'):
                producer.check_links({k: v for k, v in files.items() if k != missing})
        # Synthetic archive data only: directly linked static sources, no runtime/build.
        expected = {name: files[name] for name in files
                    if name.startswith('core/.apm/skills/core-typesafe/examples/images/')
                    or name.endswith(('/typesafe_collection.py', '/typesafe_owner.py'))}
        self.assertEqual({Path(name).name for name in expected},
                         {'image_probe.py', 'cases.json', 'typesafe_collection.py', 'typesafe_owner.py'})
        for name in expected:
            for mutation in ('missing', 'changed'):
                actual = dict(expected)
                if mutation == 'missing':
                    del actual[name]
                else:
                    actual[name] += b'\nchanged static source\n'
                with self.subTest(source=name, mutation=mutation), tempfile.TemporaryDirectory() as directory:
                    archive = Path(directory) / 'synthetic.tar.gz'
                    with producer.tarfile.open(archive, 'w:gz') as tar:
                        for key, data in actual.items():
                            item = producer.tarfile.TarInfo('package/' + key)
                            item.size = len(data)
                            tar.addfile(item, io.BytesIO(data))
                    with self.assertRaisesRegex(producer.CheckError, 'archive inventory/content mismatch'):
                        producer.inspect_archive(archive, expected)

    def test_typesafe_source_clauses_and_mutations(self):
        # Rules and evidence requirements only: H01 is separate actual harness evidence.
        sources = {p: (ROOT / p).read_text(encoding='utf-8') for p in checker.TYPESAFE_SOURCES}
        checker.check_typesafe_sources(sources)
        for path, patterns in checker.TYPESAFE_SOURCES.items():
            for pattern in patterns:
                changed, count = re.subn(pattern, '', sources[path])
                self.assertGreater(count, 0, (path, pattern))
                with self.subTest(path=path, pattern=pattern), self.assertRaisesRegex(checker.ContractError, 'TypeSafe-Klausel fehlt'):
                    checker.check_typesafe_sources(dict(sources, **{path: changed}))
        for clause in ('Modellresultate dürfen vor dem Ersturteil gelesen werden',
                       'Eine neue Session ersetzt die Erstprüfung',
                       'Wahrscheinlichkeiten entscheiden die Freigabe',
                       'Die Leseregel garantiert technische Isolation',
                       'Nach einem MCP-Timeout folgt automatisch ein HTTP-Zweitversand',
                       'Nach einem MCP-Fehler folgt automatisch ein HTTP-Fallback',
                       'Der API-Schlüssel wird als Toolargument übergeben',
                       'Lokales health(false) belegt Livekompatibilität',
                       'Fehlende TypeSafe-Beobachtung blockiert das normale Review',
                       'Regulärer Versuch erlaubt private Volltexte ohne Datenfreigabe',
                       'Collection wird ohne lokale Config zugestellt'):
            for path in ('.apm/skills/core-review/SKILL.md', '.apm/skills/core-shared/references/typesafe-contract.md'):
                with self.subTest(clause=clause, path=path), self.assertRaisesRegex(checker.ContractError, 'TypeSafe-Ausweitung'):
                    checker.check_typesafe_sources(dict(sources, **{path: sources[path] + '\n' + clause}))
        # Superseded over-narrow wording: object identity across processes, blanket ban on earlier model runs.
        for clause, path in (('Das PreparedRequest-Objekt muss über Prozesse identisch bleiben.', '.apm/skills/core-typesafe/SKILL.md'),
                             ('Die Modellbewertung darf erst nach dem Ersturteil erzeugt werden.', '.apm/skills/core-review/SKILL.md'),
                             ('Der Planvergleich bleibt optional.', '.apm/skills/core-plan/SKILL.md'),
                             ('Der Planvergleich nur für Pilotprojekte.', '.apm/skills/core-review/SKILL.md'),
                             ('Es gilt keine aktive Pflichtphase.', '.apm/skills/core-shared/SKILL.md')):
            with self.subTest(stale=clause), self.assertRaisesRegex(checker.ContractError, 'TypeSafe-Altregel'):
                checker.check_typesafe_sources(dict(sources, **{path: sources[path] + '\n' + clause}))
        # Positive: hidden earlier evaluation stays allowed; only disclosure follows the fixed first verdict.
        review = sources['.apm/skills/core-review/SKILL.md']
        self.assertRegex(review, r'Modellbewertung vor dem unabhängigen Erstreview durchführen und verborgen speichern')
        self.assertNotRegex(review, checker.TYPESAFE_STALE)
        # Verify the real workflows group consumes this helper, not just a standalone oracle.
        with patch.object(checker, 'check_typesafe_sources', side_effect=checker.ContractError('TypeSafe sentinel')) as checked:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, 'TypeSafe sentinel'):
                checker.check_group(ROOT, 'workflows')
            checked.assert_called_once()

    def test_typesafe_mcp_is_exact_optional_catalog_tool(self):
        catalog = checker.load_yaml((ROOT / '.apm/skills/core-shared/assets/workflow-catalog.yaml').read_text(encoding='utf-8'))
        checker.check_typesafe_catalog(catalog)
        self.assertEqual(catalog['known_tool_ids'].count('typesafe-mcp-arbitype'), 1)
        # Known vocabulary only: no workflow entry declares tools, so the MCP is never a requirement.
        self.assertFalse(any(key for w in catalog['workflows'] for key in w if 'tool' in key or 'mcp' in key))
        for ids in ([t for t in catalog['known_tool_ids'] if t != 'typesafe-mcp-arbitype'],
                    [t.replace('typesafe-mcp-arbitype', 'typesafe-arbitype') for t in catalog['known_tool_ids']],
                    [t.replace('typesafe-mcp-arbitype', 'arbitype') for t in catalog['known_tool_ids']]):
            with self.subTest(ids=ids), self.assertRaisesRegex(checker.ContractError, 'TypeSafe-MCP fehlt'):
                checker.check_typesafe_catalog(dict(catalog, known_tool_ids=ids))
        with patch.object(checker, 'check_typesafe_catalog', side_effect=checker.ContractError('catalog sentinel')) as checked:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, 'catalog sentinel'):
                checker.check_group(ROOT, 'shared')
            checked.assert_called_once()

    def test_catalog_execute_entries_and_escalation(self):
        catalog = checker.load_yaml((ROOT / '.apm/skills/core-shared/assets/workflow-catalog.yaml').read_text(encoding='utf-8'))
        checker.validate_catalog(catalog)
        mutations = (
            ('input_schemas', lambda w: w['input_schemas'].remove('text')),
            ('input_schemas', lambda w: w['input_schemas'].remove('plan/v1')),
            ('output_schemas', lambda w: w['output_schemas'].append('plan/v1')),
            ('successors', lambda w: w['successors'].remove('core-plan')),
        )
        for field, mutate in mutations:
            data = copy.deepcopy(catalog)
            mutate(next(w for w in data['workflows'] if w['id'] == 'core-execute'))
            with self.subTest(field=field), self.assertRaisesRegex(checker.ContractError, 'Execute-Plan-/Direkteingang oder Eskalation fehlt'):
                checker.validate_catalog(data)

    def test_g04_canonical_clause_removals_fail_closed(self):
        # In-memory removal of the new G04 clauses; sources stay untouched.
        original_read = Path.read_text
        mutations = (
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'- Mehr Arbeitsaufwand[^\n]*', 'Aufwand allein keine Rückfrage'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Der nächste Versuch benennt neue Erkenntnis[^\n]*', 'evidenzbasierte Fortsetzung statt starrer Rundenzahl'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'- \*\*Entscheidende Sicherheitsannahmen:\*\*[^\n]*', 'entscheidende Sicherheitsannahme'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'- Delegierte Sandbox- und Testbedienung[^\n]*', 'delegierte Testbedienung beim Agenten'),
            ('workflows', '.apm/skills/core-execute/SKILL.md', r'- Starte die nächste automatische `execute ↔ review`-Reparatur[^\n]*', 'evidenzbasierte Review-Reparatur'),
            ('domains', ('.apm/skills/core-database/SKILL.md', '.apm/skills/core-tf-infra/SKILL.md', '.apm/skills/core-devops/SKILL.md'), r'Zusätzlicher Arbeitsaufwand[^\n]*', 'Domain-Kostenklausel'),
        )
        for group, relative, pattern, label in mutations:
            sources = (relative,) if isinstance(relative, str) else relative
            rewritten = {}
            for path_relative in sources:
                source = ROOT / path_relative
                text, count = re.subn(pattern, '', original_read(source, encoding='utf-8'))
                self.assertEqual(count, 1, label)
                rewritten[source] = text
            def read_text(path, *args, **kwargs):
                return rewritten.get(Path(path), original_read(path, *args, **kwargs))
            with self.subTest(label=label), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                checker.check_group(ROOT, group)

    def test_measurement_comparison_clauses_and_canonical_mutations(self):
        # Baseline group check also rejects externally mutated canonical clauses.
        with contextlib.redirect_stdout(io.StringIO()):
            checker.check_group(ROOT, 'shared')
        # Conditional noise wording protects project prose, not a runtime noise gate.
        cases = {
            'Messvergleich nur bei Auftragsbedarf': ('Nur ein konkreter Auftrag mit tatsächlich benötigtem Vorher-/Nachher-Messvergleich aktiviert die Vergleichbarkeitsregeln:', 'Jeder Vorher-/Nachher-Messvergleich aktiviert ohne Auftragsbedarf die Vergleichbarkeitsregeln:'),
            'Messvergleich mit Metrik, Einheit und Richtung': ('benannte Metrik mit Einheit und Richtung', 'beliebige Zahl ohne Einheit oder Richtung'),
            'Messvergleich mit gleichem Befehl': ('gleiche Methode und gleicher Befehl, gleiche Daten und gleiche Umgebung', 'gleiche Methode und anderer Befehl, gleiche Daten und gleiche Umgebung'),
            'Messvergleich mit aktuellen Belegen und Akzeptanz': ('aktuelle Originalbelege mit Runbezug sowie die relevante fachliche Akzeptanz', 'beliebige alte Schätzungen ohne Runbezug'),
            'Projektmethode nur bei Rauschen': ('Bei rauschenden Metriken gilt die vorhandene projektspezifische Stichproben- oder Toleranzmethode;', 'Bei allen Vergleichen gilt immer eine beliebige Toleranzmethode;'),
            'unabhängige Pflicht- und Freigabegrenzen': ('Pflichtkriterien, Korrektheit sowie Sicherheits- und Freigabegrenzen bleiben unabhängig vom Messergebnis', 'Pflichtkriterien, Korrektheit sowie Sicherheits- und Freigabegrenzen hängen vom Messergebnis ab'),
            'Messvergleich mit gleicher Methode, Daten und Umgebung': ('Der benötigte Vorher-/Nachher-Messvergleich nutzt gleiche Methode und gleicher Befehl, gleiche Daten und gleiche Umgebung.', 'Der Vorher-/Nachher-Vergleich nutzt diesmal einen anderen Befehl mit anderen Daten.'),
            'Einzelprobe beweist keine Regression': ('Eine einzelne Timingprobe beweist keine Regression.', 'Eine einzelne Timingprobe genügt als Regressionsnachweis.'),
            'fehlende Messung ist keine Verbesserung': ('Fehlende Messungen bleiben als fehlende Evidenz offen und werden nicht als Verbesserung ausgegeben.', 'Fehlende Messungen zählen als Verbesserung.'),
            'gewöhnliche Checks lösen keine Messphase aus': ('Gewöhnliche Tests und Lint aktivieren keine Mess- oder Scoringphase.', 'Jeder Testlauf startet automatisch eine Scoringphase.'),
            'Messergebnis kompensiert keine Grenzverletzung': ('Geschwindigkeitsgewinn kompensiert keine Verletzung.', 'Geschwindigkeitsgewinn gleicht eine Sicherheitsverletzung aus.'),
        }
        policies = {label: pattern for pattern, label in checker.POLICIES['shared']}
        self.assertLessEqual(set(cases), set(policies))
        for label, (allowed, violated) in cases.items():
            with self.subTest(label=label):
                self.assertRegex(allowed, '(?i)' + policies[label])
                self.assertNotRegex(violated, '(?i)' + policies[label])
        # Each new condition is removed and contradicted independently in memory.
        original_read = Path.read_text
        contract = ROOT / '.apm/skills/core-shared/references/verification.md'
        original = original_read(contract, encoding='utf-8')
        for label, (allowed, violated) in list(cases.items())[:6]:
            self.assertEqual(original.count(allowed), 1, label)
            for replacement in ('', violated):
                changed = original.replace(allowed, replacement)
                def read_text(path, *args, _text=changed, **kwargs):
                    return _text if Path(path) == contract else original_read(path, *args, **kwargs)
                with self.subTest(label=label, replacement=replacement), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                    checker.check_group(ROOT, 'shared')
        # Individual constituents cannot disappear behind a surviving compound phrase.
        for fragment in ('benannte Metrik', 'mit Einheit', 'und Richtung', 'gleiche Methode', 'gleicher Befehl', 'gleiche Daten', 'gleiche Umgebung', 'aktuelle Originalbelege', 'mit Runbezug', 'relevante fachliche Akzeptanz', 'Bei rauschenden Metriken', 'vorhandene projektspezifische', 'Stichproben- oder Toleranzmethode', 'Pflichtkriterien, Korrektheit', 'Sicherheits- und Freigabegrenzen'):
            self.assertEqual(original.count(fragment), 1, fragment)
            for replacement in ('', 'abweichend'):
                changed = original.replace(fragment, replacement)
                def read_text(path, *args, _text=changed, **kwargs):
                    return _text if Path(path) == contract else original_read(path, *args, **kwargs)
                with self.subTest(fragment=fragment, replacement=replacement), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(checker.ContractError):
                    checker.check_group(ROOT, 'shared')
        # Existing canonical clause removals remain covered.
        original_read = Path.read_text
        contract = ROOT / '.apm/skills/core-shared/references/verification.md'
        removals = (
            (r'gleiche Methode und gleicher Befehl, gleiche Daten und gleiche Umgebung', 'Messvergleich mit gleichem Befehl|Messvergleich mit gleicher Methode, Daten und Umgebung'),
            (r'eine einzelne Timingprobe beweist keine Regression', 'Einzelprobe beweist keine Regression'),
            (r'nicht als Verbesserung ausgegeben', 'fehlende Messung ist keine Verbesserung'),
            (r'Gewöhnliche Tests und Lint aktivieren keine Mess- oder Scoringphase', 'gewöhnliche Checks lösen keine Messphase aus'),
            (r'Geschwindigkeitsgewinn kompensiert keine Verletzung', 'Messergebnis kompensiert keine Grenzverletzung'),
        )
        for pattern, label in removals:
            text, count = re.subn(pattern, '', original_read(contract, encoding='utf-8'))
            self.assertEqual(count, 1, label)
            def read_text(path, *args, _text=text, **kwargs):
                return _text if Path(path) == contract else original_read(path, *args, **kwargs)
            with self.subTest(label=label), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                checker.check_group(ROOT, 'shared')

    def test_dox_docs_relation_fails_closed_per_field(self):
        # Each modeled docs/DOX input is mandatory; a missing field is never a silent default.
        base = next(c['input'] for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases'] if c['id'] == 'docs-positive')
        checker.validate_scenario(base)
        for field in base:
            if field == 'kind':
                continue
            mutated = {k: v for k, v in base.items() if k != field}
            with self.subTest(field=field), self.assertRaises((KeyError, checker.ContractError)):
                checker.validate_scenario(mutated)
        for field, value in (('mode', 'draft'), ('tree', 'unknown')):
            with self.subTest(field=field), self.assertRaisesRegex(checker.ContractError, 'unbekannt'):
                checker.validate_scenario(dict(base, **{field: value}))

    def test_dox_clauses_accept_contract_wording_and_reject_violations(self):
        # Fixture sentences per clause; text matches show contract wording, not live model compliance.
        cases = {
            'kein Abschluss ohne Dokumentation': ('Relevante Änderungen werden nicht ohne erforderliche Dokumentationsaktualisierung abgeschlossen.', 'Relevante Änderungen werden auch ohne Dokumentation abgeschlossen.'),
            'begründeter DOX-Pass': ('Ist kein Guide-Edit nötig, werden geprüfte Pfade und der Grund festgehalten.', 'Ist kein Guide-Edit nötig, entfällt der DOX-Pass.'),
            'read-only ohne DOX-Setuppflicht': ('Read-only-Arbeit und harmlose Änderungen lösen weder Schreib- noch Setup-Pflichten aus.', 'Read-only-Arbeit initialisiert fehlende Guides automatisch.'),
            'Laufartefakt ist keine Projektdokumentation': ('Laufartefakte ersetzen keine Projektdokumentation.', 'Das Taskresultat dokumentiert die neue API ausreichend.'),
            'belegte neue Dokumentationslücke': ('Eine neue Dokumentationslücke wird ergänzt, wenn bestätigter Task, aktueller Diff und autoritative Quelle sie belegen.', 'Eine vermutete Dokumentationslücke wird vorsorglich ergänzt.'),
            'DOX-Setup nur nach Planbestätigung': ('Erst Planbestätigung autorisiert die benannten Setupwirkungen.', 'Execute initialisiert fehlende Guides spontan.'),
            'fehlende DOX-Setupfähigkeit blockiert': ('Fehlt es oder eine gültige Quelle, wird der Task blockiert.', 'Fehlt dox-setup, installiert Execute es still nach.'),
            'kein Secretwert in Dokumentation': ('Dokumentation zu Secrets nennt nur freigegebene Referenznamen und enthält weder Secretwerte noch Dateiinhalte.', 'Die Dokumentation zitiert den API-Schlüssel aus der .env-Datei.'),
            'Plan prüft DOX-Zustand': ('Prüfe den DOX-Zustand im Änderungspfad: vorhanden, fehlend, teilweise oder widersprüchlich.', 'Eine vorhandene AGENTS.md gilt als vollständiger Baum.'),
            'neue belegte Lücke ohne Driftpflicht': ('Eine vorhandene widersprüchliche Prosa ist für eine neue belegte Dokumentationslücke nicht erforderlich.', 'Ohne widersprüchliche Prosa ist keine Dokumentationsänderung zulässig.'),
        }
        policies = {label: pattern for group in ('shared', 'workflows', 'domains') for pattern, label in checker.POLICIES[group]}
        self.assertLessEqual(set(cases), set(policies))
        for label, (allowed, violated) in cases.items():
            with self.subTest(label=label):
                self.assertRegex(allowed, '(?i)' + policies[label])
                self.assertNotRegex(violated, '(?i)' + policies[label])

    def test_dox_mutations_of_canonical_sources_fail(self):
        # Controlled in-memory removal of canonical DOX sentences; sources stay untouched.
        original_read = Path.read_text
        mutations = (
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Bei schreibender Arbeit an bestehender oder neuer Funktionalität[^\n]*', 'DOX Root-to-Target-Dokumentation'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Relevante Änderungen werden nicht ohne[^.]*\.', 'kein Abschluss ohne Dokumentation'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Eine neue Dokumentationslücke darf[^.]*\.', 'belegte neue Dokumentationslücke'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Erst Planbestätigung[^.]*\.', 'DOX-Setup nur nach Planbestätigung'),
            ('shared', '.apm/skills/core-shared/references/workflow-contract.md', r'Dokumentation zu Secrets[^\n]*', 'kein Secretwert in Dokumentation'),
            ('workflows', '.apm/skills/core-plan/SKILL.md', r'Prüfe bei schreibender Arbeit zusätzlich den DOX-Zustand[^\n]*', 'Plan prüft DOX-Zustand'),
            ('workflows', '.apm/skills/core-execute/SKILL.md', r'Initialisierung oder Ergänzung darf nur[^.]*\.', 'Execute initialisiert nur gescopt'),
            ('workflows', '.apm/skills/core-review/SKILL.md', r'ein Laufprotokoll ist kein Ersatz für Projektdokumentation', 'Review prüft Projektdokumentation'),
            ('domains', '.apm/skills/core-docs/SKILL.md', r'Eine vorhandene widersprüchliche Prosa[^.]*\.', 'neue belegte Lücke ohne Driftpflicht'),
            ('domains', '.apm/skills/core-docs/SKILL.md', r'Fehlt die Fähigkeit oder eine gültige Quelle[^.]*\.', 'Docs blockiert ohne DOX-Setupfähigkeit'),
        )
        for group, relative, pattern, label in mutations:
            source = ROOT / relative
            text, count = re.subn(pattern, '', original_read(source, encoding='utf-8'))
            self.assertEqual(count, 1, label)
            def read_text(path, *args, _text=text, _source=source, **kwargs):
                return _text if Path(path) == _source else original_read(path, *args, **kwargs)
            with self.subTest(label=label), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, label):
                checker.check_group(ROOT, group)

    def test_rv02_core_docs_rejects_reintroduced_drift_only_rules(self):
        # In-memory reinsertion of the former exclusive drift-only clauses of the complete consumer.
        source = ROOT / '.apm/skills/core-docs/SKILL.md'
        original_read = Path.read_text
        text = original_read(source, encoding='utf-8')
        checker.check_docs_source(text)
        legacy = (
            'Der Skill bearbeitet nur Dokumentation, deren Drift durch den bestätigten Task oder einen aktuellen Diff nachgewiesen ist.',
            '- Dokumentiere ausschließlich belegte Drift innerhalb des bestätigten Docs-Scopes.',
            'Ändere nur die nachgewiesen veralteten Sätze, Tabellenzeilen, Beispiele oder Referenzen.',
        )
        for clause in legacy:
            mutated = text.replace('## Workflow\n', clause + '\n\n## Workflow\n', 1)
            self.assertNotEqual(mutated, text)
            def read_text(path, *args, _text=mutated, **kwargs):
                return _text if Path(path) == source else original_read(path, *args, **kwargs)
            with self.subTest(clause=clause[:40]), patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checker.ContractError, 'ausschließlich auf Drift'):
                checker.check_group(ROOT, 'domains')
        # Gap-inclusive limits and unrelated drift reporting stay allowed.
        checker.check_docs_source('Dokumentiere nur eine belegte neue Dokumentationslücke oder Drift. Unabhängige Altlasten werden als offene Drift gemeldet.')
        # The modeled relations remain: new API without prior prose passes, unproven new gap fails.
        cases = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        checker.validate_scenario(cases['dox-new-api-config-connections']['input'])
        for case_id in ('dox-new-gap-unconfirmed-task', 'dox-new-gap-no-diff', 'docs-unproven'):
            with self.subTest(case=case_id), self.assertRaises(checker.ContractError):
                checker.validate_scenario(cases[case_id]['input'])

    def test_repair_basis_survives_replacement_plan_and_new_run(self):
        cases = {c['id']: c for c in json.loads((ROOT / 'tests/core_scenario_cases.json').read_text())['cases']}
        repeated = cases['g04-progression-replacement-repeated-basis']['input']
        self.assertEqual([e['plan_path'] for e in repeated['events'] if e['action'] == 'plan'], [
            '.agentic-workflow/plans/plan-G01-M02-v1-p01.md',
            '.agentic-workflow/plans/plan-G01-M02-v1-p02.md',
        ])
        self.assertEqual([e['run_path'] for e in repeated['events'] if e['action'] == 'new'], [
            '.agentic-workflow/runs/run-G01-M02-v1-p01-r01/state.yaml',
            '.agentic-workflow/runs/run-G01-M02-v1-p02-r01/state.yaml',
        ])
        with self.assertRaisesRegex(checker.ContractError, 'Reparatur wiederholt dieselbe Begründung'):
            checker.validate_scenario(repeated)
        fresh = cases['g04-progression-replacement-new-basis']['input']
        checker.validate_scenario(fresh)
        # A separate modeled chain has no shared global repair history.
        checker.validate_scenario(fresh)

    def test_staged_targetsets(self):
        for group in checker.TARGET_GROUPS:
            paths = checker.targets(ROOT, group)
            self.assertTrue(paths)
            self.assertTrue(all(path.is_relative_to(ROOT) for path in paths))
            if group == 'milestones':
                self.assertEqual(len(paths), 3)
                self.assertFalse(any('core-shared' in str(path) for path in paths))
            if group == 'setup':
                self.assertFalse(any('README' in str(path) for path in paths))
        print('STAGING: sechs getrennte explizite versionierte Targetsets')

    def test_all_cli_groups_and_authoring_switch(self):
        for group in checker.GROUPS:
            with self.subTest(group=group), patch.object(checker, 'check_group') as checked, patch.object(checker, 'selftest') as tested:
                self.assertEqual(checker.main(['--group', group]), 0)
                if group == 'all':
                    self.assertEqual([c.args[1] for c in checked.call_args_list], list(checker.TARGET_GROUPS))
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
        with tempfile.TemporaryDirectory(prefix='core-contract-') as directory:
            root = Path(directory)
            path = root / 'target.md'
            path.write_text('read-only')
            with self.assertRaisesRegex(checker.ContractError, 'Authoringtool fehlt'), patch.object(checker.subprocess, 'run') as run:
                checker.authoring(root, [path], root / 'absent-tools')
            run.assert_not_called()
            self.assertEqual(path.read_text(), 'read-only')

    def test_authoring_exact_paths_read_only_and_observation(self):
        with tempfile.TemporaryDirectory(prefix='core-contract-') as directory:
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
        paths = list(dict.fromkeys(p for g in checker.TARGET_GROUPS for p in checker.targets(ROOT, g)))
        before = checker.snapshot(paths)
        observations = []
        for group in (*checker.TARGET_GROUPS, 'all'):
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
