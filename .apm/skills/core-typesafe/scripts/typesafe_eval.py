#!/usr/bin/env python3
"""Advisory TypeSafe evaluation for three Core question profiles (Python standard library only).

Importing and building requests never touches the network; only a transport the caller passes can
send anything. Results are hints: they grant no approval, dispatch, review verdict or workflow status.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import http.client
import json
import math
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
API_KEY_ENV = 'TYPESAFE_API_KEY'
TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 1024 * 1024
# The API documents that Choice probabilities sum to "approximately 1"; this only rejects damaged data.
PROBABILITY_SUM_TOLERANCE = 0.05
MAX_CHOICE_OPTIONS = 255
QUESTION_VERSION = '2'
# Only this fixed bootstrap and the module path enter argv; request data goes through stdin.
_WORKER_CODE = "import runpy, sys; runpy.run_path(sys.argv[1])['_transport_worker']()"
_MAX_WORKER_BYTES = 2 * MAX_RESPONSE_BYTES + 1024

PROFILES = ('skill_relevance', 'requirement_coverage', 'claim_support')

CALLABLE, NO_FIT, UNRESOLVED, ERROR = 'callable', 'no_fit', 'unresolved', 'error'
# No action threshold is confirmed yet, so a model answer never settles the semantic decision.
REASON_NO_RULE = 'no_confirmed_evaluation_rule'
UNCERTAINTY_UNASSESSED, UNCERTAINTY_NO_ANSWER = 'unassessed', 'no_model_answer'

_MESSAGES = {
    'input_invalid': 'Eingabe verletzt den Profilvertrag.',
    'transport_missing': 'Kein Transport übergeben; nichts wurde gesendet.',
    'key_missing': 'Der API-Schlüssel fehlt in der geerbten Umgebung.',
    'key_invalid': 'Der API-Schlüssel hat kein gültiges Headerformat.',
    'auth_failed': 'Die API hat die Authentifizierung abgelehnt.',
    'http_error': 'Die API antwortete mit einem unerwarteten HTTP-Status.',
    'timeout': 'Die Anfrage überschritt das Zeitlimit.',
    'network_error': 'Die Verbindung zur API schlug fehl.',
    'response_too_large': 'Die Antwort überschreitet das Größenlimit.',
    'response_invalid': 'Die Antwort verletzt den erwarteten Vertrag.',
    'transport_failed': 'Der übergebene Transport schlug fehl.',
}


class EvaluationError(Exception):
    """Technical failure with a fixed message; never carries payloads, bodies or keys."""

    def __init__(self, code, http_status=None):
        super().__init__(_MESSAGES[code])
        self.code = code
        self.http_status = http_status


class InputValidationError(EvaluationError):
    def __init__(self, field):
        super().__init__('input_invalid')
        self.field = field
        self.args = ('%s: %s' % (field, _MESSAGES['input_invalid']),)


class TransportError(EvaluationError):
    """A transport raises this to report a classified failure (see _MESSAGES for the codes)."""


@dataclass(frozen=True)
class PreparedRequest:
    profile: str
    outcome: str
    reason: str | None
    payload: dict | None
    references: tuple
    question_version: str
    question_fingerprint: str
    # Immutable build-time input snapshot; not a serialized request or authentication token.
    _source: str | None = field(default=None, init=False, repr=False, compare=False)


@dataclass(frozen=True)
class EvaluationResult:
    profile: str | None
    outcome: str
    reason: str | None
    uncertainty: str
    answers: dict | None
    references: tuple
    error: str | None
    http_status: int | None
    request_sent: bool
    requested_model: str | None
    response_model: str | None
    question_version: str | None
    question_fingerprint: str | None
    core_version: str | None
    duration_seconds: float
    usage: dict

    def to_dict(self):
        return asdict(self)


def _text(inputs, field):
    value = inputs.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(field)
    # Reject surrogate code points before UTF-8 hashing, without creating a raw encoding exception.
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise InputValidationError(field)
    return value


def _fields(inputs, *required):
    if not isinstance(inputs, dict) or set(inputs) != set(required):
        raise InputValidationError('inputs')


def _unique(refs, field):
    if len(set(refs)) != len(refs):
        raise InputValidationError(field)


def _skill_relevance(inputs):
    _fields(inputs, 'goal', 'task', 'candidates')
    candidates = inputs['candidates']
    if not isinstance(candidates, list) or len(candidates) > MAX_CHOICE_OPTIONS:
        raise InputValidationError('candidates')
    for item in candidates:
        _fields(item, 'ref', 'responsibility')
        _text(item, 'ref'), _text(item, 'responsibility')
    refs = [item['ref'] for item in candidates]
    _unique(refs, 'candidates')
    offered = {item['ref']: item['responsibility'] for item in candidates}
    state = {'goal': _text(inputs, 'goal'), 'task': _text(inputs, 'task'), 'candidates': offered}
    questions = {
        'fit': {'type': 'noul', 'instructions': 'Does `task` need any responsibility listed in `candidates`?',
                'criteria': {'true': 'At least one listed responsibility is needed to carry out the task.',
                             'false': 'The task can be carried out without any listed responsibility.'}},
        'central_responsibility': {'type': 'choice', 'instructions': 'Which responsibility in `candidates` is central to `task`?',
                                   'criteria': dict(offered)},
    }
    return state, questions, refs, (NO_FIT, 'no_candidates') if not candidates else None


def _requirement_coverage(inputs):
    _fields(inputs, 'criterion', 'task', 'evidence')
    evidence = inputs['evidence']
    if not isinstance(evidence, list):
        raise InputValidationError('evidence')
    missing = not evidence
    for item in evidence:
        _fields(item, 'ref', 'text')
        _text(item, 'ref')
        if item['text'] is None:
            missing = True
        else:
            _text(item, 'text')
    refs = [item['ref'] for item in evidence]
    _unique(refs, 'evidence')
    state = {'criterion': _text(inputs, 'criterion'), 'task': _text(inputs, 'task'),
             'evidence': {item['ref']: item['text'] for item in evidence}}
    questions = {
        'covers': {'type': 'noul', 'instructions': 'Does `task` explicitly cover `criterion`, as shown by `evidence`?',
                   'criteria': {'true': 'The evidence shows the task doing what the criterion requires.',
                                'false': 'The evidence does not explicitly establish the required work, including evidence silent about it.'}},
    }
    return state, questions, refs, (UNRESOLVED, 'missing_evidence') if missing else None


def _claim_support(inputs):
    _fields(inputs, 'claim', 'ref', 'passage')
    ref = _text(inputs, 'ref')
    if inputs['passage'] is not None:
        _text(inputs, 'passage')
    state = {'claim': _text(inputs, 'claim'), 'passage': inputs['passage']}
    questions = {
        'supports': {'type': 'noul', 'instructions': 'Does `passage` directly support `claim`?',
                     'criteria': {'true': 'The passage states the claim or directly implies it.',
                                  'false': 'A reader of the passage alone could not conclude the claim.'}},
        'relation': {'type': 'choice', 'instructions': 'How does `passage` relate to `claim`?',
                     'criteria': {'direct_support': 'The passage states the claim or directly implies it.',
                                  'contradiction': 'The passage states the opposite of the claim or implies it is false.',
                                  'topical_only': 'The passage shares the topic of the claim without establishing it.',
                                  'unrelated_passage': 'The passage addresses a different subject than the claim.'}},
        'matching_passage': {'type': 'noul', 'instructions': 'Does `passage` address the subject of `claim`?',
                             'criteria': {'true': 'The passage discusses what the claim is about.',
                                          'false': 'The passage discusses a different subject.'}},
    }
    return state, questions, [ref], (UNRESOLVED, 'missing_passage') if inputs['passage'] is None else None


_BUILDERS = dict(zip(PROFILES, (_skill_relevance, _requirement_coverage, _claim_support)))


def build_request(profile, inputs, *, model):
    """Validate inputs and build the request offline; raises InputValidationError on bad structure."""
    if not isinstance(profile, str) or profile not in _BUILDERS:
        raise InputValidationError('profile')
    if not isinstance(model, str) or not model.strip():
        raise InputValidationError('model')
    state, questions, refs, settled = _BUILDERS[profile](inputs)
    canonical = json.dumps({'profile': profile, 'version': QUESTION_VERSION, 'questions': questions},
                           sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    outcome, reason = settled or (CALLABLE, None)
    payload = None if settled else {'model': model, 'state': state, 'questions': questions}
    prepared = PreparedRequest(profile, outcome, reason, payload, tuple(refs), QUESTION_VERSION,
                               hashlib.sha256(canonical.encode('utf-8')).hexdigest())
    object.__setattr__(prepared, '_source', json.dumps({'profile': profile, 'inputs': inputs, 'model': model}))
    return prepared


def _probability(value):
    # Comparison also rejects NaN and infinities; bool is an int subclass but no probability.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def _noul_answer(answer):
    if not _probability(answer.get('noul')):
        raise EvaluationError('response_invalid')
    return {'type': 'noul', 'noul': answer['noul']}


def _choice_answer(answer, criteria):
    choice, confidence, probabilities = answer.get('choice'), answer.get('confidence'), answer.get('probabilities')
    if (not isinstance(choice, str) or choice not in criteria or not _probability(confidence)
            or not isinstance(probabilities, dict) or set(probabilities) != set(criteria)
            or not all(_probability(v) for v in probabilities.values())
            or abs(sum(probabilities.values()) - 1) > PROBABILITY_SUM_TOLERANCE
            or probabilities[choice] != max(probabilities.values())):
        raise EvaluationError('response_invalid')
    return {'type': 'choice', 'choice': choice, 'confidence': confidence, 'probabilities': dict(probabilities)}


def _token_count(usage, field):
    value = usage.get(field)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationError('response_invalid')
    return value


def _usage(response):
    usage = response.get('usage')
    if usage is None:
        return _unknown_usage()
    if not isinstance(usage, dict):
        raise EvaluationError('response_invalid')
    return {field: _token_count(usage, field) for field in ('input_tokens', 'output_tokens')}


def _unknown_usage():
    return {'input_tokens': None, 'output_tokens': None}


def _parse_response(response, questions):
    """Return (answers, model); damaged data is rejected, never repaired or normalized."""
    if not isinstance(response, dict):
        raise EvaluationError('response_invalid')
    model, answers = response.get('model'), response.get('answers')
    if not isinstance(model, str) or not model.strip() or not isinstance(answers, dict) or set(answers) != set(questions):
        raise EvaluationError('response_invalid')
    parsed = {}
    for question_id, question in questions.items():
        answer = answers[question_id]
        if not isinstance(answer, dict) or answer.get('type') != question['type']:
            raise EvaluationError('response_invalid')
        parsed[question_id] = (_noul_answer(answer) if question['type'] == 'noul'
                               else _choice_answer(answer, question['criteria']))
    return parsed, model


def finalize_response(prepared, response, *, core_version, duration_seconds):
    """Complete a raw response offline for an unchanged in-process build_request result.

    The owner must associate the actual call/response with this request and supply its locally
    measured elapsed seconds. This is not an untrusted JSON importer or proof of sending, retries,
    timing or response origin. request_sent=True means sending is possible, never a delivery claim.
    No transport, key, clock or file is accessed. Invalid completion inputs raise InputValidationError;
    malformed raw responses return an error result, not a negative model answer. Non-callable requests
    cannot be completed with a model response. Do not mutate the request or its private snapshot.
    """
    valid = False
    if type(prepared) is PreparedRequest and isinstance(prepared._source, str):
        try:
            original = build_request(**json.loads(prepared._source))
            valid = prepared == original and original.outcome == CALLABLE
        except (EvaluationError, ValueError, TypeError, RecursionError):
            pass
    # Raise outside the handler: no raw decoder exception or input is reachable as context.
    if not valid:
        raise InputValidationError('prepared')
    if not isinstance(core_version, str) or not core_version.strip():
        raise InputValidationError('core_version')
    if (not isinstance(duration_seconds, (int, float)) or isinstance(duration_seconds, bool)
            or duration_seconds < 0 or duration_seconds > sys.float_info.max
            or not math.isfinite(duration_seconds)):
        raise InputValidationError('duration_seconds')
    answers, response_model, usage, error = None, None, _unknown_usage(), None
    try:
        answers, response_model = _parse_response(response, original.payload['questions'])
        usage = _usage(response)
    except EvaluationError as failure:
        answers, response_model, usage, error = None, None, _unknown_usage(), failure.code
    return EvaluationResult(
        profile=original.profile, outcome=ERROR if error else UNRESOLVED,
        reason=None if error else REASON_NO_RULE,
        uncertainty=UNCERTAINTY_NO_ANSWER if error else UNCERTAINTY_UNASSESSED,
        answers=answers, references=original.references, error=error, http_status=None,
        request_sent=True, requested_model=original.payload['model'], response_model=response_model,
        question_version=original.question_version, question_fingerprint=original.question_fingerprint,
        core_version=core_version, duration_seconds=duration_seconds, usage=usage)


def evaluate(profile, inputs, *, model, core_version, transport, clock=time.monotonic):
    """Evaluate one profile; every expected failure becomes a result, none becomes a negative answer.

    transport(payload: dict) -> dict receives the JSON request and returns the decoded response. It
    runs at most once and only for a callable request; there are no retries.
    """
    started = clock()
    prepared = None
    sent = False
    response_model = None
    usage = _unknown_usage()
    answers = None
    outcome, reason, error, status = ERROR, None, None, None
    try:
        if not isinstance(core_version, str) or not core_version.strip():
            raise InputValidationError('core_version')
        prepared = build_request(profile, inputs, model=model)
        if prepared.outcome != CALLABLE:
            outcome, reason = prepared.outcome, prepared.reason
        elif not callable(transport):
            raise EvaluationError('transport_missing')
        else:
            sent = True
            try:
                response = transport(prepared.payload)
            except EvaluationError:
                raise
            except Exception:
                raise EvaluationError('transport_failed') from None
            return finalize_response(prepared, response, core_version=core_version,
                                     duration_seconds=clock() - started)
    except EvaluationError as failure:
        # Classified key failures guarantee preflight rejection; other failures may have sent data.
        if failure.code in ('key_missing', 'key_invalid'):
            sent = False
        answers, response_model, usage = None, None, _unknown_usage()
        outcome, error, status = ERROR, failure.code, failure.http_status
    return EvaluationResult(
        profile=profile if isinstance(profile, str) and profile in _BUILDERS else None,
        outcome=outcome, reason=reason,
        uncertainty=UNCERTAINTY_UNASSESSED if answers else UNCERTAINTY_NO_ANSWER,
        answers=answers, references=prepared.references if prepared else (),
        error=error, http_status=status, request_sent=sent,
        requested_model=model if isinstance(model, str) else None, response_model=response_model,
        question_version=prepared.question_version if prepared else None,
        question_fingerprint=prepared.question_fingerprint if prepared else None,
        core_version=core_version if isinstance(core_version, str) else None,
        duration_seconds=clock() - started, usage=usage)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _build_opener():
    return urllib.request.build_opener(
        _NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def _http_failure(status):
    return TransportError('auth_failed' if status in (401, 403) else 'http_error', status)


def _exchange(request, timeout):
    try:
        with _build_opener().open(request, timeout=timeout) as response:
            if response.status != 200:
                raise _http_failure(response.status)
            return response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as failure:
        status = failure.code
        failure.close()
        raise _http_failure(status) from None
    except urllib.error.URLError as failure:
        code = 'timeout' if isinstance(failure.reason, TimeoutError) else 'network_error'
        raise TransportError(code) from None
    except TimeoutError:
        raise TransportError('timeout') from None
    except (OSError, http.client.HTTPException):
        raise TransportError('network_error') from None


def _transport_worker():
    """Private one-attempt worker: bounded stdout, no diagnostic output or file writes."""
    try:
        packet = json.loads(sys.stdin.buffer.read())
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(packet['payload']).encode('utf-8'), method='POST',
            headers={'Authorization': 'Bearer ' + os.environ[API_KEY_ENV],
                     'Content-Type': 'application/json', 'Accept': 'application/json'})
        body = _exchange(request, packet['timeout'])
        message = ({'error': 'response_too_large'} if len(body) > MAX_RESPONSE_BYTES
                   else {'body': body.hex()})
    except TransportError as failure:
        message = {'error': failure.code, 'status': failure.http_status}
    except Exception:
        message = {'error': 'network_error'}
    sys.stdout.buffer.write(json.dumps(message).encode('ascii'))


def _bounded_exchange(payload, timeout, started):
    # A socket inactivity timeout cannot bound DNS or a trickling status/header/body. One private
    # process owns all IO so deadline expiry can stop it, rather than leave a sending thread alive.
    packet = json.dumps({'payload': payload, 'timeout': timeout}).encode('utf-8')
    process = None
    try:
        if time.monotonic() - started >= timeout:
            raise TransportError('timeout')
        process = subprocess.Popen(
            [sys.executable, '-I', '-B', '-c', _WORKER_CODE, os.path.abspath(__file__)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise TransportError('timeout')
        try:
            output, _ = process.communicate(packet, timeout=remaining)
        except subprocess.TimeoutExpired:
            raise TransportError('timeout') from None
        if time.monotonic() - started >= timeout:
            raise TransportError('timeout')
        if process.returncode != 0 or len(output) > _MAX_WORKER_BYTES:
            raise TransportError('network_error')
        message = json.loads(output)
        if 'error' in message:
            raise TransportError(message['error'], message.get('status'))
        return bytes.fromhex(message['body'])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise TransportError('network_error') from None
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate()  # Reap before returning, including cancellation and timeout paths.


def https_transport(payload, *, timeout=TIMEOUT_SECONDS):
    """Send once with verified TLS and a total deadline; kill and reap the IO worker on expiry."""
    started = time.monotonic()
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise TransportError('key_missing')
    if not re.fullmatch(r'[\x21-\x7e]+', key):
        raise TransportError('key_invalid')
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not math.isfinite(timeout) or timeout <= 0):
        raise TransportError('input_invalid')
    body = _bounded_exchange(payload, timeout, started)
    if len(body) > MAX_RESPONSE_BYTES:
        raise TransportError('response_too_large')
    try:
        return json.loads(body)
    except (ValueError, RecursionError):
        pass
    # Raise after leaving the handler so no raw decoder exception becomes __context__.
    raise TransportError('response_invalid')
