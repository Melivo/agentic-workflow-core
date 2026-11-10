"""Offline contract tests for the portable core-typesafe module.

Every network entry point is blocked and recorded; responses, clocks and keys are synthetic. These tests
prove the local contract, not model quality, real authentication or API availability.
"""
import ast
import copy
import email.message
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import traceback
import unittest
import unittest.mock
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / '.apm/skills/core-typesafe'
MODULE = BUNDLE / 'scripts/typesafe_eval.py'
SENTINEL = 'SYNTHETIC-SECRET-SENTINEL-4711'
PRIVATE = 'SYNTHETIC-PRIVATE-PASSAGE-0815'

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('typesafe_eval', MODULE)
ts = importlib.util.module_from_spec(spec)
sys.modules['typesafe_eval'] = ts
spec.loader.exec_module(ts)

attempts = []
patches = []


def blocked(name):
    def block(*args, **kwargs):
        attempts.append(name)
        raise AssertionError('network attempt: ' + name)
    return block


def setUpModule():
    for owner, name in ((socket.socket, 'connect'), (socket, 'create_connection'), (socket, 'getaddrinfo')):
        patcher = unittest.mock.patch.object(owner, name, blocked(name))
        patcher.start()
        patches.append(patcher)


def tearDownModule():
    for patcher in patches:
        patcher.stop()


INPUTS = {
    'skill_relevance': {'goal': 'Ship an API', 'task': 'Add an endpoint',
                        'candidates': [{'ref': 'core-backend', 'responsibility': 'Server logic'},
                                       {'ref': 'core-frontend', 'responsibility': 'User interface'}]},
    'requirement_coverage': {'criterion': 'Errors are typed', 'task': 'Add error codes',
                             'evidence': [{'ref': 'plan.md#L3', 'text': PRIVATE}]},
    'claim_support': {'claim': 'Retries are off', 'ref': 'docs/a.md#L9', 'passage': PRIVATE},
}
NOUL = {'type': 'noul', 'noul': 0.62}
ANSWERS = {
    'skill_relevance': {'fit': NOUL, 'central_responsibility': {
        'type': 'choice', 'choice': 'core-backend', 'confidence': 0.7, 'probabilities': {'core-backend': 0.8, 'core-frontend': 0.2}}},
    'requirement_coverage': {'covers': NOUL},
    'claim_support': {'supports': NOUL, 'matching_passage': NOUL, 'relation': {
        'type': 'choice', 'choice': 'topical_only', 'confidence': 0.4,
        'probabilities': {'direct_support': 0.3, 'contradiction': 0.1, 'topical_only': 0.5, 'unrelated_passage': 0.1}}},
}
MODEL = 'jev-latest'


def response(profile='claim_support', **change):
    base = {'model': 'jev-1.14.0', 'answers': copy.deepcopy(ANSWERS[profile]), 'usage': {'input_tokens': 120, 'output_tokens': 12}}
    base.update(change)
    return base


def ticking(*values):
    return unittest.mock.Mock(side_effect=list(values))


def run(profile='claim_support', inputs=..., transport=None, **kwargs):
    kwargs.setdefault('model', MODEL)
    kwargs.setdefault('core_version', '0.14.1')
    return ts.evaluate(profile, INPUTS[profile] if inputs is ... else inputs, transport=transport, **kwargs)


