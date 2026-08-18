```
OpenRai Initiative Standard: 011
```

# Nano App-Intent URI Profiles

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines an ORIS profile for the native Nano URI scheme and wallet
app-intent requests. It defines the authority-aware form
`nano://mainnet/<action>/...`, the mainnet shorthand
`nano:<action>/...`, and compatibility aliases for the existing
Nano URI forms documented by Nano. The authority-aware and action-bearing forms
are defined by this document and do not imply current wallet support.

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

This document supplies that missing scheme-specific profile. It uses the generic
URI parsing model from RFC 3986 without reproducing the generic URI grammar.
The authority-aware and action-bearing forms below are ORIS-defined forms. The
legacy forms are compatibility inputs documented by Nano.

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
- compatibility aliases for `nanorep:`, `nanokey:`, and `nanoseed:`; and
- the reserved, unprofiled status of the documented `nanoblock:` form;
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
9. Reject a fragment. This profile does not define fragment semantics.
10. Reject dot-segments, empty path segments, trailing path separators, and
    additional path segments not defined by the selected action profile.

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

Canonicalization is semantic rather than a requirement for one unique URI
serialization. Query-parameter order does not affect semantic equivalence.
Percent-encoded values are decoded once before action validation, and accepted
`xrb_` addresses are canonicalized to `nano_`. Producers still emit the
required lowercase names and percent-encode delimiters as specified above.

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
nano://mainnet/import-key/<private-key>?label=<text>&message=<text>
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
nano://mainnet/import-seed/<seed>?label=<text>&message=<text>&lastindex=<index>
```

`lastindex` is an optional unsigned decimal integer from `0`
through `4294967295`. It is a recovery-scan hint, not proof that
accounts above or below that index do not exist.

The action distinguishes a requested seed import from an `import-key` request.
It does not, by itself, distinguish legacy Nano seed derivation from another
wallet derivation family. This document does not force one derivation choice
when the URI does not identify a derivation profile.

When no derivation profile is supplied, a consumer SHOULD apply its existing
wallet seed-import behavior. A consumer MAY ask the user to select a profile,
expose an advanced option, or probe supported profiles. Before importing, the
consumer MUST identify the selected derivation profile and obtain explicit user
confirmation.

The documented `nanoseed:` form is historically associated with legacy Nano
seed derivation. A future ORIS MAY define an explicit profile for BIP-39,
BIP-32, BIP-44, or another derivation family.

A producer that requires a particular derivation profile MUST NOT rely on its
omission. It MUST use an explicitly defined profile when one is available.

Under the legacy Nano derivation behavior, the private key at index `i` is
`BLAKE2b-256(seed || uint32_be(i))`.

Seed import has the same handling requirements as private-key import. A wallet
MUST NOT overwrite an existing wallet or account without a separate explicit
confirmation.

#### `process-block`

The `process-block` action is reserved for future use. Its target, when this
document defines it, will be a JSON object that validates against the block
schema accepted by the consumer's supported Nano node version.

This document does not define a separate JSON schema, parsing rules,
block-processing semantics, or interoperability requirements for this action.
The documented `nanoblock:` form remains unprofiled here.
Until a later ORIS defines this action, producers MUST NOT generate it and
consumers MUST reject it as unsupported.

### Compatibility Alias Table

| Existing form | Canonical semantic form |
|---|---|
| `nano:<address>?...` | `nano://mainnet/send/<address>?...` |
| `nano:send/<address>?...` | `nano://mainnet/send/<address>?...` |
| `nanorep:<address>?...` | `nano://mainnet/change-representative/<address>?...` |
| `nanokey:<key>?label=...&message=...` | `nano://mainnet/import-key/<key>?label=...&message=...` |
| `nanoseed:<seed>?label=...&message=...&lastindex=...` | `nano://mainnet/import-seed/<seed>?label=...&message=...&lastindex=...` |
| `nanoblock:<json>` | Reserved; no canonical semantic form is defined |

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

Large future-reserved payloads may exceed practical QR limits. This document
does not define animated or multipart QR encoding.
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

### Vector 7 — Private-Key Import

```text
nano://mainnet/import-key/1495F2D49159CC2EAAAA97EBB42346418E1268AFF16D7FCA90E6BAD6D0965520?label=Imported%20Account
```

Semantic result:

```text
network = mainnet
action = import-key
target = 1495F2D49159CC2EAAAA97EBB42346418E1268AFF16D7FCA90E6BAD6D0965520
label = Imported Account
```

### Vector 8 — Seed Import With Existing Wallet Behavior

```text
nano://mainnet/import-seed/0000000000000000000000000000000000000000000000000000000000000001?label=Recovery%20Seed&lastindex=1
```

Semantic result:

```text
network = mainnet
action = import-seed
seed = 0000000000000000000000000000000000000000000000000000000000000001
lastindex = 1
derivation = selected by consumer's existing wallet behavior
```

The consumer MUST identify the selected derivation profile before import.

### Vector 9 — Legacy Address Prefix Canonicalization

The following URI is accepted only if the consumer supports the legacy
`xrb_` prefix. Its semantic target MUST be canonicalized to `nano_`:

```text
nano://mainnet/send/xrb_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000
```

### Vector 10 — Repeated Parameter

The following URI MUST be rejected because `amount` appears more than once:

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000&amount=1000
```

### Vector 11 — Fragment

The following URI MUST be rejected because this profile does not define
fragment semantics:

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=1000#confirmation
```

### Vector 12 — Malformed Percent-Encoding

The following URI MUST be rejected because `%ZZ` is not valid percent-encoding:

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?label=%ZZ
```

### Vector 13 — Trailing Path Segment

The following URI MUST be rejected because the `send` action has an additional
path segment:

```text
nano://mainnet/send/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn/extra
```

The reserved `process-block` action has no test vector. This document does not
define its processing semantics.

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
