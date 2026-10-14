#!/usr/bin/env python3
"""Isolated CI toolchain: setup installs pinned tools, every other command only verifies and runs."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = ROOT / 'scripts/ci_toolchain.json'
DEFAULT_WORKSPACE = '/tmp/opencode/agentic-workflow-core-ci'
DOWNLOADS = ('node', 'apm', 'actionlint', 'shellcheck')
# Follow-up task contracts: exact steps over sources owned by later plan tasks.
# Missing sources fail visibly with their owner; nothing is skipped or installed.
OWNERS = {
    'scripts/release_guard.py': 'T02', 'tests/test_release_automation.py': 'T02', 'tests/test_core_package.py': 'T02',
    'scripts/build_core_package.py': 'T02', '.github/workflows/ci.yaml': 'T03', '.github/workflows/release.yaml': 'T03',
    'tests/test_ci_workflows.py': 'T03', 'scripts/check_core_contracts.py': 'T01',
}
STEPS = {
    'version:check': [('script', 'scripts/release_guard.py', 'version-check')],
    'release:test': [('tests', 'tests/test_release_automation.py'), ('tests', 'tests/test_core_package.py')],
    'workflows:check': [('actionlint', '.github/workflows/ci.yaml', '.github/workflows/release.yaml'), ('tests', 'tests/test_ci_workflows.py')],
    'docs:check': [('script', 'scripts/check_core_contracts.py', '--group', 'docs')],
}
# Only acceptance has a planned package/installation effect (scratch package build and test install).
STEPS['acceptance'] = [('check',), *(s for t in ('version:check', 'release:test', 'workflows:check', 'docs:check') for s in STEPS[t]), ('package', 'scripts/build_core_package.py', 'verify')]


class ToolchainError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ToolchainError(message)


def load_toolchain(path=TOOLCHAIN):
    data = json.loads(path.read_text(encoding='utf-8'))
    require(data.get('schema') == 'ci-toolchain/v1', 'Toolchainschema ci-toolchain/v1 erforderlich')
    require(data.get('platform') == 'linux-x64', 'nur linux-x64 ist gepinnt')
    for name in ('mise', 'python', 'node', 'apm', 'actionlint', 'shellcheck', 'npm'):
        require(isinstance(data.get(name), dict), 'Toolchaineintrag fehlt: ' + name)
    for name in ('mise', 'python', 'node', 'apm', 'actionlint', 'shellcheck'):
        require(re.fullmatch(r'\d+\.\d+\.\d+', str(data[name].get('version', ''))), 'keine exakte Version: ' + name)
    for name in DOWNLOADS:
        require(str(data[name].get('url', '')).startswith('https://'), 'Download ohne HTTPS: ' + name)
        require(re.fullmatch(r'[0-9a-f]{64}', str(data[name].get('sha256', ''))), 'Integritätswert fehlt: ' + name)
    return data


def workspace():
    path = Path(os.environ.get('AWC_CI_WORKSPACE') or DEFAULT_WORKSPACE).resolve()
    require(not path.is_relative_to(ROOT) and path != Path.home().resolve() and not Path.home().resolve().is_relative_to(path), 'Arbeitsbereich muss außerhalb von Repository und Benutzer-Home liegen: ' + str(path))
    return path


def isolated_env(ws):
    """Every tool sees only the workspace as home, cache and config."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PIP_', 'NPM_', 'npm_', 'PYTHON', 'NODE_', 'XDG_', 'APM_'))}
    env.update(
        AWC_CI_WORKSPACE=str(ws), AWC_HABIT_SDK=str(ws / "habit-sdk"),
        HOME=str(ws / 'home'), XDG_CONFIG_HOME=str(ws / 'home/.config'), XDG_CACHE_HOME=str(ws / 'cache'), XDG_DATA_HOME=str(ws / 'home/.local/share'),
        TMPDIR=str(ws / 'tmp'), PIP_CACHE_DIR=str(ws / 'cache/pip'), PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_INPUT='1',
        npm_config_cache=str(ws / 'cache/npm'), npm_config_userconfig=str(ws / 'npmrc'), npm_config_globalconfig=str(ws / 'npmrc-global'), npm_config_prefix=str(ws / 'npm-prefix'),
        npm_config_update_notifier='false', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
        PATH=os.pathsep.join([str(ws / 'venv/bin'), str(ws / 'node/bin'), str(ws / 'apm'), str(ws / 'actionlint'), str(ws / 'shellcheck'), str(ws / 'habit-sdk/bin'), env.get('PATH', '')]),
    )
    return env


