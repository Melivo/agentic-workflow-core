#!/usr/bin/env python3
"""Explicit, integrity-pinned Habit/SDK test setup inside AWC_CI_WORKSPACE.

Only setup installs. verify checks existing tools/receipts without network access.
The runtime's /tmp/opencode boundary stays unchanged; setup creates that scratch
parent explicitly on fresh runners, never a project or user-level installation.
"""
import sys
sys.dont_write_bytecode = True
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request

import bootstrap_ci as ci

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'scripts/requirements-habit-ci.txt'
MANIFEST = ROOT / 'scripts/habit-ci/package.json'
LOCK = ROOT / 'scripts/habit-ci/package-lock.json'
PYTHON_PINS = {'habit-hooks':'1.5.0','habit-hooks-generic':'1.5.0',
               'habit-hooks-python':'1.5.0','ruff':'0.14.5','attrs':'26.1.0',
               'Jinja2':'3.1.6','MarkupSafe':'3.0.4','pathspec':'1.1.1'}
NPM_PINS = {'@opencode/plugin':'2.0.25','@opencode/schema':'2.0.25',
            '@opencode/client':'2.0.25','@opencode/cli-linux-x64-baseline':'2.0.25',
            'typescript':'5.9.3','@types/node':'22.19.1'}


def binding():
    return {p.name:ci.sha256(p) for p in (REQUIREMENTS, MANIFEST, LOCK)}


def check_pins():
    manifest = json.loads(MANIFEST.read_text())
    lock = json.loads(LOCK.read_text())
    ci.require(manifest.get('private') is True and manifest.get('type') == 'module' and
               not manifest.get('scripts'), 'unsafe Habit CI manifest (ESM required)')
    ci.require(manifest['dependencies'] == NPM_PINS, 'Habit SDK/host pins changed')
    ci.require(lock['packages']['']['dependencies'] == NPM_PINS, 'Habit lock root mismatch')
    for name, version in NPM_PINS.items():
        ci.require(lock['packages']['node_modules/'+name]['version'] == version, 'Habit lock pin mismatch: '+name)
    for name, entry in lock['packages'].items():
        if name:
            ci.require(entry.get('integrity', '').startswith('sha512-') and
                       entry.get('resolved', '').startswith('https://registry.npmjs.org/'),
                       'Habit lock integrity/registry missing: '+name)
    requirements = REQUIREMENTS.read_text()
    for name, version in PYTHON_PINS.items():
        ci.require(name+'=='+version+' \\' in requirements, 'Habit Python pin missing: '+name)
    ci.require(requirements.count('--hash=sha256:') >= len(PYTHON_PINS), 'Habit Python hashes missing')
    return lock


def scratch_parent():
    root = Path('/tmp/opencode')
    ci.require(not root.is_symlink(), 'Habit scratch symlink refused')
    root.mkdir(mode=0o700, exist_ok=True)
    st = root.stat()
    ci.require(st.st_uid == os.getuid() and not st.st_mode & 0o022, 'Habit scratch ownership/mode refused')
    return root


def setup(ws, env):
    lock = check_pins()
    scratch_parent()
    sdk = ws / 'habit-sdk'
    runtime = sdk / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    for source in (MANIFEST, LOCK):
        shutil.copyfile(source, runtime/source.name)
    ci.run([ws/'venv/bin/python', '-m', 'pip', 'install', '--require-hashes', '--no-deps',
            '--only-binary=:all:', '-r', REQUIREMENTS], env)
    ci.run([ws/'node/bin/node', ws/'node/lib/node_modules/npm/bin/npm-cli.js', 'ci',
            '--ignore-scripts', '--no-audit', '--no-fund', '--registry=https://registry.npmjs.org/'], env, cwd=runtime)
    binary = runtime/'node_modules/@opencode/cli-linux-x64-baseline/bin/opencode'
    ci.require(binary.is_file(), 'pinned OpenCode executable missing')
    bindir = sdk/'bin'
    bindir.mkdir(exist_ok=True)
    link = bindir/'opencode'
    if link.is_symlink():
        ci.require(link.resolve() == binary.resolve(), 'unexpected OpenCode link')
    else:
        ci.require(not link.exists(), 'unexpected OpenCode binding')
        link.symlink_to(binary)
    # Preserve the already-qualified independent archive integrity check.
    plugin = lock['packages']['node_modules/@opencode/plugin']
    with urllib.request.urlopen(plugin['resolved'], timeout=120) as response:
        data = response.read()
    ci.require('sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode() == plugin['integrity'],
               'pinned SDK tarball integrity violated')
    (sdk/'pkg.tgz').write_bytes(data)
    (sdk/'meta.json').write_text(json.dumps({'versions':{'2.0.25':{'dist':{'integrity':plugin['integrity']}}}})+'\n')
    (sdk/'receipt.json').write_text(json.dumps(binding(), sort_keys=True)+'\n')
    verify(ws, env)
    ci.run([ws/'venv/bin/python', '-B', ROOT/'scripts/check_habit_feedback.py', 'setup'], env)


def verify(ws, env):
    lock = check_pins()
    sdk = ws/'habit-sdk'
    ci.require((sdk/'receipt.json').is_file(), 'Habit test setup missing; run tools:setup')
    ci.require(json.loads((sdk/'receipt.json').read_text()) == binding(), 'Habit test setup stale; run tools:setup')
    output = ci.run([ws/'venv/bin/python', '-B', '-c',
                     'import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in '+repr(list(PYTHON_PINS))+'}))'], env)
    ci.require(json.loads(output) == PYTHON_PINS, 'Habit Python version mismatch')
    for name, version in NPM_PINS.items():
        p = sdk/'runtime/node_modules'/name/'package.json'
        ci.require(p.is_file() and json.loads(p.read_text())['version'] == version, 'Habit npm version mismatch: '+name)
    expected = lock['packages']['node_modules/@opencode/plugin']['integrity']
    ci.require('sha512-'+base64.b64encode(hashlib.sha512((sdk/'pkg.tgz').read_bytes()).digest()).decode() == expected,
               'Habit SDK archive changed')
    ci.require(ci.run([sdk/'bin/opencode', '--version'], env).strip() == 'opencode v2.0.25', 'Habit host version mismatch')
    ci.require(Path('/tmp/opencode').is_dir(), 'Habit scratch parent missing; run tools:setup')
    return {'python':PYTHON_PINS, 'npm':NPM_PINS}
