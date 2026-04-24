```
OpenRai Initiative Standard: 001
```

# Nano Off-chain Messages (NOMs)

> Status: Draft
> Category: Cryptographic Primitive / Application Interface

## Abstract

This document defines a standard for off-chain message signing and verification using Nano account keys. It establishes a canonical message format, encoding rules, and verification procedure to enable interoperable off-chain communication authenticated by Nano private keys.

## Motivation

Nano account key pairs can be used to sign arbitrary data, not just block lattice transactions. Defining a standard message format enables wallets and applications to provide provable, human-readable signatures without requiring an on-chain transaction — useful for authentication, attestation, and inter-application messaging.

## Specification

### Message Format

A NOM is a UTF-8 encoded string composed of the following fields, joined by newline (`\n`) characters:

```
nano-off-chain-message
version:1
account:<nano_account>
timestamp:<unix_epoch_seconds>
message:<arbitrary_utf8_payload>
```

### Signing

The canonical message string MUST be hashed with BLAKE2b-256 before signing. The resulting 32-byte digest is signed using the account's Ed25519 private key, producing a 64-byte signature.

### Verification

1. Reconstruct the canonical message string from the provided fields.
2. Compute the BLAKE2b-256 hash of the canonical string.
3. Verify the Ed25519 signature against the hash using the public key derived from the `account` field.

## Rationale

Using BLAKE2b-256 aligns with the hashing algorithm already used throughout the Nano protocol, reducing the dependency surface for implementers. Ed25519 is the native signature scheme of Nano accounts.

## Backwards Compatibility

This is a new standard and introduces no breaking changes to the Nano protocol.

## Reference Implementation

_To be provided._

## Copyright

This document is placed in the public domain.