def run(command, env, cwd=ROOT, timeout=900):
    result = subprocess.run([str(c) for c in command], cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    require(result.returncode == 0, ' '.join(map(str, command)) + ' scheiterte (' + str(result.returncode) + '): ' + (result.stderr + result.stdout)[-2000:])
    return result.stdout


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def source_snapshot():
    """Hashes of all tracked and unignored files; checks must leave them untouched."""
    listing = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, check=True).stdout
    files = sorted(p for p in listing.decode().split('\0') if p)
    return {p: sha256(ROOT / p) if (ROOT / p).is_file() else None for p in files}


def check_runtime(tc):
    mise = subprocess.run(['mise', '--version'], capture_output=True, text=True, env=dict(os.environ, MISE_QUIET='1')).stdout.split()
    require(mise and mise[0] == tc['mise']['version'], 'mise ' + tc['mise']['version'] + ' erforderlich, gefunden: ' + (mise[0] if mise else 'keines'))
    found = '%d.%d.%d' % sys.version_info[:3]
    require(found == tc['python']['version'], 'Python ' + tc['python']['version'] + ' erforderlich, gefunden: ' + found + ' (keine Ersatzversion)')


def check_pins(tc):
    """Toolchain, requirements and package manifest must name the same exact versions."""
    requirements = (ROOT / tc['python']['requirements']).read_text(encoding='utf-8')
    for name, version in tc['python']['packages'].items():
        require(re.search(r'(?m)^' + re.escape(name) + '==' + re.escape(version) + r' \\$', requirements), 'requirements-ci.txt pinnt nicht ' + name + '==' + version)
    require(requirements.count('--hash=sha256:') >= len(tc['python']['packages']), 'requirements-ci.txt ohne Integritätswerte')
    manifest = json.loads((ROOT / tc['npm']['package']).read_text(encoding='utf-8'))
    lock = json.loads((ROOT / tc['npm']['lockfile']).read_text(encoding='utf-8'))
    require(manifest.get('engines', {}).get('node') == tc['node']['version'], 'package.json pinnt Node nicht exakt')
    for name, version in tc['npm']['packages'].items():
        require(manifest.get('dependencies', {}).get(name) == version, 'package.json pinnt nicht ' + name + '@' + version)
        require(lock['packages'].get('node_modules/' + name, {}).get('version') == version, 'package-lock.json widerspricht ' + name + '@' + version)
    require(all(entry.get('integrity') for key, entry in lock['packages'].items() if key), 'package-lock.json ohne Integritätswerte')


def download(tool, ws):
    archive = ws / 'downloads' / Path(tool['url']).name
    if not archive.is_file() or sha256(archive) != tool['sha256']:
        archive.parent.mkdir(parents=True, exist_ok=True)
        partial = archive.with_suffix(archive.suffix + '.partial')
        with urllib.request.urlopen(tool['url'], timeout=300) as response, open(partial, 'wb') as handle:
            shutil.copyfileobj(response, handle)
        observed = sha256(partial)
        if observed != tool['sha256']:
            partial.unlink()
            raise ToolchainError('Integritätswert verletzt: ' + tool['url'] + ' sha256=' + observed)
        partial.replace(archive)
    return archive


def extract(archive, target):
    if target.exists():
        shutil.rmtree(target)
    staging = Path(tempfile.mkdtemp(dir=target.parent))
    with tarfile.open(archive) as handle:
        handle.extractall(staging, filter='data')
    entries = list(staging.iterdir())
    (entries[0] if len(entries) == 1 and entries[0].is_dir() else staging).rename(target)
    if staging.exists():
        shutil.rmtree(staging)


