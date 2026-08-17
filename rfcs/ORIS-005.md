```
OpenRai Initiative Standard: 005
```

# NanoNyms Profile for x402 Exact Payments

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines a NanoNyms payment profile for the x402 v2 `exact` scheme. The client first pays a stealth account derived from the resource server's NanoNym. It then submits the send-block hash and derivation proof in a
standard x402 `PaymentPayload`.

The proof reveals the scalar `r` for that payment. A resource server or facilitator can therefore verify the destination without receiving the NanoNym owner's private keys.

## Motivation

The x402 `exact` scheme describes payment for a fixed amount. Existing EVM and SVM profiles submit an authorization or transaction for later settlement. Nano does not use that authorization model, so this profile uses a confirmed payment as its proof:

- The client sends Nano before retrying the resource request.
- The payload proves that the send paid the requested amount and destination.
- A facilitator can query Nano and prevent reuse of an accepted send block.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- ORIS-002 defines NanoNyms payment codes and stealth derivation.
- ORIS-003 defines the payment event extended by this profile.
- x402 refers to protocol version `2`.
- `r` is the Ed25519 ephemeral scalar corresponding to `R`.
- x402 object and field names retain their upstream spelling.
- HTTP uses `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, and `PAYMENT-RESPONSE`.

## Specification

### Scope

This document covers:

- NanoNyms as a Nano implementation of x402 `scheme: "exact"`
- payment requirements for a NanoNym
- the proof submitted after payment
- verifier and facilitator behavior
- replay protection for a pay-first scheme

This document does not cover:

- generic x402 HTTP behavior
- subscriptions or long-lived sessions
- non-Nano assets

### Conceptual Model

The resource server advertises a NanoNym. The client chooses `r`, derives the corresponding stealth account, and pays it. The client then discloses `r`, `R`, and `tx_hash` to the verifier.

The resource server or verifier recomputes the destination and checks the confirmed send block.
This proves that the submitted derivation matches the payment.

### Payment Requirements

A resource server that accepts NanoNym payments advertises them as an x402 `PaymentRequirements` entry inside `PaymentRequired.accepts`.

The payment requirement fields are:

| Field               | Value                                                                                                                             |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `scheme`            | MUST be `"exact"`.                                                                                                                |
| `network`           | MUST identify the Nano network using the x402 v2 CAIP-2-style network field. This profile uses `"nano:mainnet"` for Nano mainnet. |
| `amount`            | MUST be a decimal string containing the required amount in raw.                                                                   |
| `asset`             | MUST be `"xno"`.                                                                                                                  |
| `payTo`             | MUST be a valid `nnym_` NanoNym address.                                                                                          |
| `maxTimeoutSeconds` | MUST be the maximum time allowed to complete the payment.                                                                         |
| `extra`             | MAY contain Nano-specific metadata.                                                                                               |

The resource server MUST include the normal x402 `resource` object in `PaymentRequired` to bind the quoted payment terms to the requested resource.

Example `PaymentRequired` object:

```json
{
  "x402Version": 2,
  "error": "PAYMENT-SIGNATURE header is required",
  "resource": {
    "url": "https://api.example.com/weather",
    "description": "Current weather report",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "nano:mainnet",
      "amount": "1000000000000000000000000000",
      "asset": "xno",
      "payTo": "nnym_...",
      "maxTimeoutSeconds": 60,
      "extra": {
        "profile": "nanonym-v2"
      }
    }
  ],
  "extensions": {}
}
```

The HTTP transport base64-encodes this object in the `PAYMENT-REQUIRED` header
of a `402 Payment Required` response.

The request header remains `PAYMENT-SIGNATURE` because x402 assigns that header to `PaymentPayload`. In this profile, the payload is a payment proof rather than a signature over a future transfer.

### Protocol Flow

```text
Client                         Resource Server                 Facilitator / Verifier
  |                                   |                                  |
  |  1. GET /resource                 |                                  |
  |---------------------------------->|                                  |
  |                                   |                                  |
  |  2. 402 Payment Required          |                                  |
  |     PAYMENT-REQUIRED:             |                                  |
  |     base64(PaymentRequired)       |                                  |
  |<----------------------------------|                                  |
  |                                   |                                  |
  |  3. Select accepted exact Nano    |                                  |
  |     requirements, derive stealth  |                                  |
  |     address, send Nano on-chain   |                                  |
  |                                   |                                  |
  |  4. GET /resource                 |                                  |
  |     PAYMENT-SIGNATURE:            |                                  |
  |     base64(PaymentPayload)        |                                  |
  |---------------------------------->|                                  |
  |                                   | 5. POST /verify or /settle        |
  |                                   |    PaymentPayload + requirements  |
  |                                   |--------------------------------->|
  |                                   |                                  |
  |                                   | 6. Verify derivation, chain state,|
  |                                   |    exact amount, and spent set    |
  |                                   |<---------------------------------|
  |                                   |                                  |
  |  7. 200 OK                        |                                  |
  |     PAYMENT-RESPONSE:             |                                  |
  |     base64(SettlementResponse)    |                                  |
  |<----------------------------------|                                  |
