```
OpenRai Initiative Standard: 011
```

# Nano App-Intent URI Profiles

> Status: Working Draft
> Category: Application Interface

## Abstract

This document formalizes the native Nano URI scheme for payment requests and
wallet app intents. It defines the authority-aware form
`nano://mainnet/<action>/...`, the mainnet shorthand
`nano:<action>/...`, and compatibility aliases for the existing
`nano:` URI forms documented by Nano.

It specifies URI components, action profiles, amount and address encoding,
canonicalization, QR transport, platform handoff behavior, user-confirmation
requirements, and handling of sensitive wallet material.

This document does not define an operating-system registry, a wallet-session
protocol, or a cryptographic authorization mechanism. Opening an app-intent URI
is a request for a wallet user interface. It is never authorization to sign,
publish, import, or change ledger state.

## Motivation

Nano documentation currently describes several URI schemes for payments,
representative changes, key imports, seed imports, and block processing. The
examples are useful, but the formats do not yet provide one interoperable
grammar or one security model.

The important ambiguity is the difference between these forms:

```
nano:send/<address>
nano://mainnet/send/<address>
```

Under RFC 3986, `//` introduces an authority component. This document
therefore uses `mainnet` as the authority in the explicit form and
defines the first form as its mainnet alias. The two forms have the same
semantic request, but they are not the same generic URI parse.

The document separates three concerns that are often mixed together:

- a payment target, such as a destination address and amount;
- a wallet action, such as changing a representative or processing a block; and
- sensitive wallet-data transfer, such as importing a seed or private key.

This separation gives newcomers one predictable model while preserving the
existing address-only payment URI used by wallets, exchanges, and QR codes.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
indicate normative requirements.

Unless otherwise stated:

- A **producer** creates a URI or QR code.
- A **consumer** parses a URI and presents or handles the requested intent.
- A **wallet** is the consumer that controls Nano account keys.
- A **target** is the address, key, seed, or block carried by an action.
- `1 XNO = 10^30 raw`.
- `mainnet` is the only network authority defined by this document.
- Strings are UTF-8 before URI percent-encoding.

## Specification

### Scope

This document covers:

- the explicit `nano://mainnet/<action>/...` URI form;
- the `nano:<action>/...` mainnet alias;
- the existing address-only `nano:<address>` payment form;
- compatibility aliases for `nanorep:`, `nanokey:`,
  `nanoseed:`, and `nanoblock:`;
- common query parameters and raw amount validation;
- producer, consumer, QR, and platform-handoff requirements; and
- published parsing and semantic-equivalence vectors.

This document does not cover:

- `payto://nano/...`, which is defined by [ORIS-009](./ORIS-009.md);
- CAIP-2 or CAIP-10 identifiers, which are defined by
  [ORIS-006](./ORIS-006.md);
- wallet-session methods, callbacks, or response objects;
- mnemonic phrases, BIP-39, or BIP-44 seed derivation; or
- a registry of installed wallet applications.

### URI Forms and Semantic Equivalence

The explicit form is:

```text
nano://<network>/<action>/<target>[?<query>]
```

This document defines only:

```text
nano://mainnet/<action>/<target>[?<query>]
```

The authority is the network namespace. It is not the action and it is not a
wallet application identifier.

The mainnet shorthand form is:

```text
nano:<action>/<target>[?<query>]
```

For every action defined by this document, the shorthand form is an alias of
the explicit `nano://mainnet/` form. A consumer MUST resolve the
shorthand to `mainnet` before applying action-specific validation.

The existing address-only payment form is also a mainnet form:

```text
nano:<nano-address>[?<query>]
```

It is semantically equivalent to:

```text
nano://mainnet/send/<nano-address>[?<query>]
```

The address-only form remains valid for compatibility. New producers SHOULD
use the explicit form when the link is intended to demonstrate or preserve the
network boundary. Producers MAY use the shorthand form when compactness or
compatibility with existing Nano integrations is more important.

The following form is not defined by this document:

```text
nano://<nano-address>[?<query>]
```

It places the address in the authority component and does not identify a
network. A consumer MAY accept it as a legacy mainnet payment alias if it has
documented support for that form. A producer MUST NOT generate it as a new
interoperable URI.

### Generic Parsing Rules

A consumer MUST:

