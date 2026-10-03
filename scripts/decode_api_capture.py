"""Offline decoder for captured Pokémon Sleep v3.8.2 responses.

Never sends requests. Private output includes authentication material; keep it
inside .research. Protocol literals are read from the matching public Android
client, rather than embedded in source. Native client code is never executed.
"""
import argparse
import base64
import hashlib
import json
import os
import struct
import zlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from elftools.elf.elffile import ELFFile
from mitmproxy import io

HOST = "api.sleep.pokemon.co.jp"
CLIENT_SHA256 = ('eb0028b16a37e12573d3c6db3872eecabce585ca469156816ae4299941e3a506', '75fbee2fdf553321dd5b243723916fe4e0979897e3432fe1b48ffe1452ce5377')
LITERAL_ADDRESSES = (0x7088B70, 0x709B7A0, 0x706D950, 0x7088470)


def load_literals(metadata_path, native_path, addresses=LITERAL_ADDRESSES):
    metadata = Path(metadata_path).read_bytes()
    if struct.unpack_from('<2I', metadata) != (0xFAB11BAF, 31):
        raise ValueError('Expected IL2CPP metadata version 31')
    native = Path(native_path).read_bytes()
    if (hashlib.sha256(metadata).hexdigest(), hashlib.sha256(native).hexdigest()) != CLIENT_SHA256:
        raise ValueError('Expected the exact supported v3.8.2 client revision')
    with Path(native_path).open('rb') as stream:
        elf = ELFFile(stream)
        if elf['e_machine'] != 'EM_AARCH64':
            raise ValueError('Expected v3.8.2 ARM64 Android library')
        segments = [(s['p_vaddr'], s['p_offset'], s['p_filesz'])
                    for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        relocations = {r['r_offset']: r['r_addend']
                       for r in elf.get_section_by_name('.rela.dyn').iter_relocations()
                       if r['r_info_type'] == 1027}
    def offset(address):
        for address_start, file_start, size in segments:
            if address_start <= address < address_start + size:
                return file_start + address - address_start
        raise ValueError('Unsupported native library layout')
    literal_table, literal_size = struct.unpack_from('<2I', metadata, 8)
    data_start, data_size = struct.unpack_from('<2I', metadata, 16)
    values = []
    for address in addresses:
        pointer = relocations[address]
        encoded = struct.unpack_from('<I', native, offset(pointer))[0]
        if encoded >> 29 != 5:
            raise ValueError('Unsupported native string layout')
        index = (encoded & 0x1FFFFFFF) >> 1
        if index * 8 >= literal_size:
            raise ValueError('Invalid string index')
        length, start = struct.unpack_from('<2I', metadata, literal_table + index * 8)
        if start + length > data_size:
            raise ValueError('Invalid literal bounds')
        values.append(metadata[data_start + start:data_start + start + length].decode())
    if addresses == LITERAL_ADDRESSES and [len(v) for v in values] != [7, 7, 1, 1]:
        raise ValueError('Library differs from supported v3.8.2 revision')
    return values


def decrypt_bytes(ciphertext, key, iv):
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


def unpack_payload(data):
    # Client uses gzip. zlib verifies its checksum and ignores AES padding after
    # the compressed member; valid JSON is required before accepting a decode.
    return json.loads(zlib.decompress(data, 31))


def decode_response(flow, literals, token=None, session=None):
    body = json.loads(flow.response.content)
    ciphertext = base64.b64decode(body['pmc'], validate=True)
    dummy = str(int(flow.response.headers['x-posl-dmy-val']))
    server_time = int(flow.response.headers['x-posl-s-time'])
    key_format, iv_format, key_separator, iv_separator = literals
    for uppercase in (False, True):
        def md5(value):
            result = hashlib.md5(value.encode()).hexdigest()
            return result.upper() if uppercase else result
        if token is not None and session is not None:
            digest = md5(session + key_separator + token + key_separator + dummy)
            rotation = 2 * (int(dummy) % 16)
            key = bytes.fromhex(digest + md5(digest[rotation:] + digest[:rotation]))
            iv = bytes.fromhex(md5(session + iv_separator + token + iv_separator + dummy))
            candidates = [(key, iv)]
        else:
            digest = md5(dummy)
            candidates = []
            for delta in (0, -1, 1):
                bucket = server_time // 600 + delta
                candidates.append((bytes.fromhex(digest + md5(key_format.format(bucket, digest))),
                                   bytes.fromhex(md5(iv_format.format(dummy, bucket)))))
        for key, iv in candidates:
            try:
                return unpack_payload(decrypt_bytes(ciphertext, key, iv))
            except (ValueError, zlib.error, UnicodeError):
                continue
    raise ValueError('Response does not match supported decoding recipe')


def decode_capture(capture, literals, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = session = None
    summary = []
    roster = {}
    with Path(capture).open('rb') as stream:
        for flow in io.FlowReader(stream).stream():
            if flow.request.host.casefold() != HOST or flow.response is None:
                continue
            route = flow.request.path.split('?', 1)[0]
            try:
                auth = route in ('/auth/get-token', '/auth/login')
                decoded = decode_response(flow, literals, None if auth else token,
                                          None if auth else session)
            except (ValueError, KeyError):
                summary.append({'route': route, 'decoded': False})
                continue
            if route == '/auth/get-token':
                token = decoded.get('token')
            elif route == '/auth/login':
                session = decoded.get('sid')
            path = output / f'response-{len(summary):04d}.json'
            with open(path, 'w', opener=lambda p, f: os.open(p, f, 0o600)) as target:
                json.dump(decoded, target, ensure_ascii=False, indent=2)
            pokemon = decoded.get('UD', {}).get('pokemon', {})
            update = pokemon.get('upd', {})
            # Retain wire records only, without assuming name/enum semantics or
            # claiming that this incremental capture contains the entire Box.
            if isinstance(update, dict):
                roster.update(update)
            summary.append({'route': route, 'decoded': True,
                            'top_level_fields': list(decoded),
                            'pokemon_update_count': len(update)})
    with open(output / 'pokemon-wire-records.json', 'w', opener=lambda p, f: os.open(p, f, 0o600)) as target:
        json.dump({'coverage': 'captured_updates_only', 'needs_review': True,
                   'records': list(roster.values())}, target, ensure_ascii=False, indent=2)
    report = {'flows': summary, 'unique_pokemon_updates': len(roster),
              'full_roster_verified': False}
    (output / 'decode-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--native', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        report = decode_capture(args.capture, load_literals(args.metadata, args.native), args.output)
    except (ValueError, KeyError):
        parser.exit(1, 'Capture or client format unsupported; no payload values printed.\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
