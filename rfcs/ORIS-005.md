```
OpenRai Initiative Standard: 005
```

# x402.NanoSession Payment Verification Profile for NanoNym

> Status: Draft\
> Category: Application Interface

## Abstract

This document defines how the NanoNym payment event schema is used in an HTTP 402 machine-to-machine payment flow. The client proves a specific payment by revealing the ephemeral scalar `r`, which allows the resource server to verify stealth-address derivation without holding the recipient's view private key.

## Motivation

NanoNym's stealth derivation can be repurposed from a privacy mechanism into a payment-commitment proof for HTTP 402 flows.

This profile exists to:

- define a proof-carrying HTTP 402 payment flow
- specify the profile extension that adds `r`
- allow servers to verify specific payments using only public NanoNym components
- preserve limited disclosure instead of sharing the recipient's view private key

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- ORIS-002 defines the NanoNym address format
- ORIS-003 defines the base payment event schema extended by this profile
- `r` denotes the Ed25519 ephemeral scalar corresponding to `R`
- the underlying stealth derivation math is assumed but not fully standardized in this document

## Specification

### Scope

This document covers:

- the HTTP 402 request and response flow for NanoNym payments
- the profile-specific payload extension that adds `r`
- server-side verification using public keys and the client-provided `r`
- the security properties of the proof mechanism

This document does not cover:

- the base payment event schema itself
- Nostr notification delivery
- general HTTP 402 semantics beyond the NanoNym-specific binding

### Conceptual Model

In the Nostr transport profile, the stealth mechanism provides privacy: the sender notifies the recipient of a payment that only the recipient can identify. In this profile, the same mechanism provides commitment: the client proves to a resource server that it made an irrevocable payment to a stealth address derived from the server's NanoNym.

The proof is non-interactive and signature-less. The binding arises from the relationship between `r`, `R`, the NanoNym public keys, the derived stealth address, and the on-chain transaction.

### Protocol Flow

```text
Client                                  Resource Server
  |                                           |
  |  1. GET /resource                         |
  |------------------------------------------>|
  |                                           |
  |  2. 402 Payment Required                  |
  |     { nanonym, amount_raw }               |
  |<------------------------------------------|
  |                                           |
  |  3. Derive stealth address from nnym,     |
  |     send Nano payment on-chain            |
  |                                           |
  |  4. GET /resource                         |
  |     X-Payment: <proof>                    |
  |------------------------------------------>|
  |                                           |
  |  5. Verify proof, return resource         |
  |<------------------------------------------|
```

The server responds with HTTP `402` and a JSON body containing the server's NanoNym and the required amount.

The client then:

1. Parses the NanoNym to extract `B_spend` and `B_view`.
2. Generates a fresh ephemeral scalar `r` and computes `R = r * G`.
3. Derives the stealth address.
4. Sends a Nano payment of the required amount to that address.
5. Waits for on-chain confirmation.
6. Retries the request with an `X-Payment` header containing a base64url-encoded JSON proof.

### Payload Extension

This profile extends the ORIS-003 base schema with one additional field:

| Field | Type | Description |
|---|---|---|
| `r` | string | Hex-encoded Ed25519 ephemeral scalar (64 hex characters). |

The `r` field is REQUIRED in this profile. The `amount_raw` field, while optional in the base schema, is effectively REQUIRED here because the server must verify the payment amount.

Example proof payload:

```json
{
  "version": 2,
  "protocol": "nanonym",
  "R": "ab3f...64 hex chars...",
  "tx_hash": "9c21...64 hex chars...",
  "amount_raw": "1000000000000000000000000000000",
  "r": "7a1f...64 hex chars..."
}
```

### Server Verification

The server holds only the public components of its NanoNym: `B_spend` and `B_view`. It does not need the recipient's view private key because the client provides `r` directly.

Verification proceeds in two stages.

Stage 1: consistency check, without network access.

- Verify that `R = r * G`.

Stage 2: derivation and on-chain verification.

1. Compute the stealth address `SA = B_spend + H(r * B_view) * G`.
2. Convert `SA` to a Nano account address.
3. Look up `tx_hash` on-chain and verify:
4. The block exists and is confirmed.
5. The destination is `SA`.
6. The amount is at least `amount_raw`.

If all checks pass, the proof is valid.

### Replay Resistance

- A server MUST persist replay state for every accepted proof.
- For single-payment authorization semantics, the server MUST reject later proof reuse for the same `tx_hash`.
- If a deployment allows one on-chain payment to authorize multiple requests, the server MUST implement explicit value accounting and MUST reject requests once the paid amount has been fully consumed.
- A server SHOULD bind successful verification to a short-lived session token or challenge state rather than requiring the raw proof on every follow-up request.

Tracking `tx_hash` is the minimum replay defense for the common case where one payment unlocks one resource or one short-lived session.

### Cryptographic Preconditions

Interoperable verification requires a single stealth-math specification covering:

- valid point decoding and rejection of malformed or small-order points
- subgroup or cofactor handling during shared-secret and stealth-point derivation
- scalar generation, reduction, and clamping rules for `r` and derived tweaks
- domain-separated hashing for shared-secret and tweak derivation

This profile therefore remains Draft until those rules are fully standardized.

### Security Properties

Non-transferability:

- the proof binds `r` to a specific stealth address derived from the server's NanoNym
- an observer cannot reuse that proof for a different server or a different transaction

Client cannot cheat:

- a client that pays an arbitrary address cannot produce an `r` that causes the server to derive that same address as the expected stealth address

Server cannot scan:

- the server receives `r` values for individual proofs but does not gain general scan capability for unrelated payments

Accumulation resistance:

- collecting multiple `r` values does not expose the recipient's long-term private keys

Minimal disclosure:

- revealing `r` discloses only what is needed for this payment verification
- sharing the view private key would disclose substantially more

### Privacy Properties

- The client voluntarily discloses `r` and `tx_hash` to the server.
- The server learns the stealth address for that specific payment only.
- Third parties observing the HTTPS connection, but not its TLS plaintext, learn nothing about the proof contents.
- The proof does not reveal the NanoNym owner's private keys or enable identification of unrelated payments.
- Reusing the same NanoNym for both this profile and the Nostr profile weakens cross-transport unlinkability.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- <https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0004-x402-nanosession-payment-verification-profile.md>
- <https://github.com/cbrunnkvist/NanoNymNault>

## Summary

This profile turns NanoNym stealth derivation into a payment-commitment proof suitable for HTTP 402. It minimizes disclosure by having the client reveal the per-payment scalar `r` instead of granting the server broader view-key access.