1. Parse the URI with a parser that preserves the scheme, authority, path,
   query, and percent-encoded octets.
2. Decode percent-encoded UTF-8 values exactly once.
3. Reject malformed percent-encoding and invalid UTF-8.
4. Reject an authority other than `mainnet` in the explicit form, except for
   the documented legacy `nano://<nano-address>` compatibility form.
5. Reject an undefined action or an action with the wrong target shape.
6. Validate the target before presenting the intent as actionable.
7. Reject duplicate parameters unless an action profile explicitly permits
   them.
8. Reject values that would be truncated, rounded, or coerced.

Scheme and network-authority comparison is case-insensitive. Producers MUST
emit the lowercase forms `nano` and `mainnet`. Action names
and parameter names are lowercase ASCII and are case-sensitive.

Producers MUST percent-encode query values and path-target data according to
RFC 3986. Unreserved characters MAY remain unencoded. A producer MUST NOT
percent-encode delimiters that are required to separate the scheme, authority,
path, or query components.

Consumers MUST NOT treat a URI string comparison as semantic equivalence. They
MUST compare the parsed, validated request after applying the aliases and
canonicalization rules in this document.

### Address Encoding

The canonical native address is:

```abnf
nano-address = "nano_" nano-first 59(nano-char)
nano-first   = %x31 / %x33
nano-char    = %x31 / %x33-39 / %x61-6B / %x6D-6F /
               %x70-75 / %x77-7A
```

The grammar does not validate the address checksum.

Producers MUST emit a complete checksum-valid `nano_` address.
Consumers MUST:

- accept `nano_` addresses;
- MAY accept the legacy `xrb_` prefix;
- validate the prefix, length, alphabet, and Blake2b-40 checksum; and
- canonicalize an accepted `xrb_` address to `nano_` before
  comparison or storage.

Consumers MUST reject an invalid address without truncation, recovery, or
similarity matching.

### Amount Encoding

The native Nano URI `amount` parameter is always an unsigned decimal
raw amount. The parameter name does not imply XNO units.

```abnf
raw-amount = "0" / nonzero-digit *DIGIT
nonzero-digit = %x31-39
```

Requirements:

- A producer MUST use raw units for `amount`.
- A producer MUST NOT emit a sign, decimal point, exponent, comma, or leading
  zero.
- A consumer MUST reject a non-decimal amount.
- A consumer MUST reject an amount greater than `2^128 - 1`.
- A consumer MUST use integer arithmetic.
- A consumer MUST NOT convert a URI amount through a floating-point type.
- A missing `amount` means that the user must enter the amount.
- A present `amount` is a fixed requested amount; the wallet MAY allow
  the user to cancel or decline it, but MUST NOT silently change it.

Wallets SHOULD display both the exact raw amount and a human-readable XNO
conversion before confirmation. The raw amount remains authoritative.

### Common Query Parameters

| Name | Applies to | Requirement | Meaning |
|---|---|---|---|
| `amount` | `send` | MAY appear once | Fixed amount in raw |
| `label` | `send`, representative change, key import, seed import | MAY appear once | Unauthenticated display label |
| `message` | `send`, representative change, key import, seed import | MAY appear once | Unauthenticated display message |
| `lastindex` | `import-seed` | MAY appear once | Recovery scan hint |

Producers MUST percent-encode `label` and `message` as UTF-8
query values. Consumers MUST NOT present either value as a verified identity or
trusted instruction.

Consumers MUST reject a repeated parameter. Unknown parameters MUST NOT change
the action, target, network, or amount. A consumer MAY ignore an unknown
parameter after warning that the request contains unsupported data. A consumer
MUST reject the URI when it cannot preserve a parameter that is required for
the requested action.

### Action Profiles

#### `send`

The `send` action requests a payment to one Nano address:

```text
nano://mainnet/send/<nano-address>?amount=<raw>&label=<text>&message=<text>
```

The target MUST be a checksum-valid Nano address. The `amount`
parameter MAY be omitted for an open amount. A wallet MUST show the
destination, network, and resolved amount before signing or submitting a send
block.

The existing address-only URI is an alias of this profile:

```text
nano:<nano-address>?amount=<raw>
```

#### `change-representative`

The `change-representative` action requests a representative change:

