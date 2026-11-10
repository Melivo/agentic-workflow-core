"""Pure byte binding and append-only comparison data; no IO, model calls or workflow state.

Public API: bind_plan, model_event, fix_review, comparison_event, append_event; ComparisonError has
fixed codes only. Values are detached JSON data, not authenticated records. The owner
must preserve originals, fix the review before disclosure, supply minimized opaque
references/metadata (never secrets), and write new events only to free paths. This
module cannot establish blindness, authorize requests, or interpret probabilities.
"""
from datetime import datetime
import hashlib
import json
import math
import re

MAX_IDENTIFIER_LENGTH = 256
SCHEMA = 'plan-comparison/v1'
EVENT_TYPE = 'criterion_comparison'
MODEL_EVENT_TYPE = 'model_observation'
LABELS = ('material_defect', 'no_material_defect', 'unresolved')
VERDICTS = ('defect_found', 'no_defect_found')
SELECTIONS = ('eligible', 'excluded', 'contaminated', 'unknown')
FIXED_SELECTIONS = ('excluded', 'contaminated')


class ComparisonError(ValueError):
    """Fixed failure code, without input values or underlying exception text."""


def _require(ok, code='invalid_data'):
    if not ok:
        raise ComparisonError(code)


def _token(value):
    _require(isinstance(value, str) and len(value) <= MAX_IDENTIFIER_LENGTH
             and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@#+-]*', value) is not None)
    return value


def _digest(value):
    _require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None)
    return value


def _bytes_hash(value):
    _require(type(value) is bytes, 'original_bytes_required')
    return hashlib.sha256(value).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def _copy(value):
    return json.loads(_canonical(value))


def _criteria(criteria):
    _require(type(criteria) is dict and bool(criteria), 'invalid_criteria')
    for key, text in criteria.items():
        _token(key)
        _require(isinstance(text, str) and bool(text) and not any(0xD800 <= ord(c) <= 0xDFFF for c in text), 'invalid_criteria')
    return sorted(criteria), hashlib.sha256(_canonical(criteria).encode('ascii')).hexdigest()


def _utc(value):
    _require(isinstance(value, str) and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]{1,6})?Z', value) is not None)
    parsed = None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        pass
    _require(parsed is not None)
    return parsed


def _binding(value):
    _require(type(value) is dict and set(value) == {'schema', 'project_id', 'plan_ref', 'plan_sha256', 'criteria_ids', 'criteria_sha256'})
    _require(value['schema'] == SCHEMA)
    _token(value['project_id']), _token(value['plan_ref'])
    _digest(value['plan_sha256']), _digest(value['criteria_sha256'])
    ids = value['criteria_ids']
    _require(type(ids) is list and bool(ids))
    for criterion in ids:
        _token(criterion)
    _require(ids == sorted(set(ids)))


def bind_plan(*, project_id, plan_ref, plan_bytes, criteria):
    """Bind exact bytes and criterion IDs/text; neither raw plans nor criteria are exported."""
    ids, digest = _criteria(criteria)
    return {'schema': SCHEMA, 'project_id': _token(project_id), 'plan_ref': _token(plan_ref),
            'plan_sha256': _bytes_hash(plan_bytes), 'criteria_ids': ids, 'criteria_sha256': digest}


def _matches(binding, plan_bytes, criteria):
    if plan_bytes is None or criteria is None:
        return False
    ids, digest = _criteria(criteria)
    return (_bytes_hash(plan_bytes) == binding['plan_sha256'] and ids == binding['criteria_ids']
            and digest == binding['criteria_sha256'])


def fix_review(binding, *, plan_bytes, criteria, review_ref, review_bytes, verdicts, reviewer_role, recorded_at):
    """Record a complete initial review; owner calls before revealing model information.

    A missing/mismatching original or an incomplete verdict set is rejected, not repaired.
    The returned data is a value snapshot; callers can persist it without storing raw text.
    """
    _binding(binding)
    _require(_matches(binding, plan_bytes, criteria), 'binding_mismatch')
    _require(type(verdicts) is dict and set(verdicts) == set(binding['criteria_ids']), 'review_criteria_mismatch')
    _require(all(v in VERDICTS for v in verdicts.values()), 'invalid_verdict')
    _utc(recorded_at)
    return {'binding': _copy(binding), 'review_ref': _token(review_ref),
            'review_sha256': _bytes_hash(review_bytes), 'verdicts': _copy(verdicts),
            'reviewer_role': _token(reviewer_role), 'recorded_at': recorded_at}


