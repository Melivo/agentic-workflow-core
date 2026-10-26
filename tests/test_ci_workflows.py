"""Security and orchestration contract of .github/workflows/ci.yaml and release.yaml.

The real workflow files must satisfy the policy below, and controlled mutations of exactly these files
must be detected: triggers, action pins, permissions, gates, app-token scope and lifetime, secret
placement, commit binding, check gates and the build -> decide -> publish order. actionlint with the
pinned shellcheck runs separately in mise run workflows:check.
"""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bootstrap_ci  # noqa: E402
import release_guard  # noqa: E402

CI = ROOT / '.github/workflows/ci.yaml'
RELEASE = ROOT / '.github/workflows/release.yaml'
TOOLCHAIN = bootstrap_ci.load_toolchain()
# Official release tags resolved to their commits (gh api repos/<action>/git/ref/tags/<tag>, peeled).
PINS = {
    'actions/checkout': '3d3c42e5aac5ba805825da76410c181273ba90b1',  # v7.0.1
    'actions/setup-python': '5fda3b95a4ea91299a34e894583c3862153e4b97',  # v7.0.0
    'jdx/mise-action': '2d8d4cafcbd33be2ea37d2b6f5ad595363d1f1ca',  # v5.1.1
    'actions/create-github-app-token': 'bcd2ba49218906704ab6c1aa796996da409d3eb1',  # v3.2.0
    'actions/upload-artifact': 'cf430e030ddbb5b0abf93d22962f4752f3646cd9',  # v7.0.2
    'actions/download-artifact': '9000827ccba6bdab643e8b6fd33ac0654aef8333',  # v8.0.2
}
# Release asset digest of mise-v<version>-linux-x64 (the binary mise-action hashes).
MISE_SHA256 = '3162760f40b6b5f706c60641e4ef5ee7322bc6c54f72fc26a7111b337aa18d9d'
TOKEN_ACTION = 'actions/create-github-app-token'
HEAD_SHA = '${{ github.event.workflow_run.head_sha }}'
PR_GATE = "vars.RELEASE_PR_AUTOMATION_ENABLED == 'true'"
PUB_GATE = "vars.RELEASE_PUBLICATION_ENABLED == 'true'"
TRUSTED = {
    "github.event.workflow_run.conclusion == 'success'", "github.event.workflow_run.event == 'push'",
    "github.event.workflow_run.head_branch == 'main'", 'github.event.workflow_run.head_repository.full_name == github.repository',
}
# Release jobs: activation gate, GITHUB_TOKEN rights, required identities and app-token rights (None = no app token).
# publish_release.py reads pulls, contents and check runs and writes releases, tags (contents)
# and PR labels (issues and pull-requests write).
JOBS = {
    'release-pr': (PR_GATE, {'contents': 'read'}, {'APP_CLIENT_ID', 'RELEASE_BOT_LOGIN'},
                   {'contents': 'write', 'pull-requests': 'write', 'issues': 'write'}),
    'build': (PUB_GATE, {'contents': 'read', 'pull-requests': 'read', 'checks': 'read'},
              {'APP_CLIENT_ID', 'RELEASE_BOT_LOGIN', 'RELEASE_MAINTAINERS', 'RELEASE_REQUIRED_CHECKS'}, None),
    'publish': (PUB_GATE, {'contents': 'read'}, {'APP_CLIENT_ID', 'RELEASE_BOT_LOGIN', 'RELEASE_MAINTAINERS', 'RELEASE_REQUIRED_CHECKS'},
                {'contents': 'write', 'issues': 'write', 'pull-requests': 'write', 'checks': 'read'}),
}
TOKEN_SECTION_MINUTES = 45
PROVIDER_STEP_MINUTES = 20


def load(text):
    doc = yaml.safe_load(text)
    doc['on'] = doc.pop(True, doc.get('on'))  # YAML 1.1 reads the key on as a boolean
    return doc


