```
OpenRai Initiative Standard: 004
```

# Nostr Notification Transport Profile for NanoNym

> Status: Draft\
> Category: Application Interface

## Abstract

This document defines how the NanoNym payment event schema is delivered over Nostr when a NanoNym's notification URI uses a `nostr:` scheme. It specifies the Nostr notification key derivation, the use of NIP-59 gift wrapping with NIP-44 encryption, and the blind-scanning model used by recipients.

## Motivation

NanoNym needs a concrete transport profile for Tier 1 payment notifications that preserves recipient privacy and fits existing Nostr infrastructure.

This profile exists to:

- bind `nostr:` notification URIs to a specific delivery mechanism
- define the Nostr-specific notification keyspace
- describe how payment events are wrapped, delivered, and discovered
- document the privacy and availability assumptions inherited from Nostr

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- ORIS-002 defines the NanoNym address carrying the `nostr:` URI
- ORIS-003 defines the base payment event schema carried by this profile
- NIP-59 and NIP-44 are incorporated by reference for wrapping and encryption behavior
- `npub` refers to the bech32-encoded secp256k1 public key used for Nostr delivery

## Specification

### Scope

This document covers:

- delivery of ORIS-003 payloads via Nostr gift-wrapped events
- the Nostr-specific notification key derived from the NanoNym owner's seed
- the blind-scanning model for incoming payment discovery

This document does not cover:

- the payment event schema itself
- the stealth address derivation math
- transport-agnostic encryption envelopes
- any non-Nostr transport mechanism

### Prerequisites

- The recipient has published a NanoNym whose notification URI uses the `nostr:` scheme.
- The sender has constructed a valid ORIS-003 payment event after completing a stealth payment.

### Notification Key Derivation

The NanoNym owner derives a secp256k1 keypair from the Nano seed using key type `2`. This keypair is used exclusively for Nostr event signing and gift-wrap decryption. It is not an Ed25519 key and is not used for stealth-address math.

The corresponding Nostr public key is encoded as an `npub` and embedded in the NanoNym's notification URI:

```text
notification_uri = "nostr:npub1<bech32-encoded secp256k1 pubkey>"
```

The three keyspaces are:

| Keyspace | Curve | Key type | Purpose |
|---|---|---|---|
| Spend / View | Ed25519 | 0, 1 | Stealth address derivation |
| Notification | secp256k1 | 2 | Nostr transport |
| Per-payment ephemeral | Ed25519 | random | Stealth input `R` |

### Event Wrapping

The sender delivers the payment event using NIP-59 gift wrap. The inner payload is encrypted using NIP-44.

The wrapping procedure is:

1. Construct the ORIS-003 JSON payload.
2. Place that payload as the content of a Nostr event.
3. Seal and gift-wrap the event per NIP-59 to the recipient's `npub`.
4. Publish the wrapped event to one or more Nostr relays.

This document does not respecify NIP-59 or NIP-44. Implementations MUST conform to those Nostr specifications.

### Payload Content

The content of the inner, decrypted Nostr event is a JSON string conforming to ORIS-003. No additional fields are added by this profile.

In particular, the ephemeral scalar `r` MUST NOT be included. The recipient possesses the view private key and can derive the shared secret from `R` alone.

### Recipient Scanning

The recipient discovers incoming stealth payments by scanning Nostr relays for gift-wrapped events addressed to the notification `npub`.

The recipient:

1. Connects to relays and fetches events addressed to the notification public key.
2. Unwraps each event per NIP-59 and decrypts it per NIP-44.
3. Parses the inner content as an ORIS-003 payment event.
4. Extracts `R` from the payload.
5. Computes the shared secret using the recipient view private key and `R`.
6. Derives the expected stealth address.
7. Verifies that `tx_hash` corresponds to an on-chain payment to that address.
8. Recovers the stealth private key for the verified payment.

The scanning model is blind in the following sense:

- relays can observe gift-wrapped events to an `npub` but cannot read their contents
- third-party observers cannot associate the `npub` with on-chain Nano activity
- the recipient processes all events addressed to the `npub`, but only valid stealth derivations correspond to actual payments

### Relay Availability

This profile inherits Nostr's relay-availability assumptions. If the relays used by the sender are not monitored by the recipient, the notification may not be discovered.

Implementations SHOULD support configuring multiple relays and MAY implement retry or redundancy strategies at the application layer.

### Privacy Properties

- The sender's identity is hidden from relays and observers by NIP-59.
- The payment amount, stealth address, and transaction hash are hidden inside NIP-44 encryption.
- The notification `npub` is unlinkable to the spend and view keys without seed knowledge.
- The ephemeral scalar `r` is never transmitted.

### Cross-Transport Correlation

If the same NanoNym is reused in the x402 proof profile defined by ORIS-005, an x402 verifier learns `r`, `R`, and `tx_hash` for that payment. If that verifier can also observe or obtain the matching Nostr payload, it can correlate the two flows.

Deployments that care about sender unlinkability across transports SHOULD use distinct NanoNyms per transport profile or per counterparty class.

### Package Boundary

Nostr event construction, NIP-59 wrapping, NIP-44 encryption, and relay communication belong in `@nanonyms/nostr-adapter`. This adapter depends on `@nanonyms/protocol` for schema validation but does not contain stealth-derivation logic.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- <https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0003-nostr-notification-transport-profile.md>
- <https://github.com/cbrunnkvist/NanoNymNault>

## Summary

This profile binds NanoNym notification delivery to Nostr without changing the base payment-event schema. It preserves the recipient-privacy model by transmitting only `R` and by delegating transport confidentiality to NIP-59 and NIP-44.
