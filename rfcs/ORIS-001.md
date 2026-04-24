```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Message Signing (NOMS)

> Status: Draft
> Category: Cryptographic Primitive / Application Interface

## Abstract

This document defines Nano Off-chain Messages (NOMs), a compact and deterministic format for signing arbitrary off-chain text with Nano account keys.

A NOMS message is encoded as UTF-8, wrapped in a domain-separated binary payload, hashed with Blake2b-256, and signed using the same Nano-compatible account-signing behavior used for block signatures.

The purpose of NOMS is to provide an interoperable off-chain signing primitive without changing Nano’s underlying cryptographic model.

## Motivation

As the Nano ecosystem expands to include agentic workflows, machine-to-machine payments, delegated authentication, and other off-chain coordination patterns, there is a need for Nano accounts to authenticate messages outside the ledger itself.

Signing raw message bytes directly is undesirable because it creates ambiguity and increases the risk of cross-protocol misuse. A message signed for one purpose should not be trivially reusable in another. Existing schemes in other ecosystems often rely on variable-length textual framing, which can be less attractive for compact or low-level implementations.

NOMS addresses this by defining:

- a fixed domain-separation header
- an explicit 4-byte big-endian message length
- deterministic UTF-8 encoding rules
- a signing flow compatible with Nano’s existing account-signature behavior

NOMS is a primitive for authenticating off-chain text. It does not by itself provide replay protection, audience restriction, typed data, or user-consent semantics.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- all lengths are measured in bytes
- all strings are UTF-8 text strings
- all hexadecimal strings are unprefixed
- all multi-byte integers are unsigned
- all byte strings are serialized exactly as written

## Specification

### Scope

This version of NOMS defines signing and verification for text messages.

Applications that require replay resistance, audience restriction, expiration, typed fields, or richer consent semantics MUST define those at a higher layer.

### Message Model

The application input to NOMS is a text string.

That string MUST be converted into a byte sequence named`MESSAGE` as specified in Section 3.3, then wrapped in a NOMS payload, hashed, and signed.

### Payload Format

A NOMS payload is the concatenation of three fields:

```text
payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE
```

Where:

-`MAGIC_HEADER` is a fixed 25-byte constant
-`MESSAGE_LENGTH` is a 4-byte unsigned integer in big-endian byte order
-`MESSAGE` is the UTF-8 byte sequence of the application message

### Magic Header

`MAGIC_HEADER` MUST be exactly the following 25-byte sequence:

```text
\x18Nano Off-chain Message:\n
```

Hexadecimal form:

```text
18 4e 61 6e 6f 20 4f 66 66 2d 63 68 61 69 6e 20 4d 65 73 73 61 67 65 3a 0a
```

The first byte,`0x18`, is part of the domain separator and also equals the byte length of the following ASCII string`Nano Off-chain Message:\n`, which is 24 bytes long.

Verifiers MUST reject any payload whose header does not exactly match this value.

Future incompatible revisions of this specification MUST define a different`MAGIC_HEADER`.

### Message Length

`MESSAGE_LENGTH` MUST be the exact byte length of`MESSAGE`, encoded as a 32-bit unsigned integer in big-endian order.

The maximum representable length is $2^{32}-1$ bytes.

Implementations MAY enforce lower local limits for operational or security reasons. Messages exceeding an implementation-defined limit MUST be rejected.

### Message Encoding

If the application input is a string,`MESSAGE` MUST be produced as follows:

- encode the string as UTF-8
- do not prepend a UTF-8 BOM
- do not normalize Unicode
- do not trim or otherwise alter whitespace
- do not rewrite line endings
- do not append a terminating NUL byte

`MESSAGE_LENGTH` is the number of UTF-8 bytes in`MESSAGE`, not the number of characters or Unicode code points.

### Hashing

The payload MUST be hashed with Blake2b using a 256-bit digest:

```text
message_hash = Blake2b256(payload)
```

The resulting`message_hash` is exactly 32 bytes.

### Signing

To produce a NOMS signature:

1. encode the application string as`MESSAGE`
2. construct`payload = MAGIC_HEADER || MESSAGE_LENGTH || MESSAGE`
3. compute`message_hash = Blake2b256(payload)`
4. sign`message_hash` using the same Nano-compatible account-signing behavior used for block hashes

Formally:

```text
signature = NanoAccountSign(private_key, message_hash)
```

Where:

-`private_key` is the 32-byte Nano account private key
-`message_hash` is the 32-byte digest from the previous step
-`signature` is the resulting 64-byte signature

Implementations:

- MUST be verification-compatible with Nano block-signature verification for the same key material and digest
- MUST NOT apply a second hash before signing
- MUST NOT substitute Ed25519ph, Ed25519ctx, or any alternate signing mode not used by Nano block signatures
- SHOULD call the same signing routine already used for Nano blocks, where available

### Verification

To verify a NOMS signature, an implementation MUST:

1. obtain the signer’s public key, either directly or by decoding a Nano account address
2. encode the message exactly as specified above
3. construct the payload exactly as specified above
4. compute`message_hash = Blake2b256(payload)`
5. verify the signature against`message_hash` using the same Nano-compatible verification behavior used for block signatures
6. reject on any failure in decoding, encoding, length handling, payload construction, hashing, or signature verification

Verification MUST be performed over the exact message bytes implied by the original application input. Any transformation of the text changes the signed message.

### Canonical Encodings

When serialized as text, a NOMS signature SHOULD be encoded as:

- exactly 128 hexadecimal characters
- lowercase
- no`0x` prefix

Verifiers MAY accept uppercase or mixed-case hexadecimal for compatibility, but lowercase hexadecimal is canonical.

When a signer account is included, the canonical textual form SHOULD be a lowercase`nano_` address.

Verifiers MAY accept legacy`xrb_` addresses if supported by the local environment.

If an account string is provided, it MUST decode to the same public key used for verification.

### Interoperability Conventions

Applications that transmit a NOMS signature together with its context SHOULD include at least:

- the signer account
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

### Security Considerations

NOMS signs a distinct binary envelope rather than raw message bytes. This provides domain separation and reduces the risk that a signature produced for one purpose can be reinterpreted for another.

NOMS authenticates message content, but not freshness. Applications using NOMS for authentication or authorization SHOULD include replay-resistant context such as:

- domain or service name
- nonce or challenge
- timestamp or expiration
- intended action
- session or request identifier

Wallets SHOULD display the exact message being signed wherever possible. Applications SHOULD avoid vague or opaque signing prompts.

Because whitespace changes, line-ending changes, normalization changes, and invisible characters all change the signed bytes, implementations MUST treat the original message text as exact data.

Although the format permits messages up to $2^{32}-1$ bytes, implementations SHOULD enforce reasonable limits and SHOULD use incremental hashing where appropriate.

### Test Vectors

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

## Rationale

The motivation for NOMS is the need for off-chain authentication with Nano account keys. The rationale for this specific design is as follows.

A fixed binary header was chosen instead of signing raw message bytes so that NOMS signatures are domain-separated from other possible uses of the same signing key.

The`MAGIC_HEADER` includes a leading`0x18` byte so the prefix is structurally non-textual and easy to recognize. It also mirrors the 24-byte length of the following ASCII literal`Nano Off-chain Message:\n`.

A fixed-width 4-byte big-endian length field was chosen instead of decimal ASCII length encoding to keep parsing simple, unambiguous, and constant-overhead.

UTF-8 was chosen as the message encoding because it is widely supported across platforms and can represent arbitrary Unicode text. The prohibition on normalization and rewriting ensures deterministic cross-language behavior.

Blake2b-256 was chosen because it matches Nano’s existing digest size and hashing model.

Signing the 32-byte NOMS digest with the same Nano-compatible signing behavior used for block hashes was chosen to maximize implementation reuse and avoid introducing a second account-signature mode into the ecosystem.

Canonical lowercase hexadecimal and lowercase`nano_` account strings were chosen to reduce avoidable serialization variance across applications.

## Reference Implementation

This section is non-normative.

A minimal reference implementation can be expressed as follows.

```ts
const MAGIC_HEADER = Uint8Array.from([
    0x18,0x4e,0x61,0x6e,0x6f,0x20,0x4f,0x66,0x66,0x2d,
    0x63,0x68,0x61,0x69,0x6e,0x20,0x4d,0x65,0x73,0x73,
    0x61,0x67,0x65,0x3a,0x0a
]);

function be32(n: number): Uint8Array {
    if (!Number.isInteger(n) || n < 0 || n > 0xffffffff) {
        throw new Error("invalid length");
    }

    return Uint8Array.from([
        (n >>> 24) & 0xff,
        (n >>> 16) & 0xff,
        (n >>> 8) & 0xff,
        n & 0xff
    ]);
}

function nomPayload(message: string): Uint8Array {
    const msg = utf8EncodeExact(message);
    const len = be32(msg.length);
    return concatBytes(MAGIC_HEADER, len, msg);
}

function signNom(
    privateKey: Uint8Array,
    message: string
): Uint8Array {
    const payload = nomPayload(message);
    const messageHash = blake2b256(payload);
    return nanoAccountSign(privateKey, messageHash);
}

function verifyNom(
    publicKey: Uint8Array,
    message: string,
    signature: Uint8Array
): boolean {
    const payload = nomPayload(message);
    const messageHash = blake2b256(payload);
    return nanoAccountVerify(publicKey, messageHash, signature);
}
```
