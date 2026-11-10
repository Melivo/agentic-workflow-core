"""Synthetic, offline regressions for pure plan-comparison values, not model quality."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / '.apm/skills/core-typesafe/scripts/plan_comparison.py'
spec = importlib.util.spec_from_file_location('plan_comparison', MODULE)
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.plan = b'# synthetic plan\r\nAC01: synthetic\r\n'
        self.review_bytes = b'Independent synthetic initial review.\r\n'
        self.criteria = {'AC01': 'Synthetic exact requirement.', 'AC02': 'Second criterion.'}
        self.binding = pc.bind_plan(project_id='project-opaque-1', plan_ref='plan.md',
                                    plan_bytes=self.plan, criteria=self.criteria)
        self.review = self.fix()
        self.evaluation = {
            'profile': 'requirement_coverage', 'outcome': 'unresolved',
            'reason': 'no_confirmed_evaluation_rule', 'uncertainty': 'unassessed',
            'answers': {'covers': {'type': 'noul', 'noul': 0.99}}, 'references': ['source.md'],
            'error': None, 'http_status': None, 'request_sent': True,
            'requested_model': 'synthetic-request-v1', 'response_model': 'synthetic-observed-v2',
            'question_version': '2', 'question_fingerprint': 'a' * 64,
            'core_version': 'synthetic-core', 'duration_seconds': 0.25,
            'usage': {'input_tokens': None, 'output_tokens': 8},
        }
        self.adjudication = {'label': 'material_defect', 'evidence_ref': 'evidence.md#AC01',
                             'reviewer_role': 'qa-reviewer', 'recorded_at': '2026-11-09T12:00:01Z'}

    def fix(self, **changes):
        args = dict(plan_bytes=self.plan, criteria=self.criteria, review_ref='initial-review.md',
                    review_bytes=self.review_bytes, verdicts={'AC01': 'no_defect_found', 'AC02': 'defect_found'},
                    reviewer_role='qa-reviewer', recorded_at='2026-11-09T12:00:00Z')
        args.update(changes)
        return pc.fix_review(self.binding, **args)

    def event(self, **changes):
        args = dict(plan_bytes=self.plan, criteria=self.criteria, review_bytes=self.review_bytes,
                    criterion_id='AC01', evaluation=self.evaluation, adjudication=self.adjudication)
        binding = changes.pop('binding', self.binding)
        review = changes.pop('initial_review', self.review)
        args.update(changes)
        model = pc.model_event(binding, criterion_id=args.pop('criterion_id'), evaluation=args.pop('evaluation'), selection='eligible')
        return pc.comparison_event(model, review, **args)

    def unresolved(self, reason, **changes):
        event = self.event(**changes)
        self.assertEqual(event['adjudication']['label'], 'unresolved')
        self.assertEqual(event['adjudication']['reported_label'], 'material_defect')
        self.assertEqual(event['unresolved_reason'], reason)
        return event

    def test_model_event_precedes_review_without_fabricated_adjudication(self):
        inputs = deepcopy([self.binding, self.evaluation])
        model = pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation)
        self.assertIsNone(model['initial_review'])
        self.assertIsNone(model['adjudication'])
        self.assertEqual(model['unresolved_reason'], 'initial_review_pending')
        self.assertEqual(model['event_type'], pc.MODEL_EVENT_TYPE)
        self.assertEqual(model['observation']['model_status'], 'uncertain')
        compared = pc.comparison_event(model, self.review, plan_bytes=self.plan, criteria=self.criteria,
                       review_bytes=self.review_bytes, adjudication=self.adjudication)
        self.assertEqual(model['selection'], 'unknown')
        self.assertEqual(compared['selection'], 'unknown')
        self.assertEqual(compared['adjudication']['label'], 'unresolved')
        self.assertEqual(compared['unresolved_reason'], 'selection_unknown')
        self.assertEqual(compared['model_event_id'], model['event_id'])
        self.assertNotEqual(compared['event_id'], model['event_id'])
        self.assertEqual(compared['observation'], model['observation'])
        self.assertIsNone(model['adjudication'])
        self.assertEqual(inputs, [self.binding, self.evaluation])
        ledger = pc.append_event([model], compared)
        self.assertEqual(ledger, [model, compared])
        revised = pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation, previous=model)
        self.assertEqual(revised['previous_id'], model['event_id'])
        self.assertEqual(revised['revision'], 2)
        self.assertEqual(len(pc.append_event(ledger, revised)), 3)
        with self.assertRaisesRegex(pc.ComparisonError, '^predecessor_mismatch$'):
            self.event(previous=model)
        changed = pc.model_event(self.binding, criterion_id='AC01', evaluation={**self.evaluation, 'duration_seconds': 1})
        with self.assertRaisesRegex(pc.ComparisonError, '^payload_conflict$'):
            pc.append_event([model], changed)

    def test_exact_originals_and_complete_criterion_binding(self):
        self.assertEqual(self.binding['plan_sha256'], hashlib.sha256(self.plan).hexdigest())
        self.assertEqual(self.review['review_sha256'], hashlib.sha256(self.review_bytes).hexdigest())
        self.assertEqual(self.binding['criteria_ids'], ['AC01', 'AC02'])
        event = self.event()
        self.assertIsNone(event['unresolved_reason'])
        self.assertEqual(event['adjudication']['label'], 'material_defect')
        self.assertEqual(event['initial_review']['verdicts']['AC01'], 'no_defect_found')
        self.assertEqual(json.loads(json.dumps(event)), event)

    def test_byte_and_line_ending_drift_is_not_normalized(self):
        for changed in [self.plan + b' ', self.plan.replace(b'\r\n', b'\n'), b'\xef\xbb\xbf' + self.plan]:
            with self.subTest(plan=changed):
                self.unresolved('binding_mismatch', plan_bytes=changed)
                with self.assertRaisesRegex(pc.ComparisonError, '^binding_mismatch$'):
                    self.fix(plan_bytes=changed)
        for changed in [self.review_bytes + b'.', self.review_bytes.replace(b'\r\n', b'\n')]:
            self.unresolved('initial_review_mismatch', review_bytes=changed)

    def test_criterion_drift_missing_extra_and_text_change(self):
        cases = [{'AC01': self.criteria['AC01']}, {**self.criteria, 'AC03': 'extra'},
                 {**self.criteria, 'AC01': self.criteria['AC01'] + ' '},
                 {**self.criteria, 'AC01': 'Line\r\n'}, {**self.criteria, 'AC01': 'Line\n'}]
        for criteria in cases:
            with self.subTest(criteria=criteria):
                self.unresolved('binding_mismatch', criteria=criteria)
        reordered = dict(reversed(list(self.criteria.items())))
        self.assertIsNone(self.event(criteria=reordered)['unresolved_reason'])
        with self.assertRaises(pc.ComparisonError):
            self.event(criterion_id='AC99')

    def test_missing_originals_or_initial_review_remain_unresolved(self):
        for key in ('plan_bytes', 'criteria', 'review_bytes', 'initial_review'):
            with self.subTest(missing=key):
                self.unresolved('missing_original', **{key: None})
        with self.assertRaisesRegex(pc.ComparisonError, '^original_bytes_required$'):
            self.fix(review_bytes=None)

    def test_incomplete_invalid_or_contradictory_initial_review(self):
        for verdicts in [{'AC01': 'no_defect_found'}, {**self.review['verdicts'], 'AC03': 'defect_found'},
                         {'AC01': 'unresolved', 'AC02': 'no_defect_found'}]:
            with self.subTest(verdicts=verdicts), self.assertRaises(pc.ComparisonError):
                self.fix(verdicts=verdicts)
        other = deepcopy(self.review)
        other['binding']['plan_sha256'] = '0' * 64
        self.unresolved('initial_review_mismatch', initial_review=other)
        other = deepcopy(self.review)
        other['binding']['criteria_sha256'] = '0' * 64
        self.unresolved('initial_review_mismatch', initial_review=other)
        other = deepcopy(self.review)
        del other['verdicts']['AC02']
        with self.assertRaises(pc.ComparisonError):
            self.event(initial_review=other)

    def test_review_must_precede_adjudication_and_utc_is_explicit(self):
        for when in ['2026-11-09T12:00:00Z', '2026-11-09T11:59:59Z']:
            self.unresolved('review_not_prior', adjudication={**self.adjudication, 'recorded_at': when})
        for when in ['2026-11-09T12:00:01', '2026-11-09T12:00:01+01:00', '2026-02-30T12:00:01Z', 'SECRET']:
            with self.subTest(when=when), self.assertRaises(pc.ComparisonError):
                self.event(adjudication={**self.adjudication, 'recorded_at': when})
        self.assertIsNone(self.event(adjudication={**self.adjudication, 'recorded_at': '2026-11-09T12:00:00.000001Z'})['unresolved_reason'])

    def test_uncertainty_error_selection_and_reviewer_label_are_distinct(self):
        event = self.event()
        self.assertEqual(event['observation']['model_status'], 'uncertain')
        self.assertEqual(event['observation']['uncertainty'], 'unassessed')
        self.assertEqual(event['observation']['api_error'], {'occurred': False, 'http_status': None})
        self.assertEqual(event['selection'], 'eligible')
        self.assertEqual(event['adjudication']['label'], 'material_defect')
        failure = {**self.evaluation, 'outcome': 'error', 'error': 'timeout', 'answers': None,
                   'uncertainty': 'no_model_answer', 'usage': None, 'response_model': None, 'http_status': 503}
        event = self.event(evaluation=failure)
        self.assertEqual(event['observation']['model_status'], 'api_error')
        self.assertEqual(event['observation']['api_error'], {'occurred': True, 'http_status': 503})
        self.assertEqual(event['adjudication']['label'], 'material_defect')
        for selection in ['excluded', 'contaminated']:
            event = self.unresolved('selection_' + selection, selection=selection)
            self.assertEqual(event['observation']['model_status'], 'uncertain')
            self.assertEqual(event['selection'], selection)

    def test_no_thresholds_or_automatic_semantic_adjudication(self):
        for p in [0, 0.5, 1]:
            evaluation = {**self.evaluation, 'answers': {'covers': {'type': 'noul', 'noul': p}}}
            for label in pc.LABELS:
                event = self.event(evaluation=evaluation, adjudication={**self.adjudication, 'label': label})
                self.assertEqual(event['observation']['model_status'], 'uncertain')
                self.assertEqual(event['adjudication']['label'], label)
        for outcome in ['alert', 'unflagged', 'selection_excluded']:
            with self.assertRaises(pc.ComparisonError):
                self.event(evaluation={**self.evaluation, 'outcome': outcome})

    def test_no_fit_and_unknown_metadata_are_not_zero(self):
        value = {**self.evaluation, 'outcome': 'no_fit', 'answers': None, 'uncertainty': 'no_model_answer',
                 'request_sent': False, 'requested_model': None, 'response_model': None,
                 'core_version': None, 'question_version': None, 'question_fingerprint': None,
                 'duration_seconds': None, 'usage': {}}
        obs = self.event(evaluation=value)['observation']
        self.assertEqual(obs['model_status'], 'no_fit')
        self.assertIsNone(obs['duration_seconds'])
        self.assertEqual(obs['usage'], {'input_tokens': None, 'output_tokens': None})
        for key in ['requested_model', 'response_model', 'core_version', 'question_fingerprint']:
            self.assertIsNone(obs[key])

    def test_observed_metadata_and_choice_probabilities_are_preserved(self):
        value = {**self.evaluation, 'answers': {'relation': {'type': 'choice', 'choice': 'not-exported',
                  'confidence': 0.8, 'probabilities': {'option-a': 0.8, 'option-b': 0.2}}}}
        obs = self.event(evaluation=value)['observation']
        self.assertEqual(obs['requested_model'], 'synthetic-request-v1')
        self.assertEqual(obs['response_model'], 'synthetic-observed-v2')
        self.assertEqual(obs['question_fingerprint'], 'a' * 64)
        self.assertEqual(obs['usage'], self.evaluation['usage'])
        self.assertEqual(obs['duration_seconds'], 0.25)
        self.assertEqual(obs['probabilities']['relation'], {'confidence': 0.8, 'probabilities': {'option-a': 0.8, 'option-b': 0.2}})

    def test_invalid_metadata_numeric_and_payload_values_rejected(self):
        cases = [{'duration_seconds': -1}, {'duration_seconds': float('nan')},
                 {'duration_seconds': float('inf')}, {'usage': {'input_tokens': True}},
                 {'usage': {'output_tokens': -1}}, {'request_sent': 'unknown'}, {'http_status': True},
                 {'http_status': 999}, {'question_fingerprint': 'not-a-hash'},
                 {'core_version': 'raw secret with spaces'}, {'uncertainty': 'certain'},
                 {'answers': {'covers': {'type': 'noul', 'noul': True}}},
                 {'answers': {'covers': {'type': 'noul', 'noul': 1.1}}},
                 {'outcome': 'error', 'error': 'timeout'}, {'error': 'timeout'}, {'outcome': 'no_fit'},
                 {'requested_model': 'a' * (pc.MAX_IDENTIFIER_LENGTH + 1)}]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(pc.ComparisonError):
                self.event(evaluation={**self.evaluation, **change})

    def test_minimal_export_and_fixed_errors_do_not_leak_raw_text(self):
        secret = 'SYNTHETIC PRIVATE KEY SENTINEL'
        evaluation = {**self.evaluation, 'payload': secret, 'reason': secret, 'references': [secret],
                      'raw_exception': RuntimeError(secret)}
        event = self.event(evaluation=evaluation)
        exported = json.dumps(event)
        for raw in [secret, self.plan.decode(), self.review_bytes.decode(), *self.criteria.values()]:
            self.assertNotIn(raw, exported)
        evaluation = {**evaluation, 'outcome': 'error', 'error': RuntimeError(secret), 'answers': None,
                      'uncertainty': 'no_model_answer'}
        self.assertNotIn(secret, json.dumps(self.event(evaluation=evaluation)))
        with self.assertRaises(pc.ComparisonError) as error:
            self.event(evaluation={**self.evaluation, 'requested_model': secret})
        self.assertEqual(str(error.exception), 'invalid_data')
        self.assertIsNone(error.exception.__context__)
        for extra in ['text', 'key', 'raw_review']:
            with self.assertRaises(pc.ComparisonError):
                self.event(adjudication={**self.adjudication, extra: secret})

    def test_event_identity_version_project_plan_criterion_and_revision(self):
        first = self.event()
        self.assertTrue(first['event_id'].startswith('pc1-'))
        self.assertEqual(first, self.event())
        second = self.event(criterion_id='AC02')
        self.assertNotEqual(first['event_id'], second['event_id'])
        other_binding = {**self.binding, 'project_id': 'project-opaque-2'}
        other_review = {**self.review, 'binding': other_binding}
        self.assertNotEqual(first['event_id'], self.event(binding=other_binding, initial_review=other_review)['event_id'])
        changed_binding = pc.bind_plan(project_id='project-opaque-1', plan_ref='plan.md', plan_bytes=self.plan + b'.', criteria=self.criteria)
        changed_review = pc.fix_review(changed_binding, plan_bytes=self.plan + b'.', criteria=self.criteria,
                         review_bytes=self.review_bytes, review_ref='initial-review-2.md', verdicts=self.review['verdicts'],
                         reviewer_role='qa-reviewer', recorded_at='2026-11-09T12:00:00Z')
        self.assertNotEqual(first['event_id'], self.event(binding=changed_binding, initial_review=changed_review, plan_bytes=self.plan + b'.')['event_id'])

    def test_idempotency_and_same_id_different_payload_conflict(self):
        first = self.event()
        ledger = pc.append_event([], first)
        self.assertEqual(pc.append_event(ledger, deepcopy(first)), ledger)
        changed = self.event(adjudication={**self.adjudication, 'label': 'no_material_defect'})
        self.assertEqual(first['event_id'], changed['event_id'])
        with self.assertRaisesRegex(pc.ComparisonError, '^payload_conflict$'):
            pc.append_event(ledger, changed)

    def test_revision_retains_predecessor_and_originals_without_mutation(self):
        inputs = deepcopy([self.binding, self.review, self.criteria, self.evaluation, self.adjudication])
        first = self.event()
        ledger = pc.append_event([], first)
        prior = deepcopy(ledger)
        second = self.event(previous=first, adjudication={**self.adjudication, 'label': 'no_material_defect'})
        result = pc.append_event(ledger, second)
        self.assertEqual(second['revision'], 2)
        self.assertEqual(second['previous_id'], first['event_id'])
        self.assertEqual(second['supersedes'], first['event_id'])
        self.assertNotEqual(second['event_id'], first['event_id'])
        self.assertEqual(result[0], first)
        self.assertEqual(ledger, prior)
        self.assertEqual(inputs, [self.binding, self.review, self.criteria, self.evaluation, self.adjudication])
        result[0]['initial_review']['verdicts']['AC01'] = 'changed'
        second['observation']['usage']['output_tokens'] = 999
        self.assertEqual(ledger, prior)
        self.assertEqual(result[1]['observation']['usage']['output_tokens'], 8)

    def test_revision_skips_forks_wrong_predecessor_and_missing_history_rejected(self):
        first = self.event()
        second = self.event(previous=first)
        third = self.event(previous=second)
        with self.assertRaisesRegex(pc.ComparisonError, '^revision_conflict$'):
            pc.append_event([], second)
        with self.assertRaisesRegex(pc.ComparisonError, '^revision_conflict$'):
            pc.append_event([first], third)
        with self.assertRaisesRegex(pc.ComparisonError, '^predecessor_mismatch$'):
            self.event(previous=self.event(criterion_id='AC02'))
        corrupted = deepcopy(second)
        corrupted['previous_id'] = corrupted['supersedes'] = 'pc1-' + '0' * 64
        with self.assertRaisesRegex(pc.ComparisonError, '^revision_conflict$'):
            pc.append_event([first], corrupted)
        corrupted = deepcopy(second)
        corrupted['event_id'] = 'pc1-' + '0' * 64
        with self.assertRaisesRegex(pc.ComparisonError, '^identity_mismatch$'):
            pc.append_event([first], corrupted)
        branch = self.event(previous=first, adjudication={**self.adjudication, 'label': 'unresolved'})
        with self.assertRaisesRegex(pc.ComparisonError, '^payload_conflict$'):
            pc.append_event([first, second], branch)

    def test_recorded_source_selection_cannot_be_promoted_or_laundered(self):
        for selection in ('contaminated', 'excluded'):
            model = pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation, selection=selection)
            original = deepcopy(model)
            for replacement in ('eligible', 'unknown'):
                with self.subTest(selection=selection, replacement=replacement):
                    with self.assertRaisesRegex(pc.ComparisonError, '^selection_conflict$'):
                        pc.comparison_event(model, self.review, plan_bytes=self.plan, criteria=self.criteria,
                            review_bytes=self.review_bytes, adjudication=self.adjudication, selection=replacement)
                    with self.assertRaisesRegex(pc.ComparisonError, '^selection_conflict$'):
                        pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation,
                            selection=replacement, previous=model)
            kept = pc.comparison_event(model, self.review, plan_bytes=self.plan, criteria=self.criteria,
                       review_bytes=self.review_bytes, adjudication=self.adjudication)
            self.assertEqual(kept['selection'], selection)
            self.assertEqual(kept['adjudication']['label'], 'unresolved')
            self.assertEqual(kept['unresolved_reason'], 'selection_' + selection)
            self.assertEqual(model, original)

    def test_previous_selection_survives_unresolved_intermediate_revisions(self):
        for selection in ('contaminated', 'excluded'):
            first = self.event(selection=selection)
            middle = self.event(previous=first, selection=selection, review_bytes=None)
            last = self.event(previous=middle, selection=selection, initial_review=None, review_bytes=None)
            ledger = pc.append_event(pc.append_event([first], middle), last)
            self.assertEqual(last['revision'], 3)
            self.assertEqual(last['initial_review'], self.review)
            for prior in (first, middle, last):
                for replacement in ('eligible', 'unknown'):
                    with self.subTest(selection=selection, revision=prior['revision'], replacement=replacement):
                        with self.assertRaisesRegex(pc.ComparisonError, '^selection_conflict$'):
                            self.event(previous=prior, selection=replacement)
            self.assertEqual(ledger, [first, middle, last])

    def test_unknown_selection_can_be_clarified_without_changing_original(self):
        model = pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation)
        original = deepcopy(model)
        first = pc.comparison_event(model, self.review, plan_bytes=self.plan, criteria=self.criteria,
                    review_bytes=self.review_bytes, adjudication=self.adjudication)
        clarified = pc.comparison_event(model, self.review, plan_bytes=self.plan, criteria=self.criteria,
                    review_bytes=self.review_bytes, adjudication=self.adjudication, selection='eligible', previous=first)
        self.assertIsNone(clarified['unresolved_reason'])
        self.assertEqual(clarified['adjudication']['label'], 'material_defect')
        self.assertEqual(clarified['initial_review'], first['initial_review'])
        self.assertEqual(clarified['supersedes'], first['event_id'])
        revised_model = pc.model_event(self.binding, criterion_id='AC01', evaluation=self.evaluation,
                            selection='eligible', previous=model)
        self.assertEqual(revised_model['selection'], 'eligible')
        self.assertEqual(model, original)

    def test_fixed_initial_review_cannot_change_in_comparison_revision(self):
        first = self.event()
        original = deepcopy(first)
        changes = [dict(review_bytes=self.review_bytes + b'Changed initial answer.'),
                   dict(review_ref='changed-initial.md'),
                   dict(verdicts={**self.review['verdicts'], 'AC01': 'defect_found'}),
                   dict(recorded_at='2026-11-09T12:00:00.5Z'),
                   dict(reviewer_role='another-reviewer')]
        for change in changes:
            with self.subTest(change=change):
                changed_review = self.fix(**change)
                with self.assertRaisesRegex(pc.ComparisonError, '^initial_review_conflict$'):
                    self.event(previous=first, initial_review=changed_review,
                               review_bytes=change.get('review_bytes', self.review_bytes))
        corrected = self.event(previous=first, adjudication={**self.adjudication, 'label': 'no_material_defect'})
        self.assertEqual(corrected['initial_review'], original['initial_review'])
        self.assertEqual(corrected['adjudication']['label'], 'no_material_defect')
        self.assertEqual(pc.append_event([first], corrected), [original, corrected])
        self.assertEqual(first, original)

    def test_fixed_review_survives_missing_originals_and_rejects_later_replacement(self):
        first = self.event()
        missing = self.event(previous=first, initial_review=None, review_bytes=None)
        still_missing = self.event(previous=missing, initial_review=None, review_bytes=None)
        for event in (missing, still_missing):
            self.assertEqual(event['initial_review'], first['initial_review'])
            self.assertEqual(event['adjudication']['label'], 'unresolved')
            self.assertEqual(event['unresolved_reason'], 'missing_original')
        changed_review = self.fix(review_ref='changed-after-gap.md')
        with self.assertRaisesRegex(pc.ComparisonError, '^initial_review_conflict$'):
            self.event(previous=still_missing, initial_review=changed_review)
        restored = self.event(previous=still_missing, initial_review=None)
        self.assertIsNone(restored['unresolved_reason'])
        self.assertEqual(restored['initial_review'], self.review)
        self.assertEqual(restored['revision'], 4)
        self.assertEqual(restored['previous_id'], still_missing['event_id'])
        self.assertEqual(len(pc.append_event([first, missing, still_missing], restored)), 4)

    def test_missing_initial_originals_can_be_supplied_later(self):
        first = self.event(initial_review=None, review_bytes=None)
        pending = self.event(previous=first, initial_review=None, review_bytes=None)
        self.assertIsNone(pending['initial_review'])
        completed = self.event(previous=pending)
        self.assertIsNone(completed['unresolved_reason'])
        self.assertEqual(completed['initial_review'], self.review)
        self.assertEqual(completed['adjudication']['label'], 'material_defect')
        self.assertEqual(pc.append_event([first, pending], completed), [first, pending, completed])
        known_record = self.event(review_bytes=None)
        supplied_bytes = self.event(previous=known_record)
        self.assertEqual(supplied_bytes['initial_review'], known_record['initial_review'])
        self.assertIsNone(supplied_bytes['unresolved_reason'])

    def test_binding_and_review_are_detached_json_values(self):
        original = deepcopy(self.binding)
        self.criteria['AC01'] = 'changed after binding'
        self.assertEqual(self.binding, original)
        self.review['binding']['criteria_ids'].append('AC99')
        self.assertEqual(self.binding, original)
        with self.assertRaises(pc.ComparisonError):
            pc.bind_plan(project_id='p', plan_ref='plan', plan_bytes='not bytes', criteria={'C': 'text'})
        for criteria in [{}, {'C': ''}, {'C': '\ud800'}]:
            with self.assertRaises(pc.ComparisonError):
                pc.bind_plan(project_id='p', plan_ref='plan', plan_bytes=b'plan', criteria=criteria)

    def test_no_file_network_process_clock_or_workflow_effect(self):
        source = MODULE.read_text()
        tree = ast.parse(source)
        imports = {n.module if isinstance(n, ast.ImportFrom) else alias.name
                   for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                   for alias in (n.names if isinstance(n, ast.Import) else [None])}
        self.assertEqual(imports, {'datetime', 'hashlib', 'json', 'math', 're'})
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertTrue(called.isdisjoint({'open', 'print', 'eval', 'exec', 'input', '__import__'}))
        with patch('builtins.open', side_effect=AssertionError('file IO')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network IO')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('process IO')):
            binding = pc.bind_plan(project_id='p', plan_ref='plan', plan_bytes=self.plan, criteria=self.criteria)
            review = pc.fix_review(binding, plan_bytes=self.plan, criteria=self.criteria,
                     review_ref='review', review_bytes=self.review_bytes, verdicts=self.review['verdicts'],
                     reviewer_role='qa-reviewer', recorded_at='2026-11-09T12:00:00Z')
            event = self.event(binding=binding, initial_review=review)
            self.assertEqual(len(pc.append_event([], event)), 1)
        self.assertNotIn('workflow_status', event)
        self.assertNotIn('dispatch', event)


if __name__ == '__main__':
    unittest.main()
