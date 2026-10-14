#!/usr/bin/env python3
"""Isolated producer build and fresh scratch installation of the Core APM package.

verify copies the canonical package sources into a temporary producer, runs
`apm install --only apm --frozen`, `apm audit --ci` and
`apm pack --offline --target agent-skills --archive`, installs the ZIP into an empty consumer
and checks archive and installation against the sources. Exit codes alone are never accepted.
ZIP and report go to --output; the repository and the user profile stay untouched.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import tempfile
import zipfile

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCES = ('apm.yml', 'apm.lock.yaml', 'LICENSE', '.apm')
PRODUCER_COMMANDS = (
    ('install', '--only', 'apm', '--frozen'),
    ('audit', '--ci'),
    ('pack', '--offline', '--target', 'agent-skills', '--archive', '--output', 'dist'),
)
BUNDLED_SKILL = release_guard.BUNDLED_SKILL
FORBIDDEN_PARTS = {'.agentic-workflow', '.git', 'apm_modules', 'node_modules', '__pycache__', '.agents', '.opencode', '.codex'}
FORBIDDEN_NAME = re.compile(r'(\.env(\..+)?|\.npmrc|\.pypirc|id_rsa|id_ed25519|.*\.(pem|key|p12|pfx|pyc))$')
SECRET = re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
SECRET_ENV = re.compile(r'TOKEN|SECRET|PASSWORD|PRIVATE|_PAT$|_KEY$|^APM_|^XDG_|^PIP_|^NPM_|^npm_')


class PackageError(RuntimeError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def core_files(files, prefix):
    """{'core-x/rel': bytes} for every file below prefix + 'core-*/'."""
    return {k[len(prefix):]: v for k, v in files.items() if k.startswith(prefix + 'core-')}


def auxiliary_files(files, prefix):
    return {k[len(prefix):]: v for k, v in files.items()
            if k.startswith(prefix + BUNDLED_SKILL + '/')}


def compare_auxiliary(sources, actual, where):
    expected = auxiliary_files(sources, '.apm/skills/')
    violations = []
    if BUNDLED_SKILL + '/SKILL.md' not in expected:
        violations.append('kanonischer Begleitskill fehlt: ' + BUNDLED_SKILL)
    for key in sorted(set(expected) | set(actual)):
        if key not in actual:
            violations.append(where + ': Begleitskill-Datei fehlt: ' + key)
        elif key not in expected:
            violations.append(where + ': unerwartete Begleitskill-Datei: ' + key)
        elif expected[key] != actual[key]:
            violations.append(where + ': Begleitskill-Datei verändert: ' + key)
    return violations


def bundles(mapping):
    return sorted({k.split('/', 1)[0] for k in mapping})


def leaks(files):
    """Run artifacts, projections, caches and secrets must never be packaged."""
    found = []
    for path, data in sorted(files.items()):
        parts = PurePosixPath(path).parts
        if FORBIDDEN_PARTS & set(parts) or FORBIDDEN_NAME.fullmatch(parts[-1]):
            found.append('verbotener Pfad im Paket: ' + path)
        elif SECRET.search(data):
            found.append('mögliches Secret im Paket: ' + path)
    return found


def links(files, prefix):
    """(count, unresolved) of relative Markdown links in prefix + 'core-*' files, resolved within files."""
    known = set(files) | {posixpath.dirname(p) for p in files}
    count, unresolved = 0, []
    for path, data in sorted(files.items()):
        if not (path.startswith(prefix + 'core-') or path.startswith(prefix + BUNDLED_SKILL + '/')) or not path.endswith('.md'):
            continue
        for ref in LINK.findall(data.decode('utf-8')):
            if re.match(r'[a-z][a-z0-9+.-]*:', ref) or ref.startswith('#'):
                continue
            count += 1
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), ref.split('#')[0]))
            if target not in known or 'apm_modules' in target:
                unresolved.append(path + ' -> ' + ref)
    return count, unresolved


def compare_core(sources, actual, where):
    """The core bundle set and every core file must be byte-identical to the canonical sources."""
    expected = core_files(sources, '.apm/skills/')
    violations = []
    if len(bundles(expected)) != release_guard.CORE_BUNDLES:
        violations.append('Quellen enthalten %d statt %d Core-Bundles' % (len(bundles(expected)), release_guard.CORE_BUNDLES))
    if bundles(actual) != bundles(expected):
        violations.append('%s: Core-Bundles weichen ab: fehlend %s, zusätzlich %s' % (
            where, sorted(set(bundles(expected)) - set(bundles(actual))), sorted(set(bundles(actual)) - set(bundles(expected)))))
    missing, extra = sorted(set(expected) - set(actual)), sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
    for label, items in (('fehlt', missing), ('zusätzlich', extra), ('verändert', changed)):
        violations += ['%s: Core-Datei %s: %s' % (where, label, k) for k in items]
    return violations


def licenses(files, prefix, sources):
    violations = []
    if files.get(prefix + 'core-shared/LICENSE') != sources.get('LICENSE'):
        violations.append(prefix + 'core-shared/LICENSE fehlt oder weicht von LICENSE ab')
    if b'MIT' not in files.get(prefix + 'core-architecture/THIRD_PARTY_NOTICES.md', b''):
        violations.append(prefix + 'core-architecture/THIRD_PARTY_NOTICES.md fehlt oder ohne MIT-Hinweis')
    if files.get(prefix + BUNDLED_SKILL + '/LICENSE') != sources.get('LICENSE'):
        violations.append(prefix + BUNDLED_SKILL + '/LICENSE fehlt oder weicht von LICENSE ab')
    return violations


def inspect_archive(name, entries, sources, version):
    """Check a packed ZIP (entry name -> bytes) against the canonical sources."""
    top = '%s-%s/' % (release_guard.PACKAGE, version)
    violations = [] if name == top[:-1] + '.zip' else ['Archivname %s passt nicht zu Version %s' % (name, version)]
    outside = sorted(k for k in entries if not k.startswith(top))
    if outside:
        return {}, violations + ['Einträge außerhalb von %s: %s' % (top, outside[:5])]
    files = {k[len(top):]: v for k, v in entries.items()}
    violations += leaks(files)
    try:
        plugin = json.loads(files.get('plugin.json', b'{}'))
        bundle_files = yaml.safe_load(files.get('apm.lock.yaml', b'')).get('pack', {}).get('bundle_files', {})
    except (ValueError, yaml.YAMLError, AttributeError):
        plugin, bundle_files = {}, {}
        violations.append('plugin.json oder eingebettetes apm.lock.yaml ist nicht lesbar')
    if (plugin.get('name'), plugin.get('version')) != (release_guard.PACKAGE, version):
        violations.append('plugin.json nennt %r/%r statt %s/%s' % (plugin.get('name'), plugin.get('version'), release_guard.PACKAGE, version))
    payload = {k: v for k, v in files.items() if k != 'apm.lock.yaml'}
    if set(bundle_files) != set(payload) or any(sha256(payload[k]) != h for k, h in bundle_files.items() if k in payload):
        violations.append('eingebettetes Inventar (pack.bundle_files) passt nicht zum Archivinhalt')
    agents = {k: v for k, v in files.items() if k.startswith('agents/')}
    if agents != {'agents/' + k[len('.apm/agents/'):]: v for k, v in sources.items() if k.startswith('.apm/agents/')}:
        violations.append('Agentendefinitionen weichen von .apm/agents ab')
    core = core_files(files, 'skills/')
    violations += compare_core(sources, core, 'Archiv')
    auxiliary = auxiliary_files(files, 'skills/')
    violations += compare_auxiliary(sources, auxiliary, 'Archiv')
    known = set(agents) | {'skills/' + k for k in core} | {'skills/' + k for k in auxiliary} | {'plugin.json', 'apm.lock.yaml'}
    violations += ['unerwarteter Archivinhalt: ' + k for k in sorted(set(files) - known)]
    violations += licenses(files, 'skills/', sources)
    return {'archive_files': len(files), 'core_bundles': len(bundles(core)), 'core_files': len(core)}, violations


def inspect_installation(files, sources):
    """Check a fresh consumer tree (relative path -> bytes) after installing the ZIP."""
    prefix = '.agents/skills/'
    core = core_files(files, prefix)
    violations = compare_core(sources, core, 'Installation')
    auxiliary = auxiliary_files(files, prefix)
    violations += compare_auxiliary(sources, auxiliary, 'Installation')
    known = {prefix + k for k in core} | {prefix + k for k in auxiliary} | {'apm.lock.yaml'}
    unexpected = sorted(set(files) - known)
    violations += ['unerwartete Installationsdatei: ' + k for k in unexpected]
    count, unresolved = links(files, prefix)
    expected_skills = core_files(sources, '.apm/skills/') | auxiliary_files(sources, '.apm/skills/')
    expected_count, _ = links({'.agents/skills/' + k: v for k, v in expected_skills.items()}, prefix)
    violations += ['interner Link nicht auflösbar: ' + u for u in unresolved]
    if count != expected_count or count == 0:
        violations.append('interne Links: %d installiert, %d in den Quellen' % (count, expected_count))
    violations += licenses(files, prefix, sources)
    return {'core_bundles': len(bundles(core)), 'core_files': len(core), 'internal_links': count}, violations


def tree(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob('*')) if p.is_file()}


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def snapshot():
    """Canonical package sources from the working tree (tracked or unignored), with Git binding."""
    listed = git('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *PACKAGE_SOURCES).decode().split('\0')
    sources = {p: (ROOT / p).read_bytes() for p in sorted(filter(None, listed)) if (ROOT / p).is_file()}
    digest = sha256(json.dumps({p: sha256(v) for p, v in sources.items()}, sort_keys=True).encode())
    clean = not git('status', '--porcelain', '--untracked-files=all', '--', *PACKAGE_SOURCES).strip()
    return sources, {'source_commit': git('rev-parse', 'HEAD').decode().strip(), 'source_clean': clean, 'source_sha256': digest}


def isolated_env(scratch):
    env = {k: v for k, v in os.environ.items() if not SECRET_ENV.search(k)}
    home = scratch / 'home'
    env.update(HOME=str(home), APM_HOME=str(home / '.apm'), XDG_CONFIG_HOME=str(home / '.config'), XDG_CACHE_HOME=str(home / '.cache'),
               XDG_DATA_HOME=str(home / '.local/share'), TMPDIR=str(scratch / 'tmp'), APM_NO_SCRIPTS='1', GIT_TERMINAL_PROMPT='0')
    for directory in ('home/.apm', 'tmp'):
        (scratch / directory).mkdir(parents=True, exist_ok=True)
    return env


def apm(command, cwd, env, log):
    binary = shutil.which('apm', path=env.get('PATH'))
    if not binary:
        raise PackageError('apm nicht gefunden; zuerst mise run tools:setup ausführen')
    result = subprocess.run([binary, *command], cwd=cwd, env=env, capture_output=True, text=True, timeout=1800)
    log.append({'command': ['apm', *command], 'cwd': str(cwd), 'exit_code': result.returncode, 'output': (result.stdout + result.stderr)[-4000:]})
    if result.returncode != 0:
        raise PackageError('apm %s scheiterte (%d): %s' % (' '.join(command), result.returncode, (result.stdout + result.stderr)[-1500:]))


def verify(output=None):
    sources, binding = snapshot()
    violations = leaks(sources)
    text = lambda p: sources.get(p, b'').decode('utf-8')
    version, problems = release_guard.version_sources((ROOT / release_guard.MANIFEST).read_text(encoding='utf-8'),
                                                      (ROOT / release_guard.VERSION_FILE).read_text(encoding='utf-8'), text('apm.yml'))
    violations += problems + release_guard.apm_pin(text('apm.yml'), text('apm.lock.yaml'))
    if violations:
        raise PackageError('Quellen nicht paketfähig: ' + '; '.join(violations))
    scratch = Path(tempfile.mkdtemp(prefix='awc-package-', dir=os.environ.get('TMPDIR'))).resolve()
    if scratch.is_relative_to(ROOT):
        raise PackageError('Scratchbereich liegt im Repository: ' + str(scratch))
    env, log = isolated_env(scratch), []
    producer, consumer = scratch / 'producer', scratch / 'consumer'
    for path, data in sources.items():
        (producer / path).parent.mkdir(parents=True, exist_ok=True)
        (producer / path).write_bytes(data)
    for command in PRODUCER_COMMANDS:
        apm(command, producer, env, log)
    archives = sorted((producer / 'dist').glob('*.zip'))
    if len(archives) != 1:
        raise PackageError('apm pack erzeugte nicht genau ein ZIP: ' + str(archives))
    archive = archives[0]
    with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as handle:
        entries = {i.filename: handle.read(i) for i in handle.infolist() if not i.is_dir()}
    archive_summary, violations = inspect_archive(archive.name, entries, sources, version)
    consumer.mkdir()
    apm(('install', str(archive), '--target', 'agent-skills'), consumer, env, log)
    install_summary, problems = inspect_installation(tree(consumer), sources)
    violations += problems
    data = archive.read_bytes()
    report = {
        'schema': 'core-package-report/v1', 'verified': not violations, 'version': version, **binding,
        'archive': {'name': archive.name, 'sha256': sha256(data), 'bytes': len(data)},
        'core_bundles': install_summary['core_bundles'], 'core_files': install_summary['core_files'],
        'internal_links': install_summary['internal_links'], 'archive_files': archive_summary.get('archive_files'),
        'bundled_skills': [BUNDLED_SKILL],
        'external_dependencies': [],
        'licenses': ['core-shared/LICENSE', 'core-architecture/THIRD_PARTY_NOTICES.md', BUNDLED_SKILL + '/LICENSE'],
        'inventory': {k: sha256(v) for k, v in sorted(entries.items())},
        'violations': violations, 'commands': log, 'scratch': str(scratch),
    }
    output = Path(output or scratch / 'verified').resolve()
    if output.is_relative_to(ROOT):
        raise PackageError('Ausgabe darf nicht im Repository liegen: ' + str(output))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(archive, output / archive.name)
    (output / 'package-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return report, output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify',))
    parser.add_argument('--output', type=Path, help='Zielverzeichnis für ZIP und package-report.json (außerhalb des Repositories)')
    args = parser.parse_args(argv)
    try:
        report, output = verify(args.output)
    except (PackageError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        return 1
    for violation in report['violations']:
        print('FAIL:', violation, file=sys.stderr)
    summary = {k: report[k] for k in ('version', 'source_commit', 'source_clean', 'archive', 'core_bundles', 'core_files', 'internal_links', 'archive_files')}
    print(('PASS' if report['verified'] else 'FAIL') + ' package', json.dumps(summary, sort_keys=True), 'report=' + str(output / 'package-report.json'))
    return 0 if report['verified'] else 1


if __name__ == '__main__':
    sys.exit(main())
