#!/usr/bin/env python3
"""Independent byte/bounds oracle across build-time sizes; no namespace/IPC."""
import ctypes
import errno
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parent
LENGTHS = (1,23,586,2047,2048,2049,4095,4096,4097,8192,8193,16384)

def expected_body(length):
    output=bytearray()
    for index in range(length):
        block,position=divmod(index,16)
        line=('%08x'%(block*16)).encode()+b':\0'+bytes(ord('A')+(block+p)%26 for p in range(10,15))+b'\n'
        output.append(line[position])
    return bytes(output)

class Body(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='nbt-large-policy-');cls.libs={}
        for length in LENGTHS:
            binary=Path(cls.temp.name)/('body-%s.so'%length)
            subprocess.run(['cc','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                            '-DNBT_BODY_LENGTH=%s'%length,str(ROOT/'large_body.c'),'-o',str(binary)],check=True)
            lib=ctypes.CDLL(str(binary));lib.nbt_body_init()
            lib.nbt_body_length.restype=ctypes.c_size_t;lib.nbt_body_data.restype=ctypes.c_void_p
            lib.nbt_body_slice.argtypes=[ctypes.c_longlong,ctypes.c_longlong,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
            lib.nbt_body_open_allowed.argtypes=[ctypes.c_uint]*3;cls.libs[length]=lib
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def slice(self,lib,offset,request):
        start,count=ctypes.c_size_t(999),ctypes.c_size_t(999)
        error=lib.nbt_body_slice(offset,request,ctypes.byref(start),ctypes.byref(count))
        return error,start.value,count.value
    def test_exact_bytes_including_nul_at_every_size(self):
        for n,lib in self.libs.items():
            with self.subTest(length=n):
                self.assertEqual(lib.nbt_body_length(),n)
                self.assertEqual(ctypes.string_at(lib.nbt_body_data(),n),expected_body(n))
                if n>=16:self.assertIn(b'\0',expected_body(n))
    def test_length_derived_edges_and_integer_extremes(self):
        for n,lib in self.libs.items():
            for offset in (-2**63,-1,0,1,n-1,n,n+1,n+1000,2**63-1):
                for request in (-1,0,1,7,n-1,n,n+1,2048,8192,2**63-1):
                    with self.subTest(length=n,offset=offset,request=request):
                        result=self.slice(lib,offset,request)
                        if offset<0 or request<0:self.assertEqual(result,(errno.EINVAL,0,0))
                        else:self.assertEqual(result,(0,min(offset,n),min(request,max(0,n-offset))))
    def test_partial_reads_reconstruct_independent_oracle(self):
        for n,lib in self.libs.items():
            data=ctypes.string_at(lib.nbt_body_data(),n)
            for chunk in sorted({1,max(1,n-1),n,n+1,2047,2048,2049,4096,8192}):
                position=0;parts=[]
                while True:
                    error,start,count=self.slice(lib,position,chunk);self.assertEqual(error,0)
                    if not count:break
                    parts.append(data[start:start+count]);position+=count
                self.assertEqual(b''.join(parts),expected_body(n))
    def test_random_offsets_reach_each_body_boundary(self):
        rng=random.Random(731)
        for n,lib in self.libs.items():
            data=expected_body(n)
            for _ in range(300):
                offset=rng.randrange(-4,n+8);request=rng.choice((-1,0,1,n-1,n,n+1,2048,8192,2**63-1))
                error,start,count=self.slice(lib,offset,request)
                if offset<0 or request<0:self.assertEqual((error,start,count),(errno.EINVAL,0,0))
                else:self.assertEqual(data[start:start+count],data[offset:offset+request])
    def test_null_outputs_and_readonly_policy(self):
        for lib in self.libs.values():
            out=ctypes.c_size_t()
            self.assertEqual(lib.nbt_body_slice(0,1,None,ctypes.byref(out)),errno.EINVAL)
            self.assertEqual(lib.nbt_body_slice(0,1,ctypes.byref(out),None),errno.EINVAL)
            self.assertEqual(lib.nbt_body_open_allowed(1,2,0x300),1)
            for flags in (2,3,0x100,0x200,0x301,0xffffffff):self.assertEqual(lib.nbt_body_open_allowed(flags,2,0x300),0)
            self.assertEqual(lib.nbt_body_open_allowed(8,8,0x40),0)
    def test_invalid_build_lengths_are_refused(self):
        for length in (0,-1,16385,2147483648):
            result=subprocess.run(['cc','-std=gnu99','-DNBT_BODY_LENGTH=%s'%length,'-fsyntax-only',str(ROOT/'large_body.c')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('must be between 1 and 16384',result.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
