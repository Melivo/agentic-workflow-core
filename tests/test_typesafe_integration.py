"""Synthetic consumer/owner protocol tests; no live API, installation or actual H01.

Temporary fixtures are not workflow state. Rules do not prove harness compliance.
"""
import sys
sys.dont_write_bytecode = True
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / '.apm/skills/core-typesafe'
TEMPLATE = '.apm/skills/core-typesafe/assets/evaluation-directory-AGENTS.md'
CONTRACT = '.apm/skills/core-shared/references/typesafe-contract.md'
EVALUATION = '.apm/skills/core-review/references/typesafe-evaluation.md'
IMAGES = '.apm/skills/core-typesafe/references/images.md'
IMAGE_EVALUATION = '.apm/skills/core-typesafe/references/images-evaluation.md'
PLAN = b'# SYNTHETIC private plan\r\n'
REVIEW = b'SYNTHETIC original independent answer\r\n'
CRITERIA = {'AC01': 'SYNTHETIC explicit evidence'}
PRIVATE = 'SYNTHETIC-PRIVATE-PASSAGE-5501'
SECRET = 'SYNTHETIC-SECRET-5502'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ts = load('integration_ts', BUNDLE / 'scripts/typesafe_eval.py')
pc = load('integration_pc', BUNDLE / 'scripts/plan_comparison.py')
checker = load('integration_contracts', ROOT / 'scripts/check_core_contracts.py')
design = load('integration_links', ROOT / 'scripts/check_design_principles.py')
INPUTS = {
    'skill_relevance': {'goal': 'SYNTHETIC API', 'task': 'SYNTHETIC endpoint',
                        'candidates': [{'ref': 'backend', 'responsibility': 'Server implementation'}]},
    'requirement_coverage': {'criterion': CRITERIA['AC01'], 'task': 'SYNTHETIC source check',
                             'evidence': [{'ref': 'source.md#L1', 'text': PRIVATE}]},
    'claim_support': {'claim': 'SYNTHETIC claim', 'ref': 'source.md#L1', 'passage': PRIVATE},
}
# Semantic edges use existing link helpers, not a new parser or contract target group.
REQUIRED_LINKS = {
    'AGENTS.md': (TEMPLATE,),
    '.apm/skills/core-plan/SKILL.md': (CONTRACT, TEMPLATE,
        '.apm/skills/core-typesafe/scripts/typesafe_collection.py',
        '.apm/skills/core-typesafe/scripts/typesafe_owner.py'),
    '.apm/skills/core-review/SKILL.md': (CONTRACT, EVALUATION),
    '.apm/skills/core-docs/SKILL.md': (CONTRACT,),
    '.apm/skills/core-typesafe/SKILL.md': (CONTRACT, TEMPLATE,
        '.apm/skills/core-typesafe/scripts/plan_comparison.py', IMAGES, IMAGE_EVALUATION),
    '.apm/skills/core-typesafe/AGENTS.md': (CONTRACT, TEMPLATE, IMAGES, IMAGE_EVALUATION),
    EVALUATION: (CONTRACT, IMAGES, IMAGE_EVALUATION),
    CONTRACT: (EVALUATION, TEMPLATE, IMAGES, IMAGE_EVALUATION,
        '.apm/skills/core-typesafe/scripts/typesafe_collection.py',
        '.apm/skills/core-typesafe/scripts/typesafe_owner.py'),
    '.apm/skills/core-shared/SKILL.md': (CONTRACT,),
    '.apm/skills/core-shared/references/tool-routing.md': (CONTRACT,),
    '.apm/skills/core-shared/AGENTS.md': (CONTRACT,),
}