class NoStrayNetwork(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(attempts, [])


class Profiles(NoStrayNetwork):
    def test_three_profiles_answer_through_one_api(self):
        self.assertEqual(ts.PROFILES, ('skill_relevance', 'requirement_coverage', 'claim_support'))
        for profile in ts.PROFILES:
            with self.subTest(profile):
                result = run(profile, transport=lambda payload: response(profile))
                self.assertEqual(result.answers, ANSWERS[profile])
                self.assertEqual((result.outcome, result.reason, result.error), ('unresolved', 'no_confirmed_evaluation_rule', None))
                self.assertEqual(result.uncertainty, 'unassessed')

    def test_every_choice_has_a_companion_noul_and_questions_are_atomic(self):
        for profile in ts.PROFILES:
            questions = ts.build_request(profile, INPUTS[profile], model=MODEL).payload['questions']
            types = [q['type'] for q in questions.values()]
            if 'choice' in types:
                self.assertIn('noul', types, profile)
            for question in questions.values():
                self.assertNotIn(' or ', question['instructions'], profile)

    def test_every_backticked_fact_is_visible_in_state(self):
        for profile in ts.PROFILES:
            payload = ts.build_request(profile, INPUTS[profile], model=MODEL).payload
            for question in payload['questions'].values():
                for name in question['instructions'].split(chr(96))[1::2]:
                    self.assertIn(name, payload['state'], (profile, name))

    def test_references_are_copied_only_from_input(self):
        result = run('requirement_coverage', transport=lambda payload: response('requirement_coverage', references=['invented']))
        self.assertEqual(result.references, ('plan.md#L3',))
        self.assertEqual(run(transport=lambda payload: response()).references, ('docs/a.md#L9',))

    def test_build_request_and_import_are_offline_and_keyless(self):
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            prepared = ts.build_request('claim_support', INPUTS['claim_support'], model=MODEL)
        self.assertEqual(prepared.payload['model'], MODEL)
        self.assertEqual(sorted(prepared.payload), ['model', 'questions', 'state'])
        self.assertNotIn('authorization', json.dumps(prepared.payload).lower())


class CoverageRegression(NoStrayNetwork):
    def test_silent_evidence_is_explicitly_in_false_criterion_and_versioned(self):
        inputs = dict(INPUTS['requirement_coverage'], evidence=[{'ref': 'p', 'text': 'Only styling is discussed.'}])
        prepared = ts.build_request('requirement_coverage', inputs, model=MODEL)
        criteria = prepared.payload['questions']['covers']['criteria']
        self.assertIn('silent', criteria['false'])
        self.assertIn('does not explicitly establish', criteria['false'])
        self.assertEqual(prepared.question_version, '2')
        old_questions = copy.deepcopy(prepared.payload['questions'])
        old_questions['covers']['criteria']['false'] = 'The evidence shows the task leaving what the criterion requires undone.'
        import hashlib
        old = json.dumps({'profile': 'requirement_coverage', 'version': '1', 'questions': old_questions},
                         sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        self.assertNotEqual(prepared.question_fingerprint, hashlib.sha256(old.encode()).hexdigest())
        result = run('requirement_coverage', inputs, lambda payload: response('requirement_coverage'))
        self.assertEqual((result.outcome, result.reason), ('unresolved', ts.REASON_NO_RULE))


class SettledWithoutNetwork(NoStrayNetwork):
    def assertSettled(self, profile, inputs, outcome, reason):
        transport = unittest.mock.Mock()
        result = run(profile, inputs, transport)
        transport.assert_not_called()
        self.assertEqual((result.outcome, result.reason, result.error, result.request_sent), (outcome, reason, None, False))
        self.assertIsNone(result.answers)
        self.assertEqual(result.uncertainty, 'no_model_answer')
        self.assertIsNone(ts.build_request(profile, inputs, model=MODEL).payload)

    def test_empty_candidates_are_no_fit(self):
        self.assertSettled('skill_relevance', dict(INPUTS['skill_relevance'], candidates=[]), 'no_fit', 'no_candidates')

    def test_missing_originals_are_unresolved(self):
        coverage = INPUTS['requirement_coverage']
        self.assertSettled('requirement_coverage', dict(coverage, evidence=[]), 'unresolved', 'missing_evidence')
        self.assertSettled('requirement_coverage', dict(coverage, evidence=[{'ref': 'a', 'text': None}]), 'unresolved', 'missing_evidence')
        self.assertSettled('claim_support', dict(INPUTS['claim_support'], passage=None), 'unresolved', 'missing_passage')


class InputErrors(NoStrayNetwork):
    def test_surrogates_are_sanitized_before_hashing_or_transport(self):
        for character in (chr(0xD800), chr(0xDBFF), chr(0xDC00), chr(0xDFFF)):
            for field in ('responsibility', 'ref'):
                with self.subTest(codepoint=ord(character), field=field):
                    inputs = copy.deepcopy(INPUTS['skill_relevance'])
                    inputs['candidates'][0][field] = PRIVATE + character
                    with self.assertRaises(ts.InputValidationError) as caught:
                        ts.build_request('skill_relevance', inputs, model=MODEL)
                    failure = caught.exception
                    self.assertEqual((failure.code, failure.field), ('input_invalid', field))
                    self.assertIsNone(failure.__cause__)
                    self.assertIsNone(failure.__context__)
                    self.assertFalse(hasattr(failure, 'object'))
                    text = ''.join(traceback.format_exception(failure)) + repr(vars(failure))
                    self.assertNotIn(PRIVATE, text)
                    transport = unittest.mock.Mock()
                    result = run('skill_relevance', inputs, transport)
                    transport.assert_not_called()
                    self.assertEqual((result.outcome, result.error, result.request_sent),
                                     ('error', 'input_invalid', False))
                    self.assertIsNone(result.answers)
                    self.assertNotIn(PRIVATE, json.dumps(result.to_dict()))

    def test_valid_unicode_is_preserved_without_normalization(self):
        inputs = copy.deepcopy(INPUTS['skill_relevance'])
        text = 'Ä漢🧪e' + chr(0x0301) + chr(0xD7FF) + chr(0xE000) + chr(0x10FFFF)
        inputs['candidates'][0]['responsibility'] = text
        prepared = ts.build_request('skill_relevance', inputs, model=MODEL)
        self.assertEqual(prepared.payload['state']['candidates']['core-backend'], text)
        self.assertEqual(prepared.payload['questions']['central_responsibility']['criteria']['core-backend'], text)
        transport = unittest.mock.Mock(return_value=response('skill_relevance'))
        result = run('skill_relevance', inputs, transport)
        transport.assert_called_once_with(prepared.payload)
        self.assertEqual((result.error, result.answers), (None, ANSWERS['skill_relevance']))

    def test_invalid_structure_is_a_validation_error_not_a_verdict(self):
        cases = [
            ('claim_support', {}), ('claim_support', None), ('claim_support', dict(INPUTS['claim_support'], extra=1)),
            ('claim_support', dict(INPUTS['claim_support'], claim=' ')), ('claim_support', dict(INPUTS['claim_support'], passage=3)),
            ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence='x')),
            ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence=[{'ref': 'a'}])),
            ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence=[{'ref': 'a', 'text': 't'}, {'ref': 'a', 'text': 'u'}])),
            ('skill_relevance', dict(INPUTS['skill_relevance'], candidates=None)),
            ('skill_relevance', dict(INPUTS['skill_relevance'], candidates=['x'])),
            ('skill_relevance', dict(INPUTS['skill_relevance'], candidates=[{'ref': str(i), 'responsibility': 'r'} for i in range(256)])),
        ]
        for profile, inputs in cases:
            with self.subTest(inputs=inputs):
                transport = unittest.mock.Mock()
                result = run(profile, inputs, transport)
                transport.assert_not_called()
                self.assertEqual((result.outcome, result.error, result.answers), ('error', 'input_invalid', None))
                self.assertEqual(result.uncertainty, 'no_model_answer')

    def test_unknown_profile_model_and_core_version_are_rejected(self):
        self.assertIsNone(ts.evaluate(['x'], {}, model=MODEL, core_version='1', transport=None).profile)
        for kwargs in ({'model': ''}, {'model': None}, {'core_version': ''}, {'core_version': 1}):
            with self.subTest(kwargs):
                self.assertEqual(run(transport=lambda payload: response(), **kwargs).error, 'input_invalid')
        with self.assertRaises(ts.InputValidationError) as caught:
            ts.build_request('claim_support', dict(INPUTS['claim_support'], claim=7), model=MODEL)
        self.assertEqual(caught.exception.field, 'claim')

    def test_no_transport_means_nothing_is_sent(self):
        result = run(transport=None)
        self.assertEqual((result.outcome, result.error, result.request_sent), ('error', 'transport_missing', False))


