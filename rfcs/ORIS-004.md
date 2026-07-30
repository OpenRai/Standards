```
OpenRai Initiative Standard: 004
```

# Nostr Transport Profile for NanoNyms

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines how NanoNyms deliver payment events over Nostr. It covers
notification keys, NIP-59 gift wrapping, NIP-44 encryption, relay discovery, and
recipient scanning for a NanoNym with a `nostr:` notification URI.

## Motivation

ORIS-003 deliberately leaves transport and encryption to separate profiles.
This profile provides those rules for applications that choose Nostr.

This profile exists to:

- bind `nostr:` notification URIs to Nostr delivery,
- define a separate Nostr notification key,
- explain how senders wrap and publish events, and
- state the privacy and retention limits inherited from Nostr.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- ORIS-002 defines the NanoNym that carries the `nostr:` URI.
- ORIS-003 defines the payment event carried by this profile.
- NIP-59 and NIP-44 define wrapping and encryption.
- `npub` is the bech32-encoded secp256k1 public key used for delivery.

## Specification

### Scope

This document covers:

- delivery of ORIS-003 events through Nostr gift wraps,
- the Nostr notification key for one NanoNym, and
- recipient scanning for incoming payments.

This document does not cover:

- the payment event schema,
- stealth-account derivation,
- a transport-independent encryption envelope, or
- non-Nostr transports.

### Prerequisites

- The recipient has published a NanoNym whose notification URI uses the `nostr:` scheme.
- The sender has constructed a valid ORIS-003 payment event after completing a stealth payment.

### Notification Key Derivation

The owner of a NanoNym derives or assigns a secp256k1 keypair for Nostr
notifications. The recipient uses this keypair to decrypt gift wraps. A sender
can also use a Nostr keypair to construct events. These keys are separate from
the Ed25519 keys used for stealth-account derivation.

Seed-based wallets SHOULD derive a distinct Nostr notification key for each
NanoNym account index. The wallet SHOULD use the index that derives the same
NanoNym's spend and view keys. A wallet MAY reuse one notification key, but that
choice links the affected NanoNyms on Nostr.

NanoNymNault currently uses key type `2` under the NanoNyms account-index
derivation branch.

The corresponding Nostr public key is encoded as an `npub` and embedded in the NanoNym's notification URI:

```text
notification_uri = "nostr:npub1<bech32-encoded secp256k1 pubkey>"
```

The three keyspaces are:

| Keyspace | Curve | Key type | Purpose |
|---|---|---|---|
| Spend / View | Ed25519 | 0, 1 | Stealth address derivation |
| Notification | secp256k1 | 2 | Nostr transport, when derived from seed |
| Per-payment ephemeral | Ed25519 | random | Stealth input `R` |

### Event Wrapping

The sender delivers the payment event using NIP-59 gift wrap. The inner payload is encrypted using NIP-44.

The wrapping procedure is:

1. Construct the ORIS-003 JSON payload.
2. Place that payload as the `content` of a NIP-59 rumor event.
3. Set the rumor event kind to `2165`.
4. Add a `p` tag containing the recipient notification public key in lowercase 64-character hex form.
5. Seal and gift-wrap the rumor per NIP-59 to the recipient's `npub`.
6. Publish the resulting kind `1059` gift-wrap event to one or more Nostr relays.

Event kind `2165` identifies a NanoNyms v2 payment event. Its number follows
Nano's SLIP-0044 coin type `165`.

This document does not repeat NIP-59 or NIP-44. Implementations MUST follow both
Nostr specifications.

### Payload Content

The content of the decrypted rumor is a JSON string that conforms to ORIS-003.
This profile adds no event fields.

In particular, the ephemeral scalar `r` MUST NOT be included. The recipient possesses the view private key and can derive the shared secret from `R` alone.

### Recipient Scanning

The recipient scans its configured relays for gift wraps addressed to the
notification `npub`.

The recipient:

1. Connects to relays and fetches kind `1059` gift-wrap events.
2. Unwraps each event per NIP-59 and decrypts it per NIP-44.
3. Parses the inner content as an ORIS-003 payment event.
4. Extracts `R` from the payload.
5. Computes the shared secret using the recipient view private key and `R`.
6. Derives the expected stealth address.
7. Verifies that `tx_hash` corresponds to an on-chain payment to that address.
8. Recovers the stealth private key for the verified payment.

The scan is blind to the event contents until the recipient decrypts them:

- Relays can observe gift wraps addressed to an `npub`, but cannot read them.
- Protocol fields do not directly link the `npub` to a Nano account.
- The recipient checks every addressed event and keeps only verified payments.

### Relay Discovery and Permanence

A `nostr:npub1...` URI does not contain relay hints. A wallet that supports
NanoNyms MUST publish a NIP-65 kind `10002` relay-list event for each
notification key. A sender SHOULD resolve that event through its configured
directory relays before publishing a gift wrap.

Nostr delivery is the Tier 1 notification path. Wallets SHOULD retain these
events as the primary payment history and MAY use paid or archival relays.
Public relays can prune events, so Tier 1 storage is not guaranteed to be
permanent.

Tier 2 recovery scans Nano ledger state when notifications are unavailable. An
implementation MUST NOT assume that a public relay provides a complete payment
history.

### Privacy Properties

- NIP-59 hides the sender's Nostr identity when the sender uses an unlinkable
  wrapping key.
- The payment amount, stealth address, and transaction hash are hidden inside NIP-44 encryption.
- A notification `npub` derived in the NanoNyms keyspace does not reveal the
  spend or view keys.
- Reusing a notification `npub` across multiple NanoNyms links those NanoNyms at the transport layer even though it does not reveal their spend or view keys.
- The ephemeral scalar `r` is never transmitted.

### Cross-Transport Correlation

When the same NanoNym is used with ORIS-005, the x402 verifier learns `r`, `R`,
and `tx_hash` for that payment. A verifier with the matching Nostr event can
correlate the two flows.

Deployments that care about sender unlinkability across transports SHOULD use distinct NanoNyms per transport profile or per counterparty class.

### Package Boundary

`@nanonyms/nostr-adapter` constructs events, applies NIP-59 and NIP-44, and
communicates with relays. It uses `@nanonyms/protocol` to validate payment
events. Stealth-account derivation remains in `@nanonyms/crypto`.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- [NanoNymNault Nostr transport profile](https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/rfcs/0003-nostr-notification-transport-profile.md)
- [NanoNymNault source](https://github.com/cbrunnkvist/NanoNymNault)
