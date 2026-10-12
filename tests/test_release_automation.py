"""Release automation: real Release Please 17.11.2 offline, version guard and a local provider fixture.

Release Please runs unmodified on raw commit fixtures through an in-memory SCM whose write methods
throw. The publisher talks HTTP to a loopback GitHub fixture; no request ever leaves the machine.
"""
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bootstrap_ci  # noqa: E402
import publish_release  # noqa: E402
import release_guard  # noqa: E402

BASE = release_guard.BASELINE_COMMIT
OLDER = 'b' * 40
REPO = 'Melivo/agentic-workflow-core'
BOT, MAINTAINER = 'awc-release[bot]', 'Melivo'
CURRENT_FILES = {p: (ROOT / p).read_text(encoding='utf-8') for p in (release_guard.CONFIG, release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)}

# Policy/provider scenarios describe the historical 0.2.1 release, not the mutable checkout.
# Retain all non-version YAML fields so the real updater and dependency guards stay exercised.
FILES = dict(CURRENT_FILES)
FILES[release_guard.MANIFEST] = json.dumps({'.': '0.2.1'}) + '\n'
FILES[release_guard.VERSION_FILE] = '0.2.1\n'
FILES[release_guard.APM_MANIFEST], _fixture_version_count = re.subn(
    r'^version:.*$', 'version: "0.2.1"', CURRENT_FILES[release_guard.APM_MANIFEST], flags=re.MULTILINE)
assert _fixture_version_count == 1, 'fixture requires exactly one root version field'

# Drives the real Manifest/strategy/updaters. The SCM serves fixture files and raw commits only.
DRIVER = r'''
'use strict';
const rp = process.argv[1];
const {Manifest} = require(rp + '/build/src/manifest');
const {FileNotFoundError} = require(rp + '/build/src/errors');
const quiet = {error() {}, warn() {}, info() {}, debug() {}, trace() {}, child() { return quiet; }};
require(rp + '/build/src/util/logger').setLogger(quiet);
const fixture = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const writes = [];
const file = path => {
  if (!(path in fixture.files)) throw new FileNotFoundError(path);
  const text = fixture.files[path];
  return {sha: 'fixture', content: Buffer.from(text).toString('base64'), parsedContent: text, mode: '100644'};
};
const scm = {
  repository: {owner: 'Melivo', repo: 'agentic-workflow-core', defaultBranch: 'main'},
  getFileContents: async p => file(p),
  getFileContentsOnBranch: async p => file(p),
  getFileJson: async p => JSON.parse(file(p).parsedContent),
  async *mergeCommitIterator() { for (const c of fixture.commits) yield c; },
  async *releaseIterator() { for (const r of fixture.releases) yield r; },
  async *tagIterator() { for (const t of fixture.tags) yield t; },
  async *pullRequestIterator() {},
};
for (const name of ['findFilesByFilename', 'findFilesByFilenameAndRef', 'findFilesByGlob', 'findFilesByGlobAndRef',
  'findFilesByExtension', 'findFilesByExtensionAndRef', 'commitsSince', 'createPullRequest', 'updatePullRequest',
  'getPullRequest', 'createRelease', 'commentOnIssue', 'removeIssueLabels', 'addIssueLabels', 'generateReleaseNotes',
  'createFileOnNewBranch', 'buildChangeSet']) {
  scm[name] = async () => { writes.push(name); throw new Error('offline fixture forbids ' + name); };
}
(async () => {
  const manifest = await Manifest.fromManifest(scm, 'main', '.release-please-config.json', '.release-please-manifest.json');
  const pulls = (await manifest.buildPullRequests()).map(pr => ({
    version: pr.version && pr.version.toString(), title: pr.title.toString(), head: pr.headRefName, labels: pr.labels,
    files: Object.fromEntries(pr.updates.map(u => [u.path, u.updater.updateContent(fixture.files[u.path])])),
  }));
  process.stdout.write(JSON.stringify({pulls, writes}));
})().catch(e => { process.stdout.write(JSON.stringify({error: String(e && e.message || e), writes})); process.exit(3); });
'''

TOOLS = {}


def setUpModule():
    """Only the pinned isolated toolchain is accepted; a missing one fails instead of skipping."""
    ws = Path(os.environ.get('AWC_CI_WORKSPACE') or Path(sys.prefix).parent)
    tc, ws, env, observed = bootstrap_ci.verify(ws)
    TOOLS.update(node=ws / 'node/bin/node', module=ws / 'npm/node_modules/release-please', env=env, version=observed['release-please'])


