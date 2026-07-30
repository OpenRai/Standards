```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Message Signing (NOMS)

> Status: Implementation Draft
> Category: Cryptographic Primitive / Application Interface

## Abstract

Nano Off-chain Message Signing (NOMS) defines one deterministic way to sign
UTF-8 text with a Nano account key. It frames the message with a fixed header
and byte length, hashes the payload with Blake2b-256, and signs that digest with
Nano's account-signing algorithm.

## Motivation

Applications use Nano accounts for more than ledger transactions. Examples
include authentication challenges, wallet-to-application requests, and
machine-to-machine messages.

Signing raw message bytes does not identify the protocol or define how each
implementation encodes the message. NOMS removes that ambiguity with:

- a fixed domain-separation header,
- an explicit message length,
- UTF-8 message encoding, and
- Nano-compatible hashing and signing.

NOMS only defines how to sign and verify text. Applications must add their own
replay protection, audience restriction, typed data, and consent rules.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- Lengths are measured in bytes.
- Strings are encoded as UTF-8.
- Hexadecimal strings do not include a prefix.
- Multi-byte integers use big-endian byte order.

## Scope

This document specifies:

- the NOMS payload format,
- the hash used to produce the signed digest,
- the signing and verification procedures, and
- canonical text encodings.

This document does not specify:

- replay protection,
- nonce formats,
- audience binding,
- structured or typed data, or
- user-interface requirements beyond the security guidance below.

Applications requiring those properties MUST define them at a higher layer.

## Payload Format

A NOMS payload is the concatenation of three fields:

```text
payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE
```

### MAGIC\_HEADER

`MAGIC_HEADER` is a fixed 25-byte constant used for domain separation.

String representation:

```text
\x18Nano Off-chain Message:\n
```

Hexadecimal representation:

```text
18 4e 61 6e 6f 20 4f 66 66 2d 63 68 61 69 6e 20 4d 65 73 73 61 67 65 3a 0a
```

Implementations MUST use this exact byte sequence.

### MESSAGE\_LENGTH

`MESSAGE_LENGTH` is a 4-byte unsigned integer encoding the exact byte length of `MESSAGE`.

Requirements:

- Implementations MUST encode the value as `uint32`.
- Implementations MUST use big-endian byte order.
- The value MUST count UTF-8 bytes, not characters.

The maximum encodable message length is `4294967295` bytes.

Example:

A 124-byte message is encoded as:

```text
00 00 00 7c
```

### MESSAGE

`MESSAGE` is the application message encoded as UTF-8 bytes.

Requirements:

- The signer MUST encode the original text as UTF-8.
- The verifier MUST reconstruct the payload from the exact original message.
- Implementations MUST NOT normalize, trim, or otherwise transform the message.
- Line endings, whitespace, and Unicode content are part of the signed bytes.

## Hashing

The complete `payload` is hashed using Blake2b with a 32-byte output.

```text
message_hash = Blake2b256(payload)
```

Implementations MUST use the same Blake2b-256 behavior used by Nano for block hashing.

## Signing

To produce a NOMS signature, an implementation MUST perform the following steps:

1. Encode the application message as UTF-8 bytes.
2. Construct `payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE`.
3. Compute `message_hash = Blake2b256(payload)`.
4. Sign `message_hash` using the same account-signing behavior used by Nano for block hashes.

Formally:

```text
signature = NanoAccountSign(private_key, message_hash)
```

Where:

- `private_key` is the 32-byte Nano account private key,
- `message_hash` is the 32-byte Blake2b-256 digest of the NOMS payload, and
- `signature` is the resulting Ed25519-compatible signature.

Implementations:

- MUST produce signatures accepted by Nano's block-signature verification,
- MUST sign the 32-byte digest, not the raw message, and
- MUST NOT substitute Ed25519ph, Ed25519ctx, or another signing variant.

## Verification

To verify a NOMS signature, an implementation MUST:

1. Obtain the signer's public key or account identifier.
2. Encode the application message as UTF-8 bytes.
3. Construct the payload exactly as specified.
4. Compute `message_hash = Blake2b256(payload)`.
5. Verify the signature against `message_hash` using Nano-compatible account-signature verification.

Formally:

```text
valid = NanoAccountVerify(public_key, message_hash, signature)
```

Verification MUST fail if:

- the message bytes differ in any way from the originally signed bytes
- the payload format is malformed
- the account identifier does not decode to the supplied public key
- the signature is invalid

## Canonical Encodings

For interoperability, implementations SHOULD use the following textual forms.

### Signature Encoding

A NOMS signature SHOULD be represented as:

- exactly 128 hexadecimal characters,
- lowercase, and
- without a `0x` prefix.

Each byte of the 64-byte signature MUST be encoded as exactly two lowercase hexadecimal characters, zero-padded where necessary. Variable-length or bignum-style hex encoding MUST NOT be used.

Verifiers MAY accept uppercase hexadecimal as input for compatibility, but emitters SHOULD produce lowercase.

### Account Encoding

An account identifier SHOULD be represented as:

- a lowercase `nano_` address,
- that encodes the public key used for verification.

Verifiers MAY accept equivalent legacy forms, such as `xrb_`, for compatibility. If an account string is supplied, it MUST decode to the same public key used in signature verification.

## Interoperability Conventions

NOMS does not define a transport format. An application SHOULD carry the
message, account, and signature together in a structured object.

Suggested transport shape:

```json
{
  "account": "nano_1natrium143q...",
  "message": "ChallengeNonce: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "signature": "e9b0a3...1c4f"
}
```

When integrating with wallet APIs that expect only a signature result, implementations SHOULD return the canonical signature string.

NOMS does not define or require a recovery identifier.

## Security Considerations

### Domain Separation

The fixed binary header provides domain separation between NOMS payloads and other signed data. Implementations MUST use the exact `MAGIC_HEADER` defined in this document.

### Replay Protection

NOMS does not prevent replay on its own. Applications that require freshness or single-use authorization MUST include their own replay-resistant context inside the signed message, such as:

- a nonce
- a timestamp
- an expiration time
- an audience or origin binding
- an application-specific challenge identifier

### User Consent

Wallets and signing agents SHOULD present the exact message being signed in a human-readable form. Signing opaque or transformed content increases the risk of user confusion and misuse.

### Encoding Integrity

Implementations MUST preserve the exact message bytes. Any normalization or transformation can invalidate signatures or create inconsistent verification behavior across platforms.

### Resource Limits

Although `MESSAGE_LENGTH` permits very large messages, implementations SHOULD apply practical size limits before allocation, parsing, or hashing, according to local policy.

## Implementation Notes

The NOMS frame adds 29 bytes:

- 25 bytes for `MAGIC_HEADER`
- 4 bytes for `MESSAGE_LENGTH`

An implementation can process the payload as a stream:

1. Read and validate the 25-byte header.
2. Read the 4-byte length as `L`.
3. Process the next `L` message bytes.
4. Hash each part as it is read.
5. Verify the resulting digest and signature.

A contiguous full-payload buffer is not required.

## Published Test Vectors

The following vectors are canonical for ORIS-001. Independent TypeScript and
Rust implementations produce the same values.

### Keypair

Both vectors below use the same keypair.

The private key is a raw 32-byte account private key in the format produced by
[`PlasmaPower/nano-vanity`](https://github.com/PlasmaPower/nano-vanity). Some
desktop wallets call this an "adhoc key."

The private key is **not** a Nano wallet seed. Treating it as a seed produces a
different keypair.

```
private key : 681fd5ed71a9f81e9d29e3450f6cd8aacb87346fd21a26003389290b9d0cb173
public key  : d2b3c9d00ffb55e84e7979d67308a515fb07ca79e40a77eb1aafe62881781783
account     : nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 1 — Non-ASCII UTF-8 with emoji