class ResponseErrors(NoStrayNetwork):
    def assertInvalid(self, body, profile='claim_support'):
        result = run(profile, transport=lambda payload: body)
        self.assertEqual((result.outcome, result.error, result.answers, result.response_model), ('error', 'response_invalid', None, None))
        self.assertEqual(result.usage, {'input_tokens': None, 'output_tokens': None})

    def test_damaged_noul_values_are_rejected(self):
        for value in (float('nan'), float('inf'), -0.1, 1.5, True, '0.5', None, 10 ** 400):
            with self.subTest(value=value):
                answers = dict(ANSWERS['claim_support'], supports={'type': 'noul', 'noul': value})
                self.assertInvalid(response(answers=answers))

    def test_wrong_ids_and_types_are_rejected(self):
        good = ANSWERS['claim_support']
        self.assertInvalid(response(answers={k: v for k, v in good.items() if k != 'supports'}))
        self.assertInvalid(response(answers=dict(good, extra=NOUL)))
        self.assertInvalid(response(answers=dict(good, supports=good['relation'])))
        self.assertInvalid(response(answers=dict(good, relation=NOUL)))
        self.assertInvalid(response(answers=dict(good, supports=[])))
        for body in ([], None, 'x', {'answers': good}, response(model=''), response(answers=None)):
            self.assertInvalid(body)

    def test_damaged_choice_is_rejected_not_repaired(self):
        relation = ANSWERS['claim_support']['relation']
        probs = relation['probabilities']
        for change in ({'choice': 'invented'}, {'choice': None}, {'confidence': float('nan')}, {'confidence': None},
                       {'probabilities': None},
                       {'probabilities': {k: v for k, v in probs.items() if k != 'contradiction'}},
                       {'probabilities': dict(probs, invented=0.0)},
                       {'probabilities': dict(probs, topical_only=float('nan'))},
                       {'probabilities': dict(probs, topical_only=-0.5)},
                       {'probabilities': dict(probs, topical_only=0.1)},
                       {'choice': 'contradiction'}):
            with self.subTest(change=change):
                self.assertInvalid(response(answers=dict(ANSWERS['claim_support'], relation=dict(relation, **change))))

    def test_probabilities_are_kept_unnormalized(self):
        relation = dict(ANSWERS['claim_support']['relation'], probabilities={'direct_support': 0.3, 'contradiction': 0.1, 'topical_only': 0.52, 'unrelated_passage': 0.1})
        result = run(transport=lambda payload: response(answers=dict(ANSWERS['claim_support'], relation=relation)))
        self.assertEqual(result.answers['relation']['probabilities']['topical_only'], 0.52)

    def test_invalid_usage_is_rejected(self):
        for usage in ('x', {'input_tokens': -1}, {'input_tokens': 1.5}, {'output_tokens': True}):
            with self.subTest(usage=usage):
                self.assertInvalid(response(usage=usage))


class Metadata(NoStrayNetwork):
    def test_success_metadata_is_observed_and_separate(self):
        result = run(transport=lambda payload: response(), clock=ticking(10.0, 12.5))
        self.assertEqual((result.requested_model, result.response_model), (MODEL, 'jev-1.14.0'))
        self.assertEqual((result.question_version, result.core_version, result.duration_seconds), ('2', '0.14.1', 2.5))
        self.assertEqual(result.usage, {'input_tokens': 120, 'output_tokens': 12})
        self.assertTrue(result.request_sent)
        self.assertEqual(result.to_dict()['usage'], result.usage)

    def test_missing_usage_stays_unknown_never_zero(self):
        body = response()
        del body['usage']
        self.assertEqual(run(transport=lambda payload: body).usage, {'input_tokens': None, 'output_tokens': None})
        self.assertEqual(run(transport=lambda payload: response(usage={'input_tokens': None, 'output_tokens': 3})).usage,
                         {'input_tokens': None, 'output_tokens': 3})
        self.assertEqual(run(transport=lambda payload: response(usage={'input_tokens': 0, 'output_tokens': 0})).usage,
                         {'input_tokens': 0, 'output_tokens': 0})

    def test_failed_attempt_has_duration_and_no_claimed_model(self):
        def fail(payload):
            raise ts.TransportError('timeout')
        result = run(transport=fail, clock=ticking(1.0, 4.0))
        self.assertEqual((result.duration_seconds, result.response_model, result.requested_model), (3.0, None, MODEL))
        self.assertEqual(result.usage, {'input_tokens': None, 'output_tokens': None})

    def test_fingerprint_is_deterministic_and_tracks_wording(self):
        first = ts.build_request('skill_relevance', INPUTS['skill_relevance'], model=MODEL)
        again = ts.build_request('skill_relevance', copy.deepcopy(INPUTS['skill_relevance']), model='other')
        self.assertEqual(first.question_fingerprint, again.question_fingerprint)
        self.assertRegex(first.question_fingerprint, '^[0-9a-f]{64}$')
        changed = copy.deepcopy(INPUTS['skill_relevance'])
        changed['candidates'][0]['responsibility'] = 'Other'
        self.assertNotEqual(first.question_fingerprint, ts.build_request('skill_relevance', changed, model=MODEL).question_fingerprint)
        self.assertEqual(first.question_fingerprint, run('skill_relevance', transport=lambda payload: response('skill_relevance')).question_fingerprint)
        with unittest.mock.patch.object(ts, 'QUESTION_VERSION', 'future'):
            self.assertNotEqual(first.question_fingerprint, ts.build_request('skill_relevance', INPUTS['skill_relevance'], model=MODEL).question_fingerprint)