def propose(messages, files=None, release=True, extra_config=None, previous_version='0.2.1'):
    files = dict(FILES if files is None else files)
    if extra_config:
        config = json.loads(files[release_guard.CONFIG])
        config.update(extra_config)
        files[release_guard.CONFIG] = json.dumps(config)
    commits = [{'sha': '%040x' % (i + 1), 'message': m, 'files': ['scripts/x.py']} for i, m in enumerate(messages)]
    commits += [{'sha': BASE, 'message': 'fix(core-devops): recommend consistent pre-1.0 versioning', 'files': ['x']},
                {'sha': OLDER, 'message': 'feat: already released before the baseline', 'files': ['x']}]
    fixture = {'files': files, 'commits': commits, 'tags': [],
               'releases': [{'id': 1, 'tagName': 'v' + previous_version, 'sha': BASE, 'url': 'fixture'}] if release else []}
    result = subprocess.run([str(TOOLS['node']), '-e', DRIVER, str(TOOLS['module'])], input=json.dumps(fixture), env=TOOLS['env'],
                            capture_output=True, text=True, timeout=120)
    out = json.loads(result.stdout)
    if result.returncode != 0:
        raise AssertionError('release-please: ' + out.get('error', result.stderr))
    assert out['writes'] == [], out['writes']
    return out['pulls']


class RealReleasePleasePolicy(unittest.TestCase):
    def proposal(self, *messages, **kwargs):
        pulls = propose(list(messages), **kwargs)
        self.assertEqual(len(pulls), 1, pulls)
        return pulls[0]

    def assertConsistent(self, pull, version):
        files = pull['files']
        self.assertEqual(pull['version'], version)
        self.assertEqual(pull['title'], 'chore(main): release ' + version)
        self.assertEqual(pull['labels'], [release_guard.PENDING_LABEL])
        self.assertTrue(pull['head'].startswith(release_guard.RELEASE_BRANCH_PREFIX))
        self.assertEqual(sorted(files), sorted(['CHANGELOG.md', release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST]))
        found, violations = release_guard.version_sources(files[release_guard.MANIFEST], files[release_guard.VERSION_FILE], files[release_guard.APM_MANIFEST])
        self.assertEqual((found, violations), (version, []))
        self.assertEqual(release_guard.release_step('0.2.1', version), [])

    def test_pinned_library_version(self):
        self.assertEqual(TOOLS['version'], '17.11.2')

    def test_fix_is_patch(self):
        self.assertConsistent(self.proposal('fix(core-plan): repair'), '0.2.2')

    def test_feature_is_minor(self):
        self.assertConsistent(self.proposal('feat(core): add'), '0.3.0')

    def test_breaking_change_is_minor_not_major(self):
        self.assertConsistent(self.proposal('feat!: incompatible'), '0.3.0')
        self.assertConsistent(self.proposal('refactor: reshape\n\nBREAKING CHANGE: contract changed'), '0.3.0')

    def test_mixed_changes_take_highest_required_step(self):
        pull = self.proposal('fix: one', 'feat: two', 'docs: three', 'fix!: four')
        self.assertConsistent(pull, '0.3.0')
        self.assertIn('### Features', pull['files']['CHANGELOG.md'])

    def test_no_releasable_change_proposes_nothing(self):
        self.assertEqual(propose(['chore: tooling', 'docs: wording']), [])

    def test_baseline_is_not_proposed_again(self):
        # Without a found v0.2.1 release, bootstrap-sha stops before the older feature commit.
        pull = self.proposal('fix: after baseline', release=False)
        self.assertConsistent(pull, '0.2.2')
        self.assertNotIn('already released', pull['files']['CHANGELOG.md'])
        self.assertNotIn('recommend consistent', pull['files']['CHANGELOG.md'])

    def test_yaml_updater_changes_only_version(self):
        pull = self.proposal('feat: x')
        before, after = yaml.safe_load(FILES[release_guard.APM_MANIFEST]), yaml.safe_load(pull['files'][release_guard.APM_MANIFEST])
        self.assertEqual(after, dict(before, version='0.3.0'))
        self.assertEqual(release_guard.apm_pin(pull['files'][release_guard.APM_MANIFEST], (ROOT / release_guard.APM_LOCK).read_text(encoding='utf-8')), [])

    def test_release_as_one_point_zero_is_blocked_by_guard(self):
        pull = self.proposal('fix: y\n\nRelease-As: 1.0.0')
        self.assertEqual(pull['version'], '1.0.0')  # the library honours the footer ...
        _, violations = release_guard.version_sources(*(pull['files'][p] for p in (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)))
        self.assertTrue(any('1.0.0' in v for v in violations), violations)  # ... the guard does not
        self.assertNotEqual(release_guard.release_step('0.2.1', '1.0.0'), [])

    def test_wrong_policy_settings_change_versions_and_are_rejected(self):
        for change, message, version in (({'bump-minor-pre-major': False}, 'feat!: x', '1.0.0'),
                                         ({'bump-patch-for-minor-pre-major': True}, 'feat: x', '0.2.2')):
            with self.subTest(change=change):
                self.assertEqual(self.proposal(message, extra_config=change)['version'], version)
                config = dict(json.loads(FILES[release_guard.CONFIG]), **change)
                self.assertNotEqual(release_guard.release_config(json.dumps(config)), [])

    def test_wrong_manifest_source_is_rejected(self):
        files = dict(FILES, **{release_guard.MANIFEST: '{".": "0.2.0"}\n'})
        self.assertEqual(self.proposal('fix: x', files=files)['version'], '0.2.1')  # silently re-proposes a released version
        _, violations = release_guard.version_sources(files[release_guard.MANIFEST], files[release_guard.VERSION_FILE], files[release_guard.APM_MANIFEST])
        self.assertTrue(violations)


