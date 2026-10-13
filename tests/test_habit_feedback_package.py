"""Archive/source/license safety tests. Tar fixtures are unit tests, not CK04 host mocks."""
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('habit_package_tests',ROOT/'scripts/check_habit_feedback.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='habit-unit-',dir='/tmp/opencode')
        cls.root=Path(cls.tmp.name);env=p.isolated_env(cls.root)
        cls.expected=p.stage(p.source_files(),cls.root/'producer',env)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
    def archive(self,files=None,special=None):
        name=self.root/'fixture.tgz'
        with tarfile.open(name,'w:gz') as tar:
            for key,data in (files if files is not None else self.expected).items():
                item=tarfile.TarInfo('package/'+key);item.size=len(data);tar.addfile(item,io.BytesIO(data))
            if special:tar.addfile(special)
        return name
    def test_complete_fixture_archive(self):
        self.assertEqual(p.inspect_archive(self.archive(),self.expected),self.expected)
    def test_every_core_file_matches_canonical_allowlist(self):
        for name in p.CORE_FILES:
            self.assertEqual(self.expected['core/'+name],(ROOT/name).read_bytes())
        p.check_links(self.expected)
    def test_t04_reference_closure_is_standalone_and_byte_identical(self):
        reference='core/.apm/skills/core-devops/references/habit-feedback.md'
        for name in ('core-devops/SKILL.md','core-plan/SKILL.md','core-review/SKILL.md'):
            self.assertIn('core/.apm/skills/'+name,self.expected)
        self.assertEqual(self.expected[reference],(ROOT/'.apm/skills/core-devops/references/habit-feedback.md').read_bytes())
        links=p.LINK.findall(self.expected[reference].decode())
        self.assertGreaterEqual(len(links),6)
        for link in links:
            if ':' in link or link.startswith('#'):continue
            target=p.posixpath.normpath(p.posixpath.join(p.posixpath.dirname(reference),link.split('#')[0]))
            self.assertIn(target,self.expected)
        self.assertEqual(self.expected['VERSIONS.md'],self.expected['core/.apm/skills/core-devops/assets/opencode-habit-feedback/VERSIONS.md'])
    def test_missing_t04_transitive_source_is_not_silently_ignored(self):
        files=dict(self.expected)
        del files['core/.apm/skills/core-devops/references/habit-feedback.md']
        with self.assertRaisesRegex(p.CheckError,'unresolved'):p.check_links(files)
    def test_license_copies_exact(self):
        self.assertEqual(self.expected['LICENSE'],(ROOT/'LICENSE').read_bytes())
        self.assertEqual(self.expected['core/.apm/skills/core-shared/LICENSE'],self.expected['LICENSE'])
        self.assertIn(b'Copyright',self.expected['core/.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md'])
    def test_no_install_scripts_or_runtime_dependencies(self):
        manifest=json.loads(self.expected['package.json']);p.manifest_checks(manifest)
        self.assertEqual(manifest['scripts'],{})
        self.assertTrue(manifest['peerDependenciesMeta']['@opencode/plugin']['optional'])
        self.assertNotIn('dependencies',manifest)
    def test_real_compiled_esm_exports(self):
        self.assertEqual(json.loads(self.expected['package.json'])['exports'],{'.':'./index.js'})
        self.assertIn(b'export { default }',self.expected['index.js'])
        self.assertNotIn(b'import type',self.expected['plugin/index.js'])
        self.assertIn(b'import.meta.url',self.expected['plugin/index.js'])
    def test_missing_file_never_passes(self):
        files=dict(self.expected);del files['hook/habit_feedback_hook.py']
        with self.assertRaisesRegex(p.CheckError,'inventory/content mismatch'):p.inspect_archive(self.archive(files),self.expected)
    def test_changed_source_never_passes(self):
        files=dict(self.expected);files['guides/too-many-parameters.md']+=b'changed'
        with self.assertRaises(p.CheckError):p.inspect_archive(self.archive(files),self.expected)
    def test_unknown_file_never_passes(self):
        files=dict(self.expected);files['foreign.md']=b'x'
        with self.assertRaises(p.CheckError):p.inspect_archive(self.archive(files),self.expected)
    def test_forbidden_paths_refused(self):
        for name in ('node_modules/x/a.js','.agentic-workflow/runs/state.yaml','.npmrc','.env.local','opencode.jsonc','__pycache__/x.pyc','x.pem'):
            with self.subTest(name=name):
                files=dict(self.expected);files[name]=b'x'
                with self.assertRaises(p.CheckError):p.inspect_archive(self.archive(files),self.expected)
    def test_path_escape_and_symlink_refused(self):
        for name,kind in (('package/../outside',tarfile.REGTYPE),('outside',tarfile.REGTYPE),('package/link',tarfile.SYMTYPE)):
            item=tarfile.TarInfo(name);item.type=kind;item.linkname='/etc/passwd'
            with self.subTest(name=name),self.assertRaises(p.CheckError):p.inspect_archive(self.archive(special=item),self.expected)
    def test_duplicate_entries_refused(self):
        item=tarfile.TarInfo('package/LICENSE')
        with self.assertRaisesRegex(p.CheckError,'duplicate'):p.inspect_archive(self.archive(special=item),self.expected)
    def test_secret_shaped_content_refused(self):
        files=dict(self.expected);files['README.md']=('gh'+'p_'+'a'*36).encode()
        with self.assertRaisesRegex(p.CheckError,'secret-shaped'):p.inspect_archive(self.archive(files),self.expected)
    def test_bad_embedded_inventory_refused(self):
        files=dict(self.expected);inv=json.loads(files['inventory.json']);inv['files']={};files['inventory.json']=json.dumps(inv).encode()
        with self.assertRaisesRegex(p.CheckError,'embedded inventory'):p.inspect_archive(self.archive(files),files)
    def test_broken_transitive_link_refused(self):
        files=dict(self.expected);name='core/.apm/skills/core-architecture/references/design-baseline.md'
        files[name]+=b'\n[bad](missing.md)'
        with self.assertRaisesRegex(p.CheckError,'unresolved'):p.check_links(files)
    def test_manifest_private_version_script_and_sdk_guards(self):
        original=json.loads(self.expected['package.json'])
        for change in ({'private':True},{'version':'0.1.1'},{'scripts':{'postinstall':'download'}},{'dependencies':{'x':'1'}},
                       {'main':'plugin/index.ts'},{'peerDependencies':{'@opencode/plugin':'latest'}},{'license':'UNLICENSED'}):
            with self.subTest(change=change),self.assertRaises(p.CheckError):p.manifest_checks(dict(original,**change))

class ActualProducer(unittest.TestCase):
    def test_real_npm_pack_is_reproducible_and_complete(self):
        report=p.package()
        self.assertTrue(report['verified'])
        self.assertTrue(report['reproducible'])
        self.assertEqual(report['source_sha256'],p.digest(p.source_files()))
        self.assertGreater(len(report['files']),35)

class SourceAndEnvironmentTests(unittest.TestCase):
    def test_environment_drops_credentials_and_uses_only_scratch(self):
        with tempfile.TemporaryDirectory(prefix='habit-env-',dir='/tmp/opencode') as tmp:
            root=Path(tmp)
            with patch.dict(os.environ,{'OPENAI_API_KEY':'not-a-real-key','GITHUB_TOKEN':'not-a-real-token','npm_config_userconfig':'/home/user/.npmrc'}):
                env=p.isolated_env(root)
            self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('GITHUB_TOKEN',env)
            for key in ('HOME','TMPDIR','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','XDG_STATE_HOME','npm_config_userconfig'):
                self.assertTrue(Path(env[key]).is_relative_to(root))
    def test_symlinked_scratch_environment_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='habit-env-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);(root/'home').symlink_to(root/'outside',target_is_directory=True)
            with self.assertRaises(p.CheckError):p.isolated_env(root)
    def test_unapproved_scratch_location_refused(self):
        with self.assertRaises(p.CheckError):p.isolated_env(ROOT/'forbidden-scratch')
    def test_source_collection_exact_allowlist_not_foreign_files(self):
        original=p.source_files()
        with tempfile.TemporaryDirectory(prefix='habit-source-',dir='/tmp/opencode') as tmp:
            asset=Path(tmp)/'source'
            for name in p.ASSET_FILES:
                target=asset/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original['asset/'+name])
            (asset/'foreign-secret.env').write_text('must not be read')
            with patch.object(p,'ASSET',asset):self.assertEqual(p.source_files(),original)
    def test_source_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix='habit-link-',dir='/tmp/opencode') as tmp:
            asset=Path(tmp);(asset/'package.json').symlink_to(p.ASSET/'package.json')
            with patch.object(p,'ASSET',asset),self.assertRaises(p.CheckError):p.source_files()
    def test_source_ancestor_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix='habit-link-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);(root/'guides').symlink_to(p.ASSET/'guides',target_is_directory=True)
            with self.assertRaises(p.CheckError):p.source_bytes(root,'guides/too-many-parameters.md')
    def test_missing_setup_blocks_not_installs(self):
        with tempfile.TemporaryDirectory(prefix='habit-unprepared-',dir='/tmp/opencode') as tmp:
            with patch.object(p,'HOST_ROOT',Path(tmp)),self.assertRaisesRegex(p.CheckError,'setup missing'):p.prepared()