class ResponseCompletion(NoStrayNetwork):
    def prepare(self, profile='claim_support', inputs=None):
        return ts.build_request(profile, INPUTS[profile] if inputs is None else inputs, model=MODEL)

    def complete(self, prepared=None, body=..., **kwargs):
        kwargs.setdefault('core_version', '0.14.1')
        kwargs.setdefault('duration_seconds', 2.5)
        return ts.finalize_response(self.prepare() if prepared is None else prepared,
                                    response() if body is ... else body, **kwargs)

    def test_all_profiles_share_exact_completion_and_metadata_with_evaluate(self):
        for profile in ts.PROFILES:
            with self.subTest(profile=profile):
                prepared = self.prepare(profile)
                body = response(profile)
                before = copy.deepcopy(prepared)
                transport = unittest.mock.Mock(return_value=body)
                direct = run(profile, transport=transport, clock=ticking(10, 12.5))
                completed = self.complete(prepared, body)
                transport.assert_called_once_with(prepared.payload)
                self.assertEqual(completed.to_dict(), direct.to_dict())
                self.assertEqual(prepared, before)
                self.assertEqual((completed.references, completed.requested_model,
                                  completed.question_version, completed.question_fingerprint),
                                 (prepared.references, MODEL, '2', prepared.question_fingerprint))
                self.assertEqual(completed.response_model, 'jev-1.14.0')
                self.assertTrue(completed.request_sent)
                self.assertIsNone(completed.http_status)

    def test_noncallable_requests_cannot_be_promoted_to_model_answers(self):
        cases = [('skill_relevance', dict(INPUTS['skill_relevance'], candidates=[])),
                 ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence=[])),
                 ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence=[{'ref': 'r', 'text': None}])),
                 ('claim_support', dict(INPUTS['claim_support'], passage=None))]
        for profile, inputs in cases:
            with self.subTest(profile=profile, inputs=inputs):
                prepared = self.prepare(profile, inputs)
                with self.assertRaises(ts.InputValidationError) as caught:
                    self.complete(prepared, response(profile))
                self.assertEqual((caught.exception.code, caught.exception.field), ('input_invalid', 'prepared'))

    def test_changed_payload_model_questions_state_and_references_are_rejected(self):
        changes = [lambda p: p.payload.update(model='other'),
                   lambda p: p.payload['state'].update(passage='different'),
                   lambda p: p.payload['questions']['supports'].update(instructions='different'),
                   lambda p: p.payload['questions']['relation']['criteria'].update(topical_only='different'),
                   lambda p: p.payload.update(extra=True),
                   lambda p: object.__setattr__(p, 'references', ('invented',)),
                   lambda p: object.__setattr__(p, 'profile', 'requirement_coverage'),
                   lambda p: object.__setattr__(p, 'question_version', 'future'),
                   lambda p: object.__setattr__(p, 'question_fingerprint', '0' * 64),
                   lambda p: object.__setattr__(p, 'outcome', 'no_fit'),
                   lambda p: object.__setattr__(p, 'reason', 'invented')]
        for change in changes:
            prepared = self.prepare()
            change(prepared)
            with self.assertRaises(ts.InputValidationError):
                self.complete(prepared)
        # Even recomputing a matching question fingerprint does not bless a changed profile.
        prepared = self.prepare('skill_relevance')
        prepared.payload['questions']['central_responsibility']['criteria']['core-backend'] = 'Other'
        import hashlib
        canonical = json.dumps({'profile': prepared.profile, 'version': prepared.question_version,
                                'questions': prepared.payload['questions']}, sort_keys=True,
                               ensure_ascii=False, separators=(',', ':'))
        object.__setattr__(prepared, 'question_fingerprint', hashlib.sha256(canonical.encode()).hexdigest())
        with self.assertRaises(ts.InputValidationError):
            self.complete(prepared, response('skill_relevance'))

    def test_only_build_request_objects_are_supported_not_json_or_manual_copies(self):
        good = self.prepare()
        manual = ts.PreparedRequest(good.profile, good.outcome, good.reason, good.payload,
                                    good.references, good.question_version, good.question_fingerprint)
        for value in (manual, good.payload, good.__dict__, None, [], PRIVATE):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(ts.InputValidationError):
                    ts.finalize_response(value, response(), core_version='1', duration_seconds=1)
        damaged = self.prepare()
        object.__setattr__(damaged, '_source', PRIVATE + '{')
        with self.assertRaises(ts.InputValidationError) as caught:
            self.complete(damaged)
        self.assertIsNone(caught.exception.__context__)
        self.assertIsNone(caught.exception.__cause__)
        self.assertNotIn(PRIVATE, repr(vars(caught.exception)))

    def test_input_mutation_after_build_does_not_change_prepared_request(self):
        inputs = copy.deepcopy(INPUTS['claim_support'])
        prepared = self.prepare(inputs=inputs)
        inputs['passage'] = 'Other'
        self.assertEqual(self.complete(prepared).answers, ANSWERS['claim_support'])

    def test_strict_response_failures_are_results_and_never_negative_answers(self):
        bodies = [None, [], PRIVATE, {}, response(answers={}), response(model=''),
                  response(answers=ANSWERS['requirement_coverage']), response(usage='invalid'),
                  response(usage={'input_tokens': -1}), response(usage={'output_tokens': True}),
                  response(answers=dict(ANSWERS['claim_support'], supports={'type': 'noul', 'noul': float('nan')})),
                  response(answers=dict(ANSWERS['claim_support'], relation=dict(
                      ANSWERS['claim_support']['relation'], choice='invented')))]
        for body in bodies:
            with self.subTest(body=body):
                result = self.complete(body=body)
                self.assertEqual((result.outcome, result.error, result.answers, result.response_model),
                                 ('error', 'response_invalid', None, None))
                self.assertTrue(result.request_sent)
                self.assertEqual(result.duration_seconds, 2.5)
                self.assertEqual(result.usage, {'input_tokens': None, 'output_tokens': None})
                self.assertNotIn(PRIVATE, repr(result))
                self.assertIsNone(result.http_status)

    def test_unknown_partial_zero_usage_and_nonnegative_observed_duration(self):
        body = response()
        del body['usage']
        for usage in (None, {}, {'input_tokens': None, 'output_tokens': 3},
                      {'input_tokens': 0, 'output_tokens': 0}):
            body['usage'] = usage
            result = self.complete(body=body, duration_seconds=0)
            self.assertEqual(result.usage, {k: usage.get(k) if usage else None
                                          for k in ('input_tokens', 'output_tokens')})
            self.assertEqual(result.duration_seconds, 0)
        import time
        started = time.monotonic()
        body = response()
        elapsed = time.monotonic() - started
        self.assertEqual(self.complete(body=body, duration_seconds=elapsed).duration_seconds, elapsed)

    def test_completion_metadata_is_validated_without_repair_or_raw_exception(self):
        for duration in (-1, float('nan'), float('inf'), -float('inf'), True, '1', None, 10 ** 400):
            with self.subTest(duration=duration):
                with self.assertRaises(ts.InputValidationError) as caught:
                    self.complete(duration_seconds=duration)
                self.assertEqual(caught.exception.field, 'duration_seconds')
        for core in ('', ' ', None, 1):
            with self.assertRaises(ts.InputValidationError) as caught:
                self.complete(core_version=core)
            self.assertEqual(caught.exception.field, 'core_version')

    def test_completion_performs_no_io_key_lookup_or_clock_and_invents_no_provenance(self):
        prepared, body = self.prepare(), response()
        environment = unittest.mock.MagicMock()
        environment.get.side_effect = AssertionError('key lookup')
        environment.__getitem__.side_effect = AssertionError('key lookup')
        body.update(request_sent=False, http_status=200, duration_seconds=0, retries=0,
                    references=['invented'], transport='https')
        with unittest.mock.patch('builtins.open', side_effect=AssertionError('file access')) as files, \
             unittest.mock.patch.object(ts.os, 'environ', environment), \
             unittest.mock.patch.object(ts, 'https_transport', side_effect=AssertionError('transport')) as transport, \
             unittest.mock.patch.object(ts.subprocess, 'Popen', side_effect=AssertionError('process')) as process, \
             unittest.mock.patch.object(ts.time, 'monotonic', side_effect=AssertionError('clock')) as clock:
            result = self.complete(prepared, body)
        self.assertEqual(environment.mock_calls, [])
        for guard in (files, transport, process, clock):
            guard.assert_not_called()
        self.assertTrue(result.request_sent)
        self.assertIsNone(result.http_status)
        self.assertEqual(result.duration_seconds, 2.5)
        self.assertEqual(result.references, prepared.references)
        self.assertFalse({'retries', 'transport'} & result.to_dict().keys())
        self.assertNotIn(PRIVATE, json.dumps(result.to_dict()))

    def test_evaluate_also_rejects_transport_mutation_instead_of_trusting_new_questions(self):
        def mutate(payload):
            payload['questions']['supports']['instructions'] = 'Other'
            return response()
        result = run(transport=mutate)
        self.assertEqual((result.outcome, result.error, result.answers, result.request_sent),
                         ('error', 'input_invalid', None, True))


