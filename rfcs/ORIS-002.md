```
OpenRai Initiative Standard: 002
```

# NanoNym Protocol and Address Format

> Status: Draft\
> Category: Application Interface

## Abstract

This document defines the NanoNym protocol and the v2 address format. It describes what a NanoNym address contains and how it is encoded, how send and receive flows work, how stealth accounts are selected, and where the protocol stops and adapters begin.

## Motivation

NanoNym uses a reusable payment identifier with transport-agnostic notification routing and deterministic stealth-account derivation. The protocol needs a concise specification that states the core model, defines the address encoding, and establishes the adapter boundary without binding either to a single wallet implementation detail or to a specific transport.

The v2 format replaces an earlier design that embedded a Nostr-specific public-key field directly into the protocol address. That made the standard transport-specific and forced relay assumptions into otherwise reusable protocol code. The v2 format is intended to provide:

- a transport-agnostic NanoNym format
- reusable `@nanonyms/*` packages
- no relay clients or wallet infrastructure in extracted protocol packages
- a clean contract that multiple applications can implement

Since v1 was a tech preview, there is no backward-compatibility requirement for it in NanoNymNault or in the `@nanonyms/*` packages.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements where they appear.

Unless otherwise stated:

- `nnym_` refers to a NanoNym v2 address
- `nano_` refers to a standard Nano account address
- `B_spend` and `B_view` are 32-byte Ed25519 public keys
- `notificationUri` is an application-routed Tier 1 destination URI
- all strings are UTF-8
- all multi-byte integers are big-endian
- Tier 1 notification routing is represented as a URI carried inside the NanoNym
- wallet-specific implementation choices are informative unless explicitly stated as protocol requirements

## Specification

### Terminology

- **NanoNym**: A reusable payment code encoded as `nnym_...`
- **Tier 1 notification**: The off-chain notification route stored as a URI inside the NanoNym
- **Stealth account**: A one-time `nano_` address derived for a specific payment
- **Aggregated NanoNym account**: The wallet view that sums all stealth accounts belonging to one NanoNym

### Versioning

NanoNyms are defined only as v2 from this point onward.

- NanoNymNault will only create and consume v2 NanoNyms.
- `@nanonyms/protocol` will only encode and decode v2 NanoNyms.
- `@nanonyms/crypto` and `@nanonyms/core` will only speak in v2 terms.
- v1 is historical context only and is not implemented.

### Address Model

A `nnym_` address contains exactly three semantic elements:

- a spend public key (`B_spend`)
- a view public key (`B_view`)
- a Tier 1 notification destination URI (`notificationUri`)

It does not contain funds, balances, transaction history, relay client configuration, or any private-key material.

At the protocol boundary, the notification route is just a URI. NanoNymNault currently uses `nostr:...`, but that is an adapter choice rather than a protocol requirement.

### Binary Layout

```text
+---------+--------------------+----------+------------------+------------------+
| Bytes   | Field              | Size     | Meaning          | Notes            |
+---------+--------------------+----------+------------------+------------------+
| 0       | version            | 1 byte   | protocol version | fixed: 0x02      |
| 1..32   | B_spend            | 32 bytes | spend pubkey     | Ed25519          |
| 33..64  | B_view             | 32 bytes | view pubkey      | Ed25519          |
| 65..66  | notificationUriLen | 2 bytes  | URI length       | uint16 BE        |
| 67..N   | notificationUri    | variable | Tier 1 route     | UTF-8            |
| N+1..N+2| checksum           | 2 bytes  | integrity check  | BLAKE2b-derived  |
+---------+--------------------+----------+------------------+------------------+
```

Logical shape:

```text
nnym_
  -> base32(payload)
       -> [ version | B_spend | B_view | uri_length | notification_uri | checksum ]
```

Human-readable encoding:

- Prefix: `nnym_`
- Body: Nano-style base32

### Example Address Breakdown

```text
notification_uri = "nostr:npub1..."
```

This means:

- the NanoNym protocol stores a generic URI
- NanoNymNault interprets that URI as a Nostr destination
- the protocol itself does not define how Nostr delivery works

### Notification URI Rules

