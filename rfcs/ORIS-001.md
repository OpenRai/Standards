```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Message Signing (NOMS)

> Status: Draft
> Category: Cryptographic Primitive / Application Interface

## 1. Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as normative requirements.

Unless otherwise stated:

- all lengths are in bytes
- all strings are UTF-8 text strings
- all hexadecimal strings are unprefixed
- all multi-byte integers are unsigned

## 2. Abstract

This document specifies Nano Off-chain Messages (NOMs), a compact format for signing arbitrary off-chain text with Nano account keys.

A NOMS message is encoded as UTF-8, wrapped in a fixed domain-separated binary envelope, hashed with Blake2b-256, and signed using the same Nano-compatible account-signing behavior used for block signatures.

The purpose of NOMS is to provide a deterministic, low-overhead, interoperable signing primitive for off-chain authentication without modifying Nano’s underlying cryptographic model.

## 3. Scope

NOMS defines a signing and verification format for off-chain text messages.

NOMS does not by itself provide:

- replay protection
- audience restriction
- structured consent semantics
- typed data encoding

Applications that require those properties MUST provide them at a higher layer.

## 4. Payload Format

A NOMS payload is the concatenation of three fields:

```text
payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE
```

Where:

-`MAGIC_HEADER` is a fixed 25-byte constant
-`MESSAGE_LENGTH` is a 4-byte big-endian unsigned integer
-`MESSAGE` is the UTF-8 byte sequence of the application message

### 4.1. Magic Header

`MAGIC_HEADER` MUST be exactly the following 25-byte sequence:

```text
\x18Nano Off-chain Message:\n
```

Hexadecimal form:

```text
18 4e 61 6e 6f 20 4f 66 66 2d 63 68 61 69 6e 20 4d 65
73 73 61 67 65 3a 0a
```

This constant provides domain separation. A verifier MUST reject any payload whose header does not exactly match this value.

Future incompatible revisions of this specification MUST use a different header.

### 4.2. Message Length

`MESSAGE_LENGTH` MUST be the exact byte length of`MESSAGE`, encoded as a 32-bit unsigned integer in big-endian order.

The maximum representable length is $2^{32}-1$ bytes.

Implementations MAY enforce lower local limits. If a message exceeds an implementation-defined limit, it MUST be rejected.

### 4.3. Message Encoding

If the application input is a string,`MESSAGE` MUST be produced as follows:

- encode the string as UTF-8
- do not prepend a UTF-8 BOM
- do not normalize Unicode
- do not alter whitespace
- do not rewrite line endings
- do not append a terminating NUL byte

`MESSAGE_LENGTH` is the number of UTF-8 bytes, not the number of characters or Unicode code points.

## 5. Signing

To produce a NOMS signature for a message string:

1. Encode the message as`MESSAGE` according to Section 4.3.
2. Construct`payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE`.
3. Compute:

```text
message_hash = Blake2b256(payload)
```

4. Sign`message_hash` using the same Nano-compatible account-signing behavior used for block hashes.

Formally:

```text
signature = NanoAccountSign(private_key, message_hash)
```

Where:

-`private_key` is the 32-byte Nano account private key
-`message_hash` is the 32-byte Blake2b-256 digest
-`signature` is a 64-byte signature

Implementations:

- MUST be verification-compatible with Nano block-signature verification for the same key and digest
- MUST NOT apply a second hash before signing
- MUST NOT substitute Ed25519ph, Ed25519ctx, or any alternate signing mode not used by Nano block signatures

## 6. Verification

To verify a NOMS signature, an implementation MUST:

1. obtain the signer’s public key, either directly or by decoding a Nano account address
2. encode the message exactly as specified in Section 4.3
3. construct the payload exactly as specified in Section 4
4. compute`message_hash = Blake2b256(payload)`
5. verify the signature against`message_hash` using the same Nano-compatible verification behavior used for block signatures
6. reject on any failure in account decoding, message encoding, length handling, payload construction, hashing, or signature verification

Verification MUST be performed over the exact message bytes implied by the original application input. Any transformation changes the signed message and invalidates the signature.

## 7. Canonical Encodings

The core NOMS primitive is binary. This section defines canonical textual forms for interoperability.

### 7.1. Signature Encoding

When serialized as text, a NOMS signature SHOULD be encoded as:

- 128 hexadecimal characters
- lowercase
- no`0x` prefix

Verifiers MAY accept uppercase or mixed-case hexadecimal for compatibility, but lowercase hexadecimal is canonical.

### 7.2. Account Encoding

When a signer account is included, the canonical textual form SHOULD be a lowercase`nano_` address.

Verifiers MAY accept legacy`xrb_` addresses if supported by the local environment.

If an account string is provided, it MUST decode to the same public key used for verification.

## 8. Interoperability Conventions

Applications that transport a NOMS signature together with its context SHOULD include at least:

- the account
- the original message string
- the signature

Suggested JSON object:

```json
{
  "account": "nano_1example...",
  "message": "ChallengeNonce: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "signature": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

If NOMS is mapped into a wallet API that expects only a signature result, the implementation SHOULD return the canonical signature string.

NOMS does not define a recovery identifier.

## 9. Security Considerations

### 9.1. Domain Separation

NOMS signs a distinct binary envelope rather than raw message bytes. This reduces the risk that an off-chain signature can be reinterpreted as authorization for another purpose.

### 9.2. Replay

NOMS authenticates message content, not freshness. Applications using NOMS for login, session binding, or authorization SHOULD include replay-resistant context such as:

- domain or service name
- nonce or challenge
- timestamp or expiration
- intended action
- session or request identifier

### 9.3. User Consent

NOMS is a primitive, not a complete user-consent protocol.

Wallets SHOULD display the exact message being signed. Applications SHOULD avoid vague or opaque signing prompts.

### 9.4. Encoding Integrity

Invisible characters, normalization changes, whitespace changes, and line-ending rewrites all change the signed bytes.

Implementations MUST treat the original message text as exact data.

### 9.5. Resource Limits

Although the format permits messages up to $2^{32}-1$ bytes, very large messages may be impractical or unsafe.

Implementations SHOULD enforce reasonable size limits and SHOULD use incremental hashing where appropriate.

## 10. Implementation Notes

The framing overhead of NOMS is always 29 bytes:

- 25 bytes for`MAGIC_HEADER`
- 4 bytes for`MESSAGE_LENGTH`

This allows straightforward parsing and streaming.

A verifier can process input in order:

1. compare the first 25 bytes to`MAGIC_HEADER`
2. read the next 4 bytes as a big-endian length
3. read exactly that many message bytes
4. hash the header, length, and message
5. verify the signature

A contiguous payload buffer is not required.

## 11. Test Vectors

Before this specification advances beyond Draft, interoperable test vectors SHOULD be published.

At minimum, the set SHOULD include:

- an empty message
- a short ASCII message
- a message containing newlines
- a message containing non-ASCII UTF-8 text
- boundary-length messages, including 255 and 256 bytes

Each test vector SHOULD include:

- private key in hex
- public key in hex
- canonical`nano_` account
- original message string
- UTF-8 message bytes in hex
- full payload in hex
- Blake2b-256 digest in hex
- final signature in canonical hex form

## 12. Summary

NOMS defines a compact, domain-separated, deterministic method for signing off-chain UTF-8 text with Nano account keys.

Its goals are:

- compatibility with Nano’s existing signing behavior
- deterministic cross-language encoding
- minimal framing overhead
- simple implementation and verification
