```
OpenRai Initiative Standard: 002
```

# NanoNyms: Privacy-Enhancing Reusable Payment Codes for Nano

> Status: Implementation Draft
> Category: Application Interface

## Abstract

A NanoNym is a reusable payment code with the `nnym_` prefix. It contains a
spend public key, a view public key, and a notification URI. A sender uses these
values to derive a new `nano_` account for each payment.

This document defines the NanoNyms encoding, payment workflow, stealth-account
derivation, and boundary between the NanoNyms protocol and transport adapters.

## Motivation

NanoNyms let a recipient publish one payment code without reusing one on-chain
account. Each payment goes to a derived account, while a separate notification
tells the recipient how to find and spend it.

Version 1 embedded a Nostr public key in the payment code. That design tied the
core format to one transport and pushed relay assumptions into protocol code.
Version 2 instead provides:

- a transport-independent encoding for each NanoNym,
- reusable `@nanonyms/*` packages,
- no relay or wallet infrastructure in the protocol packages, and
- one contract that multiple applications can implement.

Version 1 was a technical preview. NanoNymNault and the `@nanonyms/*` packages
do not support it.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements where they appear.

Unless otherwise stated:

- `nnym_` identifies a NanoNym v2 payment code.
- `nano_` identifies a standard Nano account.
- `B_spend` and `B_view` are 32-byte Ed25519 public keys.
- `notificationUri` is a Tier 1 notification destination.
- Strings use UTF-8.
- Multi-byte integers use big-endian byte order.
- Scalars are 32-byte little-endian integers modulo the Ed25519 group order.
- Wallet-specific behavior is informative unless a requirement says otherwise.

## Specification

### Terminology

- **NanoNyms protocol:** The encoding and derivation rules defined here.
- **NanoNym:** One reusable payment code encoded as `nnym_...`.
- **Tier 1 notification:** An off-chain payment notification delivered through
  the URI stored in a NanoNym.
- **Stealth account:** A one-time `nano_` account derived for one payment.
- **Aggregated NanoNym account:** A wallet view that combines the stealth
  accounts derived from one NanoNym.

### Versioning

This document defines only version 2.

- NanoNymNault creates and consumes only v2 NanoNyms.
- `@nanonyms/protocol` encodes and decodes only v2 NanoNyms.
- `@nanonyms/crypto` and `@nanonyms/core` expose only v2 behavior.
- Version 1 is historical and is not implemented.

### Address Model

A NanoNym contains exactly three semantic values:

- a spend public key (`B_spend`),
- a view public key (`B_view`), and
- a Tier 1 notification URI (`notificationUri`).

It does not contain funds, balances, transaction history, relay client configuration, or any private-key material.

The NanoNyms protocol treats the notification route as an opaque URI.
NanoNymNault currently supports `nostr:...` through an adapter. Other
implementations can provide adapters for other URI schemes.

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
| N+1..N+5| checksum           | 5 bytes  | integrity check  | BLAKE2b-derived  |
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

The binary payload is one big-endian bit stream. Encoders MUST read each byte
most-significant bit first and emit 5-bit groups using the alphabet above. An
encoder MUST pad an incomplete final group with zero bits. The encoded body MUST
NOT contain separators or `=` padding.

Decoders MUST reject characters outside the Nano alphabet. A decoder MAY
normalize uppercase alphabet characters to lowercase. The decoder MUST validate
the length declared by `notificationUriLen`. It MUST reject non-zero padding and
extra decoded bytes.

### Checksum

The checksum is a five-byte BLAKE2b digest over the payload prefix that excludes the checksum itself:

```text
checksum = BLAKE2b(payload_without_checksum, digest_length = 5)
```

The 5-byte checksum matches the checksum length of a standard Nano account. It
detects accidental changes such as typing, scanning, or truncation errors. It
does not protect against an attacker who replaces the complete payment code.

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

- the NanoNyms protocol stores the URI without transport behavior,
- NanoNymNault passes the URI to its Nostr adapter, and
- ORIS-004 defines how that adapter delivers the notification.

### Address Test Vector

This vector is for address encoding only. The keys are repeated bytes and are not production keys.

```text
version         = 02
B_spend        = 0101010101010101010101010101010101010101010101010101010101010101
B_view         = 0202020202020202020202020202020202020202020202020202020202020202
notificationUri= nostr:npub1nanonymtest
uri hex        = 6e6f7374723a6e707562316e616e6f6e796d74657374
uri length     = 0016
checksum       = d85daf4016

nnym_1a1i41a3161i41a3161i41a3161i41a3161i41a3161i41a3161i41i41a3161i41a3161i41a3161i41a3161i41a3161i41a3161i411d8wuumgjs5numigoj54um3fsqpwydfgjkq8x8rdpqn17i
```

### Notification URI Rules

