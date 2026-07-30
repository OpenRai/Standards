```
OpenRai Initiative Standard: 003
```

# NanoNyms Payment Event Schema

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines the JSON event that describes a payment to a NanoNym.
Transport and verification profiles use the same event before applying their
own encryption, delivery, or proof rules.

## Motivation

NanoNyms can use different transports without changing the meaning of a payment
notification. A shared event lets senders, receivers, and verifiers reuse the
same parser and validation rules.

The base event does not define:

- the transport,
- the encryption layer,
- push or proof-based delivery, or
- the observer privacy model.

Each profile defines those choices around the same event.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- JSON uses UTF-8.
- Hexadecimal strings are lowercase and do not include a prefix.
- `R` is the ephemeral Ed25519 public key used for stealth derivation.
- Profile extensions MUST preserve the validity of the base event.

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

This example shows the JSON shape only. It is not a test vector, and its `R`
value is not asserted to be a valid curve point.

### Validation Rules

1. `version` MUST be the integer `2`.
2. `protocol` MUST be the string `"nanonym"`.
3. `R` MUST be a 64-character lowercase hexadecimal string encoding a valid Ed25519 compressed point.
4. `tx_hash` MUST be a 64-character lowercase hexadecimal string.
5. `amount_raw`, if present, MUST be a decimal string with no leading zeros except `"0"`.
6. `memo`, if present, MUST be a valid UTF-8 string.
7. Implementations MUST reject payloads missing any required field.
8. Implementations MUST ignore unrecognized fields for forward compatibility.

Validation of `R` includes decoding the compressed Ed25519 point and rejecting
malformed encodings. Implementations SHOULD also reject small-order points. A
profile MAY require additional point checks for its proof model.

`tx_hash` identifies the Nano send block that paid the derived stealth account.
Base-schema validation does not query the ledger. The active profile must define
how to check confirmation, destination, and amount.

### Profile Extensibility

A profile event MUST satisfy the base schema. A profile MAY add fields, but it
MUST NOT remove or redefine a base field.

To reduce extension-field collisions:

1. Base-schema field names defined in this document are globally reserved.
2. A profile MAY reserve an unprefixed cryptographic symbol when that symbol is intrinsic to the proof model and is normatively defined by that profile.
3. All other profile-specific extension fields MUST use a stable profile prefix ending in `_`, such as `nostr_...` or `x402_...`.
4. Each profile document MUST define every extension field it reserves.

The `r` field defined by ORIS-005 is the canonical example of the second rule.

### Versioning

The event version is `2`. ORIS-002 also assigns version `2` to the NanoNyms
payment-code format, but each version number changes independently.

Existing implementations already emit event version `2`. Renumbering it would
break those events without changing their meaning.

### Role of `R`

`R` is the Ed25519 public key for the per-payment scalar `r`:

```text
R = r * G
```

`G` is the Ed25519 basepoint.

The event contains `R`, not `r`. The payer keeps `r` secret unless a profile
requires it as part of a proof.

ORIS-002 defines the scalar and point rules for NanoNyms v2. A later standard
may move those rules, but it MUST preserve the meaning of `R` or define a new
event version.

### Relationship to Other Standards

- ORIS-002 defines the NanoNyms payment-code format.
- ORIS-004 defines delivery of this payload via Nostr.
- ORIS-005 defines use of this payload in an HTTP 402 verification flow.

### Package Boundary

`@nanonyms/protocol` validates the JSON structure, field types, hexadecimal
format, and version. `@nanonyms/crypto` validates `R` as a curve point and
performs stealth-account derivation.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- [NanoNymNault payment-event specification](https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0002-nanonym-payment-event-schema.md)
- [NanoNymNault source](https://github.com/cbrunnkvist/NanoNymNault)