def strings(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from strings(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from strings(value, path + (index,))
    elif isinstance(node, str):
        yield path, node


def action(step):
    return str(step.get('uses', '')).split('@', 1)[0]


def conjuncts(condition):
    return {' '.join(part.split()) for part in str(condition).split('&&')}


def common_violations(text, doc):
    found = []
    if 'shellcheck disable' in text:
        found.append('shellcheck: Shellprüfung abgeschaltet')
    if 'pull_request_target' in text or 'continue-on-error' in text:
        found.append('checkbypass: pull_request_target oder continue-on-error')
    if doc.get('permissions') != {}:
        found.append('permissions: Workflow-Standardrechte müssen leer sein')
    for name, job in doc['jobs'].items():
        steps = job.get('steps') or []
        if not job.get('permissions'):
            found.append('permissions: %s ohne explizite Rechte' % name)
        for index, step in enumerate(steps):
            uses = step.get('uses')
            if uses:
                match = re.fullmatch(r'([\w.-]+/[\w.-]+)@([0-9a-f]{40})', uses)
                if not match or PINS.get(match[1]) != match[2]:
                    found.append('pin: %s nicht auf geprüften Commit gepinnt' % uses)
            if '${{' in str(step.get('run', '')):
                found.append('injection: Ausdruck direkt im Shellskript von %s' % name)
            if action(step) == 'actions/checkout' and (step.get('with') or {}).get('persist-credentials') is not False:
                found.append('credentials: Checkout behält Zugangsdaten in %s' % name)
            if action(step) == 'actions/setup-python':
                if step.get('with') != {'python-version': TOOLCHAIN['python']['version'], 'check-latest': False}:
                    found.append('toolchain: Python nicht exakt ' + TOOLCHAIN['python']['version'])
            if action(step) == 'jdx/mise-action':
                expected = {'version': TOOLCHAIN['mise']['version'], 'sha256': MISE_SHA256, 'mise_dir': '${{ runner.temp }}/mise', 'install': False, 'cache': False}
                if step.get('with') != expected:
                    found.append('toolchain: mise nicht exakt, geprüft, isoliert und ohne Cache')
            if step.get('run') == 'mise run tools:setup':
                prior = ' '.join(str(s.get('run', '')) for s in steps[:index])
                if 'AWC_CI_WORKSPACE=$RUNNER_TEMP/' not in prior:
                    found.append('workspace: tools:setup ohne temporären Arbeitsbereich in ' + name)
    return found


def ci_violations(text):
    doc = load(text)
    found = common_violations(text, doc)
    if doc['on'] != {'pull_request': {'branches': ['main']}, 'push': {'branches': ['main']}}:
        found.append('trigger: CI nur für pull_request und push auf main')
    if re.search(r'secrets\.|vars\.|APP_|id-token', text):
        found.append('secret: CI darf weder Secrets, Variablen noch App-Daten sehen')
    tasks = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8'))['tasks']
    for name, job in doc['jobs'].items():
        if job.get('permissions') != {'contents': 'read'}:
            found.append('permissions: %s braucht nur contents: read' % name)
        runs = [s['run'] for s in job['steps'] if 'run' in s and s['run'].startswith('mise run')]
        if runs != ['mise run tools:setup', 'mise run acceptance'] or not all(r.split()[2] in tasks for r in runs):
            found.append('tasks: %s muss tools:setup und danach die gemeinsame acceptance-Aufgabe ausführen' % name)
    return found


def release_violations(text):
    doc = load(text)
    found = common_violations(text, doc)
    jobs = doc['jobs']
    if doc['on'] != {'workflow_run': {'workflows': [load(CI.read_text(encoding='utf-8'))['name']], 'types': ['completed'], 'branches': ['main']}}:
        found.append('trigger: Release nur nach abgeschlossenem CI-Lauf auf main')
    if doc.get('concurrency') != {'group': 'release-${{ github.repository }}', 'cancel-in-progress': False}:
        found.append('concurrency: Releaseoperationen müssen serialisiert und nie abgebrochen werden')
    if (doc.get('env') or {}).get('HEAD_SHA') != HEAD_SHA or 'github.sha' in text:
        found.append('commit: Releasejobs müssen an den geprüften workflow_run-Commit gebunden sein')
    if set(jobs) != set(JOBS):
        found.append('gate: unerwartete oder fehlende Releasejobs ' + ', '.join(sorted(set(jobs) ^ set(JOBS))))
    for name, (gate, rights, identities, token_rights) in JOBS.items():
        job = jobs.get(name) or {}
        steps = job.get('steps') or []
        condition = str(job.get('if', ''))
        other = PUB_GATE if gate == PR_GATE else PR_GATE
        if '||' in condition or '!' in condition.replace('!=', '') or not ({gate} | TRUSTED) <= conjuncts(condition) or other in condition:
            found.append('gate: %s ohne exaktes Aktivierungsgate und vertrauenswürdigen CI-Erfolg' % name)
        if job.get('permissions') != rights:
            found.append('permissions: %s Rechte %r statt %r' % (name, job.get('permissions'), rights))
        first = steps[0] if steps else {}
        if set((first.get('env') or {})) != identities or not all('${{ vars.%s }}' % i == first['env'][i] and i in first.get('run', '') for i in identities) or 'exit 1' not in first.get('run', ''):
            found.append('identity: %s prüft nicht zuerst alle Identitäten %s' % (name, sorted(identities)))
        for step in steps:
            if action(step) == 'actions/checkout' and (step.get('with') or {}).get('ref') != HEAD_SHA:
                found.append('commit: %s checkt nicht den geprüften Commit aus' % name)
        found += token_violations(name, job, steps, token_rights)
    for path, value in strings(doc):
        allowed = len(path) == 6 and path[0] == 'jobs' and JOBS.get(path[1], (None,) * 4)[3] and path[2] == 'steps' \
            and action(jobs[path[1]]['steps'][path[3]]) == TOKEN_ACTION and path[4:] == ('with', 'private-key')
        if 'secrets.' in value and not (allowed and value == '${{ secrets.APP_PRIVATE_KEY }}'):
            found.append('secret: Secret außerhalb des Tokenschritts: ' + '/'.join(map(str, path)))
    found += order_violations(jobs)
    return found


def token_violations(name, job, steps, rights):
    found = []
    indexes = [i for i, s in enumerate(steps) if action(s) == TOKEN_ACTION]
    if rights is None:
        return ['token: %s darf kein App-Token erzeugen' % name] if indexes else []
    if len(indexes) != 1:
        return ['token: %s braucht genau einen frischen App-Token' % name]
    index, step = indexes[0], steps[indexes[0]]
    expected = {'client-id': '${{ vars.APP_CLIENT_ID }}', 'private-key': '${{ secrets.APP_PRIVATE_KEY }}', 'owner': '${{ github.repository_owner }}',
                'repositories': '${{ github.event.repository.name }}', **{'permission-' + k: v for k, v in rights.items()}}
    if step.get('with') != expected or step.get('id') != 'app-token':
        found.append('token: %s Token nicht genau auf dieses Repository und die Rechte %r begrenzt oder ohne Widerruf' % (name, rights))
    consumers = steps[index + 1:]
    if not consumers or not all('steps.app-token.outputs' in json.dumps(s) and 0 < s.get('timeout-minutes', 999) <= PROVIDER_STEP_MINUTES for s in consumers):
        found.append('token-time: %s führt nach dem Token anderes oder unbegrenztes aus; Token muss unmittelbar vor Providerzugriff entstehen' % name)
    if not 0 < job.get('timeout-minutes', 999) <= TOKEN_SECTION_MINUTES:
        found.append('token-time: %s Abschnitt nicht unter einer Stunde begrenzt' % name)
    if any('app-token' in value for path, value in strings({k: v for k, v in job.items() if k != 'steps'})) or \
            any('app-token' in json.dumps(s) for s in steps[:index]):
        found.append('token: %s gibt den Token außerhalb seiner Verbraucher weiter' % name)
    return found


def order_violations(jobs):
    """Build -> read-only decision -> handover -> fresh token -> publish; release-pr only proposes."""
    found = []
    runs = lambda job: [(i, str(s.get('run', ''))) for i, s in enumerate((jobs.get(job) or {}).get('steps') or [])]
    publishing = [(job, i) for job in jobs for i, r in runs(job) if 'publish_release.py' in r and '--dry-run' not in r]
    if [job for job, _ in publishing] != ['publish']:
        found.append('order: Veröffentlichung nur im Job publish erlaubt: %r' % publishing)
    build = runs('build')
    package = [i for i, r in build if 'build_core_package.py verify --output' in r]
    decision = [i for i, r in build if 'publish_release.py' in r and '--dry-run' in r and '--commit "$HEAD_SHA"' in r]
    upload = [i for i, s in enumerate(jobs.get('build', {}).get('steps') or []) if action(s) == 'actions/upload-artifact']
    if not (len(package) == len(decision) == len(upload) == 1 and package[0] < decision[0] < upload[0]):
        found.append('order: Paketabnahme und Entscheidung des exakten Commits fehlen vor der Übergabe')
    else:
        env = jobs['build']['steps'][decision[0]].get('env') or {}
        if env.get('GITHUB_TOKEN') != '${{ github.token }}' or env.get('RELEASE_REQUIRED_CHECKS') != '${{ vars.RELEASE_REQUIRED_CHECKS }}':
            found.append('checkbypass: Entscheidung nicht mit Lesetoken und Pflichtchecks')
    publish = jobs.get('publish') or {}
    steps = publish.get('steps') or []
    if publish.get('needs') != 'build' or "needs.build.outputs.pr != ''" not in conjuncts(publish.get('if')):
        found.append('order: publish hängt nicht von der Paketabnahme ab')
    pin = [i for i, r in runs('publish') if 'sha256sum --check --strict' in r and 'os.environ["HEAD_SHA"]' in r and 'r["source_clean"]' in r]
    token = [i for i, s in enumerate(steps) if action(s) == TOKEN_ACTION]
    download = [i for i, s in enumerate(steps) if action(s) == 'actions/download-artifact']
    if not (len(pin) == len(download) == len(token) == 1 and download[0] < pin[0] < token[0] and publishing and publishing[0][1] > token[0]):
        found.append('order: übergebenes Paket nicht vor dem Token auf Commit, Version und Hash festgelegt')
    if publishing:
        step = steps[publishing[0][1]] if publishing[0][0] == 'publish' else jobs[publishing[0][0]]['steps'][publishing[0][1]]
        if '--commit "$HEAD_SHA"' not in step['run'] or (step.get('env') or {}).get('RELEASE_REQUIRED_CHECKS') != '${{ vars.RELEASE_REQUIRED_CHECKS }}':
            found.append('checkbypass: Veröffentlichung ohne exakten Commit oder Pflichtchecks')
    proposal = ' '.join(r for _, r in runs('release-pr'))
    if not re.search(r'release-please\.js" \\\s+release-pr ', proposal) or 'github-release' in proposal:
        found.append('release-pr: release-pr darf nur Release-PRs vorschlagen')
    return found


def replace(text, old, new, occurrence=1):
    """Replace exactly the given occurrence; a mutation that matches nothing is a broken test."""
    parts = text.split(old)
    if len(parts) <= occurrence:
        raise AssertionError('Mutationsanker fehlt (%d. Vorkommen): %r' % (occurrence, old))
    return old.join(parts[:occurrence]) + new + old.join(parts[occurrence:])


class WorkflowFiles(unittest.TestCase):
    def setUp(self):
        self.ci, self.release = CI.read_text(encoding='utf-8'), RELEASE.read_text(encoding='utf-8')

    def test_real_workflows_satisfy_policy(self):
        self.assertEqual(ci_violations(self.ci), [])
        self.assertEqual(release_violations(self.release), [])

    def test_ci_runs_shared_acceptance_over_all_local_tasks(self):
        acceptance = bootstrap_ci.STEPS['acceptance']
        self.assertIn(('check',), acceptance)
        for task in ('version:check', 'release:test', 'workflows:check', 'docs:check'):
            self.assertTrue(all(step in acceptance for step in bootstrap_ci.STEPS[task]), task)
        self.assertEqual(acceptance[-1][:2], ('package', 'scripts/build_core_package.py'))

    def test_release_steps_use_existing_cli_contracts(self):
        python = sys.executable
        publish = subprocess.run([python, '-B', ROOT / 'scripts/publish_release.py', '--help'], capture_output=True, text=True, check=True).stdout
        for flag in ('--pr', '--commit', '--archive', '--report', '--dry-run'):
            self.assertIn(flag, publish)
        package = subprocess.run([python, '-B', ROOT / 'scripts/build_core_package.py', '--help'], capture_output=True, text=True, check=True).stdout
        self.assertIn('--output', package)
        self.assertIn('verify', package)
        for value in (release_guard.RELEASE_BRANCH_PREFIX, release_guard.MANIFEST, release_guard.CONFIG, release_guard.PACKAGE + '-[0-9]+'):
            self.assertIn(value, self.release)

    def test_release_please_cli_supports_used_options(self):
        # Same isolated toolchain lookup as test_release_automation; a missing toolchain fails, never skips.
        _, ws, env, _ = bootstrap_ci.verify(Path(os.environ.get('AWC_CI_WORKSPACE') or Path(sys.prefix).parent))
        cli = ws / 'npm/node_modules/release-please/build/src/bin/release-please.js'
        self.assertIn('"$AWC_CI_WORKSPACE/node/bin/node" "$AWC_CI_WORKSPACE/npm/node_modules/release-please/build/src/bin/release-please.js"', self.release)
        out = subprocess.run([ws / 'node/bin/node', cli, 'release-pr', '--help'], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        flags = re.findall(r'(--[a-z-]+)=', self.release.split('release-please.js"', 1)[1].split('\n\n', 1)[0])
        self.assertGreaterEqual(len(flags), 5)
        for flag in flags:
            self.assertIn(flag, out.stdout)

    def test_irrelevant_edits_still_pass(self):
        self.assertEqual(ci_violations(replace(self.ci, 'name: acceptance', 'name: acceptance (shared)')), [])
        self.assertEqual(release_violations(replace(self.release, 'name: Exact commit', 'name: Exact checked commit')), [])
        self.assertEqual(release_violations(replace(self.release, '# Privileged release automation', '# Privileged, gated release automation')), [])


CI_MUTATIONS = {
    'pull_request_target': ('on:\n  pull_request:\n', 'on:\n  pull_request_target:\n    branches: [main]\n  pull_request:\n', 'trigger'),
    'extra trigger': ('  push:\n    branches: [main]\n', '  push:\n    branches: [main, dev]\n', 'trigger'),
    'write permission': ('    permissions:\n      contents: read\n', '    permissions:\n      contents: write\n', 'permissions'),
    'default permissions': ('permissions: {}\n', 'permissions: write-all\n', 'permissions'),
    'app secret in PR job': ('        run: mise run acceptance\n', '        run: mise run acceptance\n        env:\n          APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}\n', 'secret'),
    'action tag': ('actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1', 'actions/checkout@v7', 'pin'),
    'foreign sha': ('jdx/mise-action@2d8d4cafcbd33be2ea37d2b6f5ad595363d1f1ca', 'jdx/mise-action@2d8d4cafcbd33be2ea37d2b6f5ad595363d1f1cb', 'pin'),
    'python minor only': ("python-version: '3.13.14'", "python-version: '3.13'", 'toolchain'),
    'mise unpinned': ("version: '2026.10.19'", "version: 'latest'", 'toolchain'),
    'mise cache': ('cache: false', 'cache: true', 'toolchain'),
    'kept credentials': ('persist-credentials: false', 'persist-credentials: true', 'credentials'),
    'weaker task': ('run: mise run acceptance', 'run: mise run check', 'tasks'),
    'home workspace': ('echo "AWC_CI_WORKSPACE=$RUNNER_TEMP/awc-ci"', 'echo "AWC_CI_WORKSPACE=$HOME/awc-ci"', 'workspace'),
    'continue on error': ('      - name: acceptance\n', '      - name: acceptance\n        continue-on-error: true\n', 'checkbypass'),
    'shellcheck off': ('      - name: acceptance\n', '      # shellcheck disable=SC2086\n      - name: acceptance\n', 'shellcheck'),
    'expression injection': ('run: mise run acceptance', 'run: mise run acceptance ${{ github.head_ref }}', 'injection'),
}

PUBLISH_STEP = '      - name: Publish (re-decides; ordered effects; never overwrites)\n'
RELEASE_MUTATIONS = {
    'pr gate removed': ("      vars.RELEASE_PR_AUTOMATION_ENABLED == 'true'\n      && ", '      ', 'gate'),
    'publication gate weakened': ("vars.RELEASE_PUBLICATION_ENABLED == 'true'", "vars.RELEASE_PUBLICATION_ENABLED != 'false'", 'gate', 2),
    'gates swapped': ("vars.RELEASE_PR_AUTOMATION_ENABLED == 'true'", "vars.RELEASE_PUBLICATION_ENABLED == 'true'", 'gate'),
    'gate bypass with or': ("vars.RELEASE_PUBLICATION_ENABLED == 'true'", "vars.RELEASE_PUBLICATION_ENABLED == 'true' || always()", 'gate'),
    'ci failure accepted': ("github.event.workflow_run.conclusion == 'success'", "github.event.workflow_run.conclusion != 'cancelled'", 'gate', 3),
    'fork run accepted': ('&& github.event.workflow_run.head_repository.full_name == github.repository', '', 'gate', 2),
    'pull request trigger': ('    workflows: [CI]\n', '    workflows: [CI]\n  pull_request:\n', 'trigger'),
    'other branch': ('    branches: [main]\n', '    branches: [main, "release/**"]\n', 'trigger'),
    'write-all': ('permissions: {}\n', 'permissions: write-all\n', 'permissions'),
    'build may write': ('      contents: read\n      pull-requests: read\n', '      contents: write\n      pull-requests: read\n', 'permissions'),
    'publish job write token': ('    permissions:\n      contents: read\n    env:\n', '    permissions:\n      contents: write\n    env:\n', 'permissions'),
    'publisher PR labels read-only': ('          permission-pull-requests: write\n          permission-checks: read\n', '          permission-pull-requests: read\n          permission-checks: read\n', 'token'),
    'token not revoked': ('          permission-checks: read\n', '          permission-checks: read\n          skip-token-revoke: true\n', 'token'),
    'token for all repos': ('          repositories: ${{ github.event.repository.name }}\n', '', 'token', 2),
    'token too broad': ('          permission-issues: write\n', '          permission-issues: write\n          permission-administration: write\n', 'token'),
    'token too few rights': ('          permission-issues: write\n      - name: Release PR', '      - name: Release PR', 'token'),
    'stale token': (PUBLISH_STEP, '      - name: Slow work after minting\n        run: sleep 3000\n' + PUBLISH_STEP, 'token-time'),
    'unbounded provider step': ('        timeout-minutes: 20\n', '', 'token-time'),
    'long token section': ('    timeout-minutes: 45\n    permissions:\n      contents: read\n    env:\n', '    timeout-minutes: 120\n    permissions:\n      contents: read\n    env:\n', 'token-time'),
    'token leaves job': ('    name: release-pr\n', '    name: release-pr\n    outputs:\n      token: ${{ steps.app-token.outputs.token }}\n', 'token'),
    'app key in build': ('          GITHUB_TOKEN: ${{ github.token }}\n', '          GITHUB_TOKEN: ${{ github.token }}\n          APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}\n', 'secret'),
    'token in build': ("      - if: steps.release-pr.outputs.pr != ''\n        uses: actions/upload-artifact", "      - uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1\n        with:\n          private-key: x\n      - if: steps.release-pr.outputs.pr != ''\n        uses: actions/upload-artifact", 'token'),
    'wrong commit binding': ('  HEAD_SHA: ${{ github.event.workflow_run.head_sha }}\n', '  HEAD_SHA: ${{ github.sha }}\n', 'commit'),
    'unbound checkout': ('          ref: ${{ github.event.workflow_run.head_sha }}\n', '', 'commit', 3),
    'publish other commit': ('--commit "$HEAD_SHA" \\\n            --archive "$RUNNER_TEMP/release-package/$ARCHIVE" --report "$RUNNER_TEMP/release-package/package-report.json"\n', '--commit "$GITHUB_SHA" \\\n            --archive "$RUNNER_TEMP/release-package/$ARCHIVE" --report "$RUNNER_TEMP/release-package/package-report.json"\n', 'checkbypass'),
    'publish without acceptance': ('    needs: build\n', '', 'order'),
    'decision not dry': ('package-report.json" --dry-run\n', 'package-report.json"\n', 'order'),
    'no package build': ('scripts/build_core_package.py verify --output "$out"', 'true', 'order'),
    'hash not pinned': ('          echo "$ARCHIVE_SHA256  $dir/$ARCHIVE" | sha256sum --check --strict\n', '', 'order'),
    'source clean ignored': ('seen = (r["verified"], r["source_clean"], ', 'seen = (r["verified"], True, ', 'order'),
    'checks not required': ('          RELEASE_REQUIRED_CHECKS: ${{ vars.RELEASE_REQUIRED_CHECKS }}\n        run: |\n          "$AWC', '        run: |\n          "$AWC', 'checkbypass'),
    'decision without checks': ('          RELEASE_REQUIRED_CHECKS: ${{ vars.RELEASE_REQUIRED_CHECKS }}\n          PR:', '          PR:', 'checkbypass'),
    'decision with secret token': ('          GITHUB_TOKEN: ${{ github.token }}\n          RELEASE_BOT_LOGIN', '          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n          RELEASE_BOT_LOGIN', 'secret'),
    'missing maintainer identity': ('          RELEASE_MAINTAINERS: ${{ vars.RELEASE_MAINTAINERS }}\n          RELEASE_REQUIRED_CHECKS: ${{ vars.RELEASE_REQUIRED_CHECKS }}\n        run: |\n          for', '          RELEASE_REQUIRED_CHECKS: ${{ vars.RELEASE_REQUIRED_CHECKS }}\n        run: |\n          for', 'identity', 2),
    'identity failure ignored': ('              exit 1\n            fi\n          done\n', '            fi\n          done\n', 'identity'),
    'parallel releases': ('cancel-in-progress: false', 'cancel-in-progress: true', 'concurrency'),
    'per-run concurrency': ('group: release-${{ github.repository }}', 'group: release-${{ github.run_id }}', 'concurrency'),
    'release-please publishes': ('            release-pr --token', '            github-release --token', 'release-pr'),
    'continue on error': (PUBLISH_STEP, PUBLISH_STEP + '        continue-on-error: true\n', 'checkbypass'),
    'action tag': ('actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1', 'actions/create-github-app-token@v3', 'pin'),
    'expression injection': ('test "$(git rev-parse HEAD)" = "$HEAD_SHA"', 'test "$(git rev-parse HEAD)" = "${{ github.event.workflow_run.head_sha }}"', 'injection'),
}


class WorkflowMutations(unittest.TestCase):
    """Each controlled defect in the real files is detected by the matching rule."""

    def check(self, path, mutations, validate):
        text = path.read_text(encoding='utf-8')
        for label, (old, new, rule, *occurrence) in mutations.items():
            with self.subTest(mutation=label):
                mutated = replace(text, old, new, *occurrence)
                self.assertNotEqual(mutated, text)
                violations = validate(mutated)
                self.assertTrue(any(v.startswith(rule + ':') for v in violations), (label, violations))

    def test_ci_mutations_are_detected(self):
        self.check(CI, CI_MUTATIONS, ci_violations)

    def test_release_mutations_are_detected(self):
        self.check(RELEASE, RELEASE_MUTATIONS, release_violations)

    def test_job_structure_mutations_are_detected(self):
        doc = load(RELEASE.read_text(encoding='utf-8'))
        for label, mutate, rule in (
            ('identity step not first', lambda d: d['jobs']['publish']['steps'].append(d['jobs']['publish']['steps'].pop(0)), 'identity'),
            ('extra privileged job', lambda d: d['jobs'].__setitem__('extra', copy.deepcopy(d['jobs']['publish'])), 'gate'),
            ('token before setup', lambda d: d['jobs']['publish']['steps'].insert(1, d['jobs']['publish']['steps'].pop(-2)), 'token-time'),
        ):
            with self.subTest(mutation=label):
                mutated = copy.deepcopy(doc)
                mutate(mutated)
                mutated[True] = mutated.pop('on')
                violations = release_violations(yaml.safe_dump(mutated, sort_keys=False, allow_unicode=True))
                self.assertTrue(any(v.startswith(rule + ':') for v in violations), (label, violations))


if __name__ == '__main__':
    unittest.main()
