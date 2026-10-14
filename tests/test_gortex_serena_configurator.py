"""Migration contract plus the unchanged configurator's original safety suite."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'.apm/skills/gortex-serena-configurator'
# Snapshot at the old source's exact migration revision, not its older import inventory.
SOURCE_HASHES = {
    'SKILL.md': '4959b985902a785b55e27afc05defca08d9edb1dadb6175d8db6c7010ec8766a',
    'scripts/serena_safety.py': 'fdc269704b2913441fcfeacf7abef5c9960124a553a61d67823f1e43c64e67b5',
    'scripts/test_serena_safety.py': 'a580f15ad982629d544fe20bad4b46cb036b6643d52bd3628ed094b50bfa2a05',
    'scripts/requirements.txt': '3eb0bcd11c478e00ecb6dca8668b5ed32dc5aa273cb278411c1d0d90e6a72584',
    'references/configuration-precedence.md': 'fea904ad710c696ca621836cdbf4f89e76446910762b426665e195a8a48fae22',
    'agents/openai.yaml': '98162f5d955ffa2ff2cb02d7a58eaf4b988686548a036c8f77972fb03cdb8dda',
}


class MigrationBoundary(unittest.TestCase):
    def test_original_instructions_resources_and_scripts_preserved(self):
        for name, expected in SOURCE_HASHES.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((SKILL/name).read_bytes()).hexdigest(), expected)

    def test_license_and_explicit_owner_grant_travel_with_skill(self):
        self.assertEqual((SKILL/'LICENSE').read_bytes(), (ROOT/'LICENSE').read_bytes())
        provenance = (SKILL/'PROVENANCE.md').read_text()
        self.assertIn('0c7838d8072dfd70c702cf2d04734a7241550c3e', provenance)
        self.assertIn('explicitly confirmed', provenance)
        self.assertIn('Current package license: MIT', provenance)

    def test_package_has_no_external_private_dependency(self):
        manifest = yaml.safe_load((ROOT/'apm.yml').read_text())
        lock = yaml.safe_load((ROOT/'apm.lock.yaml').read_text())
        self.assertEqual(manifest['dependencies'], {'apm': []})
        self.assertEqual(lock['dependencies'], [])
        self.assertTrue((SKILL/'SKILL.md').is_file())


def load_tests(loader, suite, pattern):
    """Run original skill-local tests in normal CI discovery, not an optional skip."""
    scripts = SKILL/'scripts'
    old_path = sys.path[:]
    previous = sys.modules.get('serena_safety')
    try:
        sys.path.insert(0, str(scripts))
        spec = importlib.util.spec_from_file_location('serena_safety', scripts/'serena_safety.py')
        safety = importlib.util.module_from_spec(spec)
        sys.modules['serena_safety'] = safety
        spec.loader.exec_module(safety)
        spec = importlib.util.spec_from_file_location('core_configurator_original_tests', scripts/'test_serena_safety.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = loader.loadTestsFromModule(module)
        if original.countTestCases() == 0:
            raise AssertionError('migrated safety test suite is empty')
        suite.addTests(original)
    finally:
        sys.path[:] = old_path
        if previous is None:
            sys.modules.pop('serena_safety', None)
        else:
            sys.modules['serena_safety'] = previous
    return suite


if __name__ == '__main__':
    unittest.main()
