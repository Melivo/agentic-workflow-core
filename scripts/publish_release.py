#!/usr/bin/env python3
"""Publish one merged Release-Please PR: read provider facts, let release_guard decide, then release.

Effects start only after an unconditional 'publish' decision and run strictly in order: draft release,
asset upload, digest check, tag on the exact merge commit, publication, final verification, PR label.
Any failure stops and reports the partial state; tags, releases and assets are never deleted or overwritten.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_guard  # noqa: E402

API_VERSION = '2022-11-28'
LOOPBACK = ('127.0.0.1', 'localhost', '::1')


class ProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """The token must never follow a redirect to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('unerwartete Weiterleitung %s -> %s' % (code, newurl))


class GitHub:
    """Minimal REST adapter for exactly the reads and writes this publisher needs."""

    def __init__(self, repo, token, api_url='https://api.github.com'):
        parts = urllib.parse.urlsplit(api_url)
        if not (parts.scheme == 'https' or (parts.scheme == 'http' and parts.hostname in LOOPBACK)):
            raise ProviderError('API-URL muss HTTPS verwenden: ' + api_url)
        if not token:
            raise ProviderError('kein Provider-Token gesetzt')
        self.repo, self._token, self.api = repo, token, api_url.rstrip('/')
        self._opener = urllib.request.build_opener(NoRedirect)
        self.writes = []

    def _call(self, method, url, body=None, content_type='application/json', missing_ok=False):
        if not url.startswith(('http://', 'https://')):
            url = self.api + '/repos/' + self.repo + url
        data = json.dumps(body).encode() if content_type == 'application/json' and body is not None else body
        request = urllib.request.Request(url, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self._token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': API_VERSION, 'User-Agent': 'agentic-workflow-core-publisher', 'Content-Type': content_type})
        if method != 'GET':
            self.writes.append((method, urllib.parse.urlsplit(url).path))
        try:
            with self._opener.open(request, timeout=120) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if missing_ok and exc.code == 404:
                return None
            raise ProviderError('%s %s scheiterte: HTTP %s' % (method, urllib.parse.urlsplit(url).path, exc.code)) from None
        except urllib.error.URLError as exc:
            raise ProviderError('%s %s nicht erreichbar: %s' % (method, urllib.parse.urlsplit(url).path, exc.reason)) from None
        return json.loads(payload) if payload else None

    def pages(self, url, key=None):
        items, page = [], 1
        while True:
            batch = self._call('GET', '%s%sper_page=100&page=%d' % (url, '&' if '?' in url else '?', page))
            batch = batch.get(key, []) if key else batch
            items += batch
            if len(batch) < 100:
                return items
            page += 1

    def pull(self, number):
        raw = self._call('GET', '/pulls/%d' % number)
        return {
            'number': raw['number'], 'state': raw['state'], 'merged': raw.get('merged'), 'merge_commit_sha': raw.get('merge_commit_sha'),
            'merged_by': (raw.get('merged_by') or {}).get('login'), 'user_login': raw['user']['login'], 'user_type': raw['user'].get('type'),
            'head_ref': raw['head']['ref'], 'head_sha': raw['head']['sha'], 'head_repo': ((raw['head'].get('repo') or {}).get('full_name')),
            'base_ref': raw['base']['ref'], 'base_sha': raw['base']['sha'], 'labels': [label['name'] for label in raw.get('labels') or []],
            'body': raw.get('body') or '',
        }

    def file_text(self, path, ref):
        raw = self._call('GET', '/contents/%s?ref=%s' % (urllib.parse.quote(path), ref))
        return base64.b64decode(raw['content']).decode('utf-8')

    def check_runs(self, sha):
        return [{'id': r['id'], 'name': r['name'], 'status': r['status'], 'conclusion': r.get('conclusion')}
                for r in self.pages('/commits/%s/check-runs?filter=all' % sha, 'check_runs')]

    def tags(self):
        """Version tags mapped to their peeled commit."""
        tags = {}
        for ref in self._call('GET', '/git/matching-refs/tags/v') or []:
            target = ref['object']
            if target['type'] == 'tag':
                target = self._call('GET', '/git/tags/' + target['sha'])['object']
            tags[ref['ref'].removeprefix('refs/tags/')] = target['sha']
        return tags

    def releases(self):
        return [{'id': r['id'], 'tag_name': r['tag_name'], 'draft': r['draft'], 'upload_url': r.get('upload_url'),
                 'assets': [{'name': a['name'], 'state': a.get('state'), 'digest': a.get('digest')} for a in r.get('assets') or []]}
                for r in self.pages('/releases')]

    def create_draft_release(self, tag, commit, body):
        return self._call('POST', '/releases', {'tag_name': tag, 'target_commitish': commit, 'name': tag, 'body': body, 'draft': True, 'prerelease': False})

    def upload_asset(self, release, archive):
        url = release['upload_url'].split('{', 1)[0] + '?name=' + urllib.parse.quote(archive.name)
        return self._call('POST', url, archive.read_bytes(), content_type='application/zip')

    def release(self, release_id):
        raw = self._call('GET', '/releases/%d' % release_id)
        return {'id': raw['id'], 'tag_name': raw['tag_name'], 'draft': raw['draft'],
                'assets': [{'name': a['name'], 'state': a.get('state'), 'digest': a.get('digest')} for a in raw.get('assets') or []]}

    def create_tag(self, tag, commit):
        return self._call('POST', '/git/refs', {'ref': 'refs/tags/' + tag, 'sha': commit})

    def publish(self, release_id):
        return self._call('PATCH', '/releases/%d' % release_id, {'draft': False, 'make_latest': 'true'})

    def mark_tagged(self, number):
        self._call('POST', '/issues/%d/labels' % number, {'labels': [release_guard.TAGGED_LABEL]})
        self._call('DELETE', '/issues/%d/labels/%s' % (number, urllib.parse.quote(release_guard.PENDING_LABEL)), missing_ok=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gather(provider, number, commit, archive, report):
    """Read-only provider facts for release_guard.decide_publication."""
    pull = provider.pull(number)
    previous = json.loads(provider.file_text(release_guard.MANIFEST, pull['base_sha'])).get('.')
    sources = {key: provider.file_text(path, commit) for key, path in
               (('manifest', release_guard.MANIFEST), ('version_file', release_guard.VERSION_FILE), ('apm_yml', release_guard.APM_MANIFEST))}
    runs = {sha: provider.check_runs(sha) for sha in dict.fromkeys((pull['head_sha'], commit))}
    return dict(repo=provider.repo, commit=commit, pull=pull, previous_version=previous, sources=sources, check_runs=runs,
                package=report, archive_sha256=sha256(archive), tags=provider.tags(), releases=provider.releases())


def publish(provider, decision, pull, archive):
    """Ordered effects for a 'publish' decision; returns the verified provider result."""
    tag, commit, digest = decision['tag'], decision['commit'], 'sha256:' + sha256(archive)
    expected = [(archive.name, 'uploaded', digest)]
    state = ['nichts veröffentlicht']
    try:
        draft = provider.create_draft_release(tag, commit, pull.get('body') or tag)
        state = ['Entwurf %s (id %s) angelegt' % (tag, draft['id'])]
        provider.upload_asset(draft, archive)
        state.append('Asset %s hochgeladen' % archive.name)
        uploaded = provider.release(draft['id'])
        if [(a['name'], a['state'], a['digest']) for a in uploaded['assets']] != expected:
            raise ProviderError('Asset im Entwurf entspricht nicht dem geprüften Archiv (Digest/Anzahl)')
        provider.create_tag(tag, commit)
        state.append('Tag %s auf %s angelegt' % (tag, commit))
        provider.publish(draft['id'])
        state.append('Release veröffentlicht')
        final, tags = provider.release(draft['id']), provider.tags()
        if final['draft'] or tags.get(tag) != commit or [(a['name'], a['state'], a['digest']) for a in final['assets']] != expected:
            raise ProviderError('Nachprüfung von Tag, Commit, Release oder Asset fehlgeschlagen')
        provider.mark_tagged(pull['number'])
    except ProviderError as exc:
        raise ProviderError(str(exc) + '; Teilzustand: ' + ', '.join(state) + '; nichts wurde gelöscht oder überschrieben') from None
    return {'tag': tag, 'commit': commit, 'release_id': draft['id'], 'asset': archive.name, 'digest': digest}


def policy_from_env(env):
    split = lambda name: [v.strip() for v in env.get(name, '').split(',') if v.strip()]
    return {'bot_login': env.get('RELEASE_BOT_LOGIN', '').strip(), 'maintainers': split('RELEASE_MAINTAINERS'), 'required_checks': split('RELEASE_REQUIRED_CHECKS')}


def run(args, env, provider_factory=GitHub):
    """Return (exit code, result); prints only facts, never the token."""
    policy = policy_from_env(env)
    blocked = release_guard.policy_violations(policy)
    if blocked:
        return 1, {'action': 'block', 'reasons': blocked}
    report = json.loads(args.report.read_text(encoding='utf-8'))
    provider = provider_factory(env.get('GITHUB_REPOSITORY', ''), env.get('GITHUB_TOKEN', ''), env.get('GITHUB_API_URL') or 'https://api.github.com')
    facts = gather(provider, args.pr, args.commit, args.archive, report)
    decision = release_guard.decide_publication(facts, policy)
    if decision['action'] != 'publish' or args.dry_run:
        return (1 if decision['action'] == 'block' else 0), decision
    decision['result'] = publish(provider, decision, facts['pull'], args.archive)
    decision['action'] = 'published'
    return 0, decision


def main(argv=None, env=None, provider_factory=GitHub):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr', type=int, required=True, help='Nummer des gemergten Release-PR')
    parser.add_argument('--commit', required=True, help='exakter Merge-Commit, der veröffentlicht wird')
    parser.add_argument('--archive', type=Path, required=True, help='geprüftes ZIP aus build_core_package.py')
    parser.add_argument('--report', type=Path, required=True, help='Paketbericht aus build_core_package.py')
    parser.add_argument('--dry-run', action='store_true', help='nur Fakten lesen und entscheiden')
    args = parser.parse_args(argv)
    try:
        code, result = run(args, os.environ if env is None else env, provider_factory)
    except (ProviderError, OSError, ValueError, KeyError) as exc:
        code, result = 1, {'action': 'failed', 'reasons': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