- The URI MUST use UTF-8.
- The URI MUST NOT be empty.
- The URI MUST contain a scheme.
- The encoded URI length MUST fit in `uint16`.
- An adapter MUST perform scheme-specific validation.

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

NanoNymNault currently routes `nostr:...` URIs to its Nostr adapter. The adapter
gift-wraps the payload and publishes it to Nostr relays as defined by ORIS-004.

### Receive Workflow

For each active NanoNym, the receiver:

1. Resolves the NanoNym's `notificationUri` through the wallet's configured Tier 1 adapter.
2. Receives and decrypts a notification payload intended for that NanoNym.
3. Extracts the sender ephemeral public key and transaction metadata.
4. Recomputes the expected stealth destination using the NanoNym's private view key and public spend key.
5. Derives the stealth private key needed to spend from that destination.
6. Verifies the payment against the chain and adds the resulting stealth account to wallet state.

For offline or cold recovery, the wallet repeats the derivation from its seed.
It then scans the configured notification transport and Nano ledger state.

### Stealth Derivation

This section defines the derivation required for NanoNyms v2 interoperability.
Implementations MUST follow these rules unless a later ORIS updates the v2
profile.

Let:

* `G` be the Ed25519 basepoint.
* `L` be the Ed25519 group order, `2^252 + 27742317777372353535851937790883648493`.
* `H_scalar(x)` be the scalar derivation function defined below.
* `a_spend` and `a_view` be the recipient's spend and view private scalars derived from the recipient's private seed material.
* `B_spend = a_spend * G`.
* `B_view = a_view * G`.
* `r` be the sender's per-payment ephemeral private scalar.
* `R = r * G`.

Private seed material is converted to a scalar by:

```text
hash64  = BLAKE2b(input, digest_length = 64)
clamped = hash64[0..32]
clamped[0]  &= 248
clamped[31] &= 127
clamped[31] |= 64
scalar = little_endian_integer(clamped) mod L
```

Setting bit 254 with `|= 64` can produce an integer larger than `L`. The final
`mod L` operation reduces that integer. This is compatible with point
multiplication because `(s * G) == ((s mod L) * G)`. Implementations MUST keep
both the clamping and reduction steps to produce the same scalar.

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

Implementations MUST reject malformed Ed25519 points for `B_spend`, `B_view`,
`R`, and `SA`. The curve library SHOULD reject invalid encodings and small-order
points. Otherwise, the implementation MUST perform those checks before a
shared-secret or point-addition operation.

### Stealth Account Selection

When spending from a NanoNym, the wallet selects funded stealth accounts to satisfy the target amount.

Goals:

- Prefer one stealth account when it covers the amount.
- Otherwise, use a bounded greedy selection.
- Randomize send order to reduce deterministic patterns.

NanoNymNault currently exposes a pure `selectStealthInputs` helper for this behavior.

### Wallet Model

The wallet can present each NanoNym as one aggregated account:

- one label,
- one displayed balance,
- one payment count, and
- multiple underlying stealth accounts.

Archiving a NanoNym stops active monitoring in the wallet, but does not affect recoverability from seed.

### Protocol Boundary

The NanoNyms protocol defines:

- how to encode and decode a NanoNym, and
- how to derive stealth destinations and recovery material.

It does not define:

- how an adapter delivers `notificationUri`,
- how a Nostr relay pool works,
- how an application calls Nano node RPC, or
- how a wallet stores state.

Those concerns belong to application adapters and infrastructure.

### Package Boundaries

- `@nanonyms/protocol` encodes, decodes, and validates the v2 payment code.
- Transport adapters perform scheme-specific validation.
- Downstream packages consume the decoded keys and notification URI.
- Protocol packages do not need v1 parsers or migration code.

### Current NanoNymNault Composition

NanoNymNault currently uses:

- `@nanonyms/protocol` for payment-code encoding,
- `@nanonyms/crypto` for derivation and stealth-account math,
- `@nanonyms/core` for application-independent payment flows, and
- a Nostr adapter for Tier 1 notification delivery.

The packages implement the NanoNyms protocol without requiring Nostr. The
NanoNymNault application chooses Nostr as its current transport.

### Relationship to Other Standards

- ORIS-003 defines the payment event carried by transport profiles.
- ORIS-004 defines delivery for `nostr:...` notification URIs.
- ORIS-005 defines verification when an HTTP 402 flow uses a NanoNym.

## Published Test Vectors

The [Address Test Vector](#address-test-vector) is canonical for NanoNyms
encoding. Stealth-derivation test vectors are not published yet.

## Reference Implementation

- [NanoNymNault protocol specification](https://github.com/cbrunnkvist/NanoNymNault/blob/main/docs/protocol-specification.md)
- [NanoNymNault source](https://github.com/cbrunnkvist/NanoNymNault)