- The URI is stored as UTF-8 bytes.
- The URI MUST NOT be empty.
- The URI MUST include a scheme component.
- The URI length MUST fit in `uint16`.
- Scheme-specific validation belongs in adapters, not in the protocol core.

Examples:

- `nostr:npub1...`
- `nostr:nprofile1...`
- `https://example.invalid/.well-known/nanonym/alice`

### Send Workflow

When a sender inputs a `nnym_` address, the sender:

1. Decodes the NanoNym and extracts `B_spend`, `B_view`, and `notificationUri`.
2. Generates an ephemeral keypair for the payment.
3. Derives a shared secret between the ephemeral private key and the recipient view public key.
4. Derives a one-time stealth destination from that shared secret plus the recipient spend public key.
5. Sends the Nano payment on-chain to the stealth destination.
6. Builds a Tier 1 notification payload containing the ephemeral public key and transaction metadata.
7. Hands the notification payload plus `notificationUri` to an adapter.

In NanoNymNault today:

- the adapter expects `nostr:...`
- the payload is gift-wrapped and published to Nostr relays

### Receive Workflow

For each active NanoNym, the receiver:

1. Resolves the NanoNym's `notificationUri` through the wallet's configured Tier 1 adapter.
2. Receives and decrypts a notification payload intended for that NanoNym.
3. Extracts the sender ephemeral public key and transaction metadata.
4. Recomputes the expected stealth destination using the NanoNym's private view key and public spend key.
5. Derives the stealth private key needed to spend from that destination.
6. Verifies the payment against the chain and adds the resulting stealth account to wallet state.

Offline or cold recovery works by replaying the same derivation rules from seed and scanning through the configured notification mechanism plus chain state.

### Stealth Account Selection

When spending from a NanoNym, the wallet selects funded stealth accounts to satisfy the target amount.

Goals:

- prefer a single stealth account when possible
- otherwise use a bounded greedy selection
- randomize send order to reduce deterministic patterns

NanoNymNault currently exposes a pure `selectStealthInputs` helper for this behavior.

### Wallet Model

From the wallet UI perspective, each NanoNym behaves like an aggregated account:

- one label
- one displayed balance
- one payment count
- many underlying stealth accounts

Archiving a NanoNym stops active monitoring in the wallet, but does not affect recoverability from seed.

### Protocol Boundary

The protocol layer knows:

- how to encode and decode `nnym_`
- how to derive stealth destinations and recovery material

The protocol layer does not know:

- how `notificationUri` is delivered
- how a Nostr relay pool works
- how Nano node RPC is performed
- how wallet state is stored

Those concerns belong to application adapters and infrastructure.

### Package Boundaries

- `@nanonyms/protocol` is responsible for encoding, decoding, and basic structural validation of the v2 address.
- Transport-specific validation belongs outside the core protocol package.
- Downstream packages consume the decoded spend key, view key, and notification URI as protocol inputs.
- Because v1 is not supported, implementations do not need dual-format parsing or migration shims inside the protocol packages.

### Current NanoNymNault Composition

NanoNymNault currently uses:

- `@nanonyms/protocol` for address semantics
- `@nanonyms/crypto` for deterministic derivation and stealth math
- `@nanonyms/core` for pure use-case flows
- a Nostr adapter for Tier 1 notification delivery

This separation is intentional. The protocol is generic; the wallet is opinionated.

### Relationship to Other Standards

- ORIS-003 defines the payment event schema carried by transport profiles.
- ORIS-004 defines delivery when the URI is `nostr:npub1...`.
- ORIS-005 defines verification when a NanoNym is used in an HTTP 402 flow.

## Published Test Vectors

No published test vectors are defined in this document yet.

## Reference Implementation

- <https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/protocol-specification.md>
- <https://github.com/cbrunnkvist/NanoNymNault>

## Summary

NanoNym defines a transport-agnostic stealth-payment model around three address components: spend key, view key, and notification URI. The v2 binary layout encodes these as a versioned, base32-encoded payload with a BLAKE2b-derived checksum. Wallets and adapters may vary, but the protocol boundary remains stable if address decoding, stealth derivation, and notification handoff remain consistent.
