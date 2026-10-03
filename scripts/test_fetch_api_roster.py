import base64
import json
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from urllib.error import URLError
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import fetch_api_roster as fetch
from decode_api_capture import decrypt_bytes, unpack_payload


class RequestTests(unittest.TestCase):
    literals = ('unused', 'unused', ':', '|', '/', '{0}:{1}:{2}')

    def test_encrypted_payload_roundtrip_and_valid_signature(self):
        plain = {'udVer': 42, 'tgt': None, 'tzof': -18000, 'stzof': 3600}
        body = fetch.build_body({'sid': 'session', 'clV': 'synthetic'}, plain,
                                'session', 'token', '17', self.literals)
        key, iv = fetch.key_iv('session', 'token', '17', self.literals)
        decoded = unpack_payload(decrypt_bytes(base64.b64decode(body['pmc']), key, iv))
        self.assertEqual(decoded, plain)
        random_byte = int(body['hsh'][:2], 16)
        self.assertGreaterEqual(random_byte, 16)
        self.assertLess(random_byte, 256)
        self.assertEqual(body['hsh'], fetch.signature(body['pmc'], 'session', 'token',
                                                    '17', random_byte, self.literals))
        self.assertEqual(body['sid'], 'session')
        self.assertIsNone(body['pmp'])

    def test_signing_binds_to_ciphertext_and_current_session(self):
        sig = fetch.signature('ciphertext', 'session', 'token', '17', 32, self.literals)
        self.assertNotEqual(sig, fetch.signature('other', 'session', 'token', '17', 32, self.literals))
        self.assertNotEqual(sig, fetch.signature('ciphertext', 'other', 'token', '17', 32, self.literals))

    def test_network_failure_stops_after_one_attempt(self):
        args = SimpleNamespace(capture='unused', metadata='unused', native='unused',
                               send=True, output='unused')
        with patch.object(fetch, 'load_literals', return_value=self.literals), \
             patch.object(fetch, 'prepare', return_value=({}, {}, 'token', 'session', 7)), \
             patch.object(fetch, 'urlopen', side_effect=URLError('unreachable')) as send:
            report = fetch.run(args)
        send.assert_called_once()
        self.assertTrue(report['network_error'])
        self.assertFalse(report['sent'])
        self.assertNotIn('token', json.dumps(report))
        self.assertNotIn('session', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
