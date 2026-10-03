import base64
import gzip
import importlib.util
import json
import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

spec = importlib.util.spec_from_file_location('decoder', Path(__file__).with_name('decode_api_capture.py'))
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def frame(key, iv, payload):
    raw = gzip.compress(json.dumps(payload).encode())
    raw += bytes([16 - len(raw) % 16]) * (16 - len(raw) % 16)
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = enc.update(raw) + enc.finalize()
    return SimpleNamespace(response=SimpleNamespace(
        content=json.dumps({'pmc': base64.b64encode(ciphertext).decode()}).encode(),
        headers={'x-posl-dmy-val': '17', 'x-posl-s-time': '1200'}))


class DecoderTests(unittest.TestCase):
    literals = ('{0}:{1}', '{0}|{1}', ':', '|')

    def test_before_login_uses_headers_and_decompresses(self):
        h = md5('17')
        key = bytes.fromhex(h + md5('2:' + h))
        iv = bytes.fromhex(md5('17|2'))
        flow = frame(key, iv, {'token': 'synthetic-token'})
        self.assertEqual(decoder.decode_response(flow, self.literals), {'token': 'synthetic-token'})

    def test_after_login_uses_session_and_rotated_digest(self):
        h = md5('session:token:17')
        key = bytes.fromhex(h + md5(h[2:] + h[:2]))
        iv = bytes.fromhex(md5('session|token|17'))
        flow = frame(key, iv, {'UD': {'pokemon': {'upd': {'synthetic': {'pid': 'synthetic'}}}}})
        self.assertIn('UD', decoder.decode_response(flow, self.literals, 'token', 'session'))
        with self.assertRaises(ValueError):
            decoder.decode_response(flow, self.literals, 'wrong-token', 'session')

    def test_invalid_ciphertext_is_not_accepted(self):
        flow = frame(bytes(32), bytes(16), {'test': True})
        with self.assertRaises(ValueError):
            decoder.decode_response(flow, self.literals)


if __name__ == '__main__':
    unittest.main()