def fake_response(payload, probability=0.5):
    answers = {}
    for key, question in payload['questions'].items():
        if question['type'] == 'noul':
            answers[key] = {'type': 'noul', 'noul': probability}
        else:
            options = list(question['criteria'])
            answers[key] = {'type': 'choice', 'choice': options[0], 'confidence': probability,
                            'probabilities': {k: int(k == options[0]) for k in options}}
    return {'model': 'synthetic-response-v1', 'answers': answers,
            'usage': {'input_tokens': 7, 'output_tokens': 3}, 'ignored_private': SECRET}


def binding():
    return pc.bind_plan(project_id='synthetic-project', plan_ref='plan.md', plan_bytes=PLAN, criteria=CRITERIA)


def initial():
    return pc.fix_review(binding(), plan_bytes=PLAN, criteria=CRITERIA, review_ref='initial-review.md',
                         review_bytes=REVIEW, verdicts={'AC01': 'no_defect_found'},
                         reviewer_role='qa-reviewer', recorded_at='2026-11-09T10:00:00Z')


def adjudication(label='material_defect'):
    return dict(label=label, evidence_ref='source.md#L1', reviewer_role='qa-reviewer',
                recorded_at='2026-11-09T10:01:00Z')


def observe(profile='claim_support', probability=0.5, transport=None, inputs=None):
    result = ts.evaluate(profile, INPUTS[profile] if inputs is None else inputs,
                         model='synthetic-request-v1', core_version='synthetic-core-v1',
                         transport=transport or (lambda p: fake_response(p, probability)), clock=lambda: 1.0)
    return pc.model_event(binding(), criterion_id='AC01', evaluation=result.to_dict(), selection='eligible')


def compare(model, **changes):
    args = dict(plan_bytes=PLAN, criteria=CRITERIA, review_bytes=REVIEW, adjudication=adjudication())
    args.update(changes)
    review = args.pop('initial_review', initial())
    return pc.comparison_event(model, review, **args)


# Synthetic stand-in for the harness-owned route. Real discovery/health stay owner evidence, never test input.
MCP_TOOL = 'typesafe-mcp-arbitype'
MCP_ARGUMENTS = ('state', 'questions', 'model')
OPEN = 'open_possibly_sent'


class FakeHarness:
    """Counts discovery, MCP and HTTP separately; performs no real tool call or request."""

    def __init__(self, available=True, failure=None, response=fake_response):
        self.available, self.failure, self.response = available, failure, response
        self.events, self.mcp_calls, self.http_calls = [], [], []

    def search(self, namespace, query):
        self.events.append(('search', namespace, query))
        return [{'path': namespace + '.' + query, 'parameters': MCP_ARGUMENTS}] if self.available else []

    def mcp_evaluate(self, **arguments):
        self.events.append(('mcp',))
        self.mcp_calls.append(copy.deepcopy(arguments))
        if self.failure is not None:
            raise self.failure
        return self.response(arguments)

    def http(self, payload):
        self.events.append(('http',))
        self.http_calls.append(copy.deepcopy(payload))
        return fake_response(payload)


def owner_route(harness, profile, inputs, *, approved=True):
    """Test-local copy of the documented owner order; not a shipped runner or dispatcher."""
    if not approved:
        return None
    prepared = ts.build_request(profile, inputs, model='synthetic-request-v1')
    if prepared.outcome != ts.CALLABLE:
        return prepared
    tools = harness.search(MCP_TOOL, 'evaluate')
    if not tools:
        # Proven unavailable before any possible send: one deliberate existing HTTP call.
        return ts.evaluate(profile, inputs, model='synthetic-request-v1', core_version='synthetic-core-v1',
                           transport=harness.http, clock=lambda: 0.0)
    if tools[0]['path'] != MCP_TOOL + '.evaluate' or tuple(tools[0]['parameters']) != MCP_ARGUMENTS:
        return None
    try:
        response = harness.mcp_evaluate(**{key: prepared.payload[key] for key in MCP_ARGUMENTS})
    except Exception:
        return OPEN  # possibly sent: no retry, no HTTP follow-up
    return ts.finalize_response(prepared, response, core_version='synthetic-core-v1', duration_seconds=0.0)