class VersionCheck(unittest.TestCase):
    def run_check(self, mutate=None, previous_ref=None, root=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(root or tmp)
            if not previous_ref:
                for path in (*FILES, release_guard.APM_LOCK):
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    if path in FILES:
                        (root / path).write_text(FILES[path], encoding='utf-8')
                    else:
                        shutil.copyfile(ROOT / path, root / path)
            if mutate:
                mutate(root)
            args = [sys.executable, '-B', str(ROOT / 'scripts/release_guard.py'), 'version-check', '--root', str(root)]
            return subprocess.run(args + (['--previous-ref', previous_ref] if previous_ref else []), capture_output=True, text=True, timeout=60)

    def test_repository_sources_agree(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/release_guard.py'), 'version-check'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        version, violations = release_guard.version_sources(*(CURRENT_FILES[p] for p in
            (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)))
        self.assertEqual(violations, [])
        self.assertIn('version=' + version, result.stdout)
        self.assertIn('#' + release_guard.EXTERNAL_COMMIT, result.stdout)
        self.assertEqual(json.loads(CURRENT_FILES[release_guard.MANIFEST]), {'.': version})
        self.assertEqual(self.run_check().returncode, 0)

    def test_inconsistent_or_unpinned_sources_fail(self):
        def edit(path, old, new):
            def apply(root):
                text = (root / path).read_text(encoding='utf-8')
                assert old in text, (path, old)
                (root / path).write_text(text.replace(old, new, 1), encoding='utf-8')
            return apply
        cases = {
            'manifest': edit(release_guard.MANIFEST, '0.2.1', '0.2.2'),
            'version file newline': edit(release_guard.VERSION_FILE, '0.2.1\n', '0.2.1'),
            'apm version': edit(release_guard.APM_MANIFEST, 'version: "0.2.1"', 'version: "0.3.0"'),
            'consistent 1.0.0': lambda r: [edit(p, '0.2.1', '1.0.0')(r) for p in (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)],
            'unpinned dependency': edit(release_guard.APM_MANIFEST, '#' + release_guard.EXTERNAL_COMMIT, ''),
            'other pin': edit(release_guard.APM_MANIFEST, release_guard.EXTERNAL_COMMIT, 'f' * 40),
            'lock commit': edit(release_guard.APM_LOCK, 'resolved_commit: ' + release_guard.EXTERNAL_COMMIT, 'resolved_commit: ' + 'f' * 40),
            'config bump': edit(release_guard.CONFIG, '"bump-patch-for-minor-pre-major": false', '"bump-patch-for-minor-pre-major": true'),
            'config release-as': edit(release_guard.CONFIG, '"release-type"', '"release-as": "1.0.0",\n  "release-type"'),
            'config baseline': edit(release_guard.CONFIG, BASE, OLDER),
            'config version file': edit(release_guard.CONFIG, 'scripts/release-version.txt', 'version.txt'),
            'config publishes': edit(release_guard.CONFIG, '"skip-github-release": true', '"skip-github-release": false'),
            'missing lock': lambda r: (r / release_guard.APM_LOCK).unlink(),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                result = self.run_check(mutate)
                self.assertEqual(result.returncode, 1, name)
                self.assertIn('FAIL', result.stderr)

    def test_previous_ref_allows_only_policy_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *a], cwd=root, check=True, capture_output=True)
            git('init', '-q')
            for path in (*FILES, release_guard.APM_LOCK):
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                if path in FILES:
                    (root / path).write_text(FILES[path], encoding='utf-8')
                else:
                    shutil.copyfile(ROOT / path, root / path)
            git('add', '-A')
            git('commit', '-q', '-m', 'base')
            for new, code in (('0.2.2', 0), ('0.3.0', 0), ('0.2.3', 1), ('0.4.0', 1)):
                with self.subTest(new=new):
                    for path, old in ((release_guard.MANIFEST, '"0.2.1"'), (release_guard.VERSION_FILE, '0.2.1'), (release_guard.APM_MANIFEST, '"0.2.1"')):
                        (root / path).write_text(FILES[path].replace(old, old.replace('0.2.1', new), 1), encoding='utf-8')
                    self.assertEqual(self.run_check(previous_ref='HEAD', root=root).returncode, code)