class FakeResponse(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body)
        self.status = status


class FakeOpener:
    def __init__(self, outcome):
        self.outcome, self.requests, self.timeouts = outcome, [], []

    def open(self, request, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def http_error(status):
    return urllib.error.HTTPError(ts.ENDPOINT, status, 'reason ' + PRIVATE, email.message.Message(), io.BytesIO(SENTINEL.encode()))


def inline_worker(payload, timeout, started):
    """Exercise the actual worker protocol with an in-process, network-blocked fake opener."""
    stdin = unittest.mock.Mock(buffer=io.BytesIO(json.dumps({'payload': payload, 'timeout': timeout}).encode()))
    stdout = unittest.mock.Mock(buffer=io.BytesIO())
    with unittest.mock.patch.object(ts.sys, 'stdin', stdin), unittest.mock.patch.object(ts.sys, 'stdout', stdout):
        ts._transport_worker()
    message = json.loads(stdout.buffer.getvalue())
    if 'error' in message:
        raise ts.TransportError(message['error'], message.get('status'))
    return bytes.fromhex(message['body'])


class RealAdapter(NoStrayNetwork):
    def call(self, outcome, key=SENTINEL):
        opener = FakeOpener(outcome)
        env = {} if key is None else {ts.API_KEY_ENV: key}
        with unittest.mock.patch.dict(os.environ, env, clear=True), unittest.mock.patch.object(ts, '_build_opener', return_value=opener), unittest.mock.patch.object(ts, '_bounded_exchange', side_effect=inline_worker):
            return run(transport=ts.https_transport), opener

    def test_success_uses_same_contract_as_injected_transport(self):
        result, opener = self.call(FakeResponse(json.dumps(response()).encode()))
        injected = run(transport=lambda payload: response())
        self.assertEqual((result.outcome, result.answers, result.usage), (injected.outcome, injected.answers, injected.usage))
        request = opener.requests[0]
        self.assertEqual((request.full_url, request.get_method()), ('https://api.typesafe.ai/v1/systemone', 'POST'))
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + SENTINEL)
        self.assertEqual(json.loads(request.data), ts.build_request('claim_support', INPUTS['claim_support'], model=MODEL).payload)
        self.assertEqual(opener.timeouts, [ts.TIMEOUT_SECONDS])
        self.assertEqual(len(opener.requests), 1)

    def test_failures_map_to_separate_codes_without_retry(self):
        cases = [
            (http_error(401), 'auth_failed', 401), (http_error(403), 'auth_failed', 403), (http_error(400), 'http_error', 400),
            (http_error(422), 'http_error', 422), (http_error(500), 'http_error', 500), (http_error(302), 'http_error', 302),
            (FakeResponse(b'{}', 204), 'http_error', 204),
            (TimeoutError(PRIVATE), 'timeout', None), (urllib.error.URLError(TimeoutError(PRIVATE)), 'timeout', None),
            (urllib.error.URLError(PRIVATE), 'network_error', None), (ConnectionResetError(PRIVATE), 'network_error', None),
            (FakeResponse(PRIVATE.encode()), 'response_invalid', None), (FakeResponse(b'\xff'), 'response_invalid', None),
            (FakeResponse(b'{"answers": {}}'), 'response_invalid', None),
            (FakeResponse(b' ' * (ts.MAX_RESPONSE_BYTES + 1)), 'response_too_large', None),
        ]
        for outcome, code, status in cases:
            with self.subTest(code=code, status=status):
                result, opener = self.call(outcome)
                self.assertEqual((result.outcome, result.error, result.http_status, result.answers), ('error', code, status, None))
                self.assertEqual(len(opener.requests), 1)
                self.assertNotIn(PRIVATE, repr(result))

    def test_missing_or_malformed_key_never_sends(self):
        for key, code in ((None, 'key_missing'), ('', 'key_missing'), ('a b', 'key_invalid'), (SENTINEL + '\r\nX: y', 'key_invalid')):
            with self.subTest(code=code):
                result, opener = self.call(FakeResponse(b'{}'), key=key)
                self.assertEqual((result.error, result.request_sent, opener.requests), (code, False, []))
                self.assertNotIn(SENTINEL, repr(result))

    def test_opener_refuses_redirects_and_verifies_tls(self):
        opener = ts._build_opener()
        handlers = {type(h): h for h in opener.handlers}
        self.assertIsNone(handlers[ts._NoRedirect].redirect_request(None, None, 302, 'x', {}, 'https://elsewhere.example'))
        self.assertNotIn(urllib.request.HTTPRedirectHandler, handlers)
        context = handlers[urllib.request.HTTPSHandler]._context
        self.assertEqual((context.verify_mode, context.check_hostname), (ssl.CERT_REQUIRED, True))

    def test_endpoint_cannot_come_from_payload(self):
        inputs = dict(INPUTS['claim_support'], claim='https://evil.example/')
        opener = FakeOpener(FakeResponse(json.dumps(response()).encode()))
        with unittest.mock.patch.dict(os.environ, {ts.API_KEY_ENV: 'k'}), unittest.mock.patch.object(ts, '_build_opener', return_value=opener), unittest.mock.patch.object(ts, '_bounded_exchange', side_effect=inline_worker):
            run(inputs=inputs, transport=ts.https_transport)
        self.assertEqual(opener.requests[0].full_url, ts.ENDPOINT)