```
message (string)       : Hej Nano!🥦
message (UTF-8 hex)    : 48656a204e616e6f21f09fa5a6
message (byte length)  : 13

payload (hex, 42 bytes):
  184e616e6f204f66662d636861696e204d6573736167653a0a
  0000000d
  48656a204e616e6f21f09fa5a6

Blake2b-256 digest     : 33ce285b257df1ba87e1a91f32211a3b900ab4fdf68bebb3f75bef4b85aef951

signature              : 535c745819d0f40056f3c46402b4fae4356b3a8897bde99c955d411920e740d
                         781e6dddcbde228e8b86c4383a1003f9f315519ff73bd356f561d19865dc90f09
```

### Vector 2 — Empty message

```
message (string)       : (empty)
message (UTF-8 hex)    : (empty)
message (byte length)  : 0

payload (hex, 29 bytes):
  184e616e6f204f66662d636861696e204d6573736167653a0a
  00000000

Blake2b-256 digest     : 977a10e19a7857eefad986d73b071bbb7dad60846c7785f6d0ccffe0d7bd40b9

signature              : 8fca45d1490a276ac9d4376d9251df3a1069f673013c33d49f3490077066f174
                         d7fb6795b966e1d9078952ad065f836b35cd82d402cbeb63f9ace94b2123c506
```

## Reference Implementation

No reference implementation is listed yet. Implementations and examples are
informative. The requirements in this document are authoritative.