def facts(**change):
    archive = {'name': 'agentic-workflow-core-0.3.0.zip', 'sha256': 'd' * 64}
    base = {
        'repo': REPO, 'commit': 'c' * 40, 'previous_version': '0.2.1',
        'pull': {'number': 7, 'state': 'closed', 'merged': True, 'merge_commit_sha': 'c' * 40, 'merged_by': MAINTAINER, 'user_login': BOT,
                 'user_type': 'Bot', 'head_ref': release_guard.RELEASE_BRANCH_PREFIX + '--components--agentic-workflow-core',
                 'head_sha': 'a' * 40, 'head_repo': REPO, 'base_ref': 'main', 'base_sha': BASE, 'labels': [release_guard.PENDING_LABEL]},
        'sources': {'manifest': '{".":"0.3.0"}\n', 'version_file': '0.3.0\n', 'apm_yml': 'name: agentic-workflow-core\nversion: 0.3.0\n'},
        'check_runs': {sha: [{'id': 1, 'name': n, 'status': 'completed', 'conclusion': 'success'} for n in ('check', 'acceptance')] for sha in ('a' * 40, 'c' * 40)},
        'package': {'schema': 'core-package-report/v1', 'verified': True, 'version': '0.3.0', 'source_commit': 'c' * 40, 'source_clean': True,
                    'core_bundles': 22, 'archive': archive},
        'archive_sha256': 'd' * 64, 'tags': {'v0.2.1': BASE}, 'releases': [],
    }
    for key, value in change.items():
        target, *path = key.split('__')
        if path:
            base[target][path[0]] = value
        else:
            base[target] = value
    return base


POLICY = {'bot_login': BOT, 'maintainers': [MAINTAINER], 'required_checks': ['check', 'acceptance']}
PUBLISHED = [{'tag_name': 'v0.3.0', 'draft': False, 'assets': [{'name': 'agentic-workflow-core-0.3.0.zip', 'state': 'uploaded', 'digest': 'sha256:' + 'd' * 64}]}]