class DeadlineBoundary(NoStrayNetwork):
    def test_real_process_bounds_all_io_and_is_reaped(self):
        # Loopback exists only in this separate, short-lived test process. The suite's
        # socket/getaddrinfo blocks remain installed, unchanged, in the main test process.
        script = r'''
import importlib.util, json, os, socket, subprocess, sys, threading, time
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('typesafe_eval', sys.argv[1])
ts = importlib.util.module_from_spec(spec)
sys.modules['typesafe_eval'] = ts
spec.loader.exec_module(ts)
mode = sys.argv[2]
os.environ[ts.API_KEY_ENV] = 'SYNTHETIC-SECRET-SENTINEL-4711'
stop = threading.Event()
accepted = threading.Event()
listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen(1)
listener.settimeout(2)
port = listener.getsockname()[1]

def serve():
    try:
        with listener.accept()[0] as connection:
            accepted.set()
            connection.settimeout(1)
            connection.recv(65536)
            if mode == 'tls':
                stop.wait(2)
                return
            headers = b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n'
            if mode == 'status':
                prefix, drip = b'', b'HTTP/1.1 200 OK\r\n'
            elif mode == 'headers':
                prefix, drip = b'HTTP/1.1 200 OK\r\n', b'X-Slow: ' + b'x' * 80
            elif mode == 'body':
                prefix, drip = b'HTTP/1.1 200 OK\r\nContent-Length: 80\r\n\r\n', b' ' * 80
            else:
                connection.sendall(headers + b'{}')
                return
            connection.sendall(prefix)
            for byte in drip:
                if stop.wait(0.04):
                    return
                connection.sendall(bytes([byte]))
    except (OSError, TimeoutError):
        pass

thread = threading.Thread(target=serve, daemon=True)
if mode not in ('dns', 'tcp'):
    thread.start()
# Guard the worker against every external connection, even if a test setup regresses.
bootstrap = """
import runpy, socket, sys, time
module = runpy.run_path(sys.argv[1])
original_connect = socket.socket.connect
def local_connect(sock, address):
    if address[0] != '127.0.0.1':
        raise AssertionError('external network forbidden')
    return original_connect(sock, address)
socket.socket.connect = local_connect
"""
if mode == 'dns':
    bootstrap += "socket.getaddrinfo = lambda *a, **k: time.sleep(5)\n"
elif mode == 'tcp':
    bootstrap += "socket.create_connection = lambda *a, **k: time.sleep(5)\n"
else:
    scheme = 'https' if mode == 'tls' else 'http'
    bootstrap += "module['_transport_worker'].__globals__['ENDPOINT'] = " + repr(scheme + '://127.0.0.1:' + str(port)) + "\n"
bootstrap += "module['_transport_worker']()\n"
processes = []
real_popen = subprocess.Popen

def record(argv, **kwargs):
    assert 'SYNTHETIC-SECRET' not in repr(argv) and 'PRIVATE-INPUT' not in repr(argv)
    assert kwargs['stderr'] == subprocess.DEVNULL
    child = real_popen(argv, **kwargs)
    processes.append(child)
    return child

try:
    start = time.monotonic()
    with patch.object(ts, '_WORKER_CODE', bootstrap), patch.object(ts.subprocess, 'Popen', side_effect=record):
        try:
            result = ts.https_transport({'state': 'PRIVATE-INPUT'}, timeout=0.5)
        except ts.TransportError as failure:
            assert mode != 'success' and failure.code == 'timeout', (mode, failure.code)
        else:
            assert mode == 'success' and result == {}, (mode, result)
    elapsed = time.monotonic() - start
    assert elapsed < 1.5, (mode, elapsed)
    if mode != 'success':
        assert elapsed >= 0.45, (mode, elapsed)
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdin.closed and processes[0].stdout.closed
    if mode not in ('dns', 'tcp'):
        assert accepted.is_set(), mode
    print(mode, round(elapsed, 3), 'reaped')
finally:
    stop.set()
    listener.close()
    if thread.is_alive():
        thread.join(2)
    assert not thread.is_alive()
'''
        for mode in ('dns', 'tcp', 'tls', 'status', 'headers', 'body', 'success'):
            with self.subTest(mode=mode):
                env = {k: v for k, v in os.environ.items()
                       if k != ts.API_KEY_ENV and not k.lower().endswith('_proxy')}
                done = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(MODULE), mode],
                                      env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn(mode, done.stdout)
                self.assertIn('reaped', done.stdout)

    def test_uncertain_failure_never_claims_no_send(self):
        for code in ('timeout', 'network_error', 'auth_failed'):
            def fail(payload):
                raise ts.TransportError(code)
            self.assertTrue(run(transport=fail).request_sent)