def tool_versions(tc, ws, env):
    """Observed versions of the isolated tools; never installs."""
    venv_python = ws / 'venv/bin/python'
    for path in (venv_python, ws / 'node/bin/node', ws / 'apm/apm', ws / 'actionlint/actionlint', ws / 'shellcheck/shellcheck'):
        require(path.is_file(), 'isolierte Werkzeuge fehlen (' + str(path) + '); zuerst mise run tools:setup ausführen')
    observed = dict(
        python=run([venv_python, '-c', 'import platform; print(platform.python_version())'], env).strip(),
        PyYAML=run([venv_python, '-c', 'import yaml; print(yaml.__version__)'], env).strip(),
        node=run([ws / 'node/bin/node', '--version'], env).strip().removeprefix('v'),
        apm=re.search(r'\d+\.\d+\.\d+', run([ws / 'apm/apm', '--version'], env))[0],
        actionlint=run([ws / 'actionlint/actionlint', '-version'], env).split()[0],
        shellcheck=re.search(r'(?m)^version: (\S+)', run([ws / 'shellcheck/shellcheck', '--version'], env))[1],
    )
    observed.update(json.loads(run([venv_python, '-c',
        'import importlib.metadata as m,json; print(json.dumps({n:m.version(n) for n in ' +
        repr(list(tc['python']['packages'])) + '}))'], env)))
    for name in tc['npm']['packages']:
        manifest = ws / 'npm/node_modules' / name / 'package.json'
        require(manifest.is_file(), 'isoliertes npm-Paket fehlt: ' + name + '; zuerst mise run tools:setup ausführen')
        observed[name] = json.loads(manifest.read_text(encoding='utf-8'))['version']
    expected = dict(python=tc['python']['version'], node=tc['node']['version'], apm=tc['apm']['version'], actionlint=tc['actionlint']['version'], shellcheck=tc['shellcheck']['version'], **tc['python']['packages'], **tc['npm']['packages'])
    require(observed == expected, 'Werkzeugversionen weichen ab: erwartet ' + json.dumps(expected) + ', beobachtet ' + json.dumps(observed))
    return observed


def verify(ws=None):
    tc = load_toolchain()
    check_runtime(tc)
    check_pins(tc)
    ws = ws or workspace()
    env = isolated_env(ws)
    observed = tool_versions(tc, ws, env)
    receipt = json.loads((ws / 'toolchain-receipt.json').read_text(encoding='utf-8'))
    require(receipt.get('toolchain_sha256') == sha256(TOOLCHAIN), 'Arbeitsbereich gehört zu anderer Toolchain; mise run tools:setup erneut ausführen')
    for name in DOWNLOADS:
        archive = ws / 'downloads' / Path(tc[name]['url']).name
        require(archive.is_file() and sha256(archive) == tc[name]['sha256'], 'Integritätswert verletzt: ' + name)
    return tc, ws, env, observed


