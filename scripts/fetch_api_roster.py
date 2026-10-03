"""Prepare or fetch the full roster through the client's GetAllUD request.

Only this fixed data-read endpoint is supported. No login, account transfer,
phone modification, or automatic retries. Session material stays in private files.
By default validate captured signing and prepare locally; --send makes one call.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
import secrets
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from mitmproxy import io
from decode_api_capture import load_literals, decode_response, unpack_payload, decrypt_bytes, HOST

ROUTE = '/api/common/get-all-ud'
ADDRESSES = (0x7088B70, 0x709B7A0, 0x706D950, 0x7088470, 0x707B400, 0x709BD70)


def md5(value):
    return hashlib.md5(value.encode()).hexdigest()


def key_iv(session, token, dummy, literals):
    digest = md5(session + literals[2] + token + literals[2] + dummy)
    rotation = 2 * (int(dummy) % 16)
    return (bytes.fromhex(digest + md5(digest[rotation:] + digest[:rotation])),
            bytes.fromhex(md5(session + literals[3] + token + literals[3] + dummy)))


def signature(pmc, session, token, dummy, random_byte, literals):
    digest = md5(session + literals[4] + token + literals[4] + dummy)
    return format(random_byte, 'x') + md5(literals[5].format(md5(pmc), random_byte, digest))


def build_body(template, plain, session, token, dummy, literals):
    raw = gzip.compress(json.dumps(plain, separators=(',', ':')).encode(), mtime=0)
    padding = 16 - len(raw) % 16
    raw += bytes([padding]) * padding
    key, iv = key_iv(session, token, dummy, literals)
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    pmc = base64.b64encode(encryptor.update(raw) + encryptor.finalize()).decode()
    return dict(template, pmc=pmc, pmp=None,
                hsh=signature(pmc, session, token, dummy, secrets.randbelow(240) + 16, literals))


def private_write(path, value):
    with open(path, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def prepare(capture, literals):
    with Path(capture).open('rb') as stream:
        flows = [flow for flow in io.FlowReader(stream).stream()
                 if flow.request.host.casefold() == HOST and flow.response is not None]
    token = session = None
    latest_plain = latest = None
    verified = 0
    for flow in flows:
        route = flow.request.path.split('?', 1)[0]
        if route in ('/auth/get-token', '/auth/login'):
            decoded = decode_response(flow, literals[:4])
            if route == '/auth/get-token':
                token = decoded['token']
            else:
                session = decoded['sid']
            continue
        if token is None or session is None:
            continue
        body = json.loads(flow.request.content)
        if body.get('sid') != session:
            raise ValueError('Session format unsupported')
        dummy = flow.request.headers['x-posl-dmy-val']
        key, iv = key_iv(session, token, dummy, literals)
        plain = unpack_payload(decrypt_bytes(base64.b64decode(body['pmc']), key, iv))
        random_byte = int(body['hsh'][:2], 16)
        if signature(body['pmc'], session, token, dummy, random_byte, literals) != body['hsh']:
            raise ValueError('Captured signature verification failed')
        verified += 1
        latest = flow
        latest_plain = plain
    if not verified:
        raise ValueError('No authenticated request verified')
    dummy = str(secrets.randbelow(8_000_000_000_000_000_000) + 1_000_000_000_000_000_000)
    plain = {key: latest_plain[key] for key in ('udVer', 'tzof', 'stzof')}
    plain['tgt'] = None  # Same unfiltered argument as DataRestoreManager.RecreateDB.
    body = build_body(json.loads(latest.request.content), plain, session, token, dummy, literals)
    headers = {key: value for key, value in latest.request.headers.items()
               if key.lower() in ('content-type', 'x-unity-version', 'accept', 'x-posl-encrypt',
                                  'x-posl-hash-check', 'user-agent', 'cookie', 'accept-language')}
    headers['x-posl-dmy-val'] = dummy
    return body, headers, token, session, verified


def run(args):
    literals = load_literals(args.metadata, args.native, ADDRESSES)
    body, headers, token, session, count = prepare(args.capture, literals)
    report = {'route': ROUTE, 'verified_captured_signatures': count, 'sent': False}
    if not args.send:
        return report
    request = Request('https://' + HOST + ROUTE,
                      json.dumps(body, separators=(',', ':')).encode(), headers, method='POST')
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
            response_headers = dict(response.headers.items())
            status = response.status
    except HTTPError as error:
        content, response_headers, status = error.read(), dict(error.headers.items()), error.code
    except URLError:
        report['network_error'] = True
        return report
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    envelope = json.loads(content)
    private_write(output / 'response-envelope.json', envelope)
    private_write(output / 'response-headers.json', response_headers)
    report.update(sent=True, http_status=status, server_code=envelope.get('code'))
    if envelope.get('code') == 1100:
        report.update(decoded=False, error='session_expired', fresh_session_required=True)
        private_write(output / 'safe-summary.json', report)
        return report
    flow = SimpleNamespace(response=SimpleNamespace(content=content,
        headers={key.lower(): value for key, value in response_headers.items()}))
    try:
        decoded = decode_response(flow, literals[:4], token, session)
    except (ValueError, KeyError):
        report['decoded'] = False
        return report
    private_write(output / 'decoded.json', decoded)
    pokemon = decoded.get('UD', {}).get('pokemon', {})
    report.update(decoded=True, pokemon_sections={key: len(value)
                  for key, value in pokemon.items() if isinstance(value, (dict, list))})
    private_write(output / 'safe-summary.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--native', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    try:
        report = run(args)
    except (ValueError, KeyError):
        parser.exit(1, 'Unsupported capture/client format; no private values printed.\n')
    print(json.dumps(report, indent=2))
    if report.get('network_error'):
        parser.exit(1, 'Network unavailable; no retry or login performed.\n')


if __name__ == '__main__':
    main()
