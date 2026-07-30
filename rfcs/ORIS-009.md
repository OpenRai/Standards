```
OpenRai Initiative Standard: 009
```

# Nano Payment Targets for `payto:`

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines the `nano` payment target type for the `payto:` URI scheme
in RFC 8905. It specifies the account path, Nano amount formats, canonical
generation, and safe parsing.

The `nano` target type is not yet listed in the GANA Payto Payment Target Types
registry. RFC 8905 recommends that applications allow unregistered target types,
so implementations can test this Working Draft before registration.

## Motivation

Community documentation and wallet implementations use more than one Nano
`payto:` form. Three differences affect interoperability:

- RFC 8905 requires `payto://`, while some Nano examples omit `//`.
- RFC 8905 permits `receiver-name`, but not `receiver_name`.
- RFC 8905 amount syntax cannot represent every 30-decimal Nano raw amount.

This profile defines one canonical form and limited compatibility behavior. A
parser must reject ambiguous or inexact amounts rather than guess.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated:

- `payto:` refers to the URI scheme defined by RFC 8905.
- `nano:` refers to Nano's existing native payment URI.
- ORIS-006 defines `nano:mainnet` and Nano CAIP-10 account IDs.
- A **producer** generates a URI or QR code.
- A **consumer** parses a URI or handles it as a payment request.
- `1 XNO = 10^30 raw`.

## Specification

### Scope

This document covers:

- the `payto://nano/...` target type,
- canonical account and amount encoding,
- producer and consumer requirements,
- informative platform registration notes, and
- known compatibility questions.

This document does not cover:

- the syntax of the existing `nano:` scheme,
- non-Nano payment target types,
- payment-correlation conventions from ORIS-007, or
- NanoNyms payment targets.

### Relationship to the `nano:` URI Scheme

The `nano:` scheme remains the native Nano payment URI. The `payto:` scheme
provides a shared envelope for many payment systems. Applications SHOULD support
both when their platform can register both handlers.

When an application represents one request in both forms, the destination and
amount MUST resolve to the same values. This document does not otherwise change
the `nano:` scheme.

### Relationship to ORIS-006 CAIP Identifiers

ORIS-006 encodes a Nano account as
`nano:mainnet:nano%5F<account-body>` because CAIP-10 excludes `_`.

RFC 3986 permits `_` in a `payto:` path. The canonical forms therefore differ:

| Form | Canonical string |
|---|---|
| `payto:` URI | `payto://nano/nano_<account-body>` |
| CAIP-10 | `nano:mainnet:nano%5F<account-body>` |
| Native address | `nano_<account-body>` |

A producer MUST leave the underscore unencoded in the `payto:` path. An
implementation that supports both formats MUST compare their decoded,
checksum-valid native addresses.

The `nano` authority identifies Nano mainnet in this profile. Producers MUST NOT
invent a query option for another Nano network.

### ABNF Syntax

The generic grammar below comes from RFC 8905 Section 2. The Nano additions are
defined here.

```abnf
; Generic payto grammar (RFC 8905 §2)
payto-URI      = "payto://" authority path-abempty [ "?" opts ]
opts           = opt *( "&" opt )
opt            = opt-name "=" opt-value
opt-name       = generic-opt / authority-specific-opt
opt-value      = *pchar
generic-opt    = "amount" / "receiver-name" / "sender-name" / "message" / "instruction"
authority-specific-opt = ALPHA *( ALPHA / DIGIT / "-" / "." )

; Nano-specific additions (this document)
authority      =/ "nano"
path-abempty   = "/" nano-address
nano-address   = ("nano_" / "xrb_") 60( base32-nano-char )
base32-nano-char = %x31 / %x33-39 / %x61-6B / %x6D-6E /
                   %x70-75 / %x77-7A
```

ABNF does not validate the address checksum.

Producers MUST emit
`payto://nano/<nano-address>[?<opts>]`. They MUST include the double slash.

Consumers MAY accept `payto:nano/<nano-address>` as legacy input. Producers MUST
NOT generate that form.

### Address Encoding

- The path MUST contain one complete, checksum-valid Nano address.
- The address underscore MUST remain unencoded.
- Producers MUST use the `nano_` prefix.
- Consumers MUST accept `nano_` and `xrb_`.
- Consumers MUST validate the Nano alphabet, length, and Blake2b-40 checksum.
- Consumers MUST reject an invalid address without truncation or recovery.

### Query Parameters

| Name | Source | Requirement | Notes |
|---|---|---|---|
| `amount` | generic option | MAY appear once | XNO amount, defined below |
| `nano-raw` | Nano option | MAY appear once | Exact amount in raw |
| `receiver-name` | generic-opt | MAY be present | Canonical hyphenated form |
| `sender-name` | generic-opt | MAY be present | Sender-supplied name |
| `message` | generic-opt | MAY be present | Free-text, producer-supplied, unauthenticated |
| `instruction` | generic-opt | MAY be present | Reconciliation instructions |

Producers MUST use hyphenated generic option names. They MUST NOT emit
underscore forms such as `receiver_name`. Consumers MAY accept an underscore
form as legacy input.

