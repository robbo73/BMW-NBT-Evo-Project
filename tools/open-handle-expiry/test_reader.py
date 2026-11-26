#!/usr/bin/env python3
"""Host signals and injected errors, not emulation of QNX descriptor death."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
import unittest
ROOT=Path(__file__).resolve().parent

def body():
    out=bytearray()
    for base in range(0,586,16):
        out.extend(('{:08x}:'.format(base)).encode()); out.append(0)
        out.extend(ord('A')+(base//16+i)%26 for i in range(10,15)); out.append(10)
    return bytes(out[:586])

class HeldReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='nbt-held-host-'); cls.root=Path(cls.temp.name)
        source=(ROOT/'nbt_hold_reader.c').read_text().replace('/ramdisk/mm',str(cls.root))
        source=source.replace('/dev/nbt_large_endpoint_586.',str(cls.root)+'/endpoint.')
        # Host-only shortened alarms; original target source remains 5/18/3 s.
        source=source.replace('alarm(5)','alarm(1)').replace('arm(18)','arm(1)').replace('arm(3)','arm(1)')
        (cls.root/'reader.c').write_text(source)
        cls.binary=cls.root/'reader'; cls.plain=cls.root/'plain'
        command=['cc','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-U_FORTIFY_SOURCE','-D_FORTIFY_SOURCE=2',
                 '-I',str(ROOT),str(cls.root/'reader.c'),str(ROOT/'large_body.c')]
        subprocess.run(command+['-o',str(cls.plain)],check=True)
        subprocess.run(command+[str(ROOT/'test_support/raw_faults.c'),
            *['-Wl,--wrap='+n for n in ('read','__read_chk','write','lseek','close','sigwaitinfo')],
            '-o',str(cls.binary)],check=True)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def setUp(self):
        self.parent=os.getpid(); self.fixture=self.root/('.nbt-held-alias-586.'+str(self.parent)); self.fixture.mkdir()
        self.target=self.root/'endpoint.42'; self.target.write_bytes(body())
        self.alias=self.fixture/'dummy-body.bin'; self.alias.symlink_to(self.target)
    def tearDown(self):
        if self.fixture.is_symlink():
            self.fixture.unlink(); (self.root/'moved').rename(self.fixture)
        for item in self.fixture.iterdir(): item.unlink()
        self.fixture.rmdir()
        if self.target.exists(): self.target.unlink()
    def run_child(self,fault='',release=True,plain=False,args=None,blocked_alarm=False):
        args=['--hold-alias',str(self.parent),'42'] if args is None else args
        proc=subprocess.Popen([str(self.plain if plain else self.binary),*args],
            env=dict(os.environ,NBT_RAW_FAULT=fault),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            preexec_fn=(lambda: signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM})) if blocked_alarm else None)
        data=bytearray(); sent=False; end=time.monotonic()+5
        selector=selectors.DefaultSelector(); selector.register(proc.stdout,selectors.EVENT_READ)
        try:
            while True:
                if time.monotonic()>end: self.fail('host harness exceeded five seconds')
                for key,_ in selector.select(0.1):
                    chunk=os.read(key.fileobj.fileno(),4096)
                    if not chunk:
                        proc.wait(timeout=1); return proc.returncode,data.decode()
                    data.extend(chunk)
                    if release and not sent and b'\nHELD ' in data and data.endswith(b'offset=100\n'):
                        os.kill(proc.pid,signal.SIGUSR1); sent=True
        finally:
            selector.close()
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=2); proc.stdout.close()
    def test_expected_errors_are_observation_not_final_pass(self):
        rc,log=self.run_child(); self.assertEqual(rc,0,log)
        self.assertIn('CONTROL_END name=read100 rc=100 errno=0',log)
        self.assertIn('CONTROL_END name=seek_current rc=100 errno=0',log)
        self.assertIn('three probes failed; requires provider/trace assessment',log)
        self.assertNotIn('PASS:',log); self.assertEqual(self.target.read_bytes(),body())
        self.assertTrue(self.alias.is_symlink())
    def test_regular_file_success_is_rejected(self):
        rc,log=self.run_child(plain=True); self.assertEqual(rc,1,log)
        self.assertIn('name=read64_a rc=64',log); self.assertNotIn('OP_BEGIN name=seek_start',log)
    def test_zero_partial_and_positive_read_stop_probes(self):
        for mode in ('zero','partial','read_success'):
            with self.subTest(mode=mode):
                rc,log=self.run_child(mode); self.assertEqual(rc,1,log)
                self.assertNotIn('OP_BEGIN name=seek_start',log); self.assertIn('OP_END name=close',log)
                self.assertNotIn('OBSERVED:',log)
    def test_seek_success_stops_second_read(self):
        rc,log=self.run_child('seek_success'); self.assertEqual(rc,1,log)
        self.assertNotIn('OP_BEGIN name=read64_b',log)
    def test_control_failure_never_announces_held(self):
        for mode in ('control_read','control_seek'):
            rc,log=self.run_child(mode); self.assertEqual(rc,1,log); self.assertNotIn('HELD ',log)
    def test_pending_release_is_not_lost(self):
        rc,log=self.run_child('pending_release'); self.assertEqual(rc,0,log); self.assertIn('RELEASED sender=',log)
    def test_missing_release_is_alarm_failure(self):
        rc,log=self.run_child(release=False); self.assertEqual(rc,-signal.SIGALRM,log)
        self.assertIn('HELD ',log); self.assertNotIn('RELEASED',log); self.assertNotIn('OBSERVED:',log)
    def test_wrong_sender_is_refused(self):
        rc,log=self.run_child('wrong_sender'); self.assertEqual(rc,1,log); self.assertNotIn('RELEASED',log)
    def test_stalled_ops_keep_last_marker(self):
        for mode,name in (('read_hang','read64_a'),('seek_hang','seek_start'),('close_hang','close')):
            with self.subTest(mode=mode):
                rc,log=self.run_child(mode); self.assertEqual(rc,-signal.SIGALRM,log)
                self.assertIn('OP_BEGIN name='+name,log); self.assertNotIn('OP_END name='+name,log)
                self.assertNotIn('OBSERVED:',log)
    def test_partial_output_is_completed(self):
        rc,log=self.run_child('partial_output'); self.assertEqual(rc,0,log); self.assertIn('OBSERVED:',log)
    def test_zero_output_fails(self):
        rc,log=self.run_child('output_zero'); self.assertEqual(rc,1,log); self.assertEqual(log,'')
    def test_blocked_output_remains_bounded(self):
        rc,log=self.run_child('output_hang'); self.assertEqual(rc,-signal.SIGALRM,log); self.assertEqual(log,'')
    def test_interrupted_output_is_completed(self):
        rc,log=self.run_child('output_eintr'); self.assertEqual(rc,0,log); self.assertIn('OBSERVED:',log)
    def test_inherited_alarm_mask_does_not_disable_timeout(self):
        rc,log=self.run_child(release=False,blocked_alarm=True)
        self.assertEqual(rc,-signal.SIGALRM,log); self.assertIn('HELD ',log)
    def test_closed_output_pipe_is_failure(self):
        read_fd,write_fd=os.pipe()
        os.close(read_fd)
        proc=subprocess.Popen([str(self.binary),'--hold-alias',str(self.parent),'42'],stdout=write_fd,stderr=subprocess.DEVNULL)
        os.close(write_fd)
        try:
            self.assertEqual(proc.wait(timeout=3),1)
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
    def test_close_error_is_recorded_separately(self):
        rc,log=self.run_child('close_failure'); self.assertEqual(rc,0,log); self.assertIn('OP_END name=close rc=-1',log)
    def test_help_and_bad_arguments(self):
        self.alias.unlink()
        for args in ([],['--help']):
            rc,log=self.run_child(args=args); self.assertEqual(rc,0,log); self.assertIn('help performs no file reads',log)
        for args in (['activate'],['--hold-alias'],['--hold-alias','01','42'],
            ['--hold-alias','2147483648','42'],['--hold-alias','1','42'],
            ['--hold-alias',str(self.parent),str(self.parent)],['--hold-alias','123','42']):
            rc,log=self.run_child(args=args); self.assertEqual(rc,2,log); self.assertNotIn('HELD',log)
    def test_wrong_bytes_and_lengths(self):
        for content in (b'x'*586,body()[:-1],body()+b'x'):
            self.target.write_bytes(content); rc,log=self.run_child()
            self.assertEqual(rc,1,log); self.assertNotIn('HELD',log)
    def test_exact_link_target_required(self):
        self.alias.unlink(); self.alias.symlink_to(self.root/'elsewhere')
        rc,log=self.run_child(); self.assertEqual(rc,1,log); self.assertNotIn('CONTROL_BEGIN',log)
    def test_parent_symlink_is_refused(self):
        moved=self.root/'moved'; self.fixture.rename(moved); self.fixture.symlink_to(moved)
        rc,log=self.run_child(); self.assertEqual(rc,1,log); self.assertNotIn('CONTROL_BEGIN',log)
    def test_regular_alias_is_refused(self):
        self.alias.unlink(); self.alias.write_bytes(body())
        rc,log=self.run_child(); self.assertEqual(rc,1,log); self.assertNotIn('CONTROL_BEGIN',log)
    def test_dangling_alias_is_refused(self):
        self.target.unlink(); rc,log=self.run_child(); self.assertEqual(rc,1,log); self.assertNotIn('HELD',log)

if __name__=='__main__': unittest.main(verbosity=2)
