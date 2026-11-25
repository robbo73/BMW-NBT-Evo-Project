#!/usr/bin/env python3
"""Parser tests on synthetic text only, never a native trace or IPC model."""
from pathlib import Path
import subprocess
import sys
import unittest
from assess_trace import assess,FINAL

VALID='\n'.join([
 'READY pid=42 path=/dev/nbt_large_endpoint_586.42 bytes=586 lease_ms=10000',
 'PASS: larger-reader-1; bytes=586 items=1; seek-end/tell/rewind/read/close',
 'Stdio reader exit: 0',
 'TRACE_SUMMARY events=3 dropped=0 overflow=0 elapsed_ms=10001',
 'TRACE_SEEK index=0 before=0 offset_bits=0000000000000000 whence=2 after=586 rc=-1',
 'TRACE_SEEK index=1 before=586 offset_bits=0000000000000000 whence=0 after=0 rc=-1',
 'TRACE_READ index=2 before=0 requested=8192 xtype=0 count=586 after=586 rc=-1',
 'DETACHED reason=deadline; endpoint server exiting',
 'Endpoint server exit: 0',
 'DANGLING: dummy alias remains a link; target unavailable',
 'CLEANED: dummy alias and owned fixture directory',FINAL])+'\n'


class Trace(unittest.TestCase):
    def test_complete_trace_is_accepted(self):
        result=assess(VALID)
        self.assertEqual(result['events'],3)
        self.assertEqual(len(result['seeks']),2)
        self.assertEqual(result['reads'][0]['requested'],8192)
        self.assertFalse(result['xml_parsing_verified'])

    def test_overflow_cannot_count_as_complete(self):
        for old,new in [('dropped=0','dropped=1'),('overflow=0','overflow=1')]:
            with self.assertRaises(ValueError):assess(VALID.replace(old,new))

    def test_missing_or_duplicate_records_are_refused(self):
        read=next(line for line in VALID.splitlines() if line.startswith('TRACE_READ'))+'\n'
        for text in (VALID.replace(read,''),VALID+read,VALID.replace('index=2','index=1')):
            with self.assertRaises(ValueError):assess(text)

    def test_unknown_or_malformed_trace_is_refused(self):
        for text in (VALID+'TRACE_UNKNOWN value=1\n',VALID.replace('requested=8192','requested=bad')):
            with self.assertRaises(ValueError):assess(text)

    def test_incomplete_or_failed_runner_is_refused(self):
        for text in (VALID.replace(FINAL,''),VALID.replace('Endpoint server exit: 0','Endpoint server exit: 1'),
                     VALID+'WATCHDOG: fallback\n',VALID+'STOP: failure\n'):
            with self.assertRaises(ValueError):assess(text)

    def test_invalid_summary_is_refused(self):
        for text in (VALID.replace('events=3','events=65'),VALID.replace('elapsed_ms=10001','elapsed_ms=-1'),
                     VALID+'TRACE_SUMMARY events=3 dropped=0 overflow=0 elapsed_ms=10001\n'):
            with self.assertRaises(ValueError):assess(text)

    def test_count_and_offset_corruption_are_refused(self):
        for old,new in [('count=586','count=587'),('after=586 rc=-1\nDETACHED','after=585 rc=-1\nDETACHED'),
                        ('requested=8192','requested=2147483648')]:
            with self.assertRaises(ValueError):assess(VALID.replace(old,new))

    def test_seek_reply_codes_are_not_posix_error_classified(self):
        result=assess(VALID.replace('whence=2 after=586 rc=-1','whence=2 after=586 rc=-3'))
        self.assertEqual(result['seeks'][0]['rc'],-3)

    def test_zero_seek_count_is_recorded_without_assuming_libc_strategy(self):
        lines=[line for line in VALID.splitlines() if not line.startswith('TRACE_SEEK')]
        text='\n'.join(lines).replace('events=3','events=1').replace('index=2','index=0')
        self.assertEqual(assess(text)['seeks'],[])

    def test_cli_defaults_to_help_without_reading_files(self):
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('assess_trace.py'))],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('--input',result.stdout)


if __name__=='__main__':unittest.main(verbosity=2)
