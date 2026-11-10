"""Offline checks of the opt-in image learning probe; no live model/authentication calls."""
import base64
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).absolute().parents[1]
PROBE = ROOT / '.apm/skills/core-typesafe/examples/images/image_probe.py'
spec = importlib.util.spec_from_file_location('image_probe', PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class NoSecrets(dict):
    def get(self, key, default=None):
        if key == 'TYPESAFE_API_KEY':
            raise AssertionError('offline code looked up a secret')
        return super().get(key, default)

    def __getitem__(self, key):
        if key == 'TYPESAFE_API_KEY':
            raise AssertionError('offline code looked up a secret')
        return super().__getitem__(key)


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


class ImageProbeTests(unittest.TestCase):
    def setUp(self):
        self.net = patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))
        self.net.start()
        self.addCleanup(self.net.stop)
        self.prepared = probe._load_corpus(probe.BASE)
        self.case, self.payload, self.body, self.binding = self.prepared[0]
        self.response = json.loads(probe._synthetic_response(self.payload))

    def cli(self, args=(), transport=None, key='unit-test-token'):
        output = io.StringIO()
        env = NoSecrets() if key is None else {'TYPESAFE_API_KEY': key}
        with patch.object(probe.os, 'environ', env), redirect_stdout(output):
            code = probe.main(list(args), transport=transport)
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_import_default_offline_are_keyless_and_netless(self):
        with patch.object(probe.os, 'environ', NoSecrets()):
            fresh = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fresh)
        for args in ([], ['--offline'], ['--offline', '--model', probe.MODEL]):
            code, records = self.cli(args, key=None)
            self.assertEqual(code, 0)
            self.assertEqual(len(records), 25)
            self.assertTrue(all(r['model_answer'] is False for r in records[:-1]))
            self.assertEqual(records[-1]['attempted'], 0)

    def test_all_24_requests_bound_and_labels_local(self):
        self.assertEqual(len(self.prepared), 24)
        for i, (case, payload, body, binding) in enumerate(self.prepared, 1):
            self.assertEqual(payload['state'], {k: case[k] for k in ('asset_reference', 'target_description', 'comparison_input')})
            asset = f'image-{i:03d}'
            self.assertEqual(payload['assets'], {asset: {'type': 'image', 'part': asset}})
            wire_json = probe._json(payload).decode()
            for forbidden in ('reference', 'dom_evidence', 'case_kind', 'sha256', 'split'):
                # asset_reference is the one permitted occurrence of 'reference'.
                self.assertNotIn('"' + forbidden + '"', wire_json)
            self.assertNotIn(case['id'], wire_json)
            self.assertNotIn(case['path'].encode(), body)
            self.assertIn(('filename="' + asset + '.png"').encode(), body)
            self.assertEqual(binding['manifest_sha256'], probe.MANIFEST_SHA256)
            self.assertEqual(binding['multipart_sha256'], probe._sha(body))
            for q in case['questions']:
                actual = payload['questions'][q['id']]
                self.assertTrue(actual['instructions'].startswith(q['question']))
                self.assertIn('state.asset_reference', actual['instructions'])
                if q['type'] == 'score':
                    self.assertEqual(actual['criteria'], [r['description'] for r in q['rubric']])

    def test_multipart_first_json_exactly_one_png_and_limits(self):
        from email.parser import BytesParser
        from email.policy import default
        header = ('Content-Type: multipart/form-data; boundary=' + probe.BOUNDARY + '\r\nMIME-Version: 1.0\r\n\r\n').encode()
        for case, payload, body, _ in self.prepared:
            parts = list(BytesParser(policy=default).parsebytes(header + body).iter_parts())
            self.assertEqual(len(parts), 2)
            self.assertEqual(parts[0].get_param('name', header='content-disposition'), 'request')
            self.assertEqual(parts[0].get_content_type(), 'application/json')
            self.assertEqual(json.loads(parts[0].get_payload(decode=True)), payload)
            self.assertEqual(parts[1].get_content_type(), 'image/png')
            image = parts[1].get_payload(decode=True)
            self.assertEqual(probe._sha(image), case['sha256'])
            self.assertEqual(probe._png(image), case['dimensions'])
            self.assertLess(len(body), probe.MAX_BODY_BYTES)
        with patch.object(probe, 'MAX_BODY_BYTES', 10):
            with self.assertRaises(probe.ProbeError):
                probe._request(self.case, b'png')
        bad = copy.deepcopy(self.case)
        for asset in ('request', 'image-001\r\nx', 'image-../'):
            bad['asset_reference'] = asset
            with self.assertRaises(probe.ProbeError):
                probe._request(bad, b'png')
        with self.assertRaises(probe.ProbeError):
            probe._request(self.case, probe.BOUNDARY.encode())

    def test_safe_files_parent_symlink_leaf_fifo_directory_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'regular').write_bytes(b'ok')
            self.assertEqual(probe._read_regular(root / 'regular', 2), b'ok')
            (root / 'link').symlink_to(root / 'regular')
            (root / 'parent').symlink_to(root, target_is_directory=True)
            os.mkfifo(root / 'fifo')
            for path in (root / 'link', root / 'parent/regular', root / 'fifo', root):
                with self.assertRaises(probe.ProbeError):
                    probe._read_regular(path, 10)
            with self.assertRaises(probe.ProbeError):
                probe._read_regular(root / 'regular', 1)
            with self.assertRaises(probe.ProbeError):
                probe._read_regular(root / '../anything', 10)

    def test_corpus_data_boundary_no_changed_manifest_source_or_image(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'images'
            shutil.copytree(probe.BASE, target)
            original = (target / 'cases.json').read_bytes()
            (target / 'cases.json').write_bytes(original + b' ')
            with self.assertRaisesRegex(probe.ProbeError, 'manifest_hash'):
                probe._load_corpus(target)
            (target / 'cases.json').write_bytes(original)
            (target / 'fixtures.html').write_bytes(b'private replacement')
            with self.assertRaisesRegex(probe.ProbeError, 'source_hash'):
                probe._load_corpus(target)
            shutil.copyfile(probe.BASE / 'fixtures.html', target / 'fixtures.html')
            image = target / self.case['path']
            image.write_bytes(b'private image')
            with self.assertRaisesRegex(probe.ProbeError, 'image_hash'):
                probe._load_corpus(target)
            with patch.object(probe, 'BASE', target):
                code, records = self.cli(['--send-corpus', '--model', probe.MODEL], key=None)
            self.assertEqual(code, 2)
            self.assertEqual(records[0]['attempted'], 0)

    def test_png_truncation_crc_animation_dimensions_raster(self):
        original = (probe.BASE / self.case['path']).read_bytes()
        bad_crc = bytearray(original)
        bad_crc[20] ^= 1
        header = struct.pack('>IIBBBBB', 1280, 800, 8, 2, 0, 0, 0)
        for raw in (b'JPEG', original[:8], original[:-1], bytes(bad_crc),
                    original[:33] + png_chunk(b'acTL', struct.pack('>II', 2, 0)) + original[33:],
                    original[:8] + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 279, 800, 8, 2, 0, 0, 0)) + original[33:],
                    original[:8] + png_chunk(b'IHDR', header) + png_chunk(b'IDAT', zlib.compress(b'bad raster')) + png_chunk(b'IEND', b'')):
            with self.subTest(length=len(raw)), self.assertRaises(probe.ProbeError):
                probe._png(raw)

    def test_transform_and_reference_geometry_rejected_before_send(self):
        for field, value in (('crop_css_px', [1, 0, 1280, 800]), ('scale_xy', [2, 1]),
                             ('padding_px', [1, 0, 0, 0]), ('orientation', 'rotated')):
            case = copy.deepcopy(self.case)
            case['transform'][field] = value
            with self.assertRaises(probe.ProbeError):
                probe._validate_transform(case)
        case = copy.deepcopy(self.case)
        case['reference']['box_normalized']['left'] += .01
        with self.assertRaises(probe.ProbeError):
            probe._validate_transform(case)

    def validate(self, response):
        return probe._validate_response(probe._json(response), self.payload)

    def test_strict_ids_types_model_usage_json(self):
        self.assertEqual(self.validate(self.response), self.response)
        mutations = []
        for field, value in (('model', 'jev-latest'), ('usage', {}), ('answers', [])):
            bad = copy.deepcopy(self.response)
            bad[field] = value
            mutations.append(bad)
        for value in (True, -1, 1.5, '1'):
            bad = copy.deepcopy(self.response)
            bad['usage']['input_tokens'] = value
            mutations.append(bad)
        bad = copy.deepcopy(self.response)
        bad['answers']['extra'] = bad['answers']['presence']
        mutations.append(bad)
        bad = copy.deepcopy(self.response)
        bad['answers']['presence']['type'] = 'choice'
        mutations.append(bad)
        for bad in mutations:
            with self.assertRaises(probe.ProbeError):
                self.validate(bad)
        for raw in (b'not json', b'{"a":1,"a":2}', b'{"value":NaN}', b'\xff'):
            with self.assertRaises(probe.ProbeError):
                probe._validate_response(raw, self.payload)

    def test_noul_finite_probability(self):
        for value in (True, -0.1, 1.1, '0.5', None):
            bad = copy.deepcopy(self.response)
            bad['answers']['presence']['noul'] = value
            with self.assertRaises(probe.ProbeError):
                self.validate(bad)
        for value in (float('nan'), float('inf'), -float('inf')):
            self.assertFalse(probe._number(value, 0, 1))

    def test_score_distribution_legend_levels_mean(self):
        for field, value in (('score', 4), ('score', -1), ('score', True),
                             ('score', '2'), ('score', None), ('confidence', True),
                             ('legend', {'0': 'changed'}), ('probabilities', {'0': 1}),
                             ('probabilities', {'0': .2, '1': .2, '2': .2, '3': .2}),
                             ('probabilities', {'0': -.1, '1': .3, '2': .4, '3': .4})):
            bad = copy.deepcopy(self.response)
            bad['answers']['score'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(probe.ProbeError):
                self.validate(bad)
        # Equal means do not imply equal distributions: both originals remain different.
        first = copy.deepcopy(self.response)
        second = copy.deepcopy(self.response)
        first['answers']['score']['probabilities'] = {'0': .5, '1': 0, '2': 0, '3': .5}
        second['answers']['score']['probabilities'] = {'0': 0, '1': .5, '2': .5, '3': 0}
        self.assertEqual(self.validate(first)['answers']['score']['score'], 1.5)
        self.assertNotEqual(self.validate(first), self.validate(second))

    def test_box_edges_and_no_automatic_presence_threshold(self):
        for box in ({'left': 0, 'right': 1, 'top': 0},
                    {'left': -1, 'right': 1, 'top': 0, 'bottom': 1},
                    {'left': .8, 'right': .1, 'top': 0, 'bottom': 1},
                    {'left': 0, 'right': 1, 'top': True, 'bottom': 1}):
            bad = copy.deepcopy(self.response)
            bad['answers']['box']['box'] = box
            with self.assertRaises(probe.ProbeError):
                self.validate(bad)
        for probability in (0, .5, .99, 1):
            response = copy.deepcopy(self.response)
            response['answers']['presence']['noul'] = probability
            for case, payload, _, _ in self.prepared:
                response['answers']['score'] = json.loads(probe._synthetic_response(payload))['answers']['score']
                local = probe._local_comparison(case, response)
                self.assertFalse(local['box_usable'])
                self.assertEqual(local['presence_review'], 'unresolved_no_automatic_threshold')
                self.assertEqual(local['reference_visibility'], case['reference']['visibility'])
        exact = copy.deepcopy(self.response)
        exact['answers']['box']['box'] = self.case['reference']['box_normalized']
        local = probe._local_comparison(self.case, exact)
        self.assertAlmostEqual(local['box_reference_iou_diagnostic_only'], 1)
        self.assertAlmostEqual(local['box_candidate_source_css_px']['left'], 154)

    def test_document_comparison_is_local_not_ocr_or_score(self):
        for index, expected in ((12, True), (14, False), (15, None), (16, True), (17, True)):
            case, payload, _, _ = self.prepared[index]
            local = probe._local_comparison(case, json.loads(probe._synthetic_response(payload)))
            self.assertIs(local['source_text_matches_input'], expected)
            self.assertEqual(local['visible_text_comparison_available'], case['reference']['presence'] is True)

    def fake_success(self, body, key):
        item = next(item for item in self.prepared if item[2] == body)
        return 200, probe._synthetic_response(item[1])

    def test_send_opt_in_limit_streamed_originals_and_request_count(self):
        sent = []
        def fake(body, key):
            sent.append(body)
            return self.fake_success(body, key)
        code, records = self.cli(['--send-corpus', '--model', probe.MODEL, '--max-requests', '2'], fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(sent), 2)
        self.assertEqual([r['event'] for r in records], ['attempt_started', 'case_completed'] * 2 + ['summary'])
        for record in records[1:4:2]:
            raw = base64.b64decode(record['raw_response_base64'])
            self.assertEqual(json.loads(raw), record['response'])
            self.assertEqual(probe._sha(raw), record['response_sha256'])
            self.assertIn('started_at', record)
            self.assertTrue(record['request_sent'])
        self.assertEqual(records[-1]['status'], 'bounded_partial')
        code, records = self.cli(['--send-corpus', '--model', probe.MODEL], fake)
        self.assertEqual(code, 0)
        self.assertEqual(records[-1]['attempted'], 24)
        for args in (['--send-corpus'], ['--send-corpus', '--model', 'jev-latest'],
                     ['--max-requests', '25'], ['--max-requests', '0'], ['--send-corpus', '--offline']):
            with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), patch('sys.stderr', io.StringIO()):
                self.cli(args, fake)

    def test_missing_key_blocks_before_first_transport(self):
        fake = unittest.mock.Mock(side_effect=AssertionError('must not send'))
        for key in ('', 'line\nbreak', 'ü'):
            code, records = self.cli(['--send-corpus', '--model', probe.MODEL], fake, key=key)
            self.assertEqual(code, 2)
            self.assertFalse(records[0]['request_sent'])
        fake.assert_not_called()

    def test_first_technical_error_stops_no_retry_preserves_previous_raw(self):
        for status in (400, 413, 429, 401, 403, 302, 500):
            calls = []
            def fake(body, key):
                calls.append(body)
                return self.fake_success(body, key) if len(calls) == 1 else (status, b'{"error":"synthetic"}')
            code, records = self.cli(['--send-corpus', '--model', probe.MODEL], fake)
            self.assertEqual(code, 1)
            self.assertEqual(len(calls), 2)
            self.assertIn('raw_response_base64', records[1])
            self.assertEqual(records[-2]['http_status'], status)
            self.assertEqual(records[-1]['attempted'], 2)
            self.assertEqual(records[-1]['completed'], 1)
            self.assertEqual(base64.b64decode(records[-2]['raw_response_base64']), b'{"error":"synthetic"}')

    def test_timeout_malformed_schema_failure_stops_and_no_secret_in_errors(self):
        for failure in ('timeout', 'exception', 'forged_code', 'malformed', 'score', 'box', 'too_large', 'echo', 'escaped_echo'):
            calls = []
            def fake(body, key):
                calls.append(1)
                if failure == 'timeout':
                    raise TimeoutError(key)
                if failure == 'exception':
                    raise RuntimeError(key)
                if failure == 'forged_code':
                    raise probe.ProbeError(key)
                if failure == 'escaped_echo':
                    return 401, ('{"error":"' + key.replace('-', '\\u002d') + '"}').encode()
                if failure == 'malformed':
                    return 200, b'{bad'
                if failure == 'too_large':
                    return 200, b'x' * (probe.MAX_RESPONSE_BYTES + 1)
                if failure == 'echo':
                    return 401, key.encode()
                response = copy.deepcopy(self.response)
                response['answers'][failure]['confidence'] = -1
                return 200, probe._json(response)
            code, records = self.cli(['--send-corpus', '--model', probe.MODEL], fake)
            self.assertEqual(code, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(records[-1]['attempted'], 1)
            self.assertNotIn('unit-test-token', json.dumps(records))
            self.assertNotIn('response', records[-2])
            if failure == 'too_large':
                self.assertTrue(records[-2]['response_truncated'])
                self.assertIn('response_prefix', records[-2])
            if failure in ('echo', 'escaped_echo'):
                self.assertEqual(records[-2]['raw_response_withheld'], 'credential_echo_safety_boundary')

    def prior_fixture(self, directory):
        """Reconstruct exact original stdout; no ignored run artifacts required by tests."""
        raw = base64.b64decode(
            'eyJtb2RlbCI6Impldi0xLjE0LjAiLCJhbnN3ZXJzIjp7ImJveCI6eyJ0eXBlIjoiYm94IiwiYm94Ijp7InRvcCI6MC40NCwiYm90dG9tIjowLjUyLCJsZWZ0IjowLjEyLCJyaWdodCI6MC4yN30sImNvbmZpZGVuY2UiOjAuOTV9LCJwcmVzZW5jZSI6eyJ0eXBlIjoibm91bCIsIm5vdWwiOjAuOTl9LCJzY29yZSI6eyJ0eXBlIjoic2NvcmUiLCJzY29yZSI6Mi45NywiY29uZmlkZW5jZSI6MC45OCwibGVnZW5kIjp7IjAiOiJOaWNodCBzaWNodGJhciBvZGVyIHZlcmRlY2t0LiIsIjEiOiJTaWNodGJhciwgYWJlciBrYXVtIHZvbiBOZWJlbmFrdGlvbmVuIHVudGVyc2NoZWlkYmFyLiIsIjIiOiJFcmtlbm5iYXIsIGFiZXIgbWl0IMOkaG5saWNoIGF1ZmbDpGxsaWdlciBrb25rdXJyaWVyZW5kZXIgQWt0aW9uLiIsIjMiOiJFaW5kZXV0aWcgaGVydm9yZ2Vob2JlbmUgSGF1cHRha3Rpb24uIn0sInByb2JhYmlsaXRpZXMiOnsiMCI6MC4wLCIxIjowLjAsIjIiOjAuMDIsIjMiOjAuOTh9fX0sInVzYWdlIjp7ImlucHV0X3Rva2VucyI6MzE5Niwib3V0cHV0X3Rva2VucyI6NDl9fQ==')
        start = {'event': 'attempt_started', 'case_id': self.case['id'], 'attempted': 1,
                 'binding': self.binding, 'requested_model': probe.MODEL,
                 'started_at': '2026-11-10T03:59:06.869939+00:00', 'request_sent': True}
        failed = dict(start, event='case_failed', error='score_value', http_status=200,
                      raw_response_base64=base64.b64encode(raw).decode(),
                      response_bytes=len(raw), response_sha256=probe._sha(raw),
                      finished_at='2026-11-10T03:59:07.202947+00:00',
                      duration_seconds=0.3330180369957816)
        summary = {'event': 'summary', 'mode': 'send', 'attempted': 1, 'completed': 0,
                   'status': 'failed', 'stop': 'first_technical_error_no_retry', 'unsent': 23}
        stdout = b''.join(probe._json(r) + b'\n' for r in (start, failed, summary))
        self.assertEqual(probe._sha(raw), probe.PRIOR_RAW_SHA256)
        self.assertEqual(len(raw), 550)
        self.assertEqual(probe._sha(stdout), probe.PRIOR_STDOUT_SHA256)
        attempt = {'schema': 'task-result/v1', 'task_id': 'T04', 'attempt': 1,
                   'status': 'partial', 'changed_paths': [], 'checks': [{
                       'id': 'CK05', 'status': 'fail', 'exit_code': 1, 'cwd': '.',
                       'command': ['python3', '-B', '.apm/skills/core-typesafe/examples/images/image_probe.py',
                                   '--send-corpus', '--model', probe.MODEL, '--max-requests', '24'],
                       'evidence': stdout.decode()}]}
        path = Path(directory) / 'attempt-01.yaml'
        path.write_bytes(probe._json(attempt))
        return path, attempt, raw

    def test_original_550_replay_keyless_netless_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _, raw = self.prior_fixture(directory)
            before = path.read_bytes()
            with patch.object(probe, 'PRIOR_PATH', path), patch.object(probe, 'PRIOR_SHA256', probe._sha(before)):
                code, records = self.cli(['--replay-prior', '--prior-attempt', str(path)], key=None)
            self.assertEqual(code, 0)
            self.assertEqual(path.read_bytes(), before)
            record = records[0]
            self.assertEqual(record['budget_spent'], 1)
            self.assertFalse(record['new_model_call'])
            self.assertEqual(record['historical_check_status'], 'fail')
            self.assertEqual(record['historical_status'], 'partial')
            self.assertEqual(base64.b64decode(record['original_events'][1]['raw_response_base64']), raw)
            diagnostic = record['score_consistency']
            self.assertEqual(diagnostic['raw_score'], 2.97)
            self.assertEqual(diagnostic['reconstructed_mean'], 2.98)
            self.assertAlmostEqual(diagnostic['difference'], -.01)
            self.assertEqual(diagnostic['probabilities'], {'0': 0, '1': 0, '2': .02, '3': .98})
            self.assertIn('unresolved', diagnostic['review'])
            self.assertEqual(record['response']['usage'], {'input_tokens': 3196, 'output_tokens': 49})

    def test_continuation_23_offset_budget_no_first_resend_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _, _ = self.prior_fixture(directory)
            args = ['--send-corpus', '--continue-after-first', '--prior-attempt', str(path),
                    '--model', probe.MODEL, '--max-requests', '23']
            with patch.object(probe, 'PRIOR_PATH', path), patch.object(probe, 'PRIOR_SHA256', probe._sha(path.read_bytes())):
                for fail in (False, True):
                    sent = []
                    def fake(body, key):
                        sent.append(body)
                        return (500, b'failure') if fail else self.fake_success(body, key)
                    code, records = self.cli(args, fake)
                    self.assertEqual(code, int(fail))
                    self.assertEqual(sent, [p[2] for p in self.prepared[1:2 if fail else 24]])
                    self.assertNotIn(self.body, sent)
                    self.assertEqual(len(set(sent)), len(sent))
                    self.assertEqual(records[-1]['budget_spent'], 2 if fail else 24)
                    self.assertEqual(records[-1]['unsent'], 22 if fail else 0)
                    for r in records:
                        if r['event'] == 'case_completed':
                            self.assertEqual(probe._sha(base64.b64decode(r['raw_response_base64'])), r['response_sha256'])
                            self.assertIn('score_consistency', r)
                code, records = self.cli(args[:-1] + ['2'], self.fake_success)
                self.assertEqual(code, 0)
                self.assertEqual(records[-1]['budget_spent'], 3)
                for invalid in (args[:-1] + ['24'], ['--continue-after-first'],
                                ['--replay-prior'], ['--prior-attempt', str(path)]):
                    with self.assertRaises(SystemExit), patch('sys.stderr', io.StringIO()):
                        self.cli(invalid, key=None)

    def test_prior_mismatches_stop_before_key_or_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            path, original, _ = self.prior_fixture(directory)
            args = ['--send-corpus', '--continue-after-first', '--prior-attempt', str(path), '--model', probe.MODEL]
            fake = unittest.mock.Mock(side_effect=AssertionError('must not send'))
            for field, value in (('task_id', 'T05'), ('attempt', 2), ('status', 'completed'), ('checks', [])):
                changed = copy.deepcopy(original)
                changed[field] = value
                path.write_bytes(probe._json(changed))
                with patch.object(probe, 'PRIOR_PATH', path), patch.object(probe, 'PRIOR_SHA256', probe._sha(path.read_bytes())):
                    code, records = self.cli(args, fake, key=None)
                self.assertEqual(code, 2)
                self.assertEqual(records[-1]['error'], 'prior_validation_failed')
            for mutation in ('hash', 'path', 'binding', 'state', 'ambiguous', 'raw'):
                changed = copy.deepcopy(original)
                if mutation in ('binding', 'state', 'ambiguous', 'raw'):
                    events = [json.loads(line) for line in changed['checks'][0]['evidence'].splitlines()]
                    if mutation == 'binding':
                        events[0]['binding']['image_sha256'] = '0' * 64
                    elif mutation == 'state':
                        events[2]['unsent'] = 22
                    elif mutation == 'raw':
                        events[1]['raw_response_base64'] = 'eA=='
                    else:
                        events.append(events[0])
                    changed['checks'][0]['evidence'] = ''.join(probe._json(e).decode() + '\n' for e in events)
                path.write_bytes(probe._json(changed))
                with patch.object(probe, 'PRIOR_PATH', path if mutation != 'path' else path.parent / 'other'),                      patch.object(probe, 'PRIOR_SHA256', '0' * 64 if mutation == 'hash' else probe._sha(path.read_bytes())):
                    code, records = self.cli(args, fake, key=None)
                self.assertEqual(code, 2)
                self.assertFalse(records[-1]['request_sent'])
            fake.assert_not_called()

    def test_score_mismatch_is_diagnostic_other_guards_retained(self):
        response = copy.deepcopy(self.response)
        response['answers']['score']['score'] = 2
        self.assertEqual(self.validate(response), response)
        diagnostic = probe._score_consistency(response)
        self.assertEqual(diagnostic['difference'], .5)
        for field in ('score', 'confidence'):
            for value in (-1, 4, True, None, '0.5'):
                bad = copy.deepcopy(response)
                bad['answers']['score'][field] = value
                with self.assertRaises(probe.ProbeError):
                    self.validate(bad)
        for value in (float('nan'), float('inf'), -float('inf')):
            for field in ('score', 'confidence', 'probabilities'):
                bad = copy.deepcopy(response)
                bad['answers']['score'][field] = {'0': value, '1': 0, '2': 0, '3': 1} if field == 'probabilities' else value
                with self.assertRaises(probe.ProbeError):
                    probe._validate_response(json.dumps(bad).encode(), self.payload)

    def test_https_fixed_tls_header_single_post_and_no_redirect(self):
        class Response:
            status = 302
            def read(self, limit):
                self.limit = limit
                return b'no redirect'
        connection = unittest.mock.Mock()
        connection.getresponse.return_value = Response()
        with patch.object(probe.http.client, 'HTTPSConnection', return_value=connection) as factory:
            status, raw = probe._https_exchange(self.body, 'unit-test-token')
        self.assertEqual(status, 302)
        self.assertEqual(raw, b'no redirect')
        self.assertEqual(factory.call_args.args, ('api.typesafe.ai',))
        context = factory.call_args.kwargs['context']
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, probe.ssl.CERT_REQUIRED)
        self.assertEqual(factory.call_args.kwargs['timeout'], probe.IO_TIMEOUT_SECONDS)
        self.assertEqual(connection.request.call_count, 1)
        self.assertEqual(connection.request.call_args.args, ('POST', '/v1/systemone'))
        self.assertEqual(connection.request.call_args.kwargs['headers']['TypeSafe-Danger-Zone-Images'], 'true')
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