This document defines only one Nano-specific option: `nano-raw`. Consumers MUST
ignore other unrecognized authority-specific options unless they change address
or amount resolution.

### Amount Representation

RFC 8905 requires `amount=<currency>:<unit>[.<fraction>]`. It reserves
three-letter currency names for ISO 4217, limits `unit` to values below 2^53,
and permits at most eight fractional digits. The three-letter ticker `XNO`
therefore cannot be assigned custom semantics in this field.

This profile defines the four-letter currency name `NANO`:

```text
amount=NANO:<unit>[.<fraction>]
```

Requirements:

- Consumers MUST ignore commas in `unit` and `fraction`, as RFC 8905 requires.
- After removing commas, `unit` MUST contain base-10 digits and be less than
  2^53.
- After removing commas, `fraction` MAY contain one to eight base-10 digits.
- Producers MUST NOT emit commas, signs, exponents, or trailing decimal points.
- Consumers MUST interpret the value as XNO.
- Consumers MUST convert XNO to raw with exact decimal or integer arithmetic.

For an exact raw amount, use:

```text
nano-raw=<unsigned-base-10-integer>
```

`nano-raw` has no 2^53 limit. Its value MUST contain digits only, with no
leading zero unless the value is `0`.

A producer MUST NOT include both `amount` and `nano-raw`. A consumer MUST reject
a URI containing both. A producer MAY omit both for an open amount.

### Generation Rules (Producer Requirements)

Producers:

- MUST emit `payto://nano/<nano-address>`, `nano_`-prefixed, double-slash form.
- MUST percent-encode option values according to RFC 3986.
- MUST use `amount=NANO:...` or `nano-raw=...` for a fixed amount.
- SHOULD also emit a companion `nano:` URI when the display context is Nano-specific (see [Relationship to the `nano:` Scheme](#relationship-to-the-nano-uri-scheme)).
- SHOULD include `receiver-name` where a stable, meaningful recipient identity exists.

### Parsing Rules (Consumer Requirements)

Consumers:

- MUST accept options in any order.
- MUST reject repeated `amount` or `nano-raw` options.
- MUST validate the address checksum before treating a URI as actionable.
- MUST reject an invalid address or amount without coercion, truncation, or
  rounding.
- MUST ignore unknown options that do not affect the destination or amount.
- MUST require user review before signing or submitting a transaction.
- MUST let the user inspect the complete destination and exact resolved amount.
- MUST NOT present `receiver-name` or `message` as verified identity.

### URI Handler Registration (Informative)

This section is non-normative. Verify each mechanism against current platform
documentation.

- **Android**: register an `intent-filter` with `android:scheme="payto"` (and separately `"nano"`).
- **iOS / macOS**: register `"payto"` and `"nano"` under `CFBundleURLSchemes`.
- **Web**: Browser support for `navigator.registerProtocolHandler()` and custom
  schemes varies. Treat it as an optional integration.

## Compatibility Matrix

To be populated via a community survey (tracking issue TBD) rather than unilateral reverse-engineering. Wallet maintainers should confirm current behavior directly.

| Wallet | `payto://` | legacy single-slash | `receiver-name` | `receiver_name` | `nano-raw` | `NANO:` amount | `nano:` companion | Source / notes |
|---|---|---|---|---|---|---|---|---|
| Nautilus | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Cake Wallet | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Natrium | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Nault | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |

## Open Questions

- Which wallets require the legacy single-slash input form.
- Whether `sender-name` and `instruction` need Nano-specific limits.
- Whether a future NanoNyms target belongs here or in a separate profile.

## Published Test Vectors

This document reuses [ORIS-006](./ORIS-006.md)'s published account body for continuity across the series:

```text
3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 1 — Canonical `payto:` Form

Input (native Nano address):

```text
nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

Canonical `payto:` output:

```text
payto://nano/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 2 — Equivalence with ORIS-006 CAIP-10 Form

The following two identifiers MUST be treated as denoting the same account:

```text
payto://nano/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

The underscore is raw in `payto:` and percent-encoded in CAIP-10. Both decode
to the same native Nano address.

### Vector 3 — XNO Amount

```text
payto://nano/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?amount=NANO:1.25
```

Resolved raw amount:

```text
1250000000000000000000000000000
```

### Vector 4 — Exact Raw Amount

```text
payto://nano/nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn?nano-raw=123
```

## Reference Implementation

No reference implementation is nominated yet.

## References

- [RFC 8905 — The 'payto' URI Scheme for Payments](https://www.rfc-editor.org/rfc/rfc8905)
- [GANA — Payto Payment Target Types](https://gana.gnunet.org/payto-payment-target-types/payto_payment_target_types.html)
- [docs.nano.org — URI and QR Code Standards](https://docs.nano.org/integration-guides/the-basics/#uri-and-qr-code-standards)
- [nano.community — Integrations / URI Scheme Standards](https://nano.community/getting-started-devs/integrations#uri-scheme-standards)
- [ORIS-006 — Nano CAIP Identifiers](./ORIS-006.md)
- [ORIS-007 — Nano Application-Level Metadata, Correlation, and Signaling Patterns](./ORIS-007.md)
