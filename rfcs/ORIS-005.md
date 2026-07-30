```
OpenRai Initiative Standard: 005
```

# Utilizing NanoNyms for x402 Exact Pre-payment Verification

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines a NanoNym-based payment profile for x402 v2 using the `exact` payment scheme. A client pays first by sending Nano to a stealth account derived from a _resource server-supplied_ NanoNym, then presents a _proof-payload_ through the standard x402 v2 payment headers. The proof reveals the per-payment scalar `r`, allowing the resource server (without holding the NanoNym issuer's private key), a verifier, or a facilitator to prove the requesting client's ownership of the payment by confirming the stealth derivation.

## Motivation

x402's `exact` scheme is designed for fixed-price, short-lived payment negotiation. Most existing exact-scheme implementations use sign-first authorizations that a facilitator later settles on-chain. Nano does not have an equivalent smart-contract authorization flow. For Nano, the natural model is pay-first, proof-via-receipt:

- the client completes an on-chain Nano send before retrying the resource request
- the payment payload proves that the send block paid the exact requested amount to the correct NanoNym-derived stealth account
- a facilitator can verify the proof and maintain replay state, keeping the resource server stateless with respect to Nano ledger details

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- ORIS-002 defines the NanoNym address format and stealth derivation
- ORIS-003 defines the base NanoNym payment event schema extended by this profile
- x402 refers to protocol version `2` as proposed by the x402 Foundation
- `r` denotes the Ed25519 ephemeral scalar corresponding to `R`
- x402 objects use their v2 field names, including `PaymentRequired`, `PaymentRequirements`, `PaymentPayload`, `VerifyResponse`, and `SettlementResponse`
- the HTTP transport uses `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, and `PAYMENT-RESPONSE`

## Specification

### Scope

This document covers:

- NanoNym as a Nano network implementation of x402 `scheme: "exact"`
- the x402 payment requirements needed to request a NanoNym payment
- the scheme-specific proof payload used after the client has paid on-chain
- verifier and facilitator behavior for Nano payment proofs
- replay and spent-set requirements for pay-first Nano settlement

This document does not cover:

- generic x402 HTTP semantics
- long-lived subscription, account, or session authorization models
- non-Nano payment assets or mechanisms

### Conceptual Model

In ORIS-004, the stealth mechanism provides recipient privacy: the sender notifies the recipient of a payment that only the recipient can identify. In this x402 profile, the same mechanism provides payment commitment: the client proves that a confirmed Nano send block paid a stealth address derived from the resource server's NanoNym - a payment that could only have been executed by the entity that posessed the `r` value, thereby proving the client's authorship of the public block hash.

This is still an x402 `exact` payment because the resource server declares a fixed amount and recipient. The difference is timing:

- sign-first exact schemes put an authorization in `PaymentPayload.payload` and settlement means broadcasting the transfer
- this profile puts a Nano payment receipt and derivation proof in `PaymentPayload.payload` after the transfer has already been broadcast

### Payment Requirements

A resource server that accepts NanoNym payments advertises them as an x402 `PaymentRequirements` entry inside `PaymentRequired.accepts`.

The payment requirement fields are:

| Field | Value |
|---|---|
| `scheme` | MUST be `"exact"`. |
| `network` | MUST identify the Nano network using the x402 v2 CAIP-2-style network field. This profile uses `"nano:mainnet"` for Nano mainnet. |
| `amount` | MUST be a decimal string containing the required amount in raw. |
| `asset` | MUST be `"xno"`. |
| `payTo` | MUST be a valid `nnym_` NanoNym address. |
| `maxTimeoutSeconds` | Maximum age of the payment negotiation before the client should obtain fresh requirements. |
| `extra` | MAY contain Nano-specific metadata. |

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

Under the HTTP transport, this object is base64-encoded in the `PAYMENT-REQUIRED` header on a `402 Payment Required` response.

The HTTP request header remains `PAYMENT-SIGNATURE` for x402 compatibility even though this profile's scheme payload is a Nano payment proof rather than a cryptographic signature over an authorization object.

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

The resource server MAY implement verification and settlement locally. If it delegates to a facilitator, the resource server can remain stateless with respect to Nano node access and replay/spent-set storage.

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

The `payload` object MUST be a valid ORIS-003 payment event plus this profile's required `r` field. The `amount_raw` field is REQUIRED in this profile and MUST equal `accepted.amount`.

The example above illustrates object shape only. It is not a cryptographic test vector.

### Payload Extension

This profile extends the ORIS-003 base schema with one additional field:

| Field | Type | Description |
|---|---|---|
| `r` | string | Hex-encoded Ed25519 ephemeral scalar as a 32-byte little-endian integer modulo the Ed25519 group order. |

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

If all checks pass, `/verify` returns an x402 `VerifyResponse` with `isValid: true`. If any check fails, it returns `isValid: false` with an `invalidReason`.

### Settlement

For sign-first exact schemes, `/settle` usually broadcasts or executes the authorized transfer. For this Nano profile, the transfer already happened before the payment payload was created. Settlement therefore means finalizing acceptance of the receipt:

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

This profile is intended for short-lived x402 checkout flows. Long-term access, account sessions, subscriptions, and reusable entitlements are outside this profile's scope and SHOULD be represented by application-specific authorization after payment settlement.

The x402 payment-identifier extension MAY be used for idempotent client retries. It is not a substitute for the spent set because two different payment identifiers could otherwise reference the same Nano send block.

### Cryptographic Preconditions

Interoperable verification depends on the ORIS-002 stealth derivation rules, including:

- valid point decoding and rejection of malformed points
- scalar generation, reduction, and clamping rules for `r` and derived tweaks
- BLAKE2b-based scalar conversion
- deterministic conversion of the derived public key to a Nano account address

This profile remains Draft while NanoNym v2 remains Draft.

### Security Properties

Client cannot cheat:

- a client that pays an arbitrary address cannot produce an `r` that causes the verifier to derive that same address from the resource server's NanoNym
- a client that pays the wrong amount fails exact amount verification

Verifier does not need view authority:

- the verifier receives `r` values for individual x402 payments
- those values do not grant general scan capability for unrelated payments
- the resource server does not need to disclose its view private key to a facilitator

Replay protection:

- the Nano ledger proves a send happened once
- the spent set determines whether that send can be consumed for x402 authorization again

### Privacy Properties

- The client voluntarily discloses `r`, `R`, `tx_hash`, and amount to the verifier.
- The verifier learns the stealth address for that specific payment.
- The proof does not reveal the NanoNym owner's private keys.
- Reusing the same NanoNym for both this profile and the Nostr profile weakens cross-transport unlinkability.
- Third parties observing the HTTPS connection, but not its TLS plaintext, learn nothing about the proof contents.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- <https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0004-x402-nanosession-payment-verification-profile.md>
- <https://github.com/cbrunnkvist/NanoNymNault>

## x402 References

- <https://github.com/x402-foundation/x402/blob/main/specs/x402-specification-v2.md>
- <https://github.com/x402-foundation/x402/blob/main/specs/schemes/exact/scheme_exact.md>
- <https://github.com/x402-foundation/x402/blob/main/specs/transports-v2/http.md>