def _review(value):
    _require(type(value) is dict and set(value) == {'binding', 'review_ref', 'review_sha256', 'verdicts', 'reviewer_role', 'recorded_at'})
    _binding(value['binding'])
    _token(value['review_ref']), _token(value['reviewer_role'])
    _digest(value['review_sha256'])
    _utc(value['recorded_at'])
    _require(type(value['verdicts']) is dict and set(value['verdicts']) == set(value['binding']['criteria_ids']), 'review_criteria_mismatch')
    _require(all(v in VERDICTS for v in value['verdicts'].values()), 'invalid_verdict')


def _number(value, *, probability=False):
    _require(type(value) in (int, float) and value >= 0
             and (type(value) is int or math.isfinite(value)))
    _require(not probability or value <= 1)
    return value


def _observation(result):
    # Project the existing EvaluationResult.to_dict(), never its raw payload/references,
    # free-form reasons, exceptions or answer text. Profile/question ownership stays there.
    _require(type(result) is dict)
    answers = result.get('answers')
    probabilities = None
    if answers is not None:
        _require(type(answers) is dict)
        probabilities = {}
        for question, answer in answers.items():
            _token(question)
            _require(type(answer) is dict)
            if answer.get('type') == 'noul':
                probabilities[question] = {'noul': _number(answer.get('noul'), probability=True)}
            else:
                _require(answer.get('type') == 'choice' and type(answer.get('probabilities')) is dict)
                options = answer['probabilities']
                probabilities[question] = {'probabilities': {_token(k): _number(v, probability=True) for k, v in options.items()},
                                           'confidence': _number(answer.get('confidence'), probability=True)}
    outcome = result.get('outcome')
    _require(outcome in ('unresolved', 'error', 'no_fit'))
    uncertainty = result.get('uncertainty')
    _require(uncertainty in ('unassessed', 'no_model_answer'))
    failed = outcome == 'error'
    _require(outcome == 'unresolved' or answers is None)
    _require(failed == (result.get('error') is not None))
    status = result.get('http_status')
    _require(status is None or type(status) is int and 100 <= status <= 599)
    sent = result.get('request_sent')
    _require(type(sent) is bool)
    duration = result.get('duration_seconds')
    if duration is not None:
        _number(duration)
    usage = result.get('usage')
    _require(usage is None or type(usage) is dict)
    counts = {}
    for key in ('input_tokens', 'output_tokens'):
        count = usage.get(key) if usage is not None else None
        _require(count is None or type(count) is int and count >= 0)
        counts[key] = count
    metadata = {}
    for key in ('profile', 'core_version', 'requested_model', 'response_model', 'question_version', 'question_fingerprint'):
        value = result.get(key)
        if value is not None:
            (_digest if key == 'question_fingerprint' else _token)(value)
        metadata[key] = value
    return {**metadata, 'probabilities': probabilities, 'uncertainty': uncertainty,
            'model_status': 'api_error' if failed else 'no_fit' if outcome == 'no_fit' else 'uncertain',
            'api_error': {'occurred': failed, 'http_status': status}, 'request_sent': sent,
            'duration_seconds': duration, 'usage': counts}


def _identity(event):
    binding = event['binding']
    fields = [SCHEMA, binding['project_id'], binding['plan_sha256'], event['criterion_id'], event['event_type'], event['revision']]
    return 'pc1-' + hashlib.sha256(_canonical(fields).encode('ascii')).hexdigest()


def model_event(binding, *, criterion_id, evaluation, selection='unknown', previous=None):
    """Minimized model data can be retained before review, without inventing a reviewer label.

    evaluation is the existing EvaluationResult.to_dict(); this function never calls it.
    Keep this event hidden until the owner has fixed the initial review.
    """
    _binding(binding)
    _require(criterion_id in binding['criteria_ids'], 'unknown_criterion')
    _require(selection in SELECTIONS)
    revision, predecessor = _revision(binding, criterion_id, MODEL_EVENT_TYPE, previous)
    if previous is not None:
        _preserve_selection(previous['selection'], selection)
    event = {'schema': SCHEMA, 'event_type': MODEL_EVENT_TYPE, 'binding': _copy(binding),
             'criterion_id': criterion_id, 'revision': revision, 'previous_id': predecessor, 'supersedes': predecessor,
             'initial_review': None, 'observation': _observation(evaluation), 'selection': selection,
             'adjudication': None, 'unresolved_reason': 'initial_review_pending', 'model_event_id': None}
    event['event_id'] = _identity(event)
    return event


def _preserve_selection(original, selection):
    # unknown may be clarified; recorded exclusion/contamination cannot be washed away.
    _require(original not in FIXED_SELECTIONS or selection == original, 'selection_conflict')


def _revision(binding, criterion_id, event_type, previous):
    if previous is None:
        return 1, None
    _event(previous)
    _require(previous['binding'] == binding and previous['criterion_id'] == criterion_id
             and previous['event_type'] == event_type, 'predecessor_mismatch')
    return previous['revision'] + 1, previous['event_id']


