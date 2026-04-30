```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Message Signing (NOMS)

> Status: Draft\
> Category: Cryptographic Primitive / Application Interface

## Abstract

A compact and deterministic format for signing arbitrary off-chain text with Nano account keys.

NOMS encodes a UTF-8 message inside a fixed, domain-separated binary payload, hashes that payload with Blake2b-256, and signs the resulting digest using Nano-compatible account-signing behavior. The result is a simple and interoperable signing primitive for off-chain authentication without changing Nano's cryptographic foundations.

## Motivation

Nano accounts are increasingly used outside the chain itself, including in delegated authentication, wallet-to-application flows, and machine-to-machine coordination.

Signing raw message bytes is undesirable because it provides no protocol separation and leaves too much room for inconsistent handling across implementations. NOMS addresses this by defining a single canonical payload format with:

- a fixed domain-separation header
- an explicit message length
- deterministic UTF-8 encoding
- Nano-compatible hashing and signing behavior

NOMS is intentionally minimal. It defines how a text message is signed and verified. It does not attempt to provide replay protection, audience restriction, typed data encoding, or a structured consent model.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- all lengths are measured in bytes
- all strings are UTF-8
- all hexadecimal strings are unprefixed
- all multi-byte integers are encoded in big-endian order

## Scope

This document specifies:

- the payload format for Nano Off-chain Messages
- the hashing step used to derive the signed digest
- the signing and verification procedure
- canonical textual encodings for interoperability

This document does not specify:

- replay protection
- nonce formats
- audience binding
- structured or typed data
- user-interface requirements beyond basic security guidance

Applications requiring those properties MUST define them at a higher layer.

## Payload Format

A NOMS payload is the concatenation of three fields:

```text
payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE
```

### MAGIC_HEADER

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

### MESSAGE_LENGTH

`MESSAGE_LENGTH` is a 4-byte unsigned integer encoding the exact byte length of`MESSAGE`.

Requirements:

- it MUST be encoded as`uint32`
- it MUST use big-endian byte order
- it represents the length of the UTF-8 byte sequence, not the number of characters

The maximum encodable message length is`4294967295` bytes.

Example:

A 124-byte message is encoded as:

```text
00 00 00 7c
```

### MESSAGE

`MESSAGE` is the application message encoded as UTF-8 bytes.

Requirements:

- the signer MUST encode the original text as UTF-8 before constructing the payload
- the verifier MUST reconstruct the payload from the exact original message bytes
- implementations MUST NOT normalize, trim, or otherwise transform the message before hashing
- line endings, whitespace, and Unicode content are part of the signed message exactly as encoded

## Hashing

The complete`payload` is hashed using Blake2b with a 32-byte output.

```text
message_hash = Blake2b256(payload)
```

Implementations MUST use the same Blake2b-256 behavior used by Nano for block hashing.

## Signing

To produce a NOMS signature, an implementation MUST perform the following steps:

1. Encode the application message as UTF-8 bytes.
2. Construct`payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE`.
3. Compute`message_hash = Blake2b256(payload)`.
4. Sign`message_hash` using the same account-signing behavior used by Nano for block hashes.

Formally:

```text
signature = NanoAccountSign(private_key, message_hash)
```

Where:

-`private_key` is the 32-byte Nano account private key
-`message_hash` is the 32-byte Blake2b-256 digest of the NOMS payload
-`signature` is the resulting Ed25519-compatible signature

Implementations:

- MUST produce signatures verifiable by Nano-compatible Ed25519 verification used for block signatures
- MUST sign the 32-byte digest, not the raw message
- MUST NOT use alternate signing variants such as Ed25519ph or Ed25519ctx unless they are exactly the Nano account-signing behavior, which NOMS does not define

## Verification

To verify a NOMS signature, an implementation MUST:

1. Obtain the signer's public key or account identifier.
2. Encode the application message as UTF-8 bytes.
3. Construct the payload exactly as specified.
4. Compute`message_hash = Blake2b256(payload)`.
5. Verify the signature against`message_hash` using Nano-compatible account-signature verification.

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

- 128 hexadecimal characters
- lowercase
- no`0x` prefix

Each byte of the 64-byte signature MUST be encoded as exactly two lowercase hexadecimal characters, zero-padded where necessary. Variable-length or bignum-style hex encoding MUST NOT be used.

Verifiers MAY accept uppercase hexadecimal as input for compatibility, but emitters SHOULD produce lowercase.

### Account Encoding

An account identifier SHOULD be represented as:

- a lowercase`nano_` address
- encoding the public key used for verification

Verifiers MAY accept equivalent legacy forms, such as`xrb_`, for compatibility. If an account string is supplied, it MUST decode to the same public key used in signature verification.

## Interoperability Conventions

NOMS defines the signing primitive itself. Applications transporting signed messages SHOULD use a structured object that carries the signing context alongside the signature.

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

The fixed binary header provides domain separation between NOMS payloads and other signed data. Implementations MUST use the exact`MAGIC_HEADER` defined in this document.

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

Although`MESSAGE_LENGTH` permits very large messages, implementations SHOULD apply practical size limits before allocation, parsing, or hashing, according to local policy.

## Implementation Notes

NOMS has a constant framing overhead of 29 bytes:

- 25 bytes for`MAGIC_HEADER`
- 4 bytes for`MESSAGE_LENGTH`

This allows straightforward incremental processing. A verifier or parser can:

1. read and validate the 25-byte header
2. read the 4-byte length
3. process the next`L` message bytes
4. hash the stream as it is read
5. verify the final digest and signature

A contiguous full-payload buffer is not required.

## Published Test Vectors

The following vectors are canonical for ORIS-001. All values are confirmed by independent implementations in TypeScript (using `nanocurrency` and `blakejs`) and Rust (using `ed25519-dalek` and `blake2b`).

### Keypair

Both vectors below use the same keypair.

The private key is a raw 32-byte Ed25519 account private key in the format produced by [`PlasmaPower/nano-vanity`](https://github.com/PlasmaPower/nano-vanity) — sometimes referred to as an "adhoc key" in desktop wallets. It is **not** a Nano wallet seed. A seed-based wallet that interprets this value as a seed will derive a different keypair entirely.

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

(to be added) Any reference implementation is informative only and does not override the normative requirements in this document.

## Summary

NOMS defines a compact, domain-separated, deterministic method for signing off-chain UTF-8 text with Nano account keys.

Its design goals are:

- compatibility with Nano's existing cryptographic behavior
- deterministic cross-language encoding
- minimal framing overhead
- simple signing and verification