class PublicationDecision(unittest.TestCase):
    def decide(self, policy=POLICY, **change):
        return release_guard.decide_publication(facts(**change), policy)

    def assertBlocked(self, fragment, policy=POLICY, **change):
        decision = self.decide(policy, **change)
        self.assertEqual(decision['action'], 'block', change)
        self.assertTrue(any(fragment in r for r in decision['reasons']), (fragment, decision['reasons']))

    def test_verified_release_is_published(self):
        decision = self.decide()
        self.assertEqual((decision['action'], decision['tag'], decision['commit'], decision['reasons']), ('publish', 'v0.3.0', 'c' * 40, []))

    def test_identical_verified_result_is_accepted_on_retry(self):
        self.assertEqual(self.decide(tags={'v0.2.1': BASE, 'v0.3.0': 'c' * 40}, releases=PUBLISHED)['action'], 'already_published')

    def test_missing_identity_configuration_blocks(self):
        for key, fragment in (('bot_login', 'Bot-Identität'), ('maintainers', 'Maintainer'), ('required_checks', 'Pflichtchecks')):
            with self.subTest(key):
                self.assertBlocked(fragment, policy=dict(POLICY, **{key: '' if key == 'bot_login' else []}))
        self.assertBlocked('zugleich', policy=dict(POLICY, maintainers=[MAINTAINER, BOT]))

    def test_pull_request_provenance_and_deliberate_merge(self):
        cases = {
            'nicht gemergt': {'pull__merged': False},
            'nicht vom vertrauenswürdigen Bot': {'pull__user_login': MAINTAINER},
            'vertrauenswürdigen Bot': {'pull__user_type': 'User'},
            'freigegebenen Maintainer': {'pull__merged_by': 'someone-else'},
            'nicht aus diesem Repository': {'pull__head_repo': 'fork/agentic-workflow-core'},
            'kein Release-Please-Branch': {'pull__head_ref': 'feature/x'},
            'zielt nicht': {'pull__base_ref': 'develop'},
            'Merge-Commit': {'pull__merge_commit_sha': 'e' * 40},
            'Markierung': {'pull__labels': []},
        }
        for fragment, change in cases.items():
            with self.subTest(fragment):
                self.assertBlocked(fragment, **change)
        bot_merge = facts(pull__merged_by=BOT)
        self.assertEqual(release_guard.decide_publication(bot_merge, POLICY)['action'], 'block')

    def test_title_and_label_alone_are_not_enough(self):
        self.assertBlocked('vertrauenswürdigen Bot', pull__user_login='attacker', pull__user_type='User',
                           pull__labels=[release_guard.PENDING_LABEL], pull__head_ref=release_guard.RELEASE_BRANCH_PREFIX)

    def test_checks_must_be_current_complete_and_successful(self):
        ok = lambda n, i=1, **c: dict({'id': i, 'name': n, 'status': 'completed', 'conclusion': 'success'}, **c)
        cases = {
            'missing': [ok('check')],
            'pending': [ok('check'), ok('acceptance', status='in_progress', conclusion=None)],
            'failed': [ok('check'), ok('acceptance', conclusion='failure')],
            'neutral': [ok('check'), ok('acceptance', conclusion='neutral')],
            'skipped': [ok('check'), ok('acceptance', conclusion='skipped')],
            'stale success': [ok('check'), ok('acceptance', 1), ok('acceptance', 2, conclusion='failure')],
        }
        for name, runs in cases.items():
            for sha in ('a' * 40, 'c' * 40):
                with self.subTest(name, sha=sha[0]):
                    runs_by_sha = facts()['check_runs']
                    runs_by_sha[sha] = runs
                    self.assertBlocked('Pflichtcheck', check_runs=runs_by_sha)
        self.assertBlocked('Pflichtcheck', check_runs={'a' * 40: facts()['check_runs']['a' * 40]})

    def test_version_conflicts_and_illegal_steps_block(self):
        self.assertBlocked('Versionskonflikt', tags={'v0.2.1': BASE, 'v0.4.0': 'e' * 40})
        self.assertBlocked('Tag v0.3.0 zeigt', tags={'v0.2.1': BASE, 'v0.3.0': 'e' * 40}, releases=PUBLISHED)
        self.assertBlocked('Versionsschritt', previous_version='0.3.0')
        self.assertBlocked('widerspricht', sources={'manifest': '{".":"0.3.0"}\n', 'version_file': '0.3.0\n', 'apm_yml': 'version: 0.2.9\n'})
        self.assertBlocked('1.0.0', sources={'manifest': '{".":"1.0.0"}\n', 'version_file': '1.0.0\n', 'apm_yml': 'version: 1.0.0\n'})

    def test_partial_or_different_remote_results_are_never_overwritten(self):
        draft = [dict(PUBLISHED[0], draft=True)]
        other_asset = [dict(PUBLISHED[0], assets=[dict(PUBLISHED[0]['assets'][0], digest='sha256:' + 'e' * 64)])]
        for name, change in (('tag only', {'tags': {'v0.3.0': 'c' * 40}}), ('draft only', {'releases': draft}),
                             ('draft with tag', {'tags': {'v0.3.0': 'c' * 40}, 'releases': draft}),
                             ('different asset', {'tags': {'v0.3.0': 'c' * 40}, 'releases': other_asset})):
            with self.subTest(name):
                self.assertBlocked('Teilzustand', **change)

    def test_package_must_be_verified_and_bound(self):
        self.assertBlocked('source_commit', package=dict(facts()['package'], source_commit='e' * 40))
        self.assertBlocked('verified', package=dict(facts()['package'], verified=False))
        self.assertBlocked('SHA-256', archive_sha256='e' * 64)


