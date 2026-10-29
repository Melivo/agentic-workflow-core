"""Regression tests for the managed AGENTS.md block reconcile helper.

Covers T01 of plan .agentic-workflow/plans/project-guidance-reconcile.md:
the four selections, exact confirmation binding and drift, missing and
broken markers, idempotent second run, byte-preserved outside areas and
the absence of any provider/config side effects.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / '.apm/skills/core-init-project/scripts/reconcile_blocks.py'
SERENA_SAFETY = ROOT / '.apm/skills/gortex-serena-configurator/scripts/serena_safety.py'

CORE_NAME = 'CORE-INIT-PROJECT'
SERENA_NAME = 'SERENA-GORTEX-PROJECT'


def run_helper(*argv):
    completed = subprocess.run(
        [sys.executable, '-B', str(HELPER), *[str(arg) for arg in argv]],
        capture_output=True,
        text=True,
        encoding='utf-8',
        check=False,
    )
    return completed.returncode, completed.stdout


def core_template():
    return (
        '<!-- CORE-INIT-PROJECT:START -->\n'
        '## Core-Routing und Übergaben\n'
        '\n'
        '- Einstieg: core-brainstorm, core-plan, core-execute.\n'
        '<!-- CORE-INIT-PROJECT:END -->'
    )


def serena_template():
    return (
        '<!-- SERENA-GORTEX-PROJECT:START -->\n'
        '## Serena/Gortex Code Intelligence Playbook\n'
        '\n'
        '- Use Gortex when healthy and tracked.\n'
        '<!-- SERENA-GORTEX-PROJECT:END -->'
    )


def write(path, text):
    path.write_text(text, encoding='utf-8', newline='')


class ReconcileFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.target = self.project / 'AGENTS.md'
        self.core_tpl = self.project / 'core.tpl'
        self.serena_tpl = self.project / 'serena.tpl'
        write(self.core_tpl, core_template())
        write(self.serena_tpl, serena_template())
        # Neighbour files that must stay byte-identical (no side effects).
        self.neighbours = {}
        for name in ('.gitignore', 'settings.json'):
            path = self.project / name
            write(path, 'keep me\n')
            self.neighbours[path] = path.read_bytes()

    def blocks(self):
        return [
            '--block', CORE_NAME + '=' + str(self.core_tpl),
            '--block', SERENA_NAME + '=' + str(self.serena_tpl),
        ]

    def preview(self, selection):
        code, out = run_helper(
            'preview', '--target', self.target, *self.blocks(), '--select', selection
        )
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def apply(self, selection, token):
        return run_helper(
            'apply', '--target', self.target, *self.blocks(),
            '--select', selection, '--confirm', token,
        )

    def assert_neighbours_unchanged(self):
        for path, payload in self.neighbours.items():
            self.assertEqual(path.read_bytes(), payload)
        self.assertFalse((self.project / '.serena').exists())


class FourSelections(ReconcileFixture):
    def initial_target(self):
        write(
            self.target,
            '# Projekt\n\nManueller Text.\n\n'
            '<!-- ' + CORE_NAME + ':START -->\nalt\n<!-- ' + CORE_NAME + ':END -->\n'
            'Zwischentext.\n',
        )

    def status_map(self, report):
        return {entry['name']: entry['status'] for entry in report['blocks']}

    def test_selection_core_only(self):
        self.initial_target()
        report = self.preview(CORE_NAME)
        self.assertEqual(self.status_map(report), {CORE_NAME: 'drift', SERENA_NAME: 'missing'})
        code, _ = self.apply(CORE_NAME, report['token'])
        self.assertEqual(code, 0)
        text = self.target.read_text(encoding='utf-8')
        self.assertIn(core_template(), text)
        self.assertNotIn(SERENA_NAME + ':START', text)
        self.assertEqual(text[:text.index('<!-- ' + CORE_NAME)], '# Projekt\n\nManueller Text.\n\n')
        self.assertIn('Zwischentext.', text)
        self.assert_neighbours_unchanged()

    def test_selection_serena_only(self):
        self.initial_target()
        report = self.preview(SERENA_NAME)
        code, _ = self.apply(SERENA_NAME, report['token'])
        self.assertEqual(code, 0)
        text = self.target.read_text(encoding='utf-8')
        self.assertIn('<!-- ' + CORE_NAME + ':START -->\nalt\n', text)
        self.assertIn(serena_template(), text)
        self.assert_neighbours_unchanged()

    def test_selection_both(self):
        self.initial_target()
        report = self.preview(CORE_NAME + ',' + SERENA_NAME)
        code, _ = self.apply(CORE_NAME + ',' + SERENA_NAME, report['token'])
        self.assertEqual(code, 0)
        text = self.target.read_text(encoding='utf-8')
        self.assertIn(core_template(), text)
        self.assertIn(serena_template(), text)
        self.assertIn('Manueller Text.', text)
        self.assertIn('Zwischentext.', text)
        self.assert_neighbours_unchanged()

    def test_selection_none_writes_nothing(self):
        self.initial_target()
        before = self.target.read_bytes()
        report = self.preview('none')
        self.assertEqual(report['selected'], [])
        self.assertTrue(all(not entry['selected'] for entry in report['blocks']))
        code, _ = self.apply('none', report['token'])
        self.assertEqual(code, 0)
        self.assertEqual(self.target.read_bytes(), before)
        self.assert_neighbours_unchanged()


class ConfirmationAndDrift(ReconcileFixture):
    def setUp(self):
        super().setUp()
        write(self.target, '# Projekt\n\n<!-- ' + CORE_NAME + ':START -->\nalt\n<!-- ' + CORE_NAME + ':END -->\n')

    def test_exact_token_writes(self):
        report = self.preview(CORE_NAME)
        code, out = self.apply(CORE_NAME, report['token'])
        self.assertEqual(code, 0, out)
        self.assertIn(core_template(), self.target.read_text(encoding='utf-8'))

    def test_wrong_token_refuses_without_write(self):
        before = self.target.read_bytes()
        code, out = self.apply(CORE_NAME, '0' * 64)
        self.assertEqual(code, 3, out)
        self.assertIn('confirmation-mismatch', out)
        self.assertEqual(self.target.read_bytes(), before)

    def test_drifted_target_invalidates_token(self):
        report = self.preview(CORE_NAME)
        with self.target.open('a', encoding='utf-8') as handle:
            handle.write('Zwischenzeitliche Fremdänderung.\n')
        before = self.target.read_bytes()
        code, out = self.apply(CORE_NAME, report['token'])
        self.assertEqual(code, 3, out)
        self.assertEqual(self.target.read_bytes(), before)

    def test_changed_selection_invalidates_token(self):
        report = self.preview(CORE_NAME)
        code, out = self.apply(CORE_NAME + ',' + SERENA_NAME, report['token'])
        self.assertEqual(code, 3, out)
        self.assertNotIn(core_template(), self.target.read_text(encoding='utf-8'))


class MissingAndBrokenMarkers(ReconcileFixture):
    def test_missing_blocks_are_proposed_for_creation(self):
        write(self.target, '# Nur manuell.\n')
        report = self.preview(CORE_NAME + ',' + SERENA_NAME)
        statuses = {entry['name']: entry['status'] for entry in report['blocks']}
        self.assertEqual(statuses, {CORE_NAME: 'missing', SERENA_NAME: 'missing'})
        self.assertTrue(all(report['diffs'][name] for name in statuses))
        self.assertEqual(report['changed_planned'], True)
        code, _ = self.apply(CORE_NAME + ',' + SERENA_NAME, report['token'])
        self.assertEqual(code, 0)
        text = self.target.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('# Nur manuell.\n\n'))
        self.assertIn(core_template(), text)
        self.assertIn(serena_template(), text)

    def broken_cases(self):
        return {
            'duplicate start': '# P\n\n<!-- {n}:START -->\na\n<!-- {n}:START -->\nb\n<!-- {n}:END -->\n',
            'unpaired end': '# P\n\n<!-- {n}:END -->\n',
            'unpaired start': '# P\n\n<!-- {n}:START -->\n',
            'reversed order': '# P\n\n<!-- {n}:END -->\nx\n<!-- {n}:START -->\n',
        }

    def test_broken_markers_reported_and_blocked(self):
        for label, pattern in self.broken_cases().items():
            with self.subTest(case=label):
                write(self.target, pattern.format(n=CORE_NAME))
                before = self.target.read_bytes()
                code, out = run_helper('preview', '--target', self.target, *self.blocks(), '--select', CORE_NAME)
                self.assertEqual(code, 2, out)
                code, out = self.apply(CORE_NAME + ',' + SERENA_NAME, 'bad-token')
                self.assertEqual(code, 2, out)
                self.assertIn('blocked-markers', out)
                self.assertEqual(self.target.read_bytes(), before)

    def test_nested_foreign_marker_blocks(self):
        write(
            self.target,
            '# P\n<!-- ' + CORE_NAME + ':START -->\na\n<!-- ' + SERENA_NAME + ':START -->\n'
            'b\n<!-- ' + SERENA_NAME + ':END -->\n<!-- ' + CORE_NAME + ':END -->\n',
        )
        before = self.target.read_bytes()
        code, out = run_helper(
            'preview', '--target', self.target, *self.blocks(),
            '--select', CORE_NAME,
        )
        self.assertEqual(code, 2, out)
        self.assertIn('nested managed markers', out)
        self.assertEqual(self.target.read_bytes(), before)

    def test_template_validation_rejects_foreign_markers(self):
        bad = self.project / 'bad.tpl'
        write(bad, '<!-- ' + CORE_NAME + ':START -->\n<!-- ' + SERENA_NAME + ':START -->\nx\n')
        code, out = run_helper(
            'preview', '--target', self.target,
            '--block', CORE_NAME + '=' + str(bad), '--select', CORE_NAME,
        )
        self.assertEqual(code, 2, out)
        self.assertIn('must contain its marker pair exactly once', out)


class Idempotency(ReconcileFixture):
    def test_second_run_is_diff_free(self):
        write(self.target, '# Projekt\n\n<!-- ' + CORE_NAME + ':START -->\nalt\n<!-- ' + CORE_NAME + ':END -->\n')
        first = self.preview(CORE_NAME + ',' + SERENA_NAME)
        self.assertTrue(first['changed_planned'])
        code, _ = self.apply(CORE_NAME + ',' + SERENA_NAME, first['token'])
        self.assertEqual(code, 0)
        written = self.target.read_bytes()
        second = self.preview(CORE_NAME + ',' + SERENA_NAME)
        self.assertFalse(second['changed_planned'])
        self.assertTrue(all(entry['status'] == 'current' for entry in second['blocks']))
        self.assertEqual({name: diff for name, diff in second['diffs'].items()}, {CORE_NAME: '', SERENA_NAME: ''})
        code, _ = self.apply(CORE_NAME + ',' + SERENA_NAME, second['token'])
        self.assertEqual(code, 0)
        self.assertEqual(self.target.read_bytes(), written)

    def test_crlf_line_endings_preserved(self):
        write(self.target, '# Projekt\r\n\r\n<!-- ' + CORE_NAME + ':START -->\r\nalt\r\n<!-- ' + CORE_NAME + ':END -->\r\n')
        report = self.preview(CORE_NAME)
        code, _ = self.apply(CORE_NAME, report['token'])
        self.assertEqual(code, 0)
        text = self.target.read_text(encoding='utf-8', newline='')
        self.assertIn('\r\n', text)
        self.assertNotIn('alt', text)


class AdditionalSafety(ReconcileFixture):
    def test_facts_inside_core_block_survive_reviewed_candidate(self):
        facts = '## Projektbasis\n- Python 3.13; mise; Checks: mise run check\n'
        old = core_template().replace('## Core-Routing und Übergaben', facts + '## Core-Routing und Übergaben').replace('Einstieg:', 'Alt:')
        candidate = old.replace('Alt:', 'Einstieg:')
        write(self.target, 'Manual\n' + old + '\nTAIL')
        write(self.core_tpl, candidate)
        first = self.preview(CORE_NAME)
        code, out = self.apply(CORE_NAME, first['token'])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.target.read_bytes(), ('Manual\n' + candidate + '\nTAIL').encode())
        self.assertFalse(self.preview(CORE_NAME)['changed_planned'])

    def test_diff_displays_terminal_newline_difference(self):
        write(self.target, '# Manual without newline')
        report = self.preview(CORE_NAME)
        diff = report['diffs'][CORE_NAME]
        self.assertIn('\n\\ No newline at end of file\n', diff)
        self.assertIn('+# Manual without newline', diff)

    def test_template_surrounding_evidence_drift_invalidates_token(self):
        write(self.target, '# Manual\n')
        first = self.preview(CORE_NAME)
        write(self.core_tpl, core_template() + '\n')
        code, out = self.apply(CORE_NAME, first['token'])
        self.assertEqual(code, 3, out)


    def test_two_existing_blocks_different_lengths_and_separate_diffs(self):
        prefix = '# Facts: Python 3.13; mise; check\r\nManual\n'
        middle = '\r\nMIDDLE\n'
        suffix = '\r\nTAIL without newline'
        old_core = '<!-- ' + CORE_NAME + ':START -->\nold\n<!-- ' + CORE_NAME + ':END -->'
        old_serena = '<!-- ' + SERENA_NAME + ':START -->\nvery old\n<!-- ' + SERENA_NAME + ':END -->'
        write(self.target, prefix + old_core + middle + old_serena + suffix)
        selection = CORE_NAME + ',' + SERENA_NAME
        first = self.preview(selection)
        self.assertIn('-old', first['diffs'][CORE_NAME])
        self.assertNotIn('-very old', first['diffs'][CORE_NAME])
        self.assertIn('-very old', first['diffs'][SERENA_NAME])
        code, out = self.apply(selection, first['token'])
        self.assertEqual(code, 0, out)
        expected = prefix + core_template() + middle + serena_template() + suffix
        self.assertEqual(self.target.read_bytes(), expected.encode())
        self.assertFalse(self.preview(selection)['changed_planned'])

    def test_template_drift_and_other_target_invalidate_confirmation(self):
        write(self.target, '# Project\n')
        first = self.preview(CORE_NAME)
        write(self.core_tpl, core_template().replace('Einstieg', 'Anderer Einstieg'))
        code, out = self.apply(CORE_NAME, first['token'])
        self.assertEqual(code, 3, out)
        write(self.core_tpl, core_template())
        with tempfile.TemporaryDirectory() as other:
            target = Path(other) / 'AGENTS.md'
            write(target, '# Project\n')
            code, out = run_helper('apply', '--target', target, *self.blocks(),
                                   '--select', CORE_NAME, '--confirm', first['token'])
            self.assertEqual(code, 3, out)

    def test_damaged_marker_not_treated_as_missing(self):
        for line in ('<!-- CORE-INIT-PROJECT:STAR -->',
                     '<!-- CORE-INIT-PROJECT:START --',
                     '<!-- CORE-INIT-PROJECT:END --->'):
            with self.subTest(line=line):
                write(self.target, '# Facts\n' + line + '\n')
                code, out = run_helper('preview', '--target', self.target, *self.blocks())
                self.assertEqual(code, 2, out)
                self.assertIn('blocked-markers', out)

    def test_symlink_target_refused(self):
        actual = self.project / 'actual.md'
        write(actual, 'untouched')
        self.target.symlink_to(actual)
        code, out = run_helper('preview', '--target', self.target, *self.blocks())
        self.assertEqual(code, 2, out)
        self.assertEqual(actual.read_text(), 'untouched')


class TemplateOwnership(unittest.TestCase):
    """The Serena/Gortex template stays with the configurator, unduplicated."""

    def test_extract_template_resolves_owner_constant_without_import(self):
        # No duplication: the template is resolved from the owning module by
        # AST, without executing it (ruamel.yaml is intentionally not needed).
        code, out = run_helper(
            'extract-template', '--source', SERENA_SAFETY, '--name', 'PROJECT_PLAYBOOK'
        )
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith('<!-- SERENA-GORTEX-PROJECT:START -->'))
        self.assertTrue(out.rstrip().endswith('<!-- SERENA-GORTEX-PROJECT:END -->'))
        source = SERENA_SAFETY.read_text(encoding='utf-8')
        self.assertIn('PROJECT_PLAYBOOK = f', source)
        for marker_line in (
            '{PROJECT_START}\n## Serena/Gortex Repository Code Intelligence',
            '{PROJECT_END}\n',
        ):
            self.assertIn(marker_line, source)
        # The resolved constant must equal the f-string body with the owner's
        # marker constants substituted, without embedding a second copy here.
        start = '<!-- SERENA-GORTEX-PROJECT:START -->'
        end = '<!-- SERENA-GORTEX-PROJECT:END -->'
        self.assertEqual(out.count(start), 1)
        self.assertEqual(out.count(end), 1)
        self.assertLess(out.find(start), out.find(end))
        self.assertIn('Use one provider per operation', out)

    def test_extract_template_rejects_unresolvable_names(self):
        code, out = run_helper(
            'extract-template', '--source', SERENA_SAFETY, '--name', 'DOES_NOT_EXIST'
        )
        self.assertEqual(code, 2, out)
        self.assertIn('No module-level assignment', out)

    def test_real_repo_target_parses_without_write(self):
        target = ROOT / 'AGENTS.md'
        before = target.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / 'core.tpl'
            routing = (ROOT / '.apm/skills/core-init-project/assets/core-routing.md').read_text(encoding='utf-8')
            write(template, '<!-- ' + CORE_NAME + ':START -->\n' + routing + '\n<!-- ' + CORE_NAME + ':END -->')
            code, out = run_helper(
                'preview', '--target', target, '--block', CORE_NAME + '=' + str(template),
                '--select', 'none',
            )
        self.assertEqual(code, 0, out)
        report = json.loads(out)
        status = {entry['name']: entry['status'] for entry in report['blocks']}
        self.assertEqual(status[CORE_NAME], 'drift')
        self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