```text
nano://mainnet/change-representative/<representative-address>?label=<text>&message=<text>
```

The target MUST be a checksum-valid Nano address. The URI does not identify the
source account. A wallet with multiple accounts MUST require the user to select
the source account and MUST NOT silently choose one solely because it is
currently active.

The existing `nanorep:` form is a mainnet compatibility alias:

```text
nanorep:<representative-address>?label=<text>&message=<text>
```

#### `import-key`

The `import-key` action requests import of one raw Nano account
private key:

```text
nano://mainnet/import-key/<private-key>
```

The target MUST be exactly 64 hexadecimal characters. Producers SHOULD emit
uppercase hexadecimal. Consumers MAY accept either case and MUST canonicalize
the value before internal comparison.

This action is sensitive wallet-data transfer. A consumer MUST NOT intentionally
upload, log, index, or retain the key outside encrypted wallet state. It MUST
NOT import the key without explicit user confirmation. A consumer MUST warn
that possession of the key controls the corresponding account. The existing
`nanokey:` form is a mainnet compatibility alias.

#### `import-seed`

The `import-seed` action requests import of one 32-byte Nano seed
represented as 64 hexadecimal characters:

```text
nano://mainnet/import-seed/<seed>?lastindex=<index>
```

`lastindex` is an optional unsigned decimal integer from `0`
through `4294967295`. It is a recovery-scan hint, not proof that
accounts above or below that index do not exist.

This profile defines the raw Nano seed format only. It does not define a
mnemonic, BIP-39 interpretation, or BIP-44 derivation path. A consumer MUST
identify the derivation method it will use before importing or scanning the
seed. The existing `nanoseed:` form is a mainnet compatibility alias.

Seed import has the same handling requirements as private-key import. A wallet
MUST NOT overwrite an existing wallet or account without a separate explicit
confirmation.

#### `process-block`

The `process-block` action requests processing of one serialized JSON
block:

```text
nano://mainnet/process-block/<percent-encoded-json>
```

The target is UTF-8 JSON after one percent-decoding step. It MUST represent a
complete signed Nano block accepted by the consumer's block validator. The
consumer MUST validate the block, account, signature, previous block, balance,
representative, link, and work according to its supported Nano node rules.

Processing a valid block may publish a ledger action. A consumer MUST NOT
process or publish it without explicit user approval. The existing
`nanoblock:` form is a mainnet compatibility alias, where the data
after the scheme is the same JSON payload before URI decoding.

### Compatibility Alias Table

| Existing form | Canonical semantic form |
|---|---|
| `nano:<address>?...` | `nano://mainnet/send/<address>?...` |
| `nano:send/<address>?...` | `nano://mainnet/send/<address>?...` |
| `nanorep:<address>?...` | `nano://mainnet/change-representative/<address>?...` |
| `nanokey:<key>` | `nano://mainnet/import-key/<key>` |
| `nanoseed:<seed>?lastindex=...` | `nano://mainnet/import-seed/<seed>?lastindex=...` |
| `nanoblock:<json>` | `nano://mainnet/process-block/<percent-encoded-json>` |

The alias table defines semantic equivalence, not a requirement that every
consumer implement every legacy scheme. A consumer that does not support a
profile MUST reject it clearly rather than opening a generic payment screen.

### Producer Requirements

A producer:

- MUST generate the explicit `nano://mainnet/` form for new
  app-intent profiles unless a compatibility constraint requires the shorthand
  or legacy form;
- MUST generate lowercase scheme, authority, action, and parameter names;
- MUST use a checksum-valid canonical `nano_` address;
- MUST use raw integer amounts;
- MUST percent-encode path-target data and query values correctly;
- MUST NOT place a private key or seed in a URI intended for an uncontrolled
  web page, redirect, analytics system, or public message;
- MUST NOT imply that a label, message, or URI origin authenticates a recipient;
  and
- SHOULD provide the explicit network form when the URI may be copied between
  applications or devices.

### Consumer and User-Confirmation Requirements

Receiving or opening a URI is not user authorization. Before a wallet signs,
publishes, imports, changes a representative, or processes a block, it MUST:

1. Parse and validate the complete URI.
2. Display the requested action and network.
3. Display the complete destination or relevant account identifier.
4. Display the exact raw amount, when present.
5. Identify any untrusted label, message, or instruction as informational.
6. Obtain explicit user approval for the specific action.

