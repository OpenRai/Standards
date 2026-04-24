```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Message Signing (NOMS)

> Status: Draft
> Category: Cryptographic Primitive / Application Interface

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements and recommendations.

Unless otherwise stated, all lengths are measured in bytes, all byte strings are serialized exactly as written, and all hexadecimal strings are unprefixed.

## 1. Abstract

This document defines a standard for authenticating arbitrary off-chain text messages using Nano account keys.

NOMS reuses Nano’s existing hashing and account-signing behavior. A message is first encoded as UTF-8, wrapped in a small domain-separated binary payload, hashed with Blake2b-256, and then signed using the same Nano-compatible signing primitive used for block signatures.

The result is a compact, deterministic, and easy-to-implement format for off-chain signatures without requiring any change to Nano’s underlying cryptographic foundations.

## 2. Motivation

As the Nano ecosystem expands to include agentic workflows, machine-to-machine micropayments, delegated authentication, and other off-chain coordination patterns, there is a need for accounts and agents to prove identity and intent outside the chain itself.

Signing raw message bytes directly is undesirable because it leaves room for ambiguity and cross-protocol misuse. A message signed for one purpose should not be trivially reusable in another context. Existing message-signing schemes in other ecosystems often rely on variable-length ASCII framing and parser-specific conventions, which can add unnecessary overhead and ambiguity.

NOMS addresses this by defining:

- a fixed domain-separation header
- an explicit 4-byte big-endian message length
- deterministic UTF-8 encoding rules for text input
- a signing flow that is compatible with Nano’s existing block-signature behavior

NOMS is a cryptographic primitive for authenticating off-chain text. It does not by itself provide replay protection, audience restriction, or a structured user-consent model.

## 3. Specification

This version of NOMS signs UTF-8 text messages.

Given an application message string, an implementation MUST:

1. encode the string as UTF-8 according to Section 3.1
2. construct the NOMS payload
3. hash the payload with Blake2b-256
4. sign the resulting 32-byte digest using the same account-signing behavior Nano uses for block hashes

### 3.1. Message Encoding and Payload Construction

The NOMS payload is a concatenated byte array with three strictly ordered components:

```text
payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE
```

If the application input is a string, it MUST be converted to`MESSAGE` as follows:

- UTF-8 encoding MUST be used
- a UTF-8 BOM MUST NOT be added
- implementations MUST NOT normalize Unicode
- implementations MUST NOT trim whitespace
- implementations MUST NOT rewrite line endings
- implementations MUST NOT append a terminating NUL byte

`MESSAGE_LENGTH` is the exact number of UTF-8 bytes in`MESSAGE`, not the number of Unicode code points or characters.

#### Component 1: Magic Header (25 bytes)

`MAGIC_HEADER` is the following fixed byte sequence:

```text
\x18Nano Off-chain Message:\n
```

Hexadecimal form:

```text
18 4e 61 6e 6f 20 4f 66 66 2d 63 68 61 69 6e 20 4d 65 73 73 61 67 65 3a 0a
```

The first byte is`0x18` (decimal 24), which matches the byte length of the following ASCII string`Nano Off-chain Message:\n`. The complete header is therefore 25 bytes.

This header provides domain separation. NOMS signatures are generated over a distinct payload format rather than over raw message bytes or raw Nano protocol values.

Any future incompatible revision of this standard MUST define a different`MAGIC_HEADER`.

#### Component 2: Message Length (4 bytes)

`MESSAGE_LENGTH` is a 32-bit unsigned integer encoded in big-endian byte order.

Example:

- a 124-byte message is encoded as`00 00 00 7c`

The format supports message lengths up to`2^32 - 1` bytes.

Implementations MAY impose lower operational limits for memory, latency, or denial-of-service protection. Messages exceeding an implementation’s configured maximum MUST be rejected.

#### Component 3: Message (variable length)

`MESSAGE` is the raw UTF-8 byte sequence of the application text.

### 3.2. Hashing

The constructed`payload` MUST be hashed with Blake2b using a 256-bit digest:

```text
message_hash = Blake2b256(payload)
```

This is the same digest size Nano uses for block hashes.

The result,`message_hash`, is exactly 32 bytes.

### 3.3. Signing

NOMS uses the same signing model Nano uses for block signatures.

After computing`message_hash`, implementations MUST sign that 32-byte digest exactly as a Nano block hash would be signed by the same account key. NOMS does not define a new signature primitive; it reuses Nano’s existing account-signing behavior unchanged and substitutes the NOM`message_hash` in place of a block hash.

Formally:

```text
signature = NanoAccountSign(private_key, message_hash)
```

Where:

-`private_key` is the 32-byte Nano account private key
-`message_hash` is the 32-byte Blake2b-256 digest from Section 3.2
-`signature` is the resulting 64-byte Nano-compatible signature

Requirements:

- implementations MUST be verification-compatible with Nano block signatures for the same key material and digest
- implementations MUST NOT substitute Ed25519ph, Ed25519ctx, or any other alternate signing mode not used by Nano itself
- implementations MUST NOT hash the payload a second time before calling the Nano signing primitive
- implementations using libraries that require expanded or combined secret-key representations MUST derive those representations from the 32-byte Nano private key as required by the library

In practice, implementations SHOULD call the same signing function they already use for Nano blocks.

### 3.4. Verification

To verify a NOMS signature, an implementation MUST:

1. obtain the signer’s public key, either directly or by decoding the provided Nano account address
2. UTF-8 encode the message exactly as specified in Section 3.1
3. construct`payload = MAGIC_HEADER || be32(len(MESSAGE)) || MESSAGE`
4. compute`message_hash = Blake2b256(payload)`
5. verify the signature against`message_hash` using the same Nano-compatible verification primitive used for block signatures
6. reject on any failure in decoding, encoding, length handling, or signature verification

Verification MUST be performed over the exact message bytes implied by the original application string. Any transformation of the text before verification changes the signed message.

## 4. Canonical Encodings and Interoperability

The core NOMS primitive is the payload, hash, and signature process defined in Section 3. Transport objects and wallet API mappings are secondary interoperability conventions.

### 4.1. Signature String Encoding

When a NOMS signature is represented as a string, the canonical form is:

- exactly 128 hexadecimal characters
- lowercase
- no`0x` prefix

Applications and wallets SHOULD emit lowercase hexadecimal.

Verifiers MAY accept uppercase or mixed-case hexadecimal for compatibility, but lowercase without a prefix is the canonical serialized form.

### 4.2. Account Identifiers

When a signer account is included alongside a NOMS signature, the canonical textual account form is a lowercase`nano_` address.

For compatibility, verifiers MAY accept legacy`xrb_` addresses if their environment already supports them, but`nano_` is the canonical form for new integrations.

If an account string is provided, it MUST decode to the same public key used for signature verification.

### 4.3. Suggested Transport Envelope

Applications that need to transmit both the signature and its context SHOULD use a structured object containing at least the signed message, the signer account, and the signature.

Suggested fields:

| Field | Type | Requirement | Notes |
|---|---|---|---|
| account | string | SHOULD | Canonical form is lowercase`nano_` |
| message | string | SHOULD | The exact text that was UTF-8 encoded and signed |
| signature | string | MUST | 128-character lowercase hex string |

Example:

```json
{
  "account": "nano_1example...",
  "message": "ChallengeNonce: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "signature": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

### 4.4. Wallet API Mapping

Some wallet APIs expect a flat message-signature result rather than a structured object.

When NOMS is adapted to such an interface, the returned value SHOULD be the canonical`signature` string alone unless the surrounding API explicitly supports returning additional context.

NOMS does not define a`recoveryId`, because Nano-compatible account signatures do not use recovery-based public-key reconstruction.

## 5. Security Considerations

### 5.1. Domain Separation

NOMS signs a domain-separated payload, not raw message bytes. This prevents direct reinterpretation of a NOMS signature as authorization over an arbitrary raw 32-byte Nano protocol value.

A successful cross-protocol forgery would require defeating the relevant security properties of Blake2b-256 or the Nano-compatible signature primitive, which are assumed computationally infeasible.

### 5.2. Replay Protection

NOMS authenticates a message, but it does not by itself prove freshness or restrict where the message may be replayed.

Applications using NOMS for authentication SHOULD include context such as:

- the relying-party domain or service name
- a nonce or challenge
- a timestamp and/or expiration time
- the intended action
- an audience, session identifier, or request identifier when relevant

### 5.3. Human-Readable Consent

NOMS is a cryptographic primitive, not a full consent or sign-in specification.

If NOMS is used in user-facing wallets, the wallet SHOULD display the exact message being signed as clearly as possible. Applications SHOULD avoid prompting users to sign vague or opaque text.

Higher-level application standards may define structured message templates or consent UX on top of NOM.

### 5.4. Message Encoding Pitfalls

Any change to Unicode normalization, line endings, whitespace, or invisible characters changes the signed bytes.

Implementations MUST treat the original message text as exact data, not as content to be reformatted for convenience.

### 5.5. Resource Limits

Although the encoding permits message sizes up to`2^32 - 1` bytes, large messages may be impractical or unsafe to process in constrained environments.

Implementations SHOULD enforce reasonable message-size limits and SHOULD prefer streaming hash implementations for large inputs.

## 6. Implementation Notes

The NOMS framing overhead is always 29 bytes:

- 25 bytes of`MAGIC_HEADER`
- 4 bytes of`MESSAGE_LENGTH`

This makes the framing easy to parse in both high-level and low-level environments.

A parser can process a NOMS payload as follows:

1. read and compare the first 25 bytes against`MAGIC_HEADER`
2. read the next 4 bytes as a big-endian`uint32`, giving length`L`
3. read exactly`L` bytes as`MESSAGE`
4. hash`MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE`
5. verify the signature using the signer’s public key

Implementations do not need to allocate the entire payload as a single contiguous buffer. The hash can be computed incrementally by feeding the header, length, and message bytes in sequence.

## 7. Test Vectors

Before this standard advances beyond Draft, interoperable test vectors SHOULD be published.

At minimum, the published vectors SHOULD include:

- an empty message
- a short ASCII message
- a message containing newline characters
- a Unicode message containing non-ASCII UTF-8 bytes
- messages at boundary lengths such as 255 and 256 bytes

Each test vector SHOULD include:

- the 32-byte private key in hex
- the derived public key in hex
- the canonical`nano_` account
- the original message string
- the UTF-8 message bytes in hex
- the complete payload in hex
- the Blake2b-256`message_hash` in hex
- the final signature in canonical hex form

## 8. Summary

NOMS defines a compact and domain-separated way to sign off-chain UTF-8 text messages with Nano account keys.

Its design goals are:

- compatibility with Nano’s existing cryptographic behavior
- deterministic cross-language encoding
- minimal framing overhead
- straightforward implementation across different environments

Future standards may build on NOMS to define richer authentication, delegation, or human-consent message formats, but this document is intentionally limited to the signing primitive and its basic interoperability conventions.