class FakeGitHub(BaseHTTPRequestHandler):
    """Loopback provider fixture with the GitHub REST shapes the publisher uses; records every request."""

    def log_message(self, *args):
        pass

    def reply(self, code, body=None):
        data = json.dumps(body).encode() if body is not None else b''
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_any(self):
        state = self.server.state
        url = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else b''
        state['requests'].append((self.command, url.path))
        state['auth'].add(self.headers.get('Authorization'))
        if state.get('redirect'):
            self.send_response(302)
            self.send_header('Location', 'http://198.51.100.1/steal')
            self.end_headers()
            return
        if (self.command, url.path.rsplit('/', 1)[0]) in state['fail']:
            return self.reply(500, {'message': 'fixture failure'})
        prefix = '/repos/' + REPO
        path, query = url.path[len(prefix):] if url.path.startswith(prefix) else url.path, urllib.parse.parse_qs(url.query)
        page = int(query.get('page', ['1'])[0])
        if self.command == 'GET' and path.startswith('/pulls/'):
            return self.reply(200, state['pull'])
        if self.command == 'GET' and path.startswith('/contents/'):
            text = state['contents'].get((urllib.parse.unquote(path[len('/contents/'):]), query['ref'][0]))
            return self.reply(404, {}) if text is None else self.reply(200, {'content': base64.b64encode(text.encode()).decode()})
        if self.command == 'GET' and path.endswith('/check-runs'):
            runs = state['check_runs'].get(path.split('/')[2], []) if page == 1 else []
            return self.reply(200, {'total_count': len(runs), 'check_runs': runs})
        if self.command == 'GET' and path == '/git/matching-refs/tags/v':
            return self.reply(200, [{'ref': 'refs/tags/' + t, 'object': {'type': 'commit', 'sha': s}} for t, s in sorted(state['tags'].items())])
        if self.command == 'GET' and path == '/releases':
            return self.reply(200, state['releases'] if page == 1 else [])
        if path.startswith('/releases/') and self.command in ('GET', 'PATCH'):
            release = next(r for r in state['releases'] if r['id'] == int(path.split('/')[2]))
            if self.command == 'PATCH':
                release.update(draft=json.loads(body)['draft'])
            return self.reply(200, release)
        if self.command == 'POST' and path == '/releases':
            data = json.loads(body)
            release = {'id': 100 + len(state['releases']), 'tag_name': data['tag_name'], 'draft': data['draft'], 'target_commitish': data['target_commitish'],
                       'upload_url': 'http://%s:%d/uploads/%d{?name,label}' % (*self.server.server_address, 100 + len(state['releases'])), 'assets': []}
            state['releases'].append(release)
            return self.reply(201, release)
        if self.command == 'POST' and url.path.startswith('/uploads/'):
            release = next(r for r in state['releases'] if r['id'] == int(url.path.split('/')[2]))
            digest = hashlib.sha256(body + (b'corrupt' if state.get('corrupt') else b'')).hexdigest()
            release['assets'].append({'name': query['name'][0], 'state': 'uploaded', 'digest': 'sha256:' + digest})
            return self.reply(201, release['assets'][-1])
        if self.command == 'POST' and path == '/git/refs':
            data = json.loads(body)
            tag = data['ref'].removeprefix('refs/tags/')
            if tag in state['tags']:
                return self.reply(422, {'message': 'Reference already exists'})
            state['tags'][tag] = data['sha']
            return self.reply(201, data)
        if path.startswith('/issues/') and self.command in ('POST', 'DELETE'):
            if self.command == 'POST':
                state['labels'] += json.loads(body)['labels']
            else:
                name = urllib.parse.unquote(path.rsplit('/', 1)[1])
                state['labels'] = [label for label in state['labels'] if label != name]
            return self.reply(200, [{'name': label} for label in state['labels']])
        return self.reply(404, {'message': 'not in fixture: ' + self.command + ' ' + url.path})

    do_GET = do_POST = do_PATCH = do_DELETE = handle_any