class SecretsAndSideEffects(NoStrayNetwork):
    def test_decode_errors_have_no_reachable_raw_exception(self):
        private = b'SYNTHETIC-PRIVATE-RESPONSE'
        for body in (b'{"echo":"' + private + b'",', bytes([255]) + private):
            with self.subTest(invalid_utf8=body.startswith(bytes([255]))):
                with unittest.mock.patch.dict(os.environ, {ts.API_KEY_ENV: SENTINEL}), unittest.mock.patch.object(ts, '_bounded_exchange', return_value=body):
                    with self.assertRaises(ts.TransportError) as caught:
                        ts.https_transport({'state': PRIVATE})
                    failure = caught.exception
                    self.assertEqual((failure.code, failure.http_status), ('response_invalid', None))
                    pending, seen = [failure], set()
                    while pending:
                        node = pending.pop()
                        if node is None or id(node) in seen:
                            continue
                        seen.add(id(node))
                        self.assertNotIsInstance(node, (json.JSONDecodeError, UnicodeDecodeError))
                        self.assertFalse(hasattr(node, 'doc'))
                        self.assertFalse(hasattr(node, 'object'))
                        self.assertNotIn(private.decode(), repr(vars(node)))
                        pending.extend((node.__cause__, node.__context__))
                    self.assertEqual(len(seen), 1)
                    self.assertIsNone(failure.__cause__)
                    self.assertIsNone(failure.__context__)
                    result = run(transport=ts.https_transport)
                self.assertEqual((result.outcome, result.error, result.request_sent),
                                 ('error', 'response_invalid', True))
                self.assertIsNone(result.answers)
                self.assertIsNone(result.response_model)
                self.assertEqual(result.usage, {'input_tokens': None, 'output_tokens': None})
                self.assertNotIn(private.decode(), json.dumps(result.to_dict()))
                self.assertNotIn(PRIVATE, json.dumps(result.to_dict()))
                self.assertNotIn(SENTINEL, json.dumps(result.to_dict()))

    def test_valid_utf8_response_is_unchanged(self):
        expected = response(model='jev-漢🧪')
        body = json.dumps(expected, ensure_ascii=False).encode('utf-8')
        with unittest.mock.patch.dict(os.environ, {ts.API_KEY_ENV: SENTINEL}), unittest.mock.patch.object(ts, '_bounded_exchange', return_value=body):
            self.assertEqual(ts.https_transport({'state': PRIVATE}), expected)
            result = run(transport=ts.https_transport)
        self.assertEqual((result.error, result.response_model, result.answers),
                         (None, expected['model'], expected['answers']))
        self.assertTrue(result.request_sent)

    def test_exceptions_results_and_logs_carry_no_key_body_or_request(self):
        def explode(payload):
            raise RuntimeError(SENTINEL + PRIVATE + json.dumps(payload))
        def rejected(payload):
            raise http_error(401)

        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger('probe').debug('probe')
            results = [run(transport=explode), run(transport=rejected), run(transport=lambda payload: {'answers': PRIVATE + SENTINEL})]
        self.assertEqual([r.error for r in results], ['transport_failed', 'transport_failed', 'response_invalid'])
        for text in [repr(r) for r in results] + [json.dumps(r.to_dict()) for r in results] + logs.output:
            self.assertNotIn(SENTINEL, text)
            self.assertNotIn(PRIVATE, text)

    def test_raised_transport_error_hides_cause_and_context(self):
        opener = FakeOpener(http_error(401))
        with unittest.mock.patch.dict(os.environ, {ts.API_KEY_ENV: SENTINEL}), unittest.mock.patch.object(ts, '_build_opener', return_value=opener), unittest.mock.patch.object(ts, '_bounded_exchange', side_effect=inline_worker):
            with self.assertRaises(ts.TransportError) as caught:
                ts.https_transport({'state': PRIVATE})
        text = ''.join(traceback.format_exception(caught.exception)) + repr(caught.exception) + str(caught.exception)
        self.assertNotIn(SENTINEL, text)
        self.assertNotIn(PRIVATE, text)
        self.assertEqual(caught.exception.code, 'auth_failed')

    def test_input_error_does_not_echo_values(self):
        result = run(inputs=dict(INPUTS['claim_support'], extra=SENTINEL), transport=None)
        self.assertNotIn(SENTINEL, repr(result))
        with self.assertRaises(ts.InputValidationError) as caught:
            ts.build_request('claim_support', dict(INPUTS['claim_support'], claim=[SENTINEL]), model=MODEL)
        self.assertNotIn(SENTINEL, str(caught.exception))

    def test_result_never_holds_private_input_text(self):
        for profile in ('requirement_coverage', 'claim_support'):
            result = run(profile, transport=lambda payload: response(profile))
            self.assertNotIn(PRIVATE, json.dumps(result.to_dict()))

    def test_module_has_only_stdlib_imports_and_no_write_or_log_calls(self):
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        imports = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imports |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertLessEqual(imports, set(sys.stdlib_module_names))
        self.assertFalse({'logging', 'sqlite3'} & imports)
        # The sole approved subprocess site is the private cancellable one-attempt IO boundary.
        launches = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'Popen']
        self.assertEqual(len(launches), 1)
        self.assertIn(launches[0], list(ast.walk(next(n for n in tree.body
                      if isinstance(n, ast.FunctionDef) and n.name == '_bounded_exchange'))))
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse({'open', 'print', 'exec', 'eval'} & calls)

    def test_evaluate_writes_no_files(self):
        with unittest.mock.patch('builtins.open', side_effect=AssertionError('file access')) as guarded:
            run(transport=lambda payload: response())
        guarded.assert_not_called()


