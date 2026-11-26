#!/usr/bin/env python3
"""Local protocol/mocked-SSH checks only. No network or ARM execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import capture_held_trial as C

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GATE_PATH = REPO/'tools/held-expiry-supervisor/gate_trial.py'
# The frozen ready folder places the same dependencies directly under tools/.
if not GATE_PATH.exists():
    REPO = HERE
    GATE_PATH = HERE/'tools/held-expiry-supervisor/gate_trial.py'
spec = importlib.util.spec_from_file_location('client_test_gate', GATE_PATH)
GATE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(GATE)
SYNTHETIC = (REPO/'tools/held-expiry-assessor/examples/SYNTHETIC-held-expiry-pass.log').read_bytes()


def captured(status=0, body=SYNTHETIC):
    return body + b'NBT_HELD_LAUNCHER_EXIT status=' + str(status).encode() + b'\n'


class CaptureProtocol(unittest.TestCase):
    def test_exact_synthetic_pass_needs_both_zero_statuses(self):
        body, result = C.evaluate(captured(), 0, GATE)
        self.assertEqual(body,SYNTHETIC)
        self.assertEqual(result['decision'],'ACCEPT')
        self.assertTrue(result['transport_status_agrees'])

    def test_complete_log_with_nonzero_launcher_is_rejected(self):
        for status in (1,2,3,122,123,124,125,137,255):
            with self.subTest(status=status):
                _, result=C.evaluate(captured(status),status,GATE)
                self.assertEqual(result['assessor_verdict'],'PASS')
                self.assertEqual(result['decision'],'REJECT')

    def test_ssh_failure_rejects_a_success_trailer(self):
        _, result=C.evaluate(captured(),255,GATE)
        self.assertEqual(result['decision'],'REJECT')
        self.assertFalse(result['transport_status_agrees'])

    def test_status_disagreement_is_rejected(self):
        _, result=C.evaluate(captured(3),0,GATE)
        self.assertEqual(result['decision'],'REJECT')
        self.assertFalse(result['transport_status_agrees'])

    def test_missing_partial_repeated_or_invalid_trailer_is_refused(self):
        for raw in (SYNTHETIC, captured()[:-1], captured()+captured(0,b''),
                    captured(256),captured().replace(b'status=0',b'status=00'),
                    captured()+b'unexpected\n'):
            with self.subTest(raw=raw[-70:]):
                with self.assertRaises(C.Stop):C.split_capture(raw)

    def test_forbidden_bytes_are_preserved_and_rejected(self):
        raw_body=SYNTHETIC.replace(b'READY pid=',b'\x00READY pid=',1)
        body,result=C.evaluate(captured(body=raw_body),0,GATE)
        self.assertEqual(body,raw_body)
        self.assertIn(b'\x00',body)
        self.assertEqual(result['decision'],'REJECT')

    def test_truncated_controller_body_is_not_accepted(self):
        body=SYNTHETIC[:-20]+b'\n'
        _,result=C.evaluate(captured(body=body),0,GATE)
        self.assertEqual(result['decision'],'REJECT')

    def test_oversize_capture_is_refused(self):
        with self.assertRaises(C.Stop):C.split_capture(b'x'*65637)

    def test_default_help_needs_no_package_or_network(self):
        result=subprocess.run([sys.executable,'-B',str(HERE/'capture_held_trial.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('usage:',result.stdout)
        self.assertNotIn('VERIFIED:',result.stdout)


class LocalAndRam(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='nbt-client-host-')
        self.root=Path(self.temp.name)/'package';self.root.mkdir()
        (self.root/'bin').mkdir()
        self.raw=b'own synthetic executable bytes'
        (self.root/'bin/helper').write_bytes(self.raw)
        self.item=('helper',C.digest(self.raw),len(self.raw),'/dev/shmem/fixed_helper')
        (self.root/'SHA256SUMS').write_text(C.digest(self.raw)+'  bin/helper\n')
        self.patch_root=patch.object(C,'ROOT',self.root);self.patch_root.start()
        self.patch_bins=patch.object(C,'BINS',(self.item,));self.patch_bins.start()
    def tearDown(self):
        self.patch_bins.stop();self.patch_root.stop();self.temp.cleanup()
    def test_local_pins_reject_tampering(self):
        C.check_local()
        (self.root/'bin/helper').write_bytes(b'changed')
        with self.assertRaises(C.Stop):C.check_local()
    def test_manifest_traversal_is_refused(self):
        (self.root/'SHA256SUMS').write_text('0'*64+'  ../escape\n')
        with self.assertRaises(C.Stop):C.check_local()
    def test_ram_copy_requires_independent_readback(self):
        for response in (b'RAM_COPY_COMPLETE\n',b'NBT_RAM_EXISTS\n'):
            with self.subTest(response=response):
                replies=[subprocess.CompletedProcess([],0,response),subprocess.CompletedProcess([],0,self.raw)]
                with patch.object(C,'remote',side_effect=replies) as mock:
                    C.copy_ram()
                    self.assertEqual(mock.call_count,2)
                    self.assertIn('set -C',mock.call_args_list[0].args[0])
    def test_ram_corruption_or_remote_error_is_refused(self):
        for code,raw in ((0,b'bad'),(255,self.raw)):
            with patch.object(C,'remote',return_value=subprocess.CompletedProcess([],code,raw)):
                with self.assertRaises(C.Stop):C.readback(self.item)
    def test_timeout_retains_raw_evidence_and_rejection(self):
        # trial selects third frozen item; use the same synthetic item here.
        with patch.object(C,'BINS',(self.item,)*3),patch.object(C,'help_only'), \
             patch.object(C,'remote',side_effect=subprocess.TimeoutExpired('mock ssh',90,output=b'partial capture')):
            with self.assertRaises(C.Stop):C.trial()
        folders=list(self.root.parent.glob('nbt-held-run-*'))
        self.assertEqual(len(folders),1)
        self.assertEqual((folders[0]/'ssh.stdout.raw').read_bytes(),b'partial capture')
        self.assertEqual(json.loads((folders[0]/'result.json').read_text())['decision'],'REJECT')


if __name__=='__main__':unittest.main(verbosity=2)
