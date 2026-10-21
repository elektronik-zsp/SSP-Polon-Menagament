import unittest, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from cf_crypto import encrypt,decrypt,MAGIC
class CryptoTests(unittest.TestCase):
 def test_roundtrip(self):
  k=os.urandom(32); plain=b'{"test":1}'; c=encrypt(plain,k)
  self.assertTrue(c.startswith(MAGIC));self.assertEqual(decrypt(c,k),plain)
 def test_tamper(self):
  k=os.urandom(32); c=bytearray(encrypt(b'hello',k));c[-1]^=1
  with self.assertRaises(ValueError):decrypt(bytes(c),k)
 def test_wrong_key(self):
  with self.assertRaises(ValueError):decrypt(encrypt(b'x',os.urandom(32)),os.urandom(32))
