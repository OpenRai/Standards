```
OpenRai Initiative Standard: 003
```

# NanoNym Payment Event Schema

> Status: Draft
> Category: Application Interface

## Abstract

This document defines the transport-agnostic, encryption-agnostic JSON structure used to represent a NanoNym stealth-payment notification. It is the canonical payload shared by all NanoNym transport and verification profiles.

## Motivation

NanoNym needs a single logical payment-event schema that remains stable across different transports, privacy models, and delivery methods.

This document separates the invariant payload from profile-specific concerns such as:

- transport mechanism
- encryption layer
- push versus proof-based delivery
- observer privacy model

Profiles may vary those concerns, but they share the same base payload schema.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- JSON objects are encoded using UTF-8
- hexadecimal strings are lowercase and unprefixed
- `R` denotes the ephemeral Ed25519 public key used as the stealth derivation input
- profile-specific extensions MUST preserve base-schema validity

## Specification

### Schema Definition

A payment event is a JSON object.

Required fields:

| Field | Type | Description |
|---|---|---|
| `version` | integer | Schema version. MUST be `2`. |
| `protocol` | string | Protocol identifier. MUST be `"nanonym"`. |
| `R` | string | Hex-encoded Ed25519 ephemeral public key (64 hex characters). |
| `tx_hash` | string | Hex-encoded hash of the on-chain send block (64 hex characters). |

Optional fields:

| Field | Type | Description |
|---|---|---|
| `amount_raw` | string | Decimal string of the payment amount in raw. |
| `memo` | string | Freeform UTF-8 text. |

### Example

```json
{
  "version": 2,
  "protocol": "nanonym",
  "R": "ab3f1e7c9d00000000000000000000000000000000000000000000000000fa08",
  "tx_hash": "9c21de5b3a0000000000000000000000000000000000000000000000000017f0",
  "amount_raw": "1000000000000000000000000000000"
}
```

The example above illustrates field shape only. It is not a cryptographic test vector and does not assert that `R` is a valid curve point.

### Validation Rules

1. `version` MUST be the integer `2`.
2. `protocol` MUST be the string `"nanonym"`.
3. `R` MUST be a 64-character lowercase hexadecimal string encoding a valid Ed25519 compressed point.
4. `tx_hash` MUST be a 64-character lowercase hexadecimal string.
5. `amount_raw`, if present, MUST be a decimal string with no leading zeros except `"0"`.
6. `memo`, if present, MUST be a valid UTF-8 string.
7. Implementations MUST reject payloads missing any required field.
8. Implementations MUST ignore unrecognized fields for forward compatibility.

Validation of `R` includes decoding the compressed Ed25519 point and rejecting malformed encodings. Implementations SHOULD also reject small-order points. Profile documents that use `R` for verification MAY impose stricter validation if their proof model requires it.

`tx_hash` identifies the Nano send block that transferred funds to the derived stealth account. Chain validation of that block, including confirmation state, destination, and amount, is profile-specific and is not performed by base-schema validation.

### Profile Extensibility

A valid profile payload MUST be a valid base-schema payload. Profiles MAY add fields. Profiles MUST NOT remove or redefine base-schema fields.

To reduce extension-field collisions:

1. Base-schema field names defined in this document are globally reserved.
2. A profile MAY reserve an unprefixed cryptographic symbol when that symbol is intrinsic to the proof model and is normatively defined by that profile.
3. All other profile-specific extension fields MUST use a stable profile prefix ending in `_`, such as `nostr_...` or `x402_...`.
4. Each profile document MUST define every extension field it reserves.

The `r` field defined by ORIS-005 is the canonical example of the second rule.

### Versioning

The schema version is `2`. This matches the NanoNym v2 address version defined in ORIS-002, but the two version numbers are independently governed.

The value `2` is retained because it is already emitted by the existing implementation; changing it to `1` would introduce a breaking change without functional benefit.

### Role of `R`

`R` is an Ed25519 ephemeral public key corresponding to a per-payment ephemeral scalar `r`, such that `R = r * G` where `G` is the Ed25519 basepoint.

This schema carries `R`, not `r`. The scalar remains secret to the payer and is disclosed only in profiles where the verifier lacks the recipient's view private key.

The NanoNym v2 stealth derivation used by ORIS-002 defines the current scalar and point rules. A future stealth-math standard MAY factor those rules out, but it must preserve base-schema semantics for `R` unless it also defines a new schema version.

### Relationship to Other Standards

- ORIS-002 defines the NanoNym address format that carries the public keys and notification URI.
- ORIS-004 defines delivery of this payload via Nostr.
- ORIS-005 defines use of this payload in an HTTP 402 verification flow.

### Package Boundary

Schema validation such as structure, field types, hexadecimal format, and version checks belongs in `@nanonyms/protocol`. Stealth-specific validation such as on-curve verification for `R` and stealth-address derivation belongs in `@nanonyms/crypto`.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- <https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0002-nanonym-payment-event-schema.md>
- <https://github.com/cbrunnkvist/NanoNymNault>