def comparison_event(model, initial_review, *, plan_bytes, criteria, review_bytes,
                     adjudication, selection=None, previous=None):
    """Create a detached event; missing/drifting originals or contaminated selection stay unresolved.

    Adjudication is supplied by a reviewer, never inferred. No confirmed model evaluation
    rule exists: even extreme probabilities remain uncertain. This is not review/v1.
    previous is the retained prior event for this identity, or None for revision one.
    """
    _event(model)
    _require(model['event_type'] == MODEL_EVENT_TYPE, 'model_event_required')
    binding, criterion_id = model['binding'], model['criterion_id']
    selection = model['selection'] if selection is None else selection
    _require(selection in SELECTIONS)
    revision, predecessor = _revision(binding, criterion_id, EVENT_TYPE, previous)
    _preserve_selection(model['selection'], selection)
    if previous is not None:
        _preserve_selection(previous['selection'], selection)
        fixed_review = previous['initial_review']
        if fixed_review is not None:
            _require(initial_review is None or initial_review == fixed_review, 'initial_review_conflict')
            # Carry the fixed record even while original bytes are temporarily unavailable.
            initial_review = fixed_review
    _require(type(adjudication) is dict and set(adjudication) == {'label', 'evidence_ref', 'reviewer_role', 'recorded_at'})
    _require(adjudication['label'] in LABELS)
    _token(adjudication['evidence_ref']), _token(adjudication['reviewer_role'])
    when = _utc(adjudication['recorded_at'])
    reason = None
    if plan_bytes is None or criteria is None or review_bytes is None or initial_review is None:
        reason = 'missing_original'
    elif not _matches(binding, plan_bytes, criteria):
        reason = 'binding_mismatch'
    if initial_review is not None:
        _review(initial_review)
        if reason is None and (initial_review['binding'] != binding or _bytes_hash(review_bytes) != initial_review['review_sha256']):
            reason = 'initial_review_mismatch'
        if reason is None and when <= _utc(initial_review['recorded_at']):
            reason = 'review_not_prior'
    if reason is None and selection != 'eligible':
        reason = 'selection_' + selection
    decision = _copy(adjudication)
    decision['reported_label'] = decision['label']
    if reason is not None:
        decision['label'] = 'unresolved'
    event = {'schema': SCHEMA, 'event_type': EVENT_TYPE, 'binding': _copy(binding),
             'criterion_id': criterion_id, 'revision': revision, 'previous_id': predecessor, 'supersedes': predecessor,
             'initial_review': _copy(initial_review) if initial_review is not None else None,
             'observation': _copy(model['observation']), 'selection': selection,
             'adjudication': decision, 'unresolved_reason': reason, 'model_event_id': model['event_id']}
    event['event_id'] = _identity(event)
    return event


def _event(event):
    _require(type(event) is dict and set(event) == {'schema', 'event_type', 'binding', 'criterion_id', 'revision', 'previous_id', 'supersedes', 'initial_review', 'observation', 'selection', 'adjudication', 'unresolved_reason', 'event_id', 'model_event_id'})
    _binding(event['binding'])
    _require(event['schema'] == SCHEMA and event['event_type'] in (MODEL_EVENT_TYPE, EVENT_TYPE))
    _require(type(event['revision']) is int and event['revision'] >= 1)
    _require(event['criterion_id'] in event['binding']['criteria_ids'])
    _require(event['event_id'] == _identity(event), 'identity_mismatch')
    _require(event['previous_id'] == event['supersedes'])
    _require((event['previous_id'] is None) == (event['revision'] == 1))


def append_event(events, event):
    """Return a new ledger with idempotency/conflict and linear revision checks; never write.

    events/event must be values produced by this module, not an untrusted JSON importer.
    The owner must supply the complete retained ledger; concurrent file exclusion is its job.
    """
    _require(type(events) in (list, tuple))
    result, by_id, latest = [], {}, {}
    for item in [*events, event]:
        _event(item)
        encoded = _canonical(item)
        key = (item['binding']['project_id'], item['binding']['plan_sha256'], item['criterion_id'], item['event_type'])
        identifier = item['event_id']
        if identifier in by_id:
            _require(by_id[identifier] == encoded, 'payload_conflict')
            continue
        prior = latest.get(key)
        _require((prior is None and item['revision'] == 1) or
                 (prior is not None and item['revision'] == prior['revision'] + 1 and item['previous_id'] == prior['event_id']), 'revision_conflict')
        by_id[identifier], latest[key] = encoded, item
        result.append(_copy(item))
    return result