class PublisherAgainstLocalProvider(unittest.TestCase):
    """The production publisher end to end against the loopback fixture; release files come from real Release Please."""

    @classmethod
    def setUpClass(cls):
        cls.proposal = propose(['feat(core): new capability'])[0]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name) / 'agentic-workflow-core-0.3.0.zip'
        self.archive.write_bytes(b'verified zip bytes')
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.report = Path(self.tmp.name) / 'package-report.json'
        self.report.write_text(json.dumps(dict(facts()['package'], archive={'name': self.archive.name, 'sha256': digest})))
        files = self.proposal['files']
        runs = [{'id': 1, 'name': n, 'status': 'completed', 'conclusion': 'success'} for n in ('check', 'acceptance')]
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeGitHub)
        self.server.state = {
            'pull': {'number': 7, 'state': 'closed', 'merged': True, 'merge_commit_sha': 'c' * 40, 'merged_by': {'login': MAINTAINER},
                     'user': {'login': BOT, 'type': 'Bot'}, 'body': 'Release notes', 'labels': [{'name': release_guard.PENDING_LABEL}],
                     'head': {'ref': self.proposal['head'], 'sha': 'a' * 40, 'repo': {'full_name': REPO}}, 'base': {'ref': 'main', 'sha': BASE}},
            'contents': {(release_guard.MANIFEST, BASE): FILES[release_guard.MANIFEST],
                         **{(p, 'c' * 40): files[p] for p in (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)}},
            'check_runs': {'a' * 40: runs, 'c' * 40: copy.deepcopy(runs)}, 'tags': {'v0.2.1': BASE}, 'releases': [],
            'labels': [release_guard.PENDING_LABEL], 'requests': [], 'auth': set(), 'fail': set(),
        }
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = {'GITHUB_TOKEN': 'fixture-token-value', 'GITHUB_REPOSITORY': REPO, 'GITHUB_API_URL': 'http://127.0.0.1:%d' % self.server.server_address[1],
                    'RELEASE_BOT_LOGIN': BOT, 'RELEASE_MAINTAINERS': MAINTAINER, 'RELEASE_REQUIRED_CHECKS': 'check,acceptance'}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def publish(self, *extra, env=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = publish_release.main(['--pr', '7', '--commit', 'c' * 40, '--archive', str(self.archive), '--report', str(self.report), *extra], env=env or self.env)
        self.assertNotIn('fixture-token-value', out.getvalue())
        return code, json.loads(out.getvalue())

    def writes(self):
        return [r for r in self.server.state['requests'] if r[0] != 'GET']

    def test_publishes_in_order_and_verifies(self):
        code, result = self.publish()
        self.assertEqual((code, result['action']), (0, 'published'), result)
        self.assertEqual([m for m, _ in self.writes()], ['POST', 'POST', 'POST', 'PATCH', 'POST', 'DELETE'])
        self.assertEqual([p.split('/')[-1] if p.startswith('/uploads') else p.split(REPO)[-1] for _, p in self.writes()],
                         ['/releases', '100', '/git/refs', '/releases/100', '/issues/7/labels', '/issues/7/labels/autorelease%3A%20pending'])
        state = self.server.state
        self.assertEqual(state['tags']['v0.3.0'], 'c' * 40)
        self.assertFalse(state['releases'][0]['draft'])
        self.assertEqual(state['releases'][0]['target_commitish'], 'c' * 40)
        self.assertEqual(state['labels'], [release_guard.TAGGED_LABEL])
        self.assertEqual(state['auth'], {'Bearer fixture-token-value'})
        # A repeated run finds the identical verified result and writes nothing.
        before = len(state['requests'])
        code, result = self.publish()
        self.assertEqual((code, result['action']), (0, 'already_published'), result)
        self.assertEqual([r for r in state['requests'][before:] if r[0] != 'GET'], [])

    def test_blocked_decisions_perform_no_write(self):
        def pending(state):
            state['check_runs']['c' * 40][1].update(status='queued', conclusion=None)

        def human(state):
            state['pull']['user'] = {'login': 'someone', 'type': 'User'}

        def self_merge(state):
            state['pull']['merged_by'] = {'login': BOT}

        def conflict(state):
            state['tags']['v0.3.0'] = 'e' * 40

        def release_as(state):
            for path in (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST):
                state['contents'][(path, 'c' * 40)] = state['contents'][(path, 'c' * 40)].replace('0.3.0', '1.0.0')

        for mutate in (pending, human, self_merge, conflict, release_as):
            with self.subTest(mutate.__name__):
                self.tearDown()
                self.setUp()
                mutate(self.server.state)
                code, result = self.publish()
                self.assertEqual((code, result['action']), (1, 'block'), result)
                self.assertEqual(self.writes(), [])

    def test_missing_configuration_blocks_before_any_request(self):
        code, result = self.publish(env=dict(self.env, RELEASE_MAINTAINERS=''))
        self.assertEqual((code, result['action']), (1, 'block'))
        self.assertEqual(self.server.state['requests'], [])

    def test_dry_run_decides_without_effects(self):
        code, result = self.publish('--dry-run')
        self.assertEqual((code, result['action']), (0, 'publish'))
        self.assertEqual(self.writes(), [])

    def test_digest_mismatch_stops_before_tag_and_never_deletes(self):
        self.server.state['corrupt'] = True
        code, result = self.publish()
        self.assertEqual((code, result['action']), (1, 'failed'))
        self.assertIn('Teilzustand', result['reasons'][0])
        self.assertNotIn('v0.3.0', self.server.state['tags'])
        self.assertTrue(self.server.state['releases'][0]['draft'])
        self.assertNotIn('DELETE', [m for m, p in self.writes() if '/labels' not in p])
        # The partial state is reported, not repaired or overwritten, on retry.
        before = len(self.writes())
        self.server.state['corrupt'] = False
        code, result = self.publish()
        self.assertEqual((code, result['action']), (1, 'block'))
        self.assertTrue(any('Teilzustand' in r for r in result['reasons']), result)
        self.assertEqual(len(self.writes()), before)

    def test_failed_upload_reports_partial_state(self):
        self.server.state['fail'].add(('POST', '/uploads'))
        code, result = self.publish()
        self.assertEqual((code, result['action']), (1, 'failed'))
        self.assertIn('Entwurf v0.3.0', result['reasons'][0])
        self.assertEqual([m for m, _ in self.writes()], ['POST', 'POST'])

    def test_existing_tag_is_never_overwritten(self):
        self.server.state['fail'].add(('PATCH', '/repos/' + REPO + '/releases'))
        code, _ = self.publish()
        self.assertEqual(code, 1)
        self.assertEqual(self.server.state['tags']['v0.3.0'], 'c' * 40)
        before = len(self.writes())
        self.server.state['fail'].clear()
        code, result = self.publish()
        self.assertEqual((code, result['action']), (1, 'block'))
        self.assertEqual(len(self.writes()), before)

    def test_transport_guards(self):
        with self.assertRaises(publish_release.ProviderError):
            publish_release.GitHub(REPO, 'x', 'http://api.example.test')
        with self.assertRaises(publish_release.ProviderError):
            publish_release.GitHub(REPO, '', 'https://api.github.com')
        self.server.state['redirect'] = True
        code, result = self.publish()
        self.assertEqual((code, result['action']), (1, 'failed'))
        self.assertIn('Weiterleitung', result['reasons'][0])


class ReleasePullLifecycle(unittest.TestCase):
    """Apply only real updater output to scratch sources and run every behavioral test."""

    def lifecycle(self, message, minor):
        current, violations = release_guard.version_sources(*(CURRENT_FILES[p] for p in
            (release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST)))
        self.assertEqual(violations, [])
        major, middle, patch = map(int, current.split('.'))
        expected = f'{major}.{middle + 1}.0' if minor else f'{major}.{middle}.{patch + 1}'
        pulls = propose([message], files=CURRENT_FILES, previous_version=current)
        self.assertEqual(len(pulls), 1, pulls)
        pull = pulls[0]
        self.assertEqual(pull['version'], expected)
        self.assertEqual(release_guard.release_step(current, expected), [])
        paths = ['tests/test_release_automation.py', 'scripts/bootstrap_ci.py',
                 'scripts/release_guard.py', 'scripts/publish_release.py',
                 'scripts/ci_toolchain.json', 'scripts/requirements-ci.txt',
                 'scripts/package.json', 'scripts/package-lock.json', release_guard.APM_LOCK,
                 *CURRENT_FILES, 'CHANGELOG.md']
        before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
        evidence_parent = os.environ.get('AWC_RELEASE_EVIDENCE_DIR')
        if evidence_parent:
            Path(evidence_parent).mkdir(parents=True, exist_ok=True)
        lab = Path(tempfile.mkdtemp(prefix='release-minor-' if minor else 'release-patch-',
                                    dir=evidence_parent or TOOLS['env']['TMPDIR']))
        source = lab / 'source'
        for path in paths:
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        self.assertEqual(set(pull['files']),
                         {'CHANGELOG.md', release_guard.MANIFEST, release_guard.VERSION_FILE, release_guard.APM_MANIFEST})
        for path, content in pull['files'].items():
            (source / path).write_text(content, encoding='utf-8')
        (lab / 'proposal.json').write_text(json.dumps(pull, indent=2), encoding='utf-8')
        # The child executes every behavioral TestCase (including future additions). Only this
        # orchestration class is not recursively dispatched: it is being exercised by its parent.
        runner = ("import sys, unittest; sys.path.insert(0, 'tests'); import test_release_automation as t; "
                  "suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) "
                  "for c in vars(t).values() if isinstance(c, type) and issubclass(c, unittest.TestCase) "
                  "and c is not t.ReleasePullLifecycle); "
                  "result=unittest.TextTestRunner(verbosity=2).run(suite); "
                  "sys.exit(not result.wasSuccessful())")
        command = [sys.executable, '-B', '-c', runner]
        env = dict(TOOLS['env'])
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True, timeout=900)
        (lab / 'suite.stdout').write_text(result.stdout, encoding='utf-8')
        (lab / 'suite.stderr').write_text(result.stderr, encoding='utf-8')
        # Mutate current updated sources, not the historical policy fixtures, to prove fail-closed.
        manifest = source / release_guard.MANIFEST
        updated_manifest = manifest.read_text(encoding='utf-8')
        manifest.write_text(json.dumps({'.': current}), encoding='utf-8')
        guard_command = [sys.executable, '-B', str(source / 'scripts/release_guard.py'), 'version-check', '--root', str(source)]
        negative = subprocess.run(guard_command, cwd=source, env=env, capture_output=True, text=True, timeout=60)
        manifest.write_text(updated_manifest, encoding='utf-8')
        (lab / 'negative.stdout').write_text(negative.stdout, encoding='utf-8')
        (lab / 'negative.stderr').write_text(negative.stderr, encoding='utf-8')
        after = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
        snapshot_hashes = {p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in paths}
        (lab / 'result.json').write_text(json.dumps(dict(command=command, cwd=str(source),
            exit_code=result.returncode, version=expected, previous_version=current,
            negative_command=guard_command, negative_exit_code=negative.returncode,
            source_before=before, source_after=after, snapshot_hashes=snapshot_hashes), indent=2), encoding='utf-8')
        print('LIFECYCLE evidence=' + str(lab))
        self.assertEqual(after, before, 'lifecycle changed repository sources')
        self.assertEqual(result.returncode, 0, str(lab) + '\n' + result.stderr)
        self.assertEqual(negative.returncode, 1, negative.stderr)
        self.assertIn('FAIL', negative.stderr)

    def test_patch_pull_passes_release_suite(self):
        self.lifecycle('fix(core): lifecycle regression', minor=False)

    def test_minor_pull_passes_release_suite(self):
        self.lifecycle('feat(core): lifecycle regression', minor=True)


if __name__ == '__main__':
    unittest.main()