```

The resource server MAY verify and settle locally. If it delegates both
operations, the facilitator owns Nano node access and replay state.

### Payment Payload

The client retries the protected request with a standard x402 `PaymentPayload`. The top-level `accepted` field MUST exactly match the selected Nano payment requirements. The scheme-specific `payload` field carries the NanoNym proof.

```json
{
  "x402Version": 2,
  "resource": {
    "url": "https://api.example.com/weather",
    "description": "Current weather report",
    "mimeType": "application/json"
  },
  "accepted": {
    "scheme": "exact",
    "network": "nano:mainnet",
    "amount": "1000000000000000000000000000",
    "asset": "xno",
    "payTo": "nnym_...",
    "maxTimeoutSeconds": 60,
    "extra": {
      "profile": "nanonym-v2"
    }
  },
  "payload": {
    "version": 2,
    "protocol": "nanonym",
    "R": "ab3f1e7c9d00000000000000000000000000000000000000000000000000fa08",
    "tx_hash": "9c21de5b3a0000000000000000000000000000000000000000000000000017f0",
    "amount_raw": "1000000000000000000000000000",
    "r": "7a1f000000000000000000000000000000000000000000000000000000000000"
  },
  "extensions": {}
}
```

The `payload` object MUST be a valid ORIS-003 payment event with the required
`r` extension. `amount_raw` is also REQUIRED and MUST equal `accepted.amount`.

The example above illustrates object shape only. It is not a cryptographic test vector.

### Payload Extension

This profile extends the ORIS-003 base schema with one additional field:

| Field | Type   | Description                                                                                             |
| ----- | ------ | ------------------------------------------------------------------------------------------------------- |
| `r`   | string | Hex-encoded Ed25519 ephemeral scalar as a 32-byte little-endian integer modulo the Ed25519 group order. |

The verifier MUST check that `R = r * G` using the ORIS-002 scalar and point rules.

### Facilitator Verification

For `/verify`, a verifier receives the x402 `PaymentPayload` and the selected `PaymentRequirements`.

Verification proceeds as follows:

1. Verify `x402Version` is `2`.
2. Verify `accepted` matches the supplied `PaymentRequirements`.
3. Verify `accepted.scheme` is `"exact"`.
4. Verify `accepted.network` is a supported Nano network.
5. Verify `accepted.asset` is `"xno"`.
6. Decode `accepted.payTo` as a valid ORIS-002 NanoNym.
7. Validate `payload` as an ORIS-003 payment event with required `r`.
8. Verify `payload.amount_raw` equals `accepted.amount`.
9. Verify `R = r * G`.
10. Derive the expected stealth public key and Nano destination from `r`, `B_view`, and `B_spend`.
11. Look up `tx_hash` on the Nano ledger.
12. Verify the block exists and is confirmed.
13. Verify the block is a send block whose destination is the derived Nano address.
14. Compute the send amount from the block balance delta and verify it equals `accepted.amount`.
15. Verify `tx_hash` has not already been accepted for another settlement according to the verifier's spent set.

If all checks pass, `/verify` returns `isValid: true`. If a check fails, it
returns `isValid: false` and an `invalidReason`.

### Settlement

For this profile, the transfer exists before `/settle`. Settlement means
accepting that payment exactly once:

1. Perform the full verification procedure above.
2. Atomically mark `tx_hash` as spent or consumed for this x402 settlement.
3. Return an x402 `SettlementResponse`.

A successful settlement response MUST include:

```json
{
  "success": true,
  "transaction": "9c21de5b3a0000000000000000000000000000000000000000000000000017f0",
  "network": "nano:mainnet",
  "amount": "1000000000000000000000000000"
}
```

The `payer` field MAY be omitted because the Nano send block does not reveal a stable payer identity suitable for x402 semantics. If included, it MUST identify the Nano source account of the send block, not the NanoNym owner.

### Replay Resistance

Replay resistance is mandatory, but it does not have to live on the resource server.

- A facilitator or local verifier MUST maintain a spent set for accepted Nano send block hashes.
- The spent-set check and insertion MUST be atomic at settlement time.
- A later settlement attempt for the same `tx_hash` MUST fail.
- A resource server that delegates settlement to a facilitator MAY remain stateless and rely on the facilitator's spent set.
- A resource server that verifies or settles locally MUST maintain equivalent spent-set state.

This profile covers one short-lived checkout. Applications must define their
own authorization after settlement for sessions, subscriptions, or reusable
entitlements.

The x402 payment-identifier extension MAY be used for idempotent client retries. It is not a substitute for the spent set because two different payment identifiers could otherwise reference the same Nano send block.

### Cryptographic Preconditions

Interoperable verification depends on the ORIS-002 stealth derivation rules, including:

- valid point decoding and rejection of malformed points
- scalar generation, reduction, and clamping rules for `r` and derived tweaks
- BLAKE2b-based scalar conversion
- deterministic conversion of the derived public key to a Nano account address

Changes to ORIS-002 derivation rules can require a corresponding update to this
Working Draft.

### Security Properties

What the proof establishes:

- The disclosed `r` derives the destination paid by `tx_hash`.
- The confirmed send amount exactly matches the quoted amount.

What the verifier does not receive:

- The verifier receives `r` only for the submitted payment.
- The verifier does not receive the NanoNym view private key.
- One disclosed `r` does not reveal unrelated payments.

Replay protection:

- the Nano ledger proves a send happened once
- the spent set determines whether that send can be consumed for x402 authorization again

### Privacy Properties

- The client voluntarily discloses `r`, `R`, `tx_hash`, and amount to the verifier.
- The verifier learns the stealth address for that specific payment.
- The verifier can correlate the protected HTTP request, payment proof, and corresponding on-chain send.
- The proof does not reveal the NanoNym owner's private keys.
- TLS protects the proof contents in transit. It does not hide connection
  metadata.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- [NanoNymNault x402 profile](https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0004-x402-nanosession-payment-verification-profile.md)
- [NanoNymNault source](https://github.com/cbrunnkvist/NanoNymNault)

## x402 References

- [x402 v2 protocol specification](https://github.com/x402-foundation/x402/blob/main/specs/x402-specification-v2.md)
- [x402 exact scheme](https://github.com/x402-foundation/x402/blob/main/specs/schemes/exact/scheme_exact.md)
- [x402 v2 HTTP transport](https://github.com/x402-foundation/x402/blob/main/specs/transports-v2/http.md)