class DocumentationFixtures(unittest.TestCase):
    def fixture(self,root):
        ref=root/'.apm/skills/core-devops/references/habit-feedback.md';ref.parent.mkdir(parents=True)
        ref.write_text('opencode-habit-feedback@0.1.0\npython3 -B scripts/check_habit_feedback.py package\npython3 -B scripts/check_habit_feedback.py integration\nnot_scanned SDK 2.0.25\n')
        for skill in ('core-devops','core-plan','core-execute','core-refactor','core-review'):
            file=root/'.apm/skills'/skill/'SKILL.md';file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text('[habit-feedback](../core-devops/references/habit-feedback.md)')
        for name in ('README.md','DESIGN.md'):(root/name).write_text('opencode-habit-feedback')
    def test_controlled_complete_docs_fixture(self):
        with tempfile.TemporaryDirectory(prefix='habit-docs-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);self.fixture(root);self.assertTrue(p.docs(root)['manual_review_required'])
    def test_missing_t04_is_visible_failure(self):
        with tempfile.TemporaryDirectory(prefix='habit-docs-',dir='/tmp/opencode') as tmp:
            with self.assertRaisesRegex(p.CheckError,'T04'):p.docs(Path(tmp))
    def test_broken_doc_command_and_link_are_visible(self):
        with tempfile.TemporaryDirectory(prefix='habit-docs-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);self.fixture(root)
            file=root/'.apm/skills/core-plan/SKILL.md';file.write_text('[habit-feedback](missing.md)')
            with self.assertRaisesRegex(p.CheckError,'broken skill link'):p.docs(root)

class PublicGuideTrustBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('public_guide_adapter',p.ASSET/'adapter/habit_feedback_pipeline.py')
        cls.adapter=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.adapter;spec.loader.exec_module(cls.adapter)
    def fixture(self,root):
        project=root/'repo';(project/'.habit-hooks').mkdir(parents=True)
        (project/'.habit-hooks/config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\n')
        (project/'target.py').write_text('print(1)\n')
        return project
    def invoke(self,project,**kw):
        return self.adapter.run_pipeline(project,sensor_executable=p.CI/'venv/bin/habit-sensors',mapper_executable=p.CI/'venv/bin/habit-mapper',file='target.py',**kw)
    def test_public_api_refuses_repository_jinja_before_spawning(self):
        with tempfile.TemporaryDirectory(prefix='habit-guide-trust-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);project=self.fixture(root);guides=project/'.habit-hooks/generic/guides';guides.mkdir(parents=True)
            marker=root/'should-not-execute'
            (guides/'too-many-parameters.md').write_text("{{ cycler.__init__.__globals__.os.popen("+repr('touch '+str(marker))+").read() }}")
            with self.assertRaisesRegex(self.adapter.ConfigRejected,'Jinja guides refused'):self.invoke(project)
            self.assertFalse(marker.exists())
    def test_public_api_refuses_trusted_guide_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix='habit-guide-trust-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);project=self.fixture(root);trusted=root/'trusted';guides=trusted/'.habit-hooks/generic/guides';guides.mkdir(parents=True)
            (trusted/'config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\n')
            outside=project/'sentinel.md';outside.write_text('{{ forbidden }}');(guides/'too-many-parameters.md').symlink_to(outside)
            with self.assertRaisesRegex(self.adapter.ConfigRejected,'guide symlink/escape'):
                self.invoke(project,trusted_config_root=trusted,mapper_project_root=trusted)
    def test_public_api_refuses_guide_hardlink_alias(self):
        with tempfile.TemporaryDirectory(prefix='habit-guide-trust-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);project=self.fixture(root);trusted=root/'trusted';guides=trusted/'.habit-hooks/generic/guides';guides.mkdir(parents=True)
            (trusted/'config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\n')
            outside=project/'sentinel.md';outside.write_text('{{ forbidden }}');os.link(outside,guides/'too-many-parameters.md')
            with self.assertRaises(self.adapter.ConfigRejected):self.invoke(project,trusted_config_root=trusted,mapper_project_root=trusted)
    def test_repository_path_alias_is_refused_even_after_qualified_cli_directory(self):
        with tempfile.TemporaryDirectory(prefix='habit-option-path-',dir='/tmp/opencode') as tmp:
            root=Path(tmp);project=self.fixture(root);tools=project/'tools';tools.mkdir();marker=root/'never-execute'
            binary=tools/'ruff';binary.write_text('#!/bin/sh\ntouch '+str(marker)+'\necho "[]"\n');binary.chmod(0o700)
            alias=root/'external-alias-bin';alias.mkdir();(alias/'ruff').symlink_to(binary)
            env={'PATH':str(p.CI/'venv/bin')+':'+str(alias)+':/usr/bin:/bin','TMPDIR':str(root),'PYTHONDONTWRITEBYTECODE':'1'}
            with self.assertRaisesRegex(self.adapter.ConfigRejected,'inherited PATH detector alias'):
                self.invoke(project,env=env)
            self.assertFalse(marker.exists())
    def test_guide_override_must_be_one_filename_not_a_path(self):
        cfg={'plugins':['generic'],'files':['**/*.py'],'smells':{'x':{'guide':'sub/unsafe.md'}}}
        self.assertTrue(any('unsafe guide' in s for s in self.adapter.validate_config(cfg)))

class ReceiptEnvelopeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('receipt_contract_hook',p.ASSET/'hook/habit_feedback_hook.py')
        cls.hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.hook)
    def receipt(self):
        return {'status':'applied','path':'fixture/src/a.py','new_sha':'0bbb828ebcc64c6d5743d10a66cd0b11fc3b9f94','replacements':1,'mutation_receipt':'commit-287'}
    def test_exact_observed_execute_envelope_extracts_only_receipt(self):
        r=self.receipt();result={'output':{'output':json.dumps(r),'toolCalls':[],'files':[]}}
        mutated,dry,unknown=self.hook.gortex_paths_from_result(result)
        self.assertEqual(mutated,[r['path']]);self.assertEqual(dry,[]);self.assertEqual(unknown,[])
    def test_unknown_envelope_fields_do_not_enable_recursive_search(self):
        r=self.receipt()
        for output in ({'nested':r},{'output':json.dumps(r),'toolCalls':[],'files':[],'extra':1},
                       {'output':json.dumps(r),'toolCalls':'wrong','files':[]},
                       {'output':json.dumps({'nested':r}),'toolCalls':[],'files':[]}):
            with self.subTest(output=output):
                mutated,_,unknown=self.hook.gortex_paths_from_result({'output':output})
                self.assertEqual(mutated,[]);self.assertTrue(unknown)
    def test_dry_run_envelope_is_not_a_mutation(self):
        r=dict(self.receipt(),status='would_apply',dry_run=True)
        mutated,dry,unknown=self.hook.gortex_paths_from_result({'output':{'output':json.dumps(r),'toolCalls':[],'files':[]}})
        self.assertEqual(mutated,[]);self.assertEqual(dry,[r['path']]);self.assertEqual(unknown,[])

if __name__=='__main__':
    unittest.main()