class Portability(NoStrayNetwork):
    def test_copied_bundle_works_outside_repo_without_key_or_network(self):
        script = (
            "import os, socket, sys\n"
            "def block(*a, **k): raise SystemExit('network attempt')\n"
            "socket.socket.connect = socket.create_connection = socket.getaddrinfo = block\n"
            "assert 'TYPESAFE_API_KEY' not in os.environ\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import typesafe_eval as ts\n"
            "inputs = {'claim': 'c', 'ref': 'r', 'passage': 'p'}\n"
            "assert ts.build_request('claim_support', inputs, model='m').outcome == 'callable'\n"
            "result = ts.evaluate('claim_support', inputs, model='m', core_version='1', transport=ts.https_transport)\n"
            "assert result.error == 'key_missing', result\n"
            "print('PORTABLE')\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'core-typesafe'
            shutil.copytree(BUNDLE, target)
            env = {k: v for k, v in os.environ.items() if k != 'TYPESAFE_API_KEY'}
            done = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(target / 'scripts')],
                                  cwd=tmp, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, 'PORTABLE'), done.stderr)

    def test_bundle_documents_api_and_error_codes(self):
        skill = (BUNDLE / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('name: core-typesafe\n', skill)
        for term in ts.PROFILES + tuple(ts._MESSAGES) + ('build_request', 'https_transport', 'TYPESAFE_API_KEY'):
            self.assertIn(term, skill, term)
        guide = (BUNDLE / 'AGENTS.md').read_text(encoding='utf-8')
        for heading in ('## Purpose', '## Ownership', '## Local Contracts', '## Work Guidance', '## Verification', '## Child DOX Index'):
            self.assertIn(heading, guide)
        self.assertIn('core-typesafe/AGENTS.md', (ROOT / '.apm/skills/AGENTS.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