A wallet MUST NOT execute an action merely because an operating system opened
the application. A wallet MUST NOT silently fall back from an unsupported
network or action to the current account or current network.

### QR-Code Transport

The QR payload is the exact URI string defined by this document. Producers MUST:

- encode the URI as UTF-8;
- omit leading and trailing whitespace;
- not replace percent escapes with display text; and
- not add a second URI, comment, or application-specific wrapper.

Consumers MUST pass decoded QR text through the same URI parser used for links.
QR decoding does not establish authenticity or user intent.

Large `process-block`, seed, or key payloads may exceed practical QR
limits. This document does not define animated or multipart QR encoding.
Applications that need multipart transfer SHOULD use a separately specified
secure transfer format.

### Platform Handoff

This section is informative. Operating-system handler selection is outside the
Nano URI grammar.

Android custom-scheme handlers may use scheme, authority, and path filters, but
multiple applications can still claim the same URI and trigger user
disambiguation. iOS custom URL schemes do not provide unique ownership.
Domain-verified Android App Links and iOS Universal Links can provide stronger
routing when a producer controls an HTTPS domain, but they are separate
transport surfaces from the native `nano:` scheme.

Wallets SHOULD document their installed-scheme behavior and SHOULD support a
wallet-specific deep link or verified HTTPS link when an application needs to
select one particular wallet. A producer MUST NOT claim that a generic
`nano:` URI deterministically selects one wallet on every platform.

### Network Extensibility

Only `mainnet` is defined in this version. A consumer MUST reject an
unknown network authority. It MUST NOT interpret an unknown authority as the
current wallet network.

Future network profiles MAY define additional authorities through a later ORIS.
The shorthand `nano:<action>/...` remains an alias for `mainnet`
and MUST NOT silently change meaning when another network is added.

## Published Test Vectors

These vectors reuse the checksum-valid address body from [ORIS-006](./ORIS-006.md):

```text
3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

The corresponding canonical address is:

```text
nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 1 — Explicit Send Form

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000
```

Semantic result:

```text
network = mainnet
action = send
target = nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
amount_raw = 1000
```

### Vector 2 — Shorthand Alias

The following URI MUST produce the same semantic request as Vector 1:

```text
nano:send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000
```

### Vector 3 — Existing Payment Alias

The following URI MUST produce the same semantic request as an explicit send:

```text
nano:nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000
```

### Vector 4 — Representative Change

```text
nano:change-representative/nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou?label=Official%20Rep
```

Semantic result:

```text
network = mainnet
action = change-representative
source_account = user-selected
```

### Vector 5 — Invalid Amount

The following URI MUST be rejected because the amount has a leading zero:

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=01000
```

### Vector 6 — Invalid Network

The following URI MUST be rejected because `beta` is not defined by
this document:

```text
nano://beta/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000
```

## Reference Implementation

No reference implementation is nominated yet.

## Open Questions

- Which existing wallets accept `nano://mainnet/...` authority-aware forms.
- Whether the action name should be `change-representative`,
  `representative`, or another ecosystem-compatible token.
- Whether the legacy `nano://<address>` form should remain a permitted
  consumer alias after an implementation survey.
- Whether a future ORIS should define a secure multipart QR transfer profile.
- Whether wallet-specific deep links should be catalogued in a maintained
  registry or left to each integration.

## References

- [RFC 3986 — Uniform Resource Identifier (URI): Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986.html)
- [RFC 8905 — The `payto` URI Scheme for Payments](https://www.rfc-editor.org/rfc/rfc8905.html)
- [Nano Documentation — Distribution and Units](https://docs.nano.org/protocol-design/distribution-and-units/)
- [Nano Documentation — URI and QR Code Standards](https://docs.nano.org/integration-guides/the-basics/#uri-and-qr-code-standards)
- [Android Developers — Create deep links](https://developer.android.com/training/app-links/create-deeplinks)
- [Apple — Support Universal Links](https://developer.apple.com/library/archive/documentation/General/Conceptual/AppSearch/UniversalLinks.html)
- [ORIS-006 — Nano CAIP Identifiers](./ORIS-006.md)
- [ORIS-009 — Nano Payment Targets for `payto:`](./ORIS-009.md)