def setup():
    tc = load_toolchain()
    check_runtime(tc)
    check_pins(tc)
    ws = workspace()
    before = source_snapshot()
    for directory in ('home/.config', 'cache', 'tmp', 'downloads', 'npm'):
        (ws / directory).mkdir(parents=True, exist_ok=True)
    env = isolated_env(ws)
    if not (ws / 'venv/bin/python').is_file():
        run([sys.executable, '-m', 'venv', '--clear', ws / 'venv'], env)
    run([ws / 'venv/bin/python', '-m', 'pip', 'install', '--require-hashes', '--no-deps', '--only-binary', ':all:', '-r', ROOT / tc['python']['requirements']], env)
    for name in DOWNLOADS:
        extract(download(tc[name], ws), ws / name)
    for name in ('package', 'lockfile'):
        shutil.copyfile(ROOT / tc['npm'][name], ws / 'npm' / Path(tc['npm'][name]).name)
    run([ws / 'node/bin/node', ws / 'node/lib/node_modules/npm/bin/npm-cli.js', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', '--registry=https://registry.npmjs.org/'], env, cwd=ws / 'npm')
    (ws / 'toolchain-receipt.json').write_text(json.dumps(dict(toolchain_sha256=sha256(TOOLCHAIN)), indent=2) + '\n', encoding='utf-8')
    import bootstrap_habit_ci
    bootstrap_habit_ci.setup(ws, env)
    _, _, _, observed = verify(ws)
    require(source_snapshot() == before, 'Setup hat Quellbestand verändert')
    print('PASS tools:setup', json.dumps(observed, sort_keys=True), 'workspace=' + str(ws))
    for name in DOWNLOADS:
        print('INTEGRITY', name, tc[name]['sha256'], Path(tc[name]['url']).name)


def check():
    _, ws, env, observed = verify()
    import bootstrap_habit_ci
    bootstrap_habit_ci.verify(ws, env)
    print('TOOLS', json.dumps(observed, sort_keys=True), 'workspace=' + str(ws))
    before = source_snapshot()
    python = ws / 'venv/bin/python'
    try:
        for command in ([python, '-B', '-m', 'unittest', 'discover', '-s', ROOT / 'tests', '-t', ROOT / 'tests', '-p', 'test_*.py', '-v'],
                        [python, '-B', ROOT / 'scripts/check_core_contracts.py', '--group', 'all']):
            result = subprocess.run([str(c) for c in command], cwd=ROOT, env=env, timeout=1800)
            require(result.returncode == 0, 'Prüfung fehlgeschlagen: ' + ' '.join(map(str, command[1:])))
    finally:
        require(source_snapshot() == before, 'Prüfung hat Quellbestand verändert')
    print('PASS check: Bestandssuite, Portabilitätstests und Vertragsgruppen')


def call(command, env):
    """Run one step with the isolated environment; output is echoed and returned for evidence."""
    result = subprocess.run([str(c) for c in command], cwd=ROOT, env=env, text=True, capture_output=True, timeout=1800)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result


def step_command(step, ws):
    kind, *args = step
    python = ws / 'venv/bin/python'
    if kind in ('script', 'package'):
        return [python, '-B', ROOT / args[0], *args[1:]]
    if kind == 'tests':
        return [python, '-B', '-m', 'unittest', 'discover', '-s', ROOT / 'tests', '-t', ROOT / 'tests', '-p', Path(args[0]).name, '-v']
    if kind == 'actionlint':
        # Shell analysis stays on, bound to the pinned isolated shellcheck instead of any system PATH copy.
        return [ws / 'actionlint/actionlint', '-shellcheck=' + str(ws / 'shellcheck/shellcheck'), *(ROOT / a for a in args)]
    raise ToolchainError('unbekannter Schritt: ' + kind)


def dispatch(task):
    """Run a follow-up task exactly as contracted; checks never install, only acceptance may package."""
    require(task in STEPS, 'unbekannte Aufgabe: ' + str(task))
    steps = STEPS[task]
    missing = sorted({a for kind, *args in steps if kind != 'check' for a in args if a in OWNERS and not (ROOT / a).is_file()})
    require(not missing, task + ': Folgeimplementierung fehlt: ' + ', '.join(m + ' (' + OWNERS[m] + ')' for m in missing) + '; kein grüner Skip')
    _, ws, env, observed = verify()
    print('TOOLS', json.dumps(observed, sort_keys=True), 'workspace=' + str(ws))
    before = source_snapshot()
    try:
        for step in steps:
            if step[0] == 'check':
                check()
                continue
            if step[0] == 'package':
                print('PACKAGE-EFFECT erlaubt (nur acceptance): ' + ' '.join(step[1:]) + ' baut und installiert ausschließlich in Scratchbereiche')
            result = call(step_command(step, ws), env)
            require(result.returncode == 0, task + ': Schritt fehlgeschlagen (' + str(result.returncode) + '): ' + ' '.join(step[1:]))
            if step[0] == 'tests':
                ran = re.search(r'^Ran (\d+) tests?', result.stderr, re.M)
                require(ran and int(ran[1]) > 0, task + ': keine Tests ausgeführt: ' + step[1])
    finally:
        require(source_snapshot() == before, task + ' hat Quellbestand verändert')
    print('PASS', task)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('setup', 'verify', 'check', 'run'))
    parser.add_argument('task', nargs='?')
    args = parser.parse_args(argv)
    try:
        if args.command == 'setup':
            setup()
        elif args.command == 'verify':
            print('PASS verify', json.dumps(verify()[3], sort_keys=True))
        elif args.command == 'check':
            check()
        else:
            dispatch(args.task)
        return 0
    except (ToolchainError, OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
