"""Regression: fresh CI runners must explicitly prepare the Habit test tools."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import bootstrap_ci as ci
import bootstrap_habit_ci as habit


class HabitCISetup(unittest.TestCase):
    def test_exact_pins_and_transitive_integrities(self):
        lock = habit.check_pins()
        self.assertEqual(lock['packages']['']['dependencies'], habit.NPM_PINS)
        self.assertEqual(lock['packages']['node_modules/@opencode/plugin']['integrity'],
                         'sha512-CdGaTps7W1QlMsgisPAQMVLV8g5eedV02I21blf6jf73VKoBivUIrKnXyXsjl68ePDsAZG6DX7oXieC8tdPWKw==')
        self.assertEqual(habit.PYTHON_PINS['habit-hooks'], '1.5.0')
        self.assertEqual(habit.PYTHON_PINS['ruff'], '0.14.5')

    def test_unpinned_sdk_and_missing_integrity_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'package-lock.json'
            original = json.loads(habit.LOCK.read_text())
            for change in ('version', 'integrity', 'registry'):
                data = json.loads(json.dumps(original))
                entry = data['packages']['node_modules/@opencode/plugin']
                if change == 'version': entry['version'] = '2.0.26'
                elif change == 'integrity': entry.pop('integrity')
                else: entry['resolved'] = 'http://example.invalid/plugin.tgz'
                path.write_text(json.dumps(data))
                with patch.object(habit, 'LOCK', path), self.assertRaises(ci.ToolchainError):
                    habit.check_pins()

    def test_missing_setup_fails_without_download_or_install(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(habit.ci, 'run') as run, \
             patch.object(habit.urllib.request, 'urlopen') as download:
            with self.assertRaisesRegex(ci.ToolchainError, 'tools:setup'):
                habit.verify(Path(tmp), {})
            run.assert_not_called()
            download.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_setup_creates_missing_scratch_parent_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'opencode'
            with patch.object(habit, 'Path', return_value=root):
                self.assertEqual(habit.scratch_parent(), root)
            self.assertTrue(root.is_dir())
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            link = Path(tmp)/'alias'
            link.symlink_to(root)
            with patch.object(habit, 'Path', return_value=link), self.assertRaises(ci.ToolchainError):
                habit.scratch_parent()

    def test_ci_paths_follow_selected_workspace_not_local_host(self):
        ws = Path('/tmp/fresh-github-runner/workspace')
        with patch.dict(os.environ, AWC_CI_WORKSPACE='/wrong', AWC_HABIT_SDK='/wrong'):
            env = ci.isolated_env(ws)
        self.assertEqual(env['AWC_CI_WORKSPACE'], str(ws))
        self.assertEqual(env['AWC_HABIT_SDK'], str(ws/'habit-sdk'))
        self.assertIn(str(ws/'habit-sdk/bin'), env['PATH'].split(os.pathsep))
        with patch.dict(os.environ, env):
            spec = importlib.util.spec_from_file_location('habit_fresh_paths', ROOT/'scripts/check_habit_feedback.py')
            package = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(package)
        self.assertEqual(package.CI, ws)
        self.assertEqual(package.SDK, ws/'habit-sdk/runtime/node_modules')

    def test_qualified_host_is_selected_from_isolated_child_path(self):
        source = (ROOT/'tests/test_habit_feedback_integration.py').read_text()
        self.assertIn("str(package.SDK_ROOT/'bin/opencode') if os.environ.get('AWC_HABIT_SDK')", source)
        for name in ('test_habit_feedback_hook.py', 'test_habit_feedback_pipeline.py'):
            text = (ROOT/'tests'/name).read_text()
            self.assertIn("os.environ.get('AWC_CI_WORKSPACE'", text)
            self.assertEqual(text.count('/tmp/opencode/agentic-workflow-core-ci'), 1)


if __name__ == '__main__':
    unittest.main()
