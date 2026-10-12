#!/usr/bin/env python3
"""Release policy of this repository as pure checks over plain data.

Every check returns a list of violations and never touches files, Git or a provider; only the
CLI reads the working tree. publish_release.py and the tests use the same decisions.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'agentic-workflow-core'
BRANCH = 'main'
CORE_BUNDLES = 22
BASELINE_COMMIT = 'a541a41a8a100f8a72d680356dd3b08e335ef068'
EXTERNAL_DEPENDENCY = 'Melivo/apm-package/skills/gortex-serena-configurator'
EXTERNAL_COMMIT = '0c7838d8072dfd70c702cf2d04734a7241550c3e'
MANIFEST = '.release-please-manifest.json'
CONFIG = '.release-please-config.json'
VERSION_FILE = 'scripts/release-version.txt'
APM_MANIFEST = 'apm.yml'
APM_LOCK = 'apm.lock.yaml'
PENDING_LABEL = 'autorelease: pending'
TAGGED_LABEL = 'autorelease: tagged'
RELEASE_BRANCH_PREFIX = 'release-please--branches--' + BRANCH
# Release Please settings implementing the confirmed 0.x policy (fix -> patch, feat/breaking -> minor,
# never an automatic 1.0.0) and "PR only": tags and releases belong to publish_release.py.
REQUIRED_CONFIG = {
    'release-type': 'simple',
    'bootstrap-sha': BASELINE_COMMIT,
    'bump-minor-pre-major': True,
    'bump-patch-for-minor-pre-major': False,
    'include-component-in-tag': False,
    'include-v-in-tag': True,
    'skip-github-release': True,
}
REQUIRED_PACKAGE = {
    'package-name': PACKAGE,
    'version-file': VERSION_FILE,
    'changelog-path': 'CHANGELOG.md',
    'extra-files': [{'type': 'yaml', 'path': APM_MANIFEST, 'jsonpath': '$.version'}],
}
SEMVER = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
TAG = re.compile(r'v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
SHA = re.compile(r'[0-9a-f]{40}')


def parse_version(value):
    match = SEMVER.fullmatch(value) if isinstance(value, str) else None
    return tuple(map(int, match.groups())) if match else None


def version_sources(manifest_text, version_text, apm_text):
    """Return (version, violations); all three sources must name the same 0.x version."""
    violations = []
    try:
        manifest = json.loads(manifest_text)
    except ValueError:
        manifest = None
    if not (isinstance(manifest, dict) and list(manifest) == ['.']):
        violations.append(MANIFEST + ' muss genau {".": "<version>"} enthalten')
        manifest = {}
    try:
        apm = yaml.safe_load(apm_text)
    except yaml.YAMLError:
        apm = None
    apm_version = apm.get('version') if isinstance(apm, dict) else None
    version = manifest.get('.')
    if parse_version(version) is None:
        violations.append(MANIFEST + ' nennt keine exakte Version: ' + repr(version))
    if version_text != str(version) + '\n':
        violations.append(VERSION_FILE + ' muss genau die Manifestversion und einen Zeilenumbruch enthalten: ' + repr(version_text))
    if apm_version != version:
        violations.append(APM_MANIFEST + ' version ' + repr(apm_version) + ' widerspricht Manifest ' + repr(version))
    parsed = parse_version(version)
    if parsed and parsed[0] != 0:
        violations.append('Version ' + version + ': Wechsel auf >=1.0.0 verlangt eine gesonderte ausdrückliche Entscheidung')
    return (None if violations else version), violations


def release_step(previous, current):
    """A release is exactly the next 0.x patch or minor of the previous version."""
    old, new = parse_version(previous), parse_version(current)
    if not old or not new:
        return ['ungültiger Versionsschritt: ' + repr(previous) + ' -> ' + repr(current)]
    if new in ((old[0], old[1], old[2] + 1), (old[0], old[1] + 1, 0)) and new[0] == 0:
        return []
    return ['unzulässiger Versionsschritt ' + previous + ' -> ' + current + ' (erlaubt: nächster 0.x-Patch oder -Minor)']


def release_config(config_text):
    try:
        config = json.loads(config_text)
    except ValueError:
        return [CONFIG + ' ist kein JSON']
    if not isinstance(config, dict):
        return [CONFIG + ' ist kein Objekt']
    violations = ['%s: %s=%r erforderlich' % (CONFIG, k, v) for k, v in REQUIRED_CONFIG.items() if config.get(k, object()) != v]
    unknown = sorted(set(config) - set(REQUIRED_CONFIG) - {'$schema', 'packages'})
    if unknown:
        violations.append(CONFIG + ': nicht freigegebene Schlüssel ' + ', '.join(unknown))
    packages = config.get('packages')
    if not (isinstance(packages, dict) and list(packages) == ['.'] and packages['.'] == REQUIRED_PACKAGE):
        violations.append(CONFIG + ': packages muss genau {".": ' + json.dumps(REQUIRED_PACKAGE) + '} sein')
    return violations


def apm_pin(apm_text, lock_text):
    """The external APM dependency is pinned to, and locked at, exactly EXTERNAL_COMMIT."""
    violations = []
    try:
        apm, lock = yaml.safe_load(apm_text), yaml.safe_load(lock_text)
    except yaml.YAMLError:
        return ['apm.yml oder apm.lock.yaml ist kein YAML']
    deps = ((apm or {}).get('dependencies') or {}).get('apm') if isinstance(apm, dict) else None
    if deps != [EXTERNAL_DEPENDENCY + '#' + EXTERNAL_COMMIT]:
        violations.append(APM_MANIFEST + ' muss genau ' + EXTERNAL_DEPENDENCY + '#' + EXTERNAL_COMMIT + ' deklarieren: ' + repr(deps))
    locked = (lock or {}).get('dependencies') if isinstance(lock, dict) else None
    if not (isinstance(locked, list) and len(locked) == 1 and isinstance(locked[0], dict)):
        return violations + [APM_LOCK + ' muss genau eine aufgelöste Abhängigkeit enthalten']
    entry = locked[0]
    owner_repo, _, path = EXTERNAL_DEPENDENCY.partition('/skills/')
    expected = {'repo_url': owner_repo.lower(), 'virtual_path': 'skills/' + path, 'resolved_commit': EXTERNAL_COMMIT, 'resolved_ref': EXTERNAL_COMMIT}
    for key, value in expected.items():
        if str(entry.get(key, '')).lower() != value.lower():
            violations.append('%s: %s=%r, erwartet %r' % (APM_LOCK, key, entry.get(key), value))
    return violations


def check_runs(runs, required):
    """Each required check has a latest run on the exact commit that completed with success."""
    violations = []
    for name in required:
        mine = [r for r in runs if r.get('name') == name]
        if not mine:
            violations.append('Pflichtcheck fehlt: ' + name)
            continue
        latest = max(mine, key=lambda r: r.get('id', 0))
        if latest.get('status') != 'completed' or latest.get('conclusion') != 'success':
            violations.append('Pflichtcheck %s ist %s/%s' % (name, latest.get('status'), latest.get('conclusion')))
    return violations


def package_report(report, version, commit, archive_sha256):
    """The verified package was built from exactly this clean commit and is the archive at hand."""
    report = report if isinstance(report, dict) else {}
    archive = report.get('archive') or {}
    expected = {
        'schema': 'core-package-report/v1', 'verified': True, 'version': version, 'source_commit': commit,
        'source_clean': True, 'core_bundles': CORE_BUNDLES,
    }
    violations = ['Paketbericht: %s=%r, erwartet %r' % (k, report.get(k), v) for k, v in expected.items() if report.get(k) != v]
    if archive.get('name') != '%s-%s.zip' % (PACKAGE, version):
        violations.append('Paketbericht: falscher Archivname ' + repr(archive.get('name')))
    if not archive_sha256 or archive.get('sha256') != archive_sha256:
        violations.append('Paketbericht: SHA-256 passt nicht zum vorliegenden Archiv')
    return violations


def remote_state(version, commit, archive, tags, releases):
    """Classify the provider state: 'absent', 'published' (identical, verified) or violations."""
    tag = 'v' + version
    newer = sorted(t for t in tags if TAG.fullmatch(t) and t != tag and parse_version(t[1:]) > parse_version(version))
    if newer:
        return None, ['Versionskonflikt: neuere Tags existieren bereits: ' + ', '.join(newer)]
    mine = [r for r in releases if r.get('tag_name') == tag]
    if tag not in tags and not mine:
        return 'absent', []
    problems = []
    if tags.get(tag) != commit:
        problems.append('Tag %s zeigt auf %s statt %s' % (tag, tags.get(tag), commit))
    if len(mine) != 1 or mine[0].get('draft'):
        problems.append('Release %s fehlt, ist mehrfach vorhanden oder noch Entwurf' % tag)
    else:
        assets = mine[0].get('assets') or []
        if [(a.get('name'), a.get('state'), a.get('digest')) for a in assets] != [(archive['name'], 'uploaded', 'sha256:' + archive['sha256'])]:
            problems.append('Release %s enthält nicht genau das geprüfte Asset' % tag)
    if problems:
        return None, ['Teilzustand oder abweichendes Ergebnis, nichts wird überschrieben: ' + '; '.join(problems)]
    return 'published', []


def policy_violations(policy):
    violations = []
    if not policy.get('bot_login'):
        violations.append('Bot-Identität ist nicht konfiguriert')
    if not policy.get('maintainers'):
        violations.append('freigegebene Maintainer sind nicht konfiguriert')
    if policy.get('bot_login') in (policy.get('maintainers') or ()):
        violations.append('Bot darf nicht zugleich freigebender Maintainer sein')
    if not policy.get('required_checks'):
        violations.append('Pflichtchecks sind nicht konfiguriert')
    return violations


def pull_violations(pull, policy, repo, commit):
    """Release PR from the trusted bot, deliberately merged by an authorized maintainer into main."""
    checks = [
        (pull.get('merged') is True and pull.get('state') == 'closed', 'Release-PR ist nicht gemergt'),
        (pull.get('base_ref') == BRANCH, 'Release-PR zielt nicht auf ' + BRANCH),
        (pull.get('head_repo') == repo, 'Release-PR stammt nicht aus diesem Repository'),
        (str(pull.get('head_ref', '')).startswith(RELEASE_BRANCH_PREFIX), 'Release-PR-Branch ist kein Release-Please-Branch'),
        (pull.get('user_login') == policy.get('bot_login') and pull.get('user_type') == 'Bot', 'Release-PR wurde nicht vom vertrauenswürdigen Bot erstellt'),
        (pull.get('merged_by') in (policy.get('maintainers') or ()) and pull.get('merged_by') != policy.get('bot_login'),
         'Release-PR wurde nicht von einem freigegebenen Maintainer gemergt'),
        (pull.get('merge_commit_sha') == commit, 'Merge-Commit des Release-PR ist nicht der zu veröffentlichende Commit'),
        (bool({PENDING_LABEL, TAGGED_LABEL} & set(pull.get('labels') or ())), 'Release-PR trägt keine Release-Please-Markierung'),
        (bool(SHA.fullmatch(str(pull.get('head_sha', '')))), 'Release-PR ohne exakten Head-Commit'),
    ]
    return [message for ok, message in checks if not ok]


def decide_publication(facts, policy):
    """Decide 'publish', 'already_published' or 'block' from provider facts; never performs effects.

    facts: repo, commit (exact merge SHA to release), pull (normalized PR), previous_version (manifest at
    the PR base), sources (manifest/version_file/apm_yml texts at commit), check_runs ({sha: [runs]}),
    package (report), archive_sha256 (observed), tags ({name: peeled commit}), releases (list).
    """
    commit = facts.get('commit') or ''
    reasons = policy_violations(policy)
    if not SHA.fullmatch(commit):
        reasons.append('kein exakter Commit für die Veröffentlichung: ' + repr(commit))
    pull = facts.get('pull') or {}
    reasons += pull_violations(pull, policy, facts.get('repo'), commit)
    sources = facts.get('sources') or {}
    version, violations = version_sources(sources.get('manifest', ''), sources.get('version_file', ''), sources.get('apm_yml', ''))
    reasons += violations
    if version:
        reasons += release_step(facts.get('previous_version'), version)
    for sha in dict.fromkeys((pull.get('head_sha'), commit)):
        reasons += ['%s (%s)' % (v, sha) for v in check_runs((facts.get('check_runs') or {}).get(sha) or [], policy.get('required_checks') or ())]
    decision = {'action': 'block', 'version': version, 'tag': version and 'v' + version, 'commit': commit, 'reasons': reasons}
    if not version:
        return decision
    reasons += package_report(facts.get('package'), version, commit, facts.get('archive_sha256'))
    if reasons:
        return decision
    archive = facts['package']['archive']
    state, violations = remote_state(version, commit, archive, facts.get('tags') or {}, facts.get('releases') or [])
    reasons += violations
    if not reasons:
        decision['action'] = 'already_published' if state == 'published' else 'publish'
    return decision


def read(root, path):
    return (root / path).read_text(encoding='utf-8')


def version_check(root, previous_ref=None):
    version, violations = version_sources(read(root, MANIFEST), read(root, VERSION_FILE), read(root, APM_MANIFEST))
    violations += release_config(read(root, CONFIG)) + apm_pin(read(root, APM_MANIFEST), read(root, APM_LOCK))
    if version and previous_ref:
        shown = subprocess.run(['git', 'show', previous_ref + ':' + MANIFEST], cwd=root, capture_output=True, text=True)
        previous = json.loads(shown.stdout).get('.') if shown.returncode == 0 else None
        if previous is None:
            violations.append('Basisversion unter ' + previous_ref + ' nicht lesbar')
        elif previous != version:
            violations += release_step(previous, version)
    return version, violations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('version-check', help='Versionsquellen, Releasekonfiguration und APM-Pin prüfen')
    check.add_argument('--root', type=Path, default=ROOT)
    check.add_argument('--previous-ref', help='Git-Ref, gegen dessen Manifest ein Versionsschritt geprüft wird')
    args = parser.parse_args(argv)
    try:
        version, violations = version_check(args.root.resolve(), args.previous_ref)
    except (OSError, ValueError) as exc:
        version, violations = None, ['nicht lesbar: ' + str(exc)]
    for violation in violations:
        print('FAIL:', violation, file=sys.stderr)
    if violations:
        return 1
    print('PASS version-check version=%s manifest=%s version_file=%s apm.yml=%s release-please=%s apm-dependency=%s#%s'
          % (version, version, version, version, CONFIG, EXTERNAL_DEPENDENCY, EXTERNAL_COMMIT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
