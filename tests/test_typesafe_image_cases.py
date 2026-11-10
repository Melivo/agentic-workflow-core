"""Offline integrity and local reference checks; no model or network requests."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zlib

EXAMPLE = Path(__file__).resolve().parents[1] / '.apm/skills/core-typesafe/examples/images'
CORPUS_SHA256 = 'e2d58f33f34a5d0bead9e851a39aac0ec0edf278d08fad21c44404b1b76f14e5'
QUESTIONS_SHA256 = '27ad64391eae330c08a14851d4f82a280a4bf9ac0b482b6ea4c57749f3946eb3'


def png_dimensions(data):
    """Validate static Chromium PNG chunks, CRCs and decoded raster size."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('PNG signature')
    offset, chunks, compressed = 8, [], bytearray()
    width = height = channels = None
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError('Truncated chunk')
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 8 + size
        if end + 4 > len(data):
            raise ValueError('Truncated data')
        payload = data[offset + 8:end]
        crc = struct.unpack('>I', data[end:end + 4])[0]
        if zlib.crc32(kind + payload) != crc:
            raise ValueError('CRC mismatch')
        chunks.append(kind)
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if depth != 8 or color not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError('Unsupported screenshot encoding')
            channels = 3 if color == 2 else 4
        if kind == b'IDAT':
            compressed.extend(payload)
        offset = end + 4
        if kind == b'IEND':
            break
    if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or offset != len(data):
        raise ValueError('Incomplete PNG')
    if any(k in chunks for k in (b'acTL', b'fcTL', b'fdAT', b'eXIf')):
        raise ValueError('Animated or EXIF-oriented asset')
    if len(zlib.decompress(compressed)) != height * (1 + width * channels):
        raise ValueError('Raster length')
    return [width, height]


class ImageCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((EXAMPLE / 'cases.json').read_text(encoding='utf-8'))
        cls.cases = cls.manifest['cases']

    def test_family_split_kind_variant_and_disjoint_images(self):
        self.assertEqual(len(self.cases), 24)
        self.assertEqual(len({c['id'] for c in self.cases}), 24)
        self.assertEqual([c['asset_reference'] for c in self.cases], [f'image-{i:03d}' for i in range(1, 25)])
        for family, variants in [('ui', {'desktop', 'mobile'}), ('document', {'a', 'b'})]:
            for split in ('learn', 'test'):
                selected = [c for c in self.cases if (c['family'], c['split']) == (family, split)]
                self.assertEqual(len(selected), 6)
                for kind in ('positive', 'negative', 'unclear'):
                    self.assertEqual({c['variant'] for c in selected if c['case_kind'] == kind}, variants)
        learning = {c['sha256'] for c in self.cases if c['split'] == 'learn'}
        testing = {c['sha256'] for c in self.cases if c['split'] == 'test'}
        self.assertTrue(learning.isdisjoint(testing))
        self.assertEqual(len(learning | testing), 24)

    def test_png_dimensions_hashes_limits_and_exact_inventory(self):
        paths = set()
        for c in self.cases:
            with self.subTest(case=c['id']):
                path = EXAMPLE / c['path']
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.parent, EXAMPLE / 'fixtures')
                self.assertEqual(path.name, c['id'] + '.png')
                paths.add(path)
                data = path.read_bytes()
                self.assertEqual(c['format'], 'png')
                self.assertEqual(len(data), c['byte_count'])
                self.assertLessEqual(len(data), 16 * 1024 * 1024)
                self.assertEqual(hashlib.sha256(data).hexdigest(), c['sha256'])
                self.assertEqual(png_dimensions(data), c['dimensions'])
                self.assertTrue(all(280 <= side <= 1568 for side in c['dimensions']))
                self.assertLessEqual(c['dimensions'][0] * c['dimensions'][1] * 4, 32 * 1024 * 1024)
        self.assertEqual(paths, set((EXAMPLE / 'fixtures').glob('*.png')))

    def test_source_and_pre_model_hash_bindings(self):
        m = self.manifest
        self.assertEqual(m['schema'], 'image-cases/v1')
        self.assertTrue(m['synthetic'] and m['pre_model'])
        self.assertEqual(m['model_requests'], 0)
        self.assertEqual(m['manual_inspection']['count'], 24)
        self.assertEqual(m['manual_inspection']['model_requests_before_inspection'], 0)
        source = (EXAMPLE / m['source']['path']).read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), m['source']['sha256'])
        self.assertEqual(len(source), m['source']['byte_count'])
        corpus = ''.join(c['id'] + ' ' + c['sha256'] + '\n' for c in self.cases).encode()
        self.assertEqual(hashlib.sha256(corpus).hexdigest(), CORPUS_SHA256)
        self.assertEqual(m['corpus_sha256'], CORPUS_SHA256)
        questions = [{'id': c['id'], 'version': c['question_version'], 'questions': c['questions']} for c in self.cases]
        encoded = json.dumps(questions, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), QUESTIONS_SHA256)
        self.assertEqual(m['questions_sha256'], QUESTIONS_SHA256)

    def test_questions_rubrics_and_truth_separation(self):
        self.assertEqual(self.manifest['render']['model_state_allowlist'], ['asset_reference', 'target_description', 'comparison_input'])
        for c in self.cases:
            with self.subTest(case=c['id']):
                self.assertEqual(c['question_version'], 'm08-images-v1')
                questions = c['questions']
                self.assertEqual([q['type'] for q in questions], ['noul', 'score', 'box'])
                self.assertEqual([q['id'] for q in questions], ['presence', 'score', 'box'])
                rubric = questions[1]['rubric']
                self.assertEqual([r['value'] for r in rubric], list(range(4 if c['family'] == 'ui' else 3)))
                self.assertTrue(all(len(r['description']) > 20 for r in rubric))
                self.assertTrue(all(len(q['question']) > 30 for q in questions))
                self.assertIn('Lokalisiere ausschließlich', questions[2]['question'])
                for label in ('positive', 'negative', 'unclear'):
                    self.assertNotIn(label, c['dom_evidence']['body_text'])
                self.assertNotIn('reference', json.dumps(questions))
                if c['family'] == 'document':
                    self.assertIn(c['comparison_input']['value'], questions[1]['question'])

    def test_crop_mapping_and_known_browser_geometry(self):
        known = {
            ('ui', 'learn', 'desktop'): [154, 355, 171.8125, 62],
            ('ui', 'test', 'desktop'): [229, 355, 171.8125, 62],
            ('ui', 'learn', 'mobile'): [40, 379, 161.8125, 62],
            ('ui', 'test', 'mobile'): [40, 379, 161.8125, 62],
            ('document', 'learn', 'a'): [434, 333, 152.546875, 42],
            ('document', 'learn', 'b'): [87, 333, 152.546875, 42],
            ('document', 'test', 'a'): [87, 512, 152.546875, 42],
            ('document', 'test', 'b'): [87, 344, 152.546875, 42],
        }
        for c in self.cases:
            with self.subTest(case=c['id']):
                w, h = c['dimensions']
                t, d, r = c['transform'], c['dom_evidence'], c['reference']
                self.assertEqual(t['source_viewport'], [w, h])
                self.assertEqual(t['crop_css_px'], [0, 0, w, h])
                self.assertEqual(t['scale_xy'], [1, 1])
                self.assertEqual(t['padding_px'], [0, 0, 0, 0])
                self.assertEqual(d['viewport'], [w, h])
                self.assertEqual(d['dpr'], 1)
                self.assertFalse(d['overflow'])
                self.assertEqual(d['hero_buttons'], 0)
                if r['dom_present']:
                    x, y, width, height = known[(c['family'], c['split'], c['variant'])]
                    self.assertEqual(r['box_source_css_px'], [x, y, width, height])
                    self.assertEqual(d['target']['rect'], [x, y, width, height])
                    self.assertEqual(r['box_normalized'], dict(left=x/w, top=y/h, right=(x+width)/w, bottom=(y+height)/h))
                    self.assertTrue(0 <= x < x + width <= w and 0 <= y < y + height <= h)
                else:
                    self.assertIsNone(r['box_normalized'])
                    self.assertIsNone(d['target'])

    def test_missing_covered_ambiguous_and_exact_text_are_separate(self):
        for c in self.cases:
            r, d, kind = c['reference'], c['dom_evidence'], c['case_kind']
            with self.subTest(case=c['id']):
                self.assertEqual(r['missing'], not r['dom_present'])
                self.assertEqual(r['unclear'], kind == 'unclear')
                scores = {'positive': 3, 'negative': 0, 'unclear': 2} if c['family'] == 'ui' else {'positive': 2, 'negative': 0, 'unclear': 1}
                self.assertEqual(r['score'], scores[kind])
                if r['visibility'] == 'covered':
                    self.assertFalse(d['target']['center_topmost'])
                    self.assertEqual(d['covers'], [r['box_source_css_px']])
                    self.assertFalse(r['box_usable'])
                if r['visibility'] == 'ambiguous':
                    self.assertEqual(len(d['alternatives']), 1)
                    self.assertIsNone(r['presence'])
                    self.assertFalse(r['box_usable'])
                if r['missing']:
                    self.assertEqual(r['visibility'], 'absent')
                    self.assertFalse(r['presence'])
                    self.assertFalse(r['box_usable'])
                if c['family'] == 'document' and r['dom_present']:
                    actual = d['target']['text']
                    self.assertEqual(r['text_value'], actual)
                    self.assertEqual(r['candidate_matches_source'], c['comparison_input']['value'] == actual)
                    if kind == 'negative':
                        self.assertFalse(r['candidate_matches_source'])
                if c['family'] == 'ui' and kind == 'unclear':
                    self.assertEqual(d['buttons'][0]['background'], d['buttons'][1]['background'])

    def test_corrupt_or_truncated_png_is_rejected(self):
        data = (EXAMPLE / self.cases[0]['path']).read_bytes()
        for bad in (b'not PNG', data[:-1], data[:40] + bytes([data[40] ^ 1]) + data[41:]):
            with self.assertRaises(ValueError):
                png_dimensions(bad)


if __name__ == '__main__':
    unittest.main()
