```
OpenRai Initiative Standard: 002
```

# NanoNyms: Privacy-Enhancing Reusable Payment Codes for Nano

> Status: Draft\
> Category: Application Interface

## Abstract

A NanoNym is a payment code (`nnym_`) encoding a "spend" public key, a "view" public key, and a notification URI; a sender uses these components to derive a one-time `nano_` account for each payment, preventing on-chain observers from linking separate transactions to the same NanoNym by address reuse or public NanoNym data alone. This specification defines the encoding format, the send and receive workflows, and the boundary between the core protocol and notification adapters.

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
- scalar values used by the current stealth derivation are 32-byte little-endian integers modulo the Ed25519 group order
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

### Base32 Encoding

The body uses Nano's account-address alphabet:

```text
13456789abcdefghijkmnopqrstuwxyz
```

The binary payload is encoded as a continuous big-endian bit stream. Encoders MUST process input bytes most-significant bit first, emit 5-bit groups into the alphabet above, and pad the final group with zero bits if fewer than five bits remain. The encoded body MUST NOT include separators or `=` padding.

Decoders MUST reject characters outside the Nano alphabet. Decoders MAY accept uppercase alphabet characters by normalizing them to lowercase before decoding. After decoding, implementations MUST validate the payload length implied by `notificationUriLen`; trailing non-zero padding or extra decoded bytes MUST cause decoding to fail.

### Checksum

The checksum is the first two bytes of a five-byte BLAKE2b digest over the payload prefix that excludes the checksum itself:

```text
checksum = BLAKE2b(payload_without_checksum, digest_length = 5)[0..2]
```

`payload_without_checksum` is:

```text
version || B_spend || B_view || notificationUriLen || notificationUri
```

The checksum bytes are appended in digest order. Implementations MUST verify the checksum before returning decoded fields.

### Example Address Breakdown

```text
notification_uri = "nostr:npub1..."
```

This means:

- the NanoNym protocol stores a generic URI
- NanoNymNault interprets that URI as a Nostr destination
- the protocol itself does not define how Nostr delivery works

### Address Test Vector

This vector is for address encoding only. The keys are repeated bytes and are not production keys.

```text
version         = 02
B_spend        = 0101010101010101010101010101010101010101010101010101010101010101
B_view         = 0202020202020202020202020202020202020202020202020202020202020202
notificationUri= nostr:npub1nanonymtest
uri hex        = 6e6f7374723a6e707562316e616e6f6e796d74657374
uri length     = 0016
checksum       = d85d

nnym_1a1i41a3161i41a3161i41a3161i41a3161i41a3161i41a3161i41i41a3161i41a3161i41a3161i41a3161i41a3161i41a3161i411d8wuumgjs5numigoj54um3fsqpwydfgjkq8x8rdn
```

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

### Stealth Derivation

This section defines the minimum math required for interoperable NanoNym v2 send and receive workflows. A future stealth-math standard MAY replace this section, but implementations of v2 NanoNyms MUST follow these rules unless a later ORIS explicitly updates the v2 profile.

Let:

- `G` be the Ed25519 basepoint.
- `L` be the Ed25519 group order, `2^252 + 27742317777372353535851937790883648493`.
- `H_scalar(x)` be the scalar derivation function defined below.
- `a_spend` and `a_view` be the recipient's spend and view private scalars derived from the recipient's private seed material.
- `B_spend = a_spend * G`.
- `B_view = a_view * G`.
- `r` be the sender's per-payment ephemeral private scalar.
- `R = r * G`.

Private seed material is converted to a scalar by:

```text
hash64  = BLAKE2b(input, digest_length = 64)
clamped = hash64[0..32]
clamped[0]  &= 248
clamped[31] &= 127
clamped[31] |= 64
scalar = little_endian_integer(clamped) mod L
```

In the current v2 derivation, long-term spend/view private keys and randomly generated ephemeral private keys are 32-byte seed inputs to this scalar conversion. Formulas below use the resulting scalars.

The shared secret is:

```text
S_sender   = r * B_view
S_receiver = a_view * R
```

The tweak scalar is:

```text
account_index = 00000000
tweak_seed    = BLAKE2b(S || account_index, digest_length = 32)
t             = H_scalar(tweak_seed)
```

The stealth public key and Nano destination are:

```text
SA = B_spend + t * G
destination = nano_address(SA)
```

The recipient recovers the private scalar needed to spend from `destination` as:

```text
a_stealth = (a_spend + t) mod L
```

Implementations MUST reject malformed Ed25519 points for `B_spend`, `B_view`, `R`, and `SA`. Implementations SHOULD use a curve library that rejects invalid encodings and small-order points; if the library accepts such points, the implementation MUST perform equivalent validation before using them in shared-secret or point-addition operations.

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
