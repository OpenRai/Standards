"""Slow independent ORIS-001 fixture model. Test data only; never use with secrets.

Uses Python integers and hashlib, sharing no crypto dependencies with either
reference library. Edwards arithmetic follows RFC 8032 section 5.1. Source and
expected outcomes are reviewed alongside changes to ORIS-001.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'test-vectors/oris-001'
P = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, -1, P) % P
B = (15112221349535400772501151409588531511454012693041857206046113283949847762202,
     46316835694926478169428394003475163141307993866256225615783033603165251855960)
IDENTITY = (0, 1)
HEADER = b'\x18Nano Off-chain Message:\n'
ALPHABET = '13456789abcdefghijkmnopqrstuwxyz'


def h(data, size=64):
    return hashlib.blake2b(data, digest_size=size).digest()


def add(a, b):
    x, y = a
    u, v = b
    product = D*x*u*y*v % P
    return ((x*v+y*u)*pow(1+product, -1, P) % P,
            (y*v+x*u)*pow(1-product, -1, P) % P)


def mul(point, scalar):
    result = IDENTITY
    while scalar:
        if scalar & 1:
            result = add(result, point)
        point = add(point, point)
        scalar >>= 1
    return result


def encode(point):
    x, y = point
    return (y | ((x & 1) << 255)).to_bytes(32, 'little')


def decode(data):
    value = int.from_bytes(data, 'little')
    sign, y = value >> 255, value & (2**255-1)
    if y >= P:
        raise ValueError('noncanonical y')
    xx = (y*y-1)*pow(D*y*y+1, -1, P) % P
    x = pow(xx, (P+3)//8, P)
    if x*x % P != xx:
        x = x*pow(2, (P-1)//4, P) % P
    if x*x % P != xx or (x == 0 and sign):
        raise ValueError('invalid point')
    if x & 1 != sign:
        x = P-x
    return x, y


def account(public):
    def base32(data, digits):
        n, out = int.from_bytes(data, 'big'), ''
        for _ in range(digits):
            out = ALPHABET[n & 31] + out
            n >>= 5
        return out
    return 'nano_' + base32(public, 52) + base32(h(public, 5)[::-1], 8)


def expanded(key):
    digest = h(key)
    scalar = bytearray(digest[:32])
    scalar[0] &= 248
    scalar[31] &= 127
    scalar[31] |= 64
    return digest, int.from_bytes(scalar, 'little')


def public_key(key):
    return encode(mul(B, expanded(key)[1]))


def inspect(message):
    data = message.encode('utf8')
    payload = HEADER + len(data).to_bytes(4, 'big') + data
    return dict(status='ok', message_utf8_hex=data.hex(), payload_hex=payload.hex(), digest=h(payload, 32).hex())


def sign_digest(digest, key, nonce=None):
    expansion, a = expanded(key)
    public = public_key(key)
    r = int.from_bytes(h(expansion[32:] + digest), 'little') % L if nonce is None else nonce
    assert r != 0
    encoded_r = encode(mul(B, r))
    challenge = int.from_bytes(h(encoded_r + public + digest), 'little') % L
    return encoded_r + ((r + challenge*a) % L).to_bytes(32, 'little')


def verify(digest, signature, public):
    try:
        a, r = decode(public), decode(signature[:32])
        s = int.from_bytes(signature[32:], 'little')
        if s >= L or a == IDENTITY or r == IDENTITY:
            return False
        if mul(a, L) != IDENTITY or mul(r, L) != IDENTITY:
            return False
        k = int.from_bytes(h(signature[:32] + public + digest), 'little') % L
        return mul(B, s) == add(r, mul(a, k))
    except ValueError:
        return False


def generate():
    cases = []
    def case(name, operation, inputs, expected, rule):
        scope = 'reference_policy' if rule.startswith('Reference policy') else 'compatibility' if rule.endswith('/ compatibility') else 'protocol'
        cases.append(dict(id=name, operation=operation, input=inputs, expected=expected, rule=rule, scope=scope))
    key = bytes.fromhex('681fd5ed71a9f81e9d29e3450f6cd8aacb87346fd21a26003389290b9d0cb173')
    keys = [key, bytes(32), bytes(range(32)), bytes([255])*32]
    messages = ['', 'Hej Nano!🥦', 'a\0b', 'line\nbreak', 'line\r\nbreak', ' left/right ',
                'é', 'e\u0301', '\ufeffhello', '\u007f\u0080\u07ff\u0800\ud7ff\ue000\uffff',
                '\U00010000\U0010ffff', 'a'*127, 'a'*128, 'a'*255, 'a'*256]
    for i, secret in enumerate(keys):
        public = public_key(secret)
        addr = account(public)
        case(f'key-{i}', 'derive', dict(private_key=secret.hex()),
             dict(status='ok', public_key=public.hex(), account=addr), 'Signing / Deterministic account signing')
        for j, message in enumerate(messages):
            data = inspect(message)
            digest = bytes.fromhex(data['digest'])
            sig = sign_digest(digest, secret)
            assert verify(digest, sig, public)
            if i == 0:
                case(f'message-{j}', 'inspect', dict(message=message), data, 'MESSAGE / Hashing')
            case(f'sign-{i}-{j}', 'sign', dict(message=message, private_key=secret.hex()),
                 dict(status='ok', signature=sig.hex()), 'Signing / Deterministic account signing')
            case(f'verify-{i}-{j}', 'verify', dict(message=message, account=addr, signature=sig.hex()),
                 dict(status='valid'), 'Verification / Strict verification')

    message = messages[1]
    digest = bytes.fromhex(inspect(message)['digest'])
    public = public_key(key)
    signature = sign_digest(digest, key)
    def verification(name, sig=signature, pub=public, text=message, valid=False, rule='Verification / Strict verification'):
        assert verify(bytes.fromhex(inspect(text)['digest']), sig, pub) == valid, name
        case(name, 'verify', dict(message=text, account=account(pub), signature=sig.hex()),
             dict(status='valid' if valid else 'invalid'), rule)
    s = int.from_bytes(signature[32:], 'little')
    for value, name in [(s+L, 's-plus-L'), (L-1, 's-L-minus-1'), (L, 's-L'), (L+1, 's-L-plus-1'),
                        (0, 's-zero'), (2**253, 's-high-bits'), (2**256-1, 's-max')]:
        verification(name, signature[:32]+value.to_bytes(32, 'little'))
    verification('wrong-message', text=message+'!')
    verification('wrong-account', pub=public_key(keys[1]))
    verification('alternate-nonce', sign_digest(digest, key, nonce=12345), valid=True)

    # Algebraically valid identity-R signature: rejection must come from policy.
    a = expanded(key)[1]
    ident = encode(IDENTITY)
    k = int.from_bytes(h(ident+public+digest), 'little') % L
    verification('identity-R-equation', ident+(k*a % L).to_bytes(32, 'little'))
    # Identity public key forgery: no private key is needed for R=B, S=1.
    verification('identity-A-forgery', encode(B)+(1).to_bytes(32, 'little'), ident)

    # Order-8 torsion generator, all nonidentity torsion points and mixed points.
    torsion = decode(bytes.fromhex('c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a'))
    assert mul(torsion, 8) == IDENTITY and mul(torsion, 4) != IDENTITY
    for n in range(1, 8):
        t = mul(torsion, n)
        for label, point in [('torsion', t), ('mixed', add(B, t))]:
            verification(f'{label}-A-{n}', pub=encode(point))
            verification(f'{label}-R-{n}', sig=encode(point)+signature[32:])
    malformed_points = [P, P+1, 2**255-1, (1 << 255) | 1, (1 << 255) | (P-1)]
    for n, value in enumerate(malformed_points):
        point = value.to_bytes(32, 'little')
        verification(f'noncanonical-A-{n}', pub=point)
        verification(f'noncanonical-R-{n}', sig=point+signature[32:])
    invalid_point = next(n.to_bytes(32, 'little') for n in range(2, 100)
                         if not is_point(n.to_bytes(32, 'little')))
    verification('off-curve-A', pub=invalid_point)
    verification('off-curve-R', sig=invalid_point+signature[32:])
    # A valid mixed-order forgery satisfying the uncofactored equation.
    mixed_a = add(B, mul(torsion, 4))
    for r in range(1, 100):
        rr = encode(mul(B, r))
        k = int.from_bytes(h(rr+encode(mixed_a)+digest), 'little') % L
        if k % 2 == 0:
            verification('mixed-A-equation', rr+((r+k) % L).to_bytes(32, 'little'), encode(mixed_a))
            break
    for i in range(64):
        altered = bytearray(signature)
        altered[i] ^= 1
        verification(f'bit-flip-{i}', bytes(altered))
    for value in ['', '00', 'gg'*64, '0x'+signature.hex(), signature.hex()+'00', '€'+'0'*125]:
        case(f'malformed-signature-{len(cases)}', 'verify',
             dict(message=message, account=account(public), signature=value), dict(status='input_error'), 'Canonical Encodings / Signature Encoding')
    for value in ['', '00', 'zz'*32, '€'+'0'*61]:
        case(f'malformed-key-{len(cases)}', 'derive', dict(private_key=value), dict(status='input_error'), 'Signing / private_key')
    addr = account(public)
    for value in ['', 'nano_invalid', addr+' ', addr[:-1]+('1' if addr[-1]!='1' else '3'), 'nano_z'+addr[6:], 'nano_'+'€'*20]:
        case(f'malformed-account-{len(cases)}', 'verify', dict(message=message, account=value, signature=signature.hex()), dict(status='input_error'), 'Canonical Encodings / Account Encoding')
    for prefix, sig in [('legacy', signature.hex()), ('uppercase', signature.hex().upper())]:
        case(prefix, 'verify', dict(message=message, account=addr.replace('nano_', 'xrb_') if prefix=='legacy' else addr, signature=sig), dict(status='valid'), 'Canonical Encodings / compatibility')
    for units in [[0xd800], [0xdc00], [0xd800, 0x41]]:
        case(f'invalid-utf16-{len(cases)}', 'inspect', dict(message_utf16=units), dict(status='input_error'), 'MESSAGE / Unicode scalar values')
    for data in ['c080', 'eda080', 'f4908080', 'ff', 'e282']:
        case('invalid-utf8-'+data, 'inspect', dict(message_utf8_hex=data), dict(status='input_error'), 'MESSAGE / valid UTF-8')
    case('bom-bytes', 'inspect', dict(message_utf8_hex='efbbbf68656c6c6f'), inspect('\ufeffhello'), 'MESSAGE / BOM preservation')
    framed_inputs = [
        ('truncated-header', HEADER[:-1]),
        ('truncated-length', HEADER + b'\x00\x00\x00'),
        ('truncated-message', HEADER + (2).to_bytes(4, 'big') + b'a'),
        ('trailing-bytes', HEADER + (1).to_bytes(4, 'big') + b'ab'),
        ('malformed-utf8', HEADER + (2).to_bytes(4, 'big') + bytes.fromhex('c080')),
    ]
    for name, frame in framed_inputs:
        case('frame-' + name, 'parse_frame', dict(payload_hex=frame.hex()),
             dict(status='input_error'), 'Implementation Notes / framed input')
    case('limit-over', 'inspect', dict(message_repeat=dict(text='a', count=16777217)), dict(status='input_error'), 'Reference policy / 16 MiB')
    case('malformed-signature-plus-sign', 'verify', dict(message=message, account=addr, signature='+a'*64), dict(status='input_error'), 'Canonical Encodings / Signature Encoding')
    case('malformed-key-plus-sign', 'derive', dict(private_key='+a'*32), dict(status='input_error'), 'Signing / private_key')
    for label, tail in [('lf', '\n'), ('cr', '\r'), ('crlf', '\r\n'), ('ls', '\u2028'), ('ps', '\u2029')]:
        case('malformed-signature-tail-'+label, 'verify', dict(message=message, account=addr, signature=signature.hex()+tail), dict(status='input_error'), 'Canonical Encodings / Signature Encoding')
        case('malformed-key-tail-'+label, 'derive', dict(private_key=key.hex()+tail), dict(status='input_error'), 'Signing / private_key')
        case('malformed-account-tail-'+label, 'verify', dict(message=message, account=addr+tail, signature=signature.hex()), dict(status='input_error'), 'Canonical Encodings / Account Encoding')
    suite = dict(schema_version=1, profile='oris-001-strict-v1',
                 provenance='Independent Python integer/hashlib model; RFC 8032 Edwards arithmetic; ORIS-001 deterministic BLAKE2b construction.', cases=cases)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'suite.json').write_text(json.dumps(suite, ensure_ascii=True, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'Generated {len(cases)} ORIS-001 cases')


def is_point(value):
    try:
        decode(value)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    generate()