# Two real processes exchange only original inputs, payload and metadata; never a PreparedRequest object.
PROCESS_CODE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('process_ts', sys.argv[1])
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)
def meta(p, core_version):
    return {'profile': p.profile, 'outcome': p.outcome, 'reason': p.reason,
            'payload': p.payload, 'references': list(p.references), 'core_version': core_version,
            'question_version': p.question_version, 'question_fingerprint': p.question_fingerprint}
canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
packet = json.loads(sys.stdin.read())
if sys.argv[2] == 'prepare':
    prepared = ts.build_request(packet['profile'], packet['inputs'], model=packet['model'])
    print(json.dumps(dict(packet, sent=meta(prepared, packet['core_version']))))
else:
    record = packet['record']
    fresh = ts.build_request(record['profile'], record['inputs'], model=record['model'])
    if canonical(meta(fresh, record['core_version'])) != canonical(record['sent']) or fresh.payload['model'] != record['model']:
        print(json.dumps({'drift': True}))
    else:
        result = ts.finalize_response(fresh, packet['response'], core_version=record['core_version'],
                                      duration_seconds=packet['duration_seconds'])
        print(json.dumps(result.to_dict()))
'''


def run_process(mode, packet):
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', PROCESS_CODE, str(BUNDLE / 'scripts/typesafe_eval.py'), mode],
                               input=json.dumps(packet), capture_output=True, text=True, timeout=30,
                               env={k: v for k, v in os.environ.items() if k != ts.API_KEY_ENV})
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


class ConsumerIntegration(unittest.TestCase):
    def setUp(self):
        self.attempts = []
        def blocked(*args, **kwargs):
            self.attempts.append('network')
            raise AssertionError('offline integration attempted network')
        for owner, name in ((socket.socket, 'connect'), (socket, 'create_connection'),
                            (socket, 'getaddrinfo'), (ts, 'https_transport')):
            patcher = patch.object(owner, name, blocked)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(lambda: self.assertEqual(self.attempts, []))

    def test_three_profiles_consumed_minimally_without_model_labels(self):
        self.assertEqual(set(INPUTS), set(ts.PROFILES))
        for profile in ts.PROFILES:
            for probability in (0, 0.5, 1):
                calls = []
                def transport(payload):
                    calls.append(copy.deepcopy(payload))
                    return fake_response(payload, probability)
                with self.subTest(profile=profile, probability=probability):
                    model = observe(profile, transport=transport)
                    self.assertEqual(len(calls), 1)
                    obs = model['observation']
                    self.assertEqual(obs['profile'], profile)
                    self.assertEqual(obs['model_status'], 'uncertain')
                    self.assertEqual(obs['uncertainty'], 'unassessed')
                    self.assertEqual(obs['usage'], {'input_tokens': 7, 'output_tokens': 3})
                    self.assertEqual(obs['duration_seconds'], 0)
                    prepared = ts.build_request(profile, INPUTS[profile], model='synthetic-request-v1')
                    self.assertEqual(obs['question_fingerprint'], prepared.question_fingerprint)
                    self.assertEqual(obs['question_version'], prepared.question_version)
                    self.assertIsNone(model['initial_review'])
                    self.assertIsNone(model['adjudication'])
                    event = compare(model)
                    self.assertEqual(event['adjudication']['label'], 'material_defect')
                    self.assertEqual(event['model_event_id'], model['event_id'])
                    self.assertEqual(event['initial_review']['review_sha256'], hashlib.sha256(REVIEW).hexdigest())
                    self.assertEqual(event['binding']['plan_sha256'], hashlib.sha256(PLAN).hexdigest())
                    for forbidden in (PRIVATE, SECRET, PLAN.decode(), REVIEW.decode(), 'references', 'ignored_private'):
                        self.assertNotIn(forbidden, json.dumps(event))
                    self.assertEqual(set(obs), {'profile', 'core_version', 'requested_model', 'response_model',
                        'question_version', 'question_fingerprint', 'probabilities', 'uncertainty', 'model_status',
                        'api_error', 'request_sent', 'duration_seconds', 'usage'})

    def test_drift_missing_first_review_and_contamination_stay_open(self):
        model = observe()
        changes = [({'plan_bytes': PLAN + b'x'}, 'binding_mismatch'),
                   ({'plan_bytes': PLAN.replace(b'\r\n', b'\n')}, 'binding_mismatch'),
                   ({'criteria': {'AC01': 'changed'}}, 'binding_mismatch'),
                   ({'criteria': dict(CRITERIA, AC02='extra')}, 'binding_mismatch'),
                   ({'review_bytes': REVIEW + b'x'}, 'initial_review_mismatch'),
                   ({'initial_review': None}, 'missing_original'),
                   ({'adjudication': dict(adjudication(), recorded_at='2026-11-09T10:00:00Z')}, 'review_not_prior')]
        changes += [({k: None}, 'missing_original') for k in ('plan_bytes', 'criteria', 'review_bytes')]
        changes += [({'selection': s}, 'selection_' + s) for s in ('unknown', 'contaminated', 'excluded')]
        for change, reason in changes:
            with self.subTest(change=change):
                event = compare(model, **change)
                self.assertEqual(event['unresolved_reason'], reason)
                self.assertEqual(event['adjudication']['label'], 'unresolved')
                self.assertEqual(event['adjudication']['reported_label'], 'material_defect')
        for verdicts in ({}, {'AC01': 'unresolved'}, dict(AC01='no_defect_found', AC02='defect_found')):
            with self.subTest(verdicts=verdicts), self.assertRaises(pc.ComparisonError):
                pc.fix_review(binding(), plan_bytes=PLAN, criteria=CRITERIA, review_ref='r.md', review_bytes=REVIEW,
                              verdicts=verdicts, reviewer_role='qa-reviewer', recorded_at='2026-11-09T10:00:00Z')

    def test_api_errors_no_fit_missing_evidence_and_usage_stay_distinct(self):
        def failed(payload):
            raise ts.TransportError('http_error', 429)
        error = observe(transport=failed)
        self.assertEqual(error['observation']['model_status'], 'api_error')
        self.assertEqual(error['observation']['api_error'], {'occurred': True, 'http_status': 429})
        no_fit = observe('skill_relevance', inputs=dict(INPUTS['skill_relevance'], candidates=[]))
        missing = observe(inputs=dict(INPUTS['claim_support'], passage=None))
        self.assertEqual(no_fit['observation']['model_status'], 'no_fit')
        self.assertEqual(missing['observation']['model_status'], 'uncertain')
        for event in (no_fit, missing):
            self.assertFalse(event['observation']['request_sent'])
            self.assertEqual(event['observation']['uncertainty'], 'no_model_answer')
            self.assertIsNone(event['observation']['probabilities'])
            self.assertEqual(event['observation']['usage'], {'input_tokens': None, 'output_tokens': None})
        for model in (error, no_fit, missing):
            result = compare(model, selection='excluded')
            self.assertEqual(result['adjudication']['label'], 'unresolved')
            self.assertEqual(result['observation'], model['observation'])

    def test_owner_files_preserve_originals_revisions_and_collisions(self):
        # Fixture IO is owner protocol, never hidden IO added to plan_comparison.
        with tempfile.TemporaryDirectory(prefix='typesafe-owner-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            plan, review = root / 'plan.md', root / 'initial-review.md'
            with plan.open('xb') as stream:
                stream.write(PLAN)
            model = observe()
            history = pc.append_event([], model)
            target = root / model['binding']['plan_sha256']
            target.mkdir()
            path = target / (model['event_id'] + '.json')
            with path.open('x', encoding='utf-8') as stream:
                json.dump(model, stream, sort_keys=True)
            with review.open('xb') as stream:
                stream.write(REVIEW)
            first = compare(model)
            history = pc.append_event(history, first)
            corrected = compare(model, previous=first, adjudication=adjudication('no_material_defect'))
            before = copy.deepcopy(history)
            next_history = pc.append_event(history, corrected)
            self.assertEqual(history, before)
            self.assertEqual(corrected['supersedes'], first['event_id'])
            self.assertEqual(corrected['previous_id'], first['event_id'])
            self.assertEqual(corrected['revision'], 2)
            self.assertEqual(corrected['initial_review'], initial())
            self.assertEqual(next_history[:2], history)
            self.assertEqual(pc.append_event(next_history, corrected), next_history)
            for event in (first, corrected):
                with (target / (event['event_id'] + '.json')).open('x', encoding='utf-8') as stream:
                    json.dump(event, stream, sort_keys=True)
            retained = {p.name: p.read_bytes() for p in target.iterdir()}
            conflict = compare(model, adjudication=adjudication('unresolved'))
            self.assertEqual(conflict['event_id'], first['event_id'])
            with self.assertRaisesRegex(pc.ComparisonError, 'payload_conflict'):
                pc.append_event(history, conflict)
            with self.assertRaisesRegex(pc.ComparisonError, 'revision_conflict'):
                pc.append_event([], corrected)
            with self.assertRaises(FileExistsError), path.open('x'):
                self.fail('existing event must never be overwritten')
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, retained)
            self.assertEqual(plan.read_bytes(), PLAN)
            self.assertEqual(review.read_bytes(), REVIEW)
            self.assertEqual(json.loads(path.read_text()), model)
            self.assertEqual(len(retained), 3)

    def test_portable_bundle_outside_repository_without_installation(self):
        with tempfile.TemporaryDirectory(prefix='typesafe-portable-', dir='/tmp/opencode') as directory:
            bundle = Path(directory) / 'core-typesafe'
            shutil.copytree(BUNDLE, bundle, ignore=shutil.ignore_patterns('__pycache__'))
            self.assertFalse(bundle.is_relative_to(ROOT))
            copied_ts = load('portable_integration_ts', bundle / 'scripts/typesafe_eval.py')
            copied_pc = load('portable_integration_pc', bundle / 'scripts/plan_comparison.py')
            for profile in copied_ts.PROFILES:
                result = copied_ts.evaluate(profile, INPUTS[profile], model='synthetic-model',
                                            core_version='synthetic-core', transport=fake_response)
                event = copied_pc.model_event(binding(), criterion_id='AC01', evaluation=result.to_dict())
                self.assertEqual(event['observation']['model_status'], 'uncertain')
                self.assertEqual(event['selection'], 'unknown')
            self.assertEqual((bundle / 'assets/evaluation-directory-AGENTS.md').read_bytes(), (ROOT / TEMPLATE).read_bytes())


class McpOwnerRoute(unittest.TestCase):
    """Offline owner-protocol regressions; no proof of live MCP behaviour or response authenticity."""

    def setUp(self):
        self.attempts = []
        def blocked(*args, **kwargs):
            self.attempts.append('network')
            raise AssertionError('offline integration attempted network')
        for owner, name in ((socket.socket, 'connect'), (socket, 'create_connection'),
                            (socket, 'getaddrinfo'), (ts, 'https_transport')):
            patcher = patch.object(owner, name, blocked)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(lambda: self.assertEqual(self.attempts, []))

    def test_available_mcp_is_preferred_with_exact_payload_and_shared_completion(self):
        with patch.dict(os.environ, {ts.API_KEY_ENV: SECRET}):
            for profile in ts.PROFILES:
                with self.subTest(profile=profile):
                    harness = FakeHarness()
                    # No key lookup is permitted even when a synthetic inherited sentinel exists.
                    with patch.object(type(os.environ), '__getitem__', side_effect=AssertionError('key lookup')), \
                         patch.object(type(os.environ), 'get', side_effect=AssertionError('key lookup')):
                        result = owner_route(harness, profile, INPUTS[profile])
                    prepared = ts.build_request(profile, INPUTS[profile], model='synthetic-request-v1')
                    self.assertEqual(harness.events, [('search', MCP_TOOL, 'evaluate'), ('mcp',)])
                    self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (1, 0))
                    self.assertEqual(harness.mcp_calls[0], prepared.payload)
                    self.assertEqual(tuple(harness.mcp_calls[0]), MCP_ARGUMENTS)
                    self.assertNotIn(SECRET, json.dumps(harness.mcp_calls))
                    via_http = ts.evaluate(profile, INPUTS[profile], model='synthetic-request-v1',
                                           core_version='synthetic-core-v1', transport=fake_response, clock=lambda: 0.0)
                    self.assertEqual(result.to_dict(), via_http.to_dict())
                    self.assertEqual((result.outcome, result.request_sent, result.http_status), (ts.UNRESOLVED, True, None))
                    self.assertEqual((result.question_fingerprint, result.response_model, result.core_version),
                                     (prepared.question_fingerprint, 'synthetic-response-v1', 'synthetic-core-v1'))
                    event = pc.model_event(binding(), criterion_id='AC01', evaluation=result.to_dict(), selection='eligible')
                    self.assertEqual(compare(event)['adjudication']['label'], 'material_defect')

    def test_proven_unavailable_mcp_allows_one_deliberate_http_call(self):
        for profile in ts.PROFILES:
            with self.subTest(profile=profile):
                harness = FakeHarness(available=False)
                result = owner_route(harness, profile, INPUTS[profile])
                self.assertEqual(harness.events, [('search', MCP_TOOL, 'evaluate'), ('http',)])
                self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (0, 1))
                self.assertEqual(harness.http_calls[0], ts.build_request(profile, INPUTS[profile],
                                                                       model='synthetic-request-v1').payload)
                self.assertEqual(result.outcome, ts.UNRESOLVED)

    def test_failures_after_possible_mcp_send_never_fall_back_or_retry(self):
        failures = {'timeout': TimeoutError(), 'auth': PermissionError(), 'api': RuntimeError(),
                    'schema': KeyError('state'), 'unclear': ConnectionResetError()}
        for profile in ts.PROFILES:
            for name, failure in failures.items():
                with self.subTest(profile=profile, failure=name):
                    harness = FakeHarness(failure=failure)
                    self.assertEqual(owner_route(harness, profile, INPUTS[profile]), OPEN)
                    self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (1, 0))
        for name, response in (('missing_answers', lambda a: {'model': 'm'}), ('not_object', lambda a: 'raw'),
                               ('bad_probability', lambda a: dict(fake_response(a), answers={
                                   k: {'type': 'noul', 'noul': 2} for k in a['questions']}))):
            with self.subTest(response=name):
                harness = FakeHarness(response=response)
                result = owner_route(harness, 'requirement_coverage', INPUTS['requirement_coverage'])
                self.assertEqual((result.outcome, result.error, result.answers), (ts.ERROR, 'response_invalid', None))
                self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (1, 0))
        harness = FakeHarness()
        harness.search = lambda namespace, query: [{'path': MCP_TOOL + '.evaluate', 'parameters': ('state',)}]
        self.assertIsNone(owner_route(harness, 'claim_support', INPUTS['claim_support']))
        self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (0, 0))

    def test_discovery_failure_is_not_proven_unavailability(self):
        harness = FakeHarness()
        with patch.object(harness, 'search', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                owner_route(harness, 'claim_support', INPUTS['claim_support'])
        self.assertEqual((len(harness.mcp_calls), len(harness.http_calls)), (0, 0))

    def test_missing_approval_evidence_no_fit_and_invalid_input_send_nothing(self):
        cases = [('claim_support', INPUTS['claim_support'], False),
                 ('claim_support', dict(INPUTS['claim_support'], passage=None), True),
                 ('requirement_coverage', dict(INPUTS['requirement_coverage'], evidence=[]), True),
                 ('skill_relevance', dict(INPUTS['skill_relevance'], candidates=[]), True)]
        for profile, inputs, approved in cases:
            with self.subTest(profile=profile, approved=approved, inputs=inputs):
                harness = FakeHarness()
                result = owner_route(harness, profile, inputs, approved=approved)
                self.assertTrue(result is None or result.outcome in (ts.NO_FIT, ts.UNRESOLVED))
                self.assertEqual((harness.events, harness.mcp_calls, harness.http_calls), ([], [], []))
        harness = FakeHarness()
        with self.assertRaises(ts.InputValidationError):
            owner_route(harness, 'claim_support', dict(INPUTS['claim_support'], extra='x'))
        self.assertEqual((harness.events, harness.mcp_calls, harness.http_calls), ([], [], []))

    def test_unknown_usage_and_transport_provenance_are_not_invented(self):
        def response(payload):
            raw = fake_response(payload)
            raw.pop('usage')
            raw.update(http_status=200, request_count=1, retry_count=0)
            return raw
        result = owner_route(FakeHarness(response=response), 'claim_support', INPUTS['claim_support'])
        self.assertEqual(result.usage, {'input_tokens': None, 'output_tokens': None})
        self.assertIsNone(result.http_status)
        self.assertTrue(result.request_sent)  # possible, not proven delivery or one provider request
        self.assertTrue({'request_count', 'retry_count'}.isdisjoint(result.to_dict()))

    def test_process_boundary_uses_fresh_build_and_exact_value_binding(self):
        packet = {'profile': 'claim_support', 'inputs': INPUTS['claim_support'], 'model': 'synthetic-request-v1',
                  'core_version': 'synthetic-core-v1'}
        record = run_process('prepare', packet)
        response = fake_response(record['sent']['payload'])
        result = run_process('complete', {'record': record, 'response': response, 'duration_seconds': 0.0})
        local = ts.evaluate('claim_support', INPUTS['claim_support'], model='synthetic-request-v1',
                            core_version='synthetic-core-v1', transport=fake_response, clock=lambda: 0.0)
        self.assertEqual(result, json.loads(json.dumps(local.to_dict())))
        self.assertEqual(result['outcome'], ts.UNRESOLVED)
        drifted = []
        for mutate in (lambda r: r['sent']['payload']['state'].update(claim='drift'),
                       lambda r: r['sent']['payload']['questions']['supports'].update(instructions='changed question'),
                       lambda r: r['sent'].update(profile='requirement_coverage'),
                       lambda r: r['sent'].update(outcome=ts.NO_FIT),
                       lambda r: r['sent'].update(reason='changed reason'),
                       lambda r: r['sent'].update(question_fingerprint='0' * 64),
                       lambda r: r['sent'].update(question_version='1'),
                       lambda r: r['sent'].update(references=['other.md']),
                       lambda r: r.update(core_version='other-core'),
                       lambda r: r['sent']['payload'].update(model='other-model'),
                       lambda r: r['inputs'].update(claim='changed original')):
            changed = copy.deepcopy(record)
            mutate(changed)
            drifted.append(run_process('complete', {'record': changed, 'response': response, 'duration_seconds': 0.0}))
        self.assertEqual(drifted, [{'drift': True}] * len(drifted))


class SourceContracts(unittest.TestCase):
    def setUp(self):
        # Enforce clean-checkout independence even when ignored artifacts happen to exist.
        for name in ('open', 'exists', 'is_file'):
            original = getattr(Path, name)
            def guarded(path, *args, _original=original, **kwargs):
                self.assertFalse(Path(path).absolute().is_relative_to(ROOT / '.agentic-workflow'),
                                 'real ignored artifacts are not test prerequisites')
                return _original(path, *args, **kwargs)
            patcher = patch.object(Path, name, guarded)
            patcher.start()
            self.addCleanup(patcher.stop)

    def sources(self):
        return {p: (ROOT / p).read_text(encoding='utf-8') for p in checker.TYPESAFE_SOURCES}

    def check_links(self, texts):
        sources = design.Sources(ROOT)
        for relative, text in texts.items():
            path = ROOT / relative
            checker.check_links(ROOT, path, text)
            self.assertEqual(design.link_findings(sources, path, text, ROOT), [], relative)
            for target in REQUIRED_LINKS.get(relative, ()):
                self.assertTrue(design.links_to(path, text, ROOT / target), (relative, target))

    def test_all_changed_versioned_markdown_links_and_required_edges(self):
        texts = self.sources()
        self.check_links(texts)
        checker.check_typesafe_sources(texts)
        for relative, targets in REQUIRED_LINKS.items():
            for target in targets:
                path, text = ROOT / relative, texts[relative]
                for match in list(design.LINK.finditer(text)):
                    if design.resolve(path, match.group(2)) == (ROOT / target).resolve():
                        text = text.replace(match.group(0), '')
                with self.subTest(source=relative, removed=target), self.assertRaises(AssertionError):
                    self.check_links(dict(texts, **{relative: text}))
        target = ROOT / TEMPLATE
        original_exists, original_is_file = Path.exists, Path.is_file
        with patch.object(Path, 'exists', lambda p: False if p == target else original_exists(p)), patch.object(Path, 'is_file', lambda p: False if p == target else original_is_file(p)):
            with self.assertRaises(checker.ContractError):
                self.check_links(texts)
        text = texts['AGENTS.md'].replace(TEMPLATE + ')', TEMPLATE + '#nonexistent-anchor)')
        self.assertTrue(design.link_findings(design.Sources(ROOT), ROOT / 'AGENTS.md', text, ROOT))

    def test_template_creation_equality_collision_and_conditional_root(self):
        # Real .agentic-workflow files are never inputs or outputs of these tests.
        with tempfile.TemporaryDirectory(prefix='typesafe-project-', dir='/tmp/opencode') as directory:
            project = Path(directory)
            self.assertFalse((project / '.agentic-workflow').exists())
            template = (ROOT / TEMPLATE).read_bytes()
            local = project / '.agentic-workflow/evaluations/typesafe/AGENTS.md'
            local.parent.mkdir(parents=True)
            with local.open('xb') as stream:
                stream.write(template)
            self.assertEqual(local.read_bytes(), template)
            with self.assertRaises(FileExistsError), local.open('xb'):
                self.fail('foreign guide must not be overwritten')
            with patch.object(Path, 'read_bytes', return_value=template + b'changed'):
                with self.assertRaises(AssertionError):
                    self.assertEqual(local.read_bytes(), template)
            self.assertEqual(local.read_bytes(), template)
            texts = self.sources()
            text = texts['AGENTS.md']
            self.assertTrue(design.links_to(ROOT / 'AGENTS.md', text, ROOT / TEMPLATE))
            bad = text.replace(TEMPLATE, '.agentic-workflow/evaluations/typesafe/AGENTS.md')
            with self.assertRaises(AssertionError):
                self.assertTrue(design.links_to(ROOT / 'AGENTS.md', bad, ROOT / TEMPLATE))
            for clause in checker.TYPESAFE_SOURCES['AGENTS.md']:
                bad = re.sub(clause, '', text)
                with self.assertRaises(checker.ContractError):
                    checker.check_typesafe_sources(dict(texts, **{'AGENTS.md': bad}))


if __name__ == '__main__':
    unittest.main()
