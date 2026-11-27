#!/usr/bin/env python3
"""Synthetic renderer/latch tests. Builds Linux C++98 only; no native or BMW code."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from replay_preview import replay

HERE = Path(__file__).resolve().parent


def callback(rpm=700, ms=1000):
    return {'op': 'callback', 'received_ms': ms, 'payload': {'RPMSpeed': rpm}}


def poll(ms):
    return {'op': 'poll', 'now_ms': ms}


def glyphs(results, model=60, width=4):
    """Decode captured IMAGE IDs independently, retaining unchanged models."""
    state = {}
    for result in results:
        for key, image in result.get('models', []):
            state[key] = image
    chars = []
    for key in range(model, model + width):
        image = state[key]
        index = image - (55902 if 55902 <= image <= 55913 else 55890)
        chars.append('0123456789- '[index])
    return ''.join(chars)


def images(result):
    return dict(result['models'])


class Preview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='cds-shift-host-')
        cls.binary = Path(cls.tmp.name) / 'host-replay'
        subprocess.run(['g++', '-std=c++98', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-fno-exceptions', '-pthread', '-I' + str(HERE),
                        str(HERE / 'host_replay.cpp'), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_events(self, events):
        return replay(self.binary, events)

    def test_initial_blank_rpm_and_unavailable_speed(self):
        r = self.run_events([poll(1000)])
        self.assertEqual(glyphs(r), ' -- ')
        self.assertEqual(glyphs(r, 70, 3), '-- ')
        self.assertEqual(images(r[-1])[54], 56400)

    def test_json_rpm_is_not_divided_again(self):
        r = self.run_events([callback(700), poll(1000)])
        self.assertEqual(glyphs(r), '700 ')
        self.assertEqual(images(r[-1])[54], 56411)
        self.assertFalse(r[-1]['producer_freshness_verified'])

    def test_zero_is_valid_and_distinct_from_no_sample(self):
        r = self.run_events([callback(0), poll(1000)])
        self.assertTrue(r[0]['accepted'])
        self.assertEqual(glyphs(r), ' 0  ')

    def test_error_payload_is_not_zero_or_a_new_receipt(self):
        r = self.run_events([callback(), poll(1000),
            {'op': 'callback', 'received_ms': 1500, 'payload': {'error': 402}}, poll(1500), poll(1750)])
        self.assertFalse(r[2]['accepted'])
        self.assertEqual(r[3]['received_ms'], 1000)
        self.assertEqual(r[3]['sequence'], 1)
        self.assertEqual(glyphs(r), ' -- ')

    def test_error_with_rpm_is_also_rejected_by_fixture_boundary(self):
        r = self.run_events([{'op': 'callback', 'received_ms': 1000,
                             'payload': {'error': 402, 'RPMSpeed': 0}}, poll(1000)])
        self.assertFalse(r[0]['accepted'])
        self.assertEqual(glyphs(r), ' -- ')

    def test_invalid_values_never_reach_renderer(self):
        for value in (-1, 9001, True, None, '700', float('nan'), float('inf')):
            with self.subTest(value=value):
                r = self.run_events([callback(value), poll(1000)])
                self.assertFalse(r[0]['accepted'])
                self.assertEqual(glyphs(r), ' -- ')

    def test_native_numeric_latch_also_rejects_nan_and_out_of_range(self):
        r = subprocess.run([str(self.binary)], input='sample 1000 nan\nsample 1000 9001\npoll 1000\n',
                           text=True, capture_output=True, check=True)
        result = [json.loads(line) for line in r.stdout.splitlines()]
        self.assertFalse(result[0]['accepted'])
        self.assertFalse(result[1]['accepted'])
        self.assertEqual(glyphs(result), ' -- ')

    def test_existing_9000_policy_is_preserved(self):
        r = self.run_events([callback(9000), poll(1000)])
        self.assertEqual(glyphs(r), '9000')
        self.assertEqual(images(r[-1])[54], 56657)

    def test_round_once_at_display_boundary(self):
        r = self.run_events([callback(700.5), poll(1000)])
        self.assertEqual(glyphs(r), '701 ')

    def test_polling_does_not_refresh_arrival(self):
        r = self.run_events([callback(), poll(1000), poll(1600), poll(1749), poll(1750)])
        self.assertTrue(r[-2]['recent_arrival'])
        self.assertFalse(r[-1]['recent_arrival'])
        self.assertTrue(all(x['received_ms'] == 1000 for x in r[1:]))
        self.assertEqual(glyphs(r), ' -- ')

    def test_same_rpm_in_later_callback_is_a_new_receipt_not_proven_fresh(self):
        r = self.run_events([callback(), poll(1000), callback(700, 1700), poll(1750)])
        self.assertEqual(r[-1]['received_ms'], 1700)
        self.assertEqual(r[-1]['sequence'], 2)
        self.assertTrue(r[-1]['recent_arrival'])
        self.assertFalse(r[-1]['producer_freshness_verified'])

    def test_duplicate_millisecond_does_not_extend_expiry(self):
        r = self.run_events([callback(), callback(), poll(1750)])
        self.assertEqual(r[-1]['sequence'], 2)  # two calls may share one clock millisecond
        self.assertEqual(r[-1]['received_ms'], 1000)
        self.assertFalse(r[-1]['recent_arrival'])

    def test_backward_callback_preserves_last_good_receipt(self):
        r = self.run_events([callback(), callback(800, 999), poll(1000)])
        self.assertFalse(r[1]['accepted'])
        self.assertEqual(glyphs(r), '700 ')
        self.assertEqual(r[-1]['sequence'], 1)

    def test_future_receipt_is_not_rendered_as_recent(self):
        r = self.run_events([callback(700, 2000), poll(1000)])
        self.assertFalse(r[-1]['recent_arrival'])
        self.assertEqual(glyphs(r), ' -- ')

    def test_zero_clock_is_refused_not_confused_with_zero_rpm(self):
        r = self.run_events([callback(0, 0), poll(1000)])
        self.assertFalse(r[0]['accepted'])

    def test_shift_warning_images_and_digit_color(self):
        r = self.run_events([callback(6500), poll(1000)])
        self.assertEqual(glyphs(r), '6500')
        m = images(r[-1])
        self.assertEqual(m[54], 56633)
        self.assertEqual(m[55], 55879)
        self.assertEqual(m[57], 55915)
        self.assertTrue(all(55902 <= m[n] <= 55913 for n in range(60, 64)))

    def test_approach_lights_before_shift_target(self):
        r = self.run_events([callback(5000), poll(1000)])
        self.assertEqual(images(r[-1])[55], 55869)

    def test_unmodified_easing_runs_on_ui_polls(self):
        r = self.run_events([callback(700), poll(1000), callback(1700, 1020),
                             poll(1020), poll(1045), poll(1070)])
        self.assertEqual(glyphs(r[:4]), '700 ')
        self.assertEqual(glyphs(r[:5]), '1450')
        self.assertEqual(glyphs(r), '1700')

    def test_hide_blanks_and_show_does_not_restamp(self):
        r = self.run_events([callback(), poll(1000), {'op': 'hide', 'now_ms': 1100},
                             {'op': 'show', 'now_ms': 1750}])
        self.assertEqual(glyphs(r[:3]), ' -- ')
        self.assertEqual(glyphs(r), ' -- ')
        self.assertEqual(r[-1]['received_ms'], 1000)

    def test_stop_refuses_late_updates_while_object_is_alive(self):
        r = self.run_events([callback(), poll(1000), {'op': 'stop'}, callback(800, 1100), poll(1100)])
        self.assertFalse(r[-2]['accepted'])
        self.assertFalse(r[-1]['recent_arrival'])
        self.assertEqual(glyphs(r), ' -- ')

    def test_clock_failure_stops_receipts_in_host_fixture(self):
        r = self.run_events([callback(), {'op': 'clock_failure'}, callback(800, 1100), poll(1100)])
        self.assertFalse(r[-2]['accepted'])
        self.assertFalse(r[-1]['recent_arrival'])

    def test_malformed_json_and_duplicate_fields_are_discarded(self):
        for text in ('{', '[]', '{"RPMSpeed":700,"RPMSpeed":800}', '{"RPMSpeed":NaN}'):
            with self.subTest(payload=text):
                r = self.run_events([{'op': 'callback', 'received_ms': 1000, 'payload': text}, poll(1000)])
                self.assertFalse(r[0]['accepted'])

    def test_callback_has_no_model_writes_and_polls_only_emit_image_models(self):
        r = self.run_events([callback(), poll(1000)])
        self.assertEqual(r[0], {'accepted': True})
        self.assertTrue(set(images(r[1])) <= {54, 55, 57, 60, 61, 62, 63, 70, 71, 72})

    def test_threaded_latch_copies_are_consistent(self):
        r = self.run_events([{'op': 'stress'}])
        self.assertEqual(r, [{'stress': True, 'writes': 20000}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
