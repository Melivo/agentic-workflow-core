"""Private append-only collection and explicit bounded delivery; no model/workflow effects.

Public API: project_event(plan_comparison_value, *, projects) -> canonical bytes;
parse_wire(bytes, *, projects) -> detached dict; canonical_wire(dict, *, projects)
-> bytes; payload_hash(bytes) -> SHA256. Collection(path, *, projects, create=False,
lock_timeout=2.0) is a context manager with submit(bytes) -> {event_id,
payload_sha256} ONLY after commit, events() -> insertion-ordered detached values,
backup(free_path) -> consistent validated snapshot. restore(snapshot, free_path,
*, projects) restores ONLY into a new private drill file, never over live data.
CollectionError exposes fixed codes only, without input or underlying exceptions.

CLOSED collection/v1 wire: same fields as plan-comparison/v1 events, top-level
schema changed, plan_ref/review_ref/evidence_ref/reviewer_role replaced by ref- +
SHA256(UTF8 original). binding.schema remains plan-comparison/v1. pc1 identity is
SHA256 of compact sorted ASCII JSON [source schema, project, plan hash, criterion,
event type, revision]. IDs/metadata are bounded ASCII tokens; hashes lowercase
SHA256, references opaque, UTC timestamps end in Z. Numeric probabilities [0,1],
nonnegative integer usage or null, nonnegative duration seconds or null: unknown
is NOT zero. No raw text, extra fields or raw errors. Explicit projects allowlist
must contain only authorized pseudonyms. Minimization is NOT a secret detector,
source authentication, blindness proof, or interpretation of model answers.

Internal schema v1: immutable canonical payload + hash, PK event_id, UNIQUE
(project,plan,criterion,kind,revision), predecessor/model FKs and history index.
Payload is an audit document, not a duplicate relational workflow model. BEGIN
IMMEDIATE serializes history checks + insert; FULL sync, DELETE journal, bounded
lock wait, explicit rollback. No automatic retries, migrations, updates or deletes.
Open/backup/restore replay all canonical values/hashes and complete linear history.
Unknown/foreign schema is refused. Corrections append; rollback preserves data.
Max64KiB/depth32; 10000 maximal events roughly640MiB plus indexes/journal. No quota,
retention, latency or offsite/RTO guarantee; RPO is snapshot capture time, no schedule.

Paths: existing own0700 parent, own0600 regular single-link files, non-symlink
safe ancestors (root sticky temporary ancestors allowed). Existing paths are never
chmodded/adopted. Trust local Linux filesystem, SQLite/hardware persistence, root
and same UID; this is not isolation against their hostile concurrent mutations.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile

WIRE_SCHEMA = 'collection/v1'
SOURCE_SCHEMA = 'plan-comparison/v1'
MAX_WIRE_BYTES = 64 * 1024
MAX_JSON_DEPTH = 32
MAX_TOKEN_LENGTH = 256
# Match typesafe_eval; standalone collection deployment cannot import the evaluator.
PROBABILITY_SUM_TOLERANCE = 0.05
LOCK_TIMEOUT = 2.0
APPLICATION_ID = 0x54534331
SCHEMA_VERSION = 1
SELECTIONS = ('eligible', 'excluded', 'contaminated', 'unknown')
FIXED_SELECTIONS = ('excluded', 'contaminated')
LABELS = ('material_defect', 'no_material_defect', 'unresolved')
EVENT_KEYS = frozenset(('schema', 'event_type', 'binding', 'criterion_id', 'revision',
                       'previous_id', 'supersedes', 'initial_review', 'observation',
                       'selection', 'adjudication', 'unresolved_reason', 'event_id', 'model_event_id'))
BINDING_KEYS = frozenset(('schema', 'project_id', 'plan_ref', 'plan_sha256', 'criteria_ids', 'criteria_sha256'))
OBS_KEYS = frozenset(('profile', 'core_version', 'requested_model', 'response_model',
                     'question_version', 'question_fingerprint', 'probabilities', 'uncertainty',
                     'model_status', 'api_error', 'request_sent', 'duration_seconds', 'usage'))
# Exact DDL is the open-time schema fingerprint, not merely a version assertion.
DDL = (
    "CREATE TABLE events (event_id TEXT PRIMARY KEY NOT NULL, project TEXT NOT NULL, plan TEXT NOT NULL, criterion TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('model_observation','criterion_comparison')), revision INTEGER NOT NULL CHECK(revision>0), previous_id TEXT REFERENCES events(event_id), model_id TEXT REFERENCES events(event_id), payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, UNIQUE(project,plan,criterion,kind,revision), CHECK((revision=1 AND previous_id IS NULL) OR (revision>1 AND previous_id IS NOT NULL)))",
    "CREATE INDEX events_history ON events(project,plan,criterion,kind,revision)",
    "CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END",
    "CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END",
)


class CollectionError(ValueError):
    """Fixed code, without input, SQL, path or underlying exception text."""


def _require(ok, code='invalid_wire'):
    if not ok:
        raise CollectionError(code)


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _token(value):
    _require(type(value) is str and 0 < len(value) <= MAX_TOKEN_LENGTH
             and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@#+-]*', value) is not None)


def _hash(value, prefix=''):
    _require(type(value) is str and re.fullmatch(re.escape(prefix) + r'[0-9a-f]{64}', value) is not None)


def _number(value, *, probability=False, integer=False):
    _require(type(value) in ((int,) if integer else (int, float)))
    _require(value >= 0 and (type(value) is int or math.isfinite(value)))
    _require(not probability or value <= 1)


def _utc(value):
    _require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]{1,6})?Z', value) is not None)
    result = None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        pass
    _require(result is not None)
    return result


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def payload_hash(data):
    _require(type(data) is bytes)
    return hashlib.sha256(data).hexdigest()


CORE_PROJECT_PATTERN = r'core-[0-9a-f]{64}'


def project_id(identity):
    """Stable local pseudonym; not authentication or protection against guessing."""
    _require(type(identity) is str and 0 < len(identity) <= 4096
             and not any(0xD800 <= ord(c) <= 0xDFFF for c in identity), 'invalid_projects')
    return 'core-' + hashlib.sha256(b'core-project/v1\0' + identity.encode('utf-8')).hexdigest()


class ProjectPolicy(tuple):
    """Immutable explicit opt-in at the existing project membership boundary."""

    def __new__(cls, projects, *, core_project_ids=False):
        _require(type(core_project_ids) is bool, 'invalid_projects')
        allowed = _projects(projects)
        _require(type(allowed) is frozenset, 'invalid_projects')
        return tuple.__new__(cls, (allowed, core_project_ids))

    def __contains__(self, value):
        return (value in self[0] or self[1] and type(value) is str
                and re.fullmatch(CORE_PROJECT_PATTERN, value) is not None)


def _projects(projects):
    if type(projects) is ProjectPolicy:
        return projects
    _require(type(projects) in (set, frozenset, list, tuple) and bool(projects), 'invalid_projects')
    for project in projects:
        _token(project)
    return frozenset(projects)


def _depth(value, level=0):
    _require(level <= MAX_JSON_DEPTH)
    if type(value) is dict:
        for key, item in value.items():
            _require(type(key) is str)
            _depth(item, level + 1)
    elif type(value) is list:
        for item in value:
            _depth(item, level + 1)
    else:
        _require(value is None or type(value) in (str, int, float, bool))
        if type(value) is str:
            _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value))
        if type(value) is float:
            _require(math.isfinite(value))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _invalid_constant(_):
    raise CollectionError('invalid_wire')


def _binding(value, projects):
    _shape(value, BINDING_KEYS)
    _require(value['schema'] == SOURCE_SCHEMA)
    _token(value['project_id'])
    _require(value['project_id'] in projects, 'project_denied')
    _hash(value['plan_ref'], 'ref-')
    _hash(value['plan_sha256'])
    _hash(value['criteria_sha256'])
    ids = value['criteria_ids']
    _require(type(ids) is list and bool(ids))
    for identifier in ids:
        _token(identifier)
    _require(ids == sorted(set(ids)))


def _observation(obs):
    _shape(obs, OBS_KEYS)
    for key in ('profile', 'core_version', 'requested_model', 'response_model', 'question_version'):
        if obs[key] is not None:
            _token(obs[key])
    if obs['question_fingerprint'] is not None:
        _hash(obs['question_fingerprint'])
    _require(obs['model_status'] in ('uncertain', 'no_fit', 'api_error'))
    _require(obs['uncertainty'] in ('unassessed', 'no_model_answer'))
    _require(type(obs['request_sent']) is bool)
    _shape(obs['api_error'], ('occurred', 'http_status'))
    error = obs['api_error']
    _require(type(error['occurred']) is bool and error['occurred'] == (obs['model_status'] == 'api_error'))
    _require(error['http_status'] is None or type(error['http_status']) is int and 100 <= error['http_status'] <= 599)
    if obs['duration_seconds'] is not None:
        _number(obs['duration_seconds'])
    _shape(obs['usage'], ('input_tokens', 'output_tokens'))
    for count in obs['usage'].values():
        if count is not None:
            _number(count, integer=True)
    probabilities = obs['probabilities']
    if probabilities is not None:
        _require(type(probabilities) is dict and bool(probabilities) and obs['model_status'] == 'uncertain')
        for question, answer in probabilities.items():
            _token(question)
            _require(type(answer) is dict)
            if set(answer) == {'noul'}:
                _number(answer['noul'], probability=True)
            else:
                _shape(answer, ('probabilities', 'confidence'))
                _number(answer['confidence'], probability=True)
                options = answer['probabilities']
                _require(type(options) is dict and bool(options))
                for option, p in options.items():
                    _token(option)
                    _number(p, probability=True)
                _require(abs(sum(options.values()) - 1) <= PROBABILITY_SUM_TOLERANCE)
    _require(probabilities is None or obs['uncertainty'] == 'unassessed')


def _identity(event):
    b = event['binding']
    return 'pc1-' + payload_hash(_json([SOURCE_SCHEMA, b['project_id'], b['plan_sha256'],
                                       event['criterion_id'], event['event_type'], event['revision']]).encode('ascii'))


def _validate(event, projects):
    _shape(event, EVENT_KEYS)
    _require(event['schema'] == WIRE_SCHEMA)
    _binding(event['binding'], projects)
    _token(event['criterion_id'])
    _require(event['criterion_id'] in event['binding']['criteria_ids'])
    _require(event['event_type'] in ('model_observation', 'criterion_comparison'))
    _require(type(event['revision']) is int and 1 <= event['revision'] <= 2**63 - 1)
    _require(event['event_id'] == _identity(event), 'identity_conflict')
    _require(event['previous_id'] == event['supersedes'])
    _require((event['previous_id'] is None) == (event['revision'] == 1))
    if event['previous_id'] is not None:
        _hash(event['previous_id'], 'pc1-')
    _require(event['selection'] in SELECTIONS)
    _observation(event['observation'])
    review, decision, reason = event['initial_review'], event['adjudication'], event['unresolved_reason']
    if event['event_type'] == 'model_observation':
        _require(review is None and decision is None and reason == 'initial_review_pending' and event['model_event_id'] is None)
        return
    _hash(event['model_event_id'], 'pc1-')
    _shape(decision, ('label', 'reported_label', 'evidence_ref', 'reviewer_role', 'recorded_at'))
    _require(decision['label'] in LABELS and decision['reported_label'] in LABELS)
    _hash(decision['evidence_ref'], 'ref-')
    _hash(decision['reviewer_role'], 'ref-')
    when = _utc(decision['recorded_at'])
    _require(reason in (None, 'missing_original', 'binding_mismatch', 'initial_review_mismatch',
                        'review_not_prior', 'selection_unknown', 'selection_excluded', 'selection_contaminated'))
    if review is not None:
        _shape(review, ('binding', 'review_ref', 'review_sha256', 'verdicts', 'reviewer_role', 'recorded_at'))
        _binding(review['binding'], projects)
        _require(review['binding'] == event['binding'])
        _hash(review['review_ref'], 'ref-')
        _hash(review['reviewer_role'], 'ref-')
        _hash(review['review_sha256'])
        _shape(review['verdicts'], event['binding']['criteria_ids'])
        _require(all(v in ('defect_found', 'no_defect_found') for v in review['verdicts'].values()))
        prior_time = _utc(review['recorded_at'])
        if when <= prior_time:
            _require(reason in ('missing_original', 'binding_mismatch', 'initial_review_mismatch', 'review_not_prior'))
        if reason == 'review_not_prior':
            _require(when <= prior_time)
    else:
        _require(reason == 'missing_original')
    if reason is None:
        _require(event['selection'] == 'eligible' and decision['label'] == decision['reported_label'])
    else:
        _require(decision['label'] == 'unresolved')
        if reason.startswith('selection_'):
            _require(reason == 'selection_' + event['selection'] and event['selection'] != 'eligible')


def canonical_wire(event, *, projects):
    """Validate a wire value and return canonical bytes, not an envelope."""
    result = None
    try:
        _depth(event)
        _validate(event, _projects(projects))
        result = _json(event).encode('ascii')
        _require(len(result) <= MAX_WIRE_BYTES, 'wire_too_large')
    except CollectionError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    _require(result is not None)
    return result


def parse_wire(data, *, projects):
    """Strict UTF8 JSON; duplicates, constants, depth and unknown keys are rejected."""
    _require(type(data) is bytes)
    _require(len(data) <= MAX_WIRE_BYTES, 'wire_too_large')
    result = None
    try:
        result = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except CollectionError:
        raise
    except (ValueError, UnicodeError, TypeError, RecursionError):
        pass
    _require(result is not None)
    canonical_wire(result, projects=projects)
    return result


def project_event(event, *, projects):
    """Hash references, then validate independently; no private source helper."""
    result = None
    try:
        _depth(event)
        _shape(event, EVENT_KEYS)
        _require(event['schema'] == SOURCE_SCHEMA)
        result = json.loads(_json(event))
        result['schema'] = WIRE_SCHEMA
        bindings = [result['binding']]
        if result['initial_review'] is not None:
            bindings.append(result['initial_review']['binding'])
        for binding in bindings:
            _shape(binding, BINDING_KEYS)
            _token(binding['plan_ref'])
            binding['plan_ref'] = 'ref-' + payload_hash(binding['plan_ref'].encode('utf-8'))
        for value, fields in ((result['initial_review'], ('review_ref', 'reviewer_role')),
                              (result['adjudication'], ('evidence_ref', 'reviewer_role'))):
            if value is not None:
                for field in fields:
                    _token(value[field])
                    value[field] = 'ref-' + payload_hash(value[field].encode('utf-8'))
    except CollectionError:
        raise
    except (KeyError, ValueError, TypeError, OverflowError, RecursionError):
        result = None
    _require(result is not None)
    return canonical_wire(result, projects=projects)


def _key(event):
    b = event['binding']
    return b['project_id'], b['plan_sha256'], event['criterion_id'], event['event_type']


def _preserve(original, selection):
    _require(original not in FIXED_SELECTIONS or original == selection, 'history_conflict')


def _history(event, prior, model):
    if prior is None:
        _require(event['revision'] == 1, 'missing_predecessor')
    else:
        _require(event['revision'] == prior['revision'] + 1 and event['previous_id'] == prior['event_id'], 'history_conflict')
        _require(event['binding'] == prior['binding'], 'history_conflict')
        _preserve(prior['selection'], event['selection'])
        if prior['initial_review'] is not None:
            _require(_json(event['initial_review']) == _json(prior['initial_review']), 'history_conflict')
    if event['event_type'] == 'criterion_comparison':
        _require(model is not None, 'missing_model')
        _require(model['event_type'] == 'model_observation' and _key(model)[:3] == _key(event)[:3]
                 and model['binding'] == event['binding']
                 and _json(model['observation']) == _json(event['observation']), 'history_conflict')
        _preserve(model['selection'], event['selection'])


def _private_path(path, *, free=False):
    result = None
    try:
        raw = os.fspath(path)
        _require(type(raw) is str and '\x00' not in raw and '..' not in Path(raw).parts, 'unsafe_path')
        p = Path(os.path.abspath(raw))
        for parent in reversed(p.parents):
            s = parent.lstat()
            _require(stat.S_ISDIR(s.st_mode) and s.st_uid in (0, os.geteuid()), 'unsafe_path')
            _require(not s.st_mode & 0o022 or s.st_uid == 0 and s.st_mode & stat.S_ISVTX, 'unsafe_path')
        s = p.parent.lstat()
        _require(s.st_uid == os.geteuid() and stat.S_IMODE(s.st_mode) == 0o700, 'unsafe_path')
        for candidate in (p, Path(str(p) + '-journal'), Path(str(p) + '-wal'), Path(str(p) + '-shm')):
            try:
                s = candidate.lstat()
            except FileNotFoundError:
                continue
            _require(not free or candidate != p, 'path_exists')
            _require(stat.S_ISREG(s.st_mode) and s.st_uid == os.geteuid()
                     and stat.S_IMODE(s.st_mode) == 0o600 and s.st_nlink == 1, 'unsafe_path')
            _require(not free, 'unsafe_path')
        result = p
    except CollectionError:
        raise
    except (OSError, TypeError, ValueError):
        pass
    _require(result is not None, 'unsafe_path')
    return result


def _connect(path, timeout):
    connection = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=timeout, isolation_level=None)
    try:
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        _require(connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete', 'schema_mismatch')
    except BaseException:
        connection.close()
        raise
    return connection


@contextmanager
def _transaction(connection):
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise


def _sync_parent(path):
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _audit(connection, projects):
    _require(connection.execute('PRAGMA application_id').fetchone()[0] == APPLICATION_ID
             and connection.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION, 'schema_mismatch')
    actual = {row[0] for row in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL')}
    _require(actual == set(DDL), 'schema_mismatch')
    _require(connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
             and not connection.execute('PRAGMA foreign_key_check').fetchall(), 'storage_invalid')
    latest, by_id = {}, {}
    for row in connection.execute('SELECT event_id,project,plan,criterion,kind,revision,previous_id,model_id,payload,payload_sha256 FROM events ORDER BY rowid'):
        event = parse_wire(row[8].encode('ascii'), projects=projects)
        data = canonical_wire(event, projects=projects)
        _require(row[8] == data.decode('ascii') and row[9] == payload_hash(data), 'storage_invalid')
        _require(tuple(row[:8]) == (event['event_id'], *_key(event), event['revision'], event['previous_id'], event['model_event_id']), 'storage_invalid')
        _history(event, latest.get(_key(event)), by_id.get(event['model_event_id']))
        latest[_key(event)], by_id[event['event_id']] = event, event


class Collection:
    """One thread per connection; SQLite coordinates independent processes."""

    def __init__(self, path, *, projects, create=False, lock_timeout=LOCK_TIMEOUT):
        self._connection = None
        self.projects = _projects(projects)
        _require(type(create) is bool, 'invalid_configuration')
        _require(type(lock_timeout) in (int, float) and 0 <= lock_timeout <= LOCK_TIMEOUT
                 and math.isfinite(lock_timeout), 'invalid_configuration')
        self.path = _private_path(path, free=create)
        failure = False
        try:
            if create:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(fd)
            self._connection = _connect(self.path, lock_timeout)
            with _transaction(self._connection):
                if create:
                    for statement in DDL:
                        self._connection.execute(statement)
                    self._connection.execute('PRAGMA application_id=' + str(APPLICATION_ID))
                    self._connection.execute('PRAGMA user_version=' + str(SCHEMA_VERSION))
                _audit(self._connection, self.projects)
            if create:
                _sync_parent(self.path)
        except (OSError, sqlite3.Error, CollectionError, UnicodeError, ValueError):
            failure = True
        if failure:
            self.close()
            raise CollectionError('storage_unavailable')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        failed = False
        if self._connection is not None:
            connection, self._connection = self._connection, None
            try:
                connection.close()
            except sqlite3.Error:
                failed = True
        if failed:
            raise CollectionError('storage_unavailable')

    def _ready(self):
        _require(self._connection is not None, 'storage_closed')
        _private_path(self.path)

    def submit(self, data):
        """Validate, serialize check+insert, commit, then return canonical hash ACK."""
        event = parse_wire(data, projects=self.projects)
        canonical = canonical_wire(event, projects=self.projects)
        digest = payload_hash(canonical)
        self._ready()
        failed = False
        try:
            with _transaction(self._connection):
                old = self._connection.execute('SELECT payload,payload_sha256 FROM events WHERE event_id=?', (event['event_id'],)).fetchone()
                if old is not None:
                    _require(old == (canonical.decode('ascii'), digest), 'payload_conflict')
                else:
                    row = self._connection.execute('SELECT payload FROM events WHERE project=? AND plan=? AND criterion=? AND kind=? ORDER BY revision DESC LIMIT 1', _key(event)).fetchone()
                    prior = parse_wire(row[0].encode('ascii'), projects=self.projects) if row else None
                    row = self._connection.execute('SELECT payload FROM events WHERE event_id=?', (event['model_event_id'],)).fetchone()
                    model = parse_wire(row[0].encode('ascii'), projects=self.projects) if row else None
                    _history(event, prior, model)
                    self._connection.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',
                                             (event['event_id'], *_key(event), event['revision'], event['previous_id'],
                                              event['model_event_id'], canonical.decode('ascii'), digest))
        except CollectionError:
            raise
        except (sqlite3.Error, OSError, UnicodeError):
            failed = True
        if failed:
            raise CollectionError('storage_unavailable')
        return {'event_id': event['event_id'], 'payload_sha256': digest}

    def events(self):
        self._ready()
        result = None
        try:
            result = [parse_wire(row[0].encode('ascii'), projects=self.projects)
                      for row in self._connection.execute('SELECT payload FROM events ORDER BY rowid')]
        except (sqlite3.Error, UnicodeError):
            pass
        _require(result is not None, 'storage_unavailable')
        return result

    def backup(self, destination):
        """Online snapshot; validate unpublished staging before no-clobber publish."""
        self._ready()
        target = _private_path(destination, free=True)
        temp = db = None
        failure = False
        try:
            fd, name = tempfile.mkstemp(prefix='.collection-snapshot-', dir=target.parent)
            temp = Path(name)
            os.close(fd)
            db = _connect(temp, LOCK_TIMEOUT)
            self._connection.backup(db)
            _audit(db, self.projects)
            db.close()
            db = None
            fd = os.open(temp, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            _private_path(target, free=True)
            os.link(temp, target, follow_symlinks=False)
            temp.unlink()
            temp = None
            _sync_parent(target)
        except (sqlite3.Error, OSError, CollectionError, ValueError, UnicodeError):
            failure = True
        finally:
            try:
                if db is not None:
                    db.close()
                if temp is not None:
                    temp.unlink(missing_ok=True)
            except (sqlite3.Error, OSError):
                # Keep private staging on cleanup failure; never expose raw paths.
                failure = True
        if failure:
            raise CollectionError('backup_failed')
        return target


def restore(snapshot, destination, *, projects):
    """Restore a validated snapshot into a free own private path only."""
    with Collection(snapshot, projects=projects) as source:
        return source.backup(destination)


# Transport is deliberately explicit: no sender runs on import or enqueue.
import argparse
import errno
import fcntl
import selectors
import signal
import socket
import struct
import subprocess
import sys
import time

MAX_OUTBOX_EVENTS = 10000
MAX_OUTBOX_BYTES = 64 * 1024 * 1024
MAX_FLUSH_EVENTS = 100
FLUSH_TIMEOUT = 15.0
SOCKET_TIMEOUT = 5.0
MAX_ACK_BYTES = 256
OUTBOX_APPLICATION_ID = 0x54534F31
DEFAULT_SOCKET = '/run/typesafe-collection/ingest.sock'
DEFAULT_DATABASE = '/var/lib/automation/state/typesafe-collection/events.sqlite'
DEFAULT_PROJECTS = '/etc/automation/typesafe-collection/projects.json'
REMOTE_COMMAND = ('sudo -n -u typesafe-collection /usr/bin/python3 -I '
                  '/srv/automation/typesafe-collection/typesafe_collection.py submit')
OUTBOX_DDL = ('CREATE TABLE queue (sequence INTEGER PRIMARY KEY AUTOINCREMENT, '
              'event_id TEXT UNIQUE NOT NULL, payload BLOB NOT NULL, payload_sha256 TEXT NOT NULL)',)


def _bounded_number(value, maximum):
    _require(type(value) in (int, float) and 0 < value <= maximum
             and math.isfinite(value), 'invalid_configuration')
    return value


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    _require(remaining > 0, 'transport_timeout')
    return remaining


def _ack(data):
    """Only a closed, bounded commit receipt, never arbitrary server output."""
    result = None
    try:
        _require(type(data) is bytes and len(data) <= MAX_ACK_BYTES, 'invalid_ack')
        result = json.loads(data.decode('ascii'), object_pairs_hook=_pairs,
                            parse_constant=_invalid_constant)
        _shape(result, ('event_id', 'payload_sha256'))
        _hash(result['event_id'], 'pc1-')
        _hash(result['payload_sha256'])
    except (ValueError, UnicodeError, TypeError, RecursionError):
        result = None
    _require(result is not None, 'invalid_ack')
    return result


class Outbox:
    """Private SQLite queue v1. enqueue commits before success, never starts IO.

    flush(sender, timeout<=15, limit<=100) calls sender(bytes, absolute_monotonic
    deadline)->ACK bytes. A trusted sender MUST honor that deadline and clean up
    all IO before return (UnixSender/SSHSender do). No worker thread/retry loop.
    Concurrent connections may resend; only exact ID+canonical-hash ACK removes.
    Failure raises fixed CollectionError and preserves every unacknowledged row;
    earlier acknowledged rows may already be removed. pending() returns bytes.
    Limits may be reduced for tests, never enlarged. Same-UID/root and functioning
    local filesystem assumptions match Collection; not a hard real-time OS bound.
    """

    def __init__(self, path, *, projects, create=False,
                 max_events=MAX_OUTBOX_EVENTS, max_bytes=MAX_OUTBOX_BYTES):
        self.projects = _projects(projects)
        _require(type(create) is bool, 'invalid_configuration')
        for value, maximum in ((max_events, MAX_OUTBOX_EVENTS), (max_bytes, MAX_OUTBOX_BYTES)):
            _require(type(value) is int and 0 < value <= maximum, 'invalid_configuration')
        self.max_events, self.max_bytes = max_events, max_bytes
        self.path = _private_path(path, free=create)
        self._connection = None
        failed = False
        try:
            if create:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(fd)
            self._connection = _connect(self.path, LOCK_TIMEOUT)
            with _transaction(self._connection):
                if create:
                    self._connection.execute(OUTBOX_DDL[0])
                    self._connection.execute('PRAGMA application_id=' + str(OUTBOX_APPLICATION_ID))
                    self._connection.execute('PRAGMA user_version=1')
                db = self._connection
                _require(db.execute('PRAGMA application_id').fetchone()[0] == OUTBOX_APPLICATION_ID
                         and db.execute('PRAGMA user_version').fetchone()[0] == 1, 'schema_mismatch')
                actual = {r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name!='sqlite_sequence'")}
                _require(actual == set(OUTBOX_DDL), 'schema_mismatch')
                _require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'storage_invalid')
                for event_id, data, digest in db.execute('SELECT event_id,payload,payload_sha256 FROM queue'):
                    event = parse_wire(data, projects=self.projects)
                    _require(canonical_wire(event, projects=self.projects) == data
                             and event['event_id'] == event_id and payload_hash(data) == digest, 'storage_invalid')
            if create:
                _sync_parent(self.path)
        except (OSError, sqlite3.Error, CollectionError, ValueError, UnicodeError):
            failed = True
        if failed:
            self.close()
            raise CollectionError('outbox_unavailable')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        failed = False
        if self._connection is not None:
            connection, self._connection = self._connection, None
            try:
                connection.close()
            except sqlite3.Error:
                failed = True
        if failed:
            raise CollectionError('outbox_unavailable')

    def _ready(self):
        _require(self._connection is not None, 'storage_closed')
        _private_path(self.path)

    def enqueue(self, data):
        event = parse_wire(data, projects=self.projects)
        data = canonical_wire(event, projects=self.projects)
        digest = payload_hash(data)
        self._ready()
        failed = False
        try:
            with _transaction(self._connection):
                old = self._connection.execute('SELECT payload,payload_sha256 FROM queue WHERE event_id=?',
                                               (event['event_id'],)).fetchone()
                if old is not None:
                    _require(old == (data, digest), 'payload_conflict')
                else:
                    count, size = self._connection.execute('SELECT count(*),coalesce(sum(length(payload)),0) FROM queue').fetchone()
                    _require(count < self.max_events and size + len(data) <= self.max_bytes, 'outbox_full')
                    self._connection.execute('INSERT INTO queue(event_id,payload,payload_sha256) VALUES(?,?,?)',
                                             (event['event_id'], data, digest))
        except sqlite3.Error:
            failed = True
        if failed:
            raise CollectionError('outbox_unavailable')
        return {'event_id': event['event_id'], 'payload_sha256': digest}

    def pending(self):
        self._ready()
        result = None
        try:
            result = [r[0] for r in self._connection.execute('SELECT payload FROM queue ORDER BY sequence')]
        except sqlite3.Error:
            pass
        _require(result is not None, 'outbox_unavailable')
        return result

    def flush(self, sender, *, timeout=FLUSH_TIMEOUT, limit=MAX_FLUSH_EVENTS):
        deadline = time.monotonic() + _bounded_number(timeout, FLUSH_TIMEOUT)
        _require(type(limit) is int and 0 < limit <= MAX_FLUSH_EVENTS, 'invalid_configuration')
        self._ready()
        sent, failed = 0, False
        try:
            rows = self._connection.execute('SELECT sequence,event_id,payload,payload_sha256 FROM queue ORDER BY sequence LIMIT ?',
                                            (limit,)).fetchall()
            for sequence, event_id, data, digest in rows:
                _remaining(deadline)
                receipt = _ack(sender(data, deadline))
                _remaining(deadline)
                _require(receipt == {'event_id': event_id, 'payload_sha256': digest}, 'ack_mismatch')
                self._connection.execute('PRAGMA busy_timeout=' + str(int(min(LOCK_TIMEOUT, _remaining(deadline)) * 1000)))
                with _transaction(self._connection):
                    self._connection.execute('DELETE FROM queue WHERE sequence=? AND event_id=? AND payload_sha256=?',
                                             (sequence, event_id, digest))
                sent += 1
        except (sqlite3.Error, OSError):
            failed = True
        if failed:
            raise CollectionError('transport_unavailable')
        return sent


def _socket_path(path):
    """Validate ancestors/parent without pretending an existing socket is a DB."""
    p = Path(os.path.abspath(os.fspath(path)))
    _require('..' not in Path(path).parts, 'unsafe_socket')
    for parent in reversed(p.parents):
        s = parent.lstat()
        _require(stat.S_ISDIR(s.st_mode) and s.st_uid in (0, os.geteuid())
                 and (not s.st_mode & 0o022 or s.st_uid == 0 and s.st_mode & stat.S_ISVTX), 'unsafe_socket')
    s = p.parent.lstat()
    _require(s.st_uid == os.geteuid() and stat.S_IMODE(s.st_mode) == 0o700, 'unsafe_socket')
    return p


def _own_socket(path):
    s = path.lstat()
    _require(stat.S_ISSOCK(s.st_mode) and s.st_uid == os.geteuid()
             and stat.S_IMODE(s.st_mode) == 0o600, 'unsafe_socket')
    return s.st_dev, s.st_ino


def _peer(sock):
    _, uid, _ = struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
    _require(uid == os.geteuid(), 'peer_denied')


def _receive(sock, maximum, deadline):
    chunks, size = [], 0
    while True:
        sock.settimeout(min(SOCKET_TIMEOUT, _remaining(deadline)))
        chunk = sock.recv(min(4096, maximum + 1 - size))
        if not chunk:
            return b''.join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        _require(size <= maximum, 'message_too_large')


class UnixSender:
    """One EOF-framed event per connection, bounded receipt; verify server UID."""

    def __init__(self, path=DEFAULT_SOCKET):
        self.path = path

    def __call__(self, data, deadline):
        _require(type(data) is bytes and len(data) <= MAX_WIRE_BYTES, 'wire_too_large')
        failed = False
        result = None
        try:
            path = _socket_path(self.path)
            _own_socket(path)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(min(SOCKET_TIMEOUT, _remaining(deadline)))
                client.connect(str(path))
                _peer(client)
                client.settimeout(min(SOCKET_TIMEOUT, _remaining(deadline)))
                client.sendall(data)
                client.shutdown(socket.SHUT_WR)
                result = _receive(client, MAX_ACK_BYTES, deadline)
                _ack(result)
        except OSError:
            failed = True
        if failed:
            raise CollectionError('transport_unavailable')
        return result


class UnixServer:
    """Single receiver, directory flock prevents bind/stale cleanup races.

    Existing active/foreign objects are never removed. Only own0600 stale socket
    after ECONNREFUSED and unchanged inode is unlinked. close removes ONLY our
    bound inode, releases directory lock on every failure. No worker threads.
    serve_once bounds accept/read separately; read has an absolute 5s deadline.
    Commit uses the existing bounded SQLite lock wait; expired ACK is withheld.
    """

    def __init__(self, collection, path=DEFAULT_SOCKET):
        self.collection, self.socket, self._lock, self._inode = collection, None, None, None
        self.path = _socket_path(path)
        failed = False
        try:
            self._lock = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.path.lexists(self.path):
                old = _own_socket(self.path)
                stale = False
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.settimeout(SOCKET_TIMEOUT)
                    try:
                        probe.connect(str(self.path))
                    except OSError as error:
                        stale = error.errno == errno.ECONNREFUSED
                _require(stale and _own_socket(self.path) == old, 'socket_in_use')
                self.path.unlink()
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # Explicit umask makes the socket private at creation, not after exposure.
            old_mask = os.umask(0o177)
            try:
                self.socket.bind(str(self.path))
            finally:
                os.umask(old_mask)
            self._inode = _own_socket(self.path)
            self.socket.listen(8)
        except (OSError, CollectionError):
            failed = True
        if failed:
            self.close()
            raise CollectionError('socket_unavailable')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        try:
            if self.socket is not None:
                self.socket.close()
                self.socket = None
            if self._inode is not None:
                try:
                    if _own_socket(self.path) == self._inode:
                        self.path.unlink()
                except (FileNotFoundError, CollectionError):
                    pass
                self._inode = None
        finally:
            if self._lock is not None:
                os.close(self._lock)
                self._lock = None

    def serve_once(self, *, timeout=SOCKET_TIMEOUT):
        self.socket.settimeout(_bounded_number(timeout, SOCKET_TIMEOUT))
        try:
            client, _ = self.socket.accept()
        except TimeoutError:
            return False
        with client:
            deadline = time.monotonic() + SOCKET_TIMEOUT
            try:
                _peer(client)
                data = _receive(client, MAX_WIRE_BYTES, deadline)
                _remaining(deadline)
                ack = self.collection.submit(data)
                client.settimeout(_remaining(deadline))
                client.sendall(_json(ack).encode('ascii') + bytes([10]))
            except (CollectionError, OSError):
                # EOF with no receipt is failure; never leak payload/error details.
                return False
        return True


def _process(argv, data, deadline, *, maximum=MAX_ACK_BYTES):
    """Bounded stdout and process group, including children holding pipes open.

    Never shell=True; stderr discarded. killpg in finally also runs after success
    so no descendant can outlive the sender. Tests use only a fake executable.
    """
    process = None
    result, failed = bytearray(), False
    try:
        _remaining(deadline)
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        with selectors.DefaultSelector() as selector:
            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ, 'read')
            if data:
                selector.register(process.stdin, selectors.EVENT_WRITE, 'write')
            else:
                process.stdin.close()
            offset = 0
            while selector.get_map() or process.poll() is None:
                for key, _ in selector.select(min(0.05, _remaining(deadline))):
                    if key.data == 'write':
                        offset += os.write(key.fd, data[offset:])
                        if offset == len(data):
                            selector.unregister(key.fileobj)
                            process.stdin.close()
                    else:
                        chunk = os.read(key.fd, min(4096, maximum + 1 - len(result)))
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            result.extend(chunk)
                            _require(len(result) <= maximum, 'transport_output_limit')
                _remaining(deadline)
            _require(process.returncode == 0, 'transport_failed')
    except (OSError, subprocess.SubprocessError):
        failed = True
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()
    if failed:
        raise CollectionError('transport_unavailable')
    return bytes(result)


SSH_OPTIONS = ('-oBatchMode=yes', '-oStrictHostKeyChecking=yes', '-oUpdateHostKeys=no',
               '-oForwardAgent=no', '-oForwardX11=no', '-oForwardX11Trusted=no',
               '-oClearAllForwardings=yes', '-oControlMaster=no', '-oControlPath=none',
               '-oControlPersist=no', '-oProxyCommand=none', '-oProxyJump=none',
               '-oPermitLocalCommand=no', '-oRemoteCommand=none', '-oRequestTTY=no',
               '-oConnectTimeout=5', '-oConnectionAttempts=1', '-oTunnel=no',
               '-oForkAfterAuthentication=no', '-oStdinNull=no', '-oSessionType=default',
               '-oCanonicalizeHostname=no', '-T')


class SSHSender:
    """Explicit personal alias only; effective config validated before send.

    Existing authentication/known-host configuration remains operator-owned.
    Forwarding, proxy, mux, local and remote commands cannot be inherited.
    No config writes, identity discovery, hostkey acceptance or automatic retry.
    """

    def __init__(self, target, *, executable='/usr/bin/ssh', binding=None, remote_script=None):
        _require(type(target) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', target) is not None,
                 'invalid_ssh_target')
        self.target, self.executable = target, executable
        self.binding = None
        if binding is not None:
            _shape(binding, ('hostname', 'user', 'port'))
            _require(type(binding['hostname']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', binding['hostname']) is not None
                     and type(binding['user']) is str and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', binding['user']) is not None
                     and type(binding['port']) is int and 0 < binding['port'] <= 65535, 'invalid_configuration')
            self.binding = dict(binding)
        self.remote_command = REMOTE_COMMAND
        if remote_script is not None:
            _require(type(remote_script) is str and len(remote_script) <= 1024
                     and re.fullmatch(r'/[A-Za-z0-9_/-]+[.]py', remote_script) is not None
                     and '..' not in Path(remote_script).parts, 'invalid_configuration')
            self.remote_command = 'sudo -n -u typesafe-collection /usr/bin/python3 -I ' + remote_script + ' submit'

    def __call__(self, data, deadline):
        _require(type(data) is bytes and len(data) <= MAX_WIRE_BYTES, 'wire_too_large')
        prefix = [self.executable, *SSH_OPTIONS]
        raw = _process([*prefix, '-G', self.target], b'', deadline, maximum=64 * 1024)
        config = {}
        failed = False
        try:
            for line in raw.decode('utf-8').splitlines():
                if not line.strip():
                    continue
                key, value = line.split(' ', 1)
                config.setdefault(key, []).append(value)
            for key, allowed in {'batchmode': ('yes',), 'stricthostkeychecking': ('true', 'yes'),
                                 'updatehostkeys': ('false', 'no'), 'forwardagent': ('no',),
                                 'forwardx11': ('no',), 'clearallforwardings': ('yes',),
                                 'controlmaster': ('false', 'no'), 'requesttty': ('false', 'no'),
                                 'permitlocalcommand': ('no',)}.items():
                _require(len(config.get(key, [])) == 1 and config[key][0] in allowed, 'unsafe_ssh_config')
            for key in ('proxycommand', 'proxyjump', 'remotecommand', 'controlpath', 'localcommand'):
                _require(config.get(key, ['none']) == ['none'], 'unsafe_ssh_config')
            _require(not any(k in config for k in ('localforward', 'remoteforward', 'dynamicforward')), 'unsafe_ssh_config')
            _require(len(config.get('hostname', [])) == 1 and len(config.get('user', [])) == 1
                     and len(config.get('port', [])) == 1, 'unsafe_ssh_config')
            _require(config['hostname'][0].lower() != self.target.lower(), 'explicit_alias_required')
            _require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', config['hostname'][0]) is not None
                     and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', config['user'][0]) is not None
                     and config['port'][0].isdigit() and 0 < int(config['port'][0]) <= 65535, 'unsafe_ssh_config')
        except (UnicodeError, ValueError):
            failed = True
        if failed:
            raise CollectionError('unsafe_ssh_config')
        if self.binding is not None:
            _require(self.binding == {'hostname': config['hostname'][0], 'user': config['user'][0],
                                      'port': int(config['port'][0])}, 'ssh_binding_mismatch')
        receipt = _process([*prefix, self.target, self.remote_command], data, deadline)
        _ack(receipt)
        return receipt


def _read_config(path):
    """Read bounded non-secret owner/root config without following links."""
    result, failed = None, False
    try:
        p = Path(os.path.abspath(os.fspath(path)))
        _require('..' not in Path(path).parts, 'unsafe_config')
        for parent in reversed(p.parents):
            s = parent.lstat()
            _require(stat.S_ISDIR(s.st_mode) and s.st_uid in (0, os.geteuid())
                     and (not s.st_mode & 0o022 or s.st_uid == 0 and s.st_mode & stat.S_ISVTX), 'unsafe_config')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            s = os.fstat(stream.fileno())
            _require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1
                     and s.st_uid in (0, os.geteuid()) and not s.st_mode & 0o022, 'unsafe_config')
            data = stream.read(4097)
        _require(len(data) <= 4096, 'unsafe_config')
        result = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs)
    except (OSError, ValueError, UnicodeError, TypeError):
        failed = True
    if failed:
        raise CollectionError('invalid_configuration')
    return result


def project_policy(value):
    """Closed server/owner policy value, shared by both configuration boundaries."""
    _require(type(value) is dict and set(value) in ({'projects'}, {'projects', 'core_project_ids'}), 'invalid_projects')
    result = _projects(value['projects'])
    _require(type(result) is frozenset and result <= {'synthetic-a', 'synthetic-b'}, 'invalid_projects')
    if 'core_project_ids' in value:
        result = ProjectPolicy(result, core_project_ids=value['core_project_ids'])
    return result


def load_projects(path):
    """Strict synthetic legacy default; Core IDs require an explicit boolean opt-in."""
    result, failed = None, False
    try:
        result = project_policy(_read_config(path))
    except (OSError, ValueError, UnicodeError, TypeError):
        failed = True
    if failed:
        raise CollectionError('invalid_projects')
    return result


def main(argv=None):
    """No foreign DB adoption. submit defaults match the fixed remote action.

    JSON stdin is one collection/v1 wire, EOF framed, <=64KiB and 5s total.
    enqueue prints local durable receipt (NOT server ACK); flush prints sent count.
    enqueue --create requires a free DB. serve initializes only an absent own DB;
    --create forces a free DB (not for restart units). snapshot/restore never clobber.
    """
    parser = argparse.ArgumentParser(description='Private explicit collection transport')
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('enqueue', 'flush', 'serve', 'submit', 'snapshot', 'restore'):
        p = commands.add_parser(command)
        p.add_argument('--projects', default=DEFAULT_PROJECTS)
        if command in ('enqueue', 'flush'):
            p.add_argument('--outbox', required=True)
        if command in ('enqueue', 'serve'):
            p.add_argument('--create', action='store_true')
        if command in ('serve', 'snapshot'):
            p.add_argument('--database', default=DEFAULT_DATABASE)
        if command in ('serve', 'submit'):
            p.add_argument('--socket', default=DEFAULT_SOCKET)
        if command == 'flush':
            target = p.add_mutually_exclusive_group(required=True)
            target.add_argument('--socket')
            target.add_argument('--ssh-target')
        if command in ('snapshot', 'restore'):
            p.add_argument('--destination', required=True)
        if command == 'restore':
            p.add_argument('--snapshot', required=True)
    args = parser.parse_args(argv)
    failed = False
    command_deadline = time.monotonic() + FLUSH_TIMEOUT
    try:
        projects = load_projects(args.projects)
        if args.command in ('enqueue', 'submit'):
            # Select raw FD instead of buffered read: total deadline also bounds pipe stdin.
            deadline = time.monotonic() + SOCKET_TIMEOUT
            data = bytearray()
            with selectors.DefaultSelector() as selector:
                try:
                    selector.register(sys.stdin.buffer, selectors.EVENT_READ)
                except PermissionError:
                    # epoll cannot watch regular files; size-bounded read is immediate.
                    data.extend(sys.stdin.buffer.read(MAX_WIRE_BYTES + 1))
                else:
                    while True:
                        _require(selector.select(_remaining(deadline)), 'transport_timeout')
                        chunk = os.read(sys.stdin.fileno(), min(4096, MAX_WIRE_BYTES + 1 - len(data)))
                        if not chunk:
                            break
                        data.extend(chunk)
                        _require(len(data) <= MAX_WIRE_BYTES, 'wire_too_large')
            event = parse_wire(bytes(data), projects=projects)
            wire = canonical_wire(event, projects=projects)
            if args.command == 'enqueue':
                with Outbox(args.outbox, projects=projects, create=args.create) as outbox:
                    result = outbox.enqueue(wire)
            else:
                result = _ack(UnixSender(args.socket)(wire, time.monotonic() + SOCKET_TIMEOUT))
                _require(result == {'event_id': event['event_id'], 'payload_sha256': payload_hash(wire)}, 'ack_mismatch')
        elif args.command == 'flush':
            sender = SSHSender(args.ssh_target) if args.ssh_target else UnixSender(args.socket)
            with Outbox(args.outbox, projects=projects) as outbox:
                result = {'sent': outbox.flush(sender, timeout=_remaining(command_deadline))}
        elif args.command == 'serve':
            create = args.create or not os.path.lexists(args.database)
            with Collection(args.database, projects=projects, create=create) as db:
                with UnixServer(db, args.socket) as server:
                    while True:
                        server.serve_once()
        elif args.command == 'snapshot':
            with Collection(args.database, projects=projects) as db:
                db.backup(args.destination)
            result = {'snapshot': 'created'}
        else:
            restore(args.snapshot, args.destination, projects=projects)
            result = {'restore': 'created'}
        print(_json(result), flush=True)
    except (CollectionError, OSError, sqlite3.Error):
        failed = True
    except KeyboardInterrupt:
        return 130
    if failed:
        print('collection_failed', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
