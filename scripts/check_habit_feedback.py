#!/usr/bin/env python3
"""Canonical npm producer and explicit isolated setup; checks never download tools.

package: two reproducible packs + full archive inspection.
setup: explicit offline scratch npm installation (separate from runtime checks).
integration: prepared, installed package in actual OpenCode 2.0.25 hosts.
docs: T04 links/commands, with no installation or source mutation.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / '.apm/skills/core-devops/assets/opencode-habit-feedback'
SCRATCH = Path('/tmp/opencode')
HOST_ROOT = SCRATCH / 'habit-feedback-t03-runtime'
SDK_ROOT = Path(os.environ.get('AWC_HABIT_SDK', SCRATCH / 'opencode-plugin-sdk'))
SDK = SDK_ROOT / 'runtime/node_modules'
CI = Path(os.environ.get('AWC_CI_WORKSPACE', SCRATCH / 'agentic-workflow-core-ci'))
VERSION = '0.1.0'
SDK_VERSION = '2.0.25'
ASSET_FILES = ('package.json', 'README.md', 'VERSIONS.md', 'LICENSE', 'sdk-contract.md',
               'adapter/habit_feedback_pipeline.py', 'hook/habit_feedback_hook.py',
               'plugin/index.ts', 'guides/deep-nesting.md', 'guides/duplicated-code.md',
               'guides/incomplete-run.md', 'guides/oversized-function.md',
               'guides/too-many-parameters.md', 'guides/oversized-file.md')
# Closed transitive Markdown link set from the two referenced architecture seeds.
# Exact files, never a directory glob or a second manually maintained rule source.
CORE_FILES = (
 '.apm/skills/core-architecture/PROVENANCE.md',
 '.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md',
 '.apm/skills/core-architecture/assets/software-design-principles.png',
 '.apm/skills/core-architecture/references/alternatives.md',
 '.apm/skills/core-architecture/references/boundaries-and-abstractions.md',
 '.apm/skills/core-architecture/references/design-baseline.md',
 '.apm/skills/core-architecture/references/evolution-and-clarity.md',
 '.apm/skills/core-architecture/references/interface-and-errors.md',
 '.apm/skills/core-architecture/references/principles-background.md',
 '.apm/skills/core-debug/SKILL.md',
 '.apm/skills/core-devops/SKILL.md',
 '.apm/skills/core-devops/assets/opencode-habit-feedback/VERSIONS.md',
 '.apm/skills/core-devops/references/checks-and-hooks.md',
 '.apm/skills/core-devops/references/ci-and-releases.md',
 '.apm/skills/core-devops/references/development-automation.md',
 '.apm/skills/core-devops/references/failure-recovery.md',
 '.apm/skills/core-devops/references/git-operations.md',
 '.apm/skills/core-devops/references/habit-feedback.md',
 '.apm/skills/core-devops/references/tooling-profiles.md',
 '.apm/skills/core-execute/SKILL.md',
 '.apm/skills/core-plan/SKILL.md',
 '.apm/skills/core-review/SKILL.md',
 '.apm/skills/core-milestone/references/goal-format.md',
 '.apm/skills/core-milestone/references/milestone-format.md',
 '.apm/skills/core-milestone/references/milestone-index-format.md',
 '.apm/skills/core-refactor/SKILL.md', '.apm/skills/core-research/SKILL.md',
 '.apm/skills/core-shared/LICENSE',
 '.apm/skills/core-shared/assets/handoff.md',
 '.apm/skills/core-shared/assets/review-finding.yaml',
 '.apm/skills/core-shared/assets/workflow-catalog.yaml',
 '.apm/skills/core-shared/references/artifact-contract.md',
 '.apm/skills/core-shared/references/tool-routing.md',
 '.apm/skills/core-shared/references/verification.md',
 '.apm/skills/core-shared/references/workflow-contract.md')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
FORBIDDEN = {'.git', '.agentic-workflow', 'node_modules', '__pycache__', '.env',
             '.npmrc', 'opencode.json', 'opencode.jsonc', '.direnv', 'apm_modules'}
SECRET = re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}')

class CheckError(RuntimeError):
    pass

def require(ok, reason):
    if not ok:
        raise CheckError(reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_bytes(root, name):
    path = root / name
    require(root.is_dir() and not root.is_symlink(), 'source root missing/symlinked')
    require(path.resolve().is_relative_to(root.resolve()), 'source escaped canonical root: ' + name)
    for component in (path, *path.parents):
        require(not component.is_symlink(), 'source ancestor symlink: ' + name)
    require(path.is_file(), 'missing canonical source: ' + name)
    return path.read_bytes()

def source_files():
    files = {'producer/scripts/check_habit_feedback.py': source_bytes(ROOT, 'scripts/check_habit_feedback.py')}
    for name in ASSET_FILES:
        files['asset/' + name] = source_bytes(ASSET, name)
    for name in CORE_FILES:
        files[name] = source_bytes(ROOT, name)
    return files

def digest(files):
    return sha(json.dumps({k: sha(v) for k, v in sorted(files.items())}, sort_keys=True).encode())

def isolated_env(root):
    require(root.resolve().is_relative_to(SCRATCH) and not root.resolve().is_relative_to(ROOT), 'scratch root refused')
    require(not any(component.is_symlink() for component in (root,*root.parents)), 'scratch ancestor symlink refused')
    root.mkdir(parents=True,mode=0o700,exist_ok=True)
    st=root.stat()
    require(st.st_uid==os.getuid() and not st.st_mode & 0o022, 'scratch ownership/mode refused')
    env = {'PATH': str(CI / 'venv/bin') + ':' + str(CI / 'node/bin') + ':' + str(SDK_ROOT / 'bin') + ':/usr/bin:/bin',
           'HOME': str(root / 'home'), 'TMPDIR': str(root / 'tmp'),
           'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_CACHE_HOME': str(root / 'cache'),
           'XDG_DATA_HOME': str(root / 'data'), 'XDG_STATE_HOME': str(root / 'state'),
           'RUFF_CACHE_DIR': str(root / 'cache/ruff'), 'PYTHONDONTWRITEBYTECODE': '1',
           'npm_config_userconfig': str(root / 'empty.npmrc'),
           'npm_config_globalconfig': str(root / 'empty-global.npmrc'),
           'npm_config_cache': str(root / 'npm-cache'), 'npm_config_ignore_scripts': 'true',
           'npm_config_audit': 'false', 'npm_config_fund': 'false', 'npm_config_update_notifier': 'false'}
    for key in ('HOME','TMPDIR','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','XDG_STATE_HOME'):
        directory=Path(env[key])
        require(not any(component.is_symlink() for component in (directory,*directory.parents)), 'scratch environment symlink refused')
        directory.mkdir(parents=True,mode=0o700,exist_ok=True)
    for name in ('empty.npmrc','empty-global.npmrc'):
        config=root/name
        require(not config.is_symlink(), 'scratch npm config symlink refused')
        if config.exists():
            st=config.stat()
            require(st.st_uid==os.getuid() and st.st_nlink==1 and config.is_file(), 'scratch npm config ownership/link refused')
        config.write_text('')
    return env

def run(command, cwd, env, timeout=120):
    p = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    require(p.returncode == 0, 'command failed: %r; exit %s; %s' % (command,p.returncode,(p.stdout+p.stderr)[-3000:]))
    return p.stdout

def check_links(files):
    for name,data in files.items():
        if not name.startswith('core/') or not name.endswith('.md'):
            continue
        for link in LINK.findall(data.decode()):
            if ':' in link or link.startswith('#'):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name),link.split('#')[0]))
            require(target in files, 'unresolved Core snapshot link: ' + name + ' -> ' + link)

def manifest_checks(m):
    require((m.get('name'),m.get('version')) == ('opencode-habit-feedback',VERSION), 'package identity mismatch')
    require(m.get('private') is not True and m.get('license') == 'MIT', 'not public/MIT')
    require(m.get('type') == 'module' and m.get('main') == 'index.js' and m.get('exports',{}).get('.') == './index.js', 'ESM exports mismatch')
    require(not m.get('scripts') and not m.get('dependencies'), 'unexpected package scripts/dependencies')
    require(m.get('peerDependencies') == {'@opencode/plugin':SDK_VERSION}, 'SDK target mismatch')

def stage(sources, directory, env):
    directory.mkdir()
    for name in ASSET_FILES:
        if name == 'plugin/index.ts':
            continue
        p = directory / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(sources['asset/' + name])
    for name in CORE_FILES:
        p = directory / 'core' / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(sources[name])
    require(sources['asset/LICENSE'] == source_bytes(ROOT, 'LICENSE'), 'MIT license differs from repository')
    ts = SDK / 'typescript/lib/typescript.js'
    require(ts.is_file(), 'prepared TypeScript 5.9.3 missing; no automatic installation')
    script = "const fs=require('node:fs'); const ts=require(process.argv[1]); if(ts.version!=='5.9.3')throw Error('compiler pin'); const s=fs.readFileSync(process.argv[2],'utf8'); fs.writeFileSync(process.argv[3],ts.transpileModule(s,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText)"
    (directory / 'plugin').mkdir()
    run(['node','-e',script,str(ts),str(ASSET/'plugin/index.ts'),str(directory/'plugin/index.js')],directory,env)
    (directory / 'index.js').write_text('export { default } from "./plugin/index.js";\n')
    files = {p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    manifest_checks(json.loads(files['package.json']))
    check_links(files)
    inventory = {'schema':'habit-package-inventory/v1','source_sha256':digest(sources),
                 'compiler':'typescript@5.9.3','sdk_target':SDK_VERSION,
                 'sources':{k:sha(v) for k,v in sorted(sources.items())},
                 'files':{k:sha(v) for k,v in sorted(files.items())}}
    (directory/'inventory.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    files['inventory.json'] = (directory/'inventory.json').read_bytes()
    return files

def inspect_archive(path, expected):
    actual = {}
    with tarfile.open(path,'r:gz') as tar:
        for item in tar.getmembers():
            require(item.isfile() and item.name.startswith('package/'), 'non-file/outside archive entry: '+item.name)
            name = item.name[len('package/'):]
            parts = PurePosixPath(name).parts
            require('..' not in parts and not (FORBIDDEN & set(parts)) and not name.startswith('/'), 'forbidden archive path: '+name)
            require(not any(p.startswith('.env') or p.endswith(('.pyc','.key','.pem')) for p in parts), 'sensitive/cache path: '+name)
            require(name not in actual, 'duplicate archive entry: '+name)
            with tar.extractfile(item) as handle:
                data = handle.read()
            require(not SECRET.search(data), 'secret-shaped package content: '+name)
            actual[name] = data
    require(actual == expected, 'archive inventory/content mismatch; missing=%s extra=%s changed=%s' %
            (sorted(set(expected)-set(actual)),sorted(set(actual)-set(expected)),sorted(k for k in actual.keys()&expected.keys() if actual[k]!=expected[k])))
    manifest_checks(json.loads(actual['package.json']))
    check_links(actual)
    inventory = json.loads(actual['inventory.json'])
    require(inventory['files'] == {k:sha(v) for k,v in sorted(actual.items()) if k!='inventory.json'}, 'embedded inventory mismatch')
    require(b'Copyright (c) 2026 Melivo' in actual['LICENSE'] and b'MIT' in actual['core/.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md'], 'licenses missing')
    return actual

def package():
    sources = source_files()
    root = Path(tempfile.mkdtemp(prefix='habit-package-',dir=SCRATCH))
    env = isolated_env(root)
    archives = []
    for i in range(2):
        directory = root / ('producer-%s'%i)
        expected = stage(sources,directory,env)
        result = json.loads(run(['npm','pack','--json','--ignore-scripts','--offline'],directory,env))
        require(len(result)==1, 'npm pack did not emit exactly one archive')
        archive = directory/result[0]['filename']
        inspect_archive(archive,expected)
        archives.append(archive)
    require(archives[0].read_bytes()==archives[1].read_bytes(), 'npm pack is not reproducible')
    require(source_files()==sources, 'canonical sources changed during package check')
    report = {'schema':'habit-package-report/v1','verified':True,'source_sha256':digest(sources),
              'archive':str(archives[0]),'sha256':sha(archives[0].read_bytes()),'files':{k:sha(v) for k,v in sorted(expected.items())},
              'core_allowlist':list(CORE_FILES),'reproducible':True}
    (root/'package-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def setup():
    report = package()
    require(not HOST_ROOT.is_symlink(), 'setup root symlink refused')
    HOST_ROOT.mkdir(exist_ok=True)
    env = isolated_env(HOST_ROOT)
    consumer = HOST_ROOT / ('consumer-'+report['sha256'][:16])
    require(not consumer.is_symlink() and consumer.resolve().is_relative_to(HOST_ROOT.resolve()), 'consumer symlink/outside refused')
    consumer.mkdir(mode=0o700,exist_ok=True)
    (consumer/'package.json').write_text('{"private":true,"type":"module"}\n')
    run(['npm','install','--offline','--ignore-scripts','--legacy-peer-deps','--no-audit','--no-fund',report['archive']],consumer,env)
    installed = consumer/'node_modules/opencode-habit-feedback'
    for name,hash_value in report['files'].items():
        require(sha((installed/name).read_bytes())==hash_value, 'scratch installation differs: '+name)
    run(['node','--input-type=module','-e','import p from "opencode-habit-feedback"; if(p.id!=="opencode-habit-feedback"||typeof p.setup!=="function")throw Error("bad ESM entry")'],consumer,env)
    receipt = dict(report,installed=str(installed))
    (HOST_ROOT/'setup.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def prepared():
    p = HOST_ROOT/'setup.json'
    require(p.is_file(), 'isolated setup missing; run explicit setup subcommand first')
    report = json.loads(p.read_text())
    require(report['source_sha256']==digest(source_files()), 'prepared package is stale; repeat explicit setup')
    installed = Path(report['installed'])
    require(installed.resolve().is_relative_to(HOST_ROOT), 'prepared installation outside testhost')
    for name,hash_value in report['files'].items():
        require(sha((installed/name).read_bytes())==hash_value, 'prepared package changed: '+name)
    return report

def docs(root=ROOT):
    ref = root/'.apm/skills/core-devops/references/habit-feedback.md'
    require(ref.is_file(), 'T04 usage reference missing')
    text = ref.read_text()
    for literal in ('opencode-habit-feedback@0.1.0','python3 -B scripts/check_habit_feedback.py package',
                    'python3 -B scripts/check_habit_feedback.py integration','not_scanned','2.0.25'):
        require(literal in text, 'T04 documented command/contract missing: '+literal)
    for skill in ('core-devops','core-plan','core-execute','core-refactor','core-review'):
        file=root/'.apm/skills'/skill/'SKILL.md'; body=file.read_text()
        require('habit-feedback' in body, 'T04 conditional integration link missing: '+skill)
        for link in LINK.findall(body):
            if ':' in link or link.startswith('#'):continue
            require((file.parent/link.split('#')[0]).exists(), 'broken skill link: '+link)
    for file in ('README.md','DESIGN.md'):
        require('opencode-habit-feedback' in (root/file).read_text(), 'T04 overview missing: '+file)
    return {'checked':'T04 commands and conditional references','manual_review_required':True}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('package','setup','integration','docs'))
    args=parser.parse_args(argv)
    try:
        if args.command=='integration':
            report=prepared()
            spec=importlib.util.spec_from_file_location('habit_integration',ROOT/'tests/test_habit_feedback_integration.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            result=module.verify_runtime(report)
        else:
            result={'package':package,'setup':setup,'docs':docs}[args.command]()
        print('PASS '+args.command+' '+json.dumps(result,sort_keys=True))
        return 0
    except (RuntimeError,OSError,ValueError,subprocess.SubprocessError,AssertionError) as exc:
        print('FAIL '+args.command+': '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':
    sys.exit(main())
