#!/usr/bin/env python3
"""Actual callbacks with synthetic SDK defaults; not QNX seek/IPC behavior."""
import ctypes
import errno
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent

class Event(ctypes.Structure):
    _fields_=[('kind',ctypes.c_int),('result',ctypes.c_int),('whence',ctypes.c_int),
              ('xtype',ctypes.c_ulong),('before',ctypes.c_longlong),('after',ctypes.c_longlong),
              ('read_requested',ctypes.c_longlong),('seek_offset_bits',ctypes.c_ulonglong),('count',ctypes.c_size_t)]

class Callbacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='nbt-large-callbacks-');cls.libs={}
        for length in (586,2049,8193):
            out=Path(cls.temp.name)/('callbacks-%s.so'%length)
            subprocess.run(['cc','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                            '-DNBT_LARGE_TEST_RUNTIME','-DNBT_BODY_LENGTH=%s'%length,
                            str(ROOT/'test_support/callback_probe.c'),str(ROOT/'large_body.c'),str(ROOT/'trace_log.c'),
                            str(ROOT/'test_support/fake_qnx.c'),'-Wl,--wrap=lstat','-Wl,--wrap=clock_gettime','-o',str(out)],check=True)
            lib=ctypes.CDLL(str(out))
            lib.probe_read.argtypes=[ctypes.c_longlong,ctypes.c_int,ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_longlong)]
            lib.probe_seek.argtypes=[ctypes.c_longlong,ctypes.c_ulonglong,ctypes.c_int,ctypes.c_int,ctypes.c_longlong,ctypes.POINTER(ctypes.c_longlong)]
            lib.nbt_trace_count.restype=ctypes.c_size_t;lib.nbt_trace_dropped.restype=ctypes.c_ulong
            lib.nbt_trace_at.argtypes=[ctypes.c_size_t];lib.nbt_trace_at.restype=ctypes.POINTER(Event)
            cls.libs[length]=lib
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        for lib in self.libs.values():lib.nbt_trace_reset()
    def read(self,lib,offset,request,xtype=0,verify=0):
        out=(ctypes.c_longlong*5)();rc=lib.probe_read(offset,request,xtype,verify,out)
        return rc,list(out)
    def test_callbacks_registered_with_mutations_disabled(self):
        for lib in self.libs.values():self.assertEqual(lib.probe_handlers(),1)
    def test_actual_read_status_iov_and_offset_agree(self):
        for n,lib in self.libs.items():
            for offset,request in ((0,2**31-1),(1,8192),(n-1,8192),(100,10)):
                lib.nbt_trace_reset();count=min(request,n-offset)
                rc,out=self.read(lib,offset,request)
                self.assertEqual((rc,out),(-1,[count,offset+count,count,offset,2]))
                e=lib.nbt_trace_at(0).contents
                self.assertEqual((e.kind,e.before,e.after,e.read_requested,e.count,e.result),(1,offset,offset+count,request,count,-1))
    def test_eof_and_zero_requests_do_not_advance(self):
        for n,lib in self.libs.items():
            for offset,request in ((0,0),(n,10),(n+1,10),(2**63-1,2**31-1)):
                lib.nbt_trace_reset();rc,out=self.read(lib,offset,request)
                self.assertEqual((rc,out[0],out[1],out[4]),(0,0,offset,0))
                self.assertEqual(lib.nbt_trace_at(0).contents.count,0)
    def test_read_errors_preserve_offset_and_do_not_report_bytes(self):
        for lib in self.libs.values():
            for offset,request,xtype,verify,error in ((-1,10,0,0,errno.EINVAL),(0,-1,0,0,errno.EINVAL),
                                                      (0,1,1,0,errno.ENOSYS),(0,1,0,errno.EACCES,errno.EACCES)):
                lib.nbt_trace_reset();rc,out=self.read(lib,offset,request,xtype,verify)
                self.assertEqual((rc,out[0],out[1],out[3],out[4]),(error,1234,offset,-1,0))
                e=lib.nbt_trace_at(0).contents
                self.assertEqual((e.count,e.result,e.read_requested,e.xtype),(0,error,request,xtype))
    def test_seek_preserves_default_reply_and_original_union_input(self):
        for lib in self.libs.values():
            for rc in (-3,-1,0,errno.EINVAL):
                for whence,bits in ((0,0),(1,0xfffffffffffffffB),(2,100)):
                    lib.nbt_trace_reset();out=(ctypes.c_longlong*5)()
                    self.assertEqual(lib.probe_seek(10,bits,whence,rc,123,out),rc)
                    self.assertEqual(list(out),[321,123,8,1,1])
                    e=lib.nbt_trace_at(0).contents
                    self.assertEqual((e.kind,e.before,e.after,e.seek_offset_bits,e.whence,e.result),(2,10,123,bits,whence,rc))
    def test_trace_capacity_reports_drops_without_overwriting(self):
        for lib in self.libs.values():
            for index in range(70):self.read(lib,index,1)
            self.assertEqual(lib.nbt_trace_count(),64);self.assertEqual(lib.nbt_trace_dropped(),6)
            self.assertEqual(lib.nbt_trace_at(0).contents.before,0)
            self.assertEqual(lib.nbt_trace_at(63).contents.before,63)
            self.assertFalse(lib.nbt_trace_at(64))

if __name__=='__main__':unittest.main(verbosity=2)
