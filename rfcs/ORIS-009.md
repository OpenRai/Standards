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

The generic grammar below is RFC 8905 §2, reproduced for reference; the `nano`-specific additions are new in this document.

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
| `amount` | generic-opt | MAY be present | See [Amount Representation](#amount-representation) |
| `receiver-name` | generic-opt | MAY be present | Canonical hyphenated form |
| `sender-name` | generic-opt | MAY be present | Defined by RFC 8905; not yet exercised by existing Nano wallet docs |
| `message` | generic-opt | MAY be present | Free-text, producer-supplied, unauthenticated |
| `instruction` | generic-opt | MAY be present | Defined by RFC 8905; no Nano-specific semantics assigned yet |

Producers MUST NOT emit underscore-separated option names (e.g. `receiver_name`) — the RFC 8905 `opt-name` grammar only permits `ALPHA`, `DIGIT`, `-`, and `.`; underscores are not legal. Consumers MAY accept underscore variants for backward compatibility with non-conformant producers, but MUST treat the hyphenated form as canonical when generating.

No `nano`-specific `authority-specific-opt` values are defined by this document. Consumers MUST ignore unrecognized authority-specific options that do not affect address resolution or amount, to preserve forward compatibility with future extensions (e.g. NanoNym targets, correlation identifiers per ORIS-007).

### Amount Representation

- Format per RFC 8905: `amount=[<currency>:]<value>`.
- When no currency prefix is given, `<value>` MUST be interpreted as raw units, and MUST be an unsigned base-10 integer string — no decimal point, no scientific notation, no separators. Producers MUST NOT emit floating-point-formatted raw amounts.
- When a currency prefix is given (an ISO 4217 code, or the literal token `XNO`), consumers MUST convert to raw using 1 XNO = 10^30 raw, performed with arbitrary-precision/bigint arithmetic. Consumers MUST NOT perform this conversion using native IEEE-754 double-precision floats — that representation cannot hold 10^30 exactly, and this exact class of bug has caused fund-loss incidents in other ecosystems.
- Fiat-denominated amounts require an exchange-rate lookup that is inherently non-atomic between URI generation and consumption. Producers SHOULD prefer emitting raw or `XNO`-denominated amounts directly, and MAY omit `amount` entirely for open-ended requests (tips, donations).

### Generation Rules (Producer Requirements)

Producers:

- MUST emit `payto://nano/<nano-address>`, `nano_`-prefixed, double-slash form.
- MUST percent-encode option values per RFC 3986 `pchar` rules (in particular, spaces in `receiver-name` and `message`).
- MUST NOT emit float-formatted raw amounts.
- SHOULD also emit a companion `nano:` URI when the display context is Nano-specific (see [Relationship to the `nano:` Scheme](#relationship-to-the-nano-uri-scheme)).
- SHOULD include `receiver-name` where a stable, meaningful recipient identity exists.

### Parsing Rules (Consumer Requirements)

Consumers:

- MUST accept options in any order.
- MUST validate the address checksum before treating a URI as actionable.
- MUST reject the URI outright if the `amount` value or address fails validation; MUST NOT silently coerce, truncate, or round.
- MUST ignore unrecognized authority-specific options that don't affect address or amount resolution.
- MUST NOT prefill and auto-submit a transaction without explicit user review — the confirmation UI MUST display the full, untruncated destination address and the resolved amount (in both raw and a human-readable unit) before any signing occurs. This extends RFC 8905 §8's general prohibition on unreviewed transaction initiation with a Nano-specific requirement: because Nano sends are irrevocable and confirm in under a second, an ellipsized or truncated address in the confirmation dialog is a distinct phishing vector from the ones RFC 8905 already addresses.
- MUST NOT present `receiver-name` or `message` in a way that could be mistaken for consumer-verified identity (e.g., a verified badge) — these fields are producer-supplied and unauthenticated.

### URI Handler Registration (Informative)

This section is non-normative; verify exact mechanisms against current platform documentation before implementing.

- **Android**: register an `intent-filter` with `android:scheme="payto"` (and separately `"nano"`).
- **iOS / macOS**: register `"payto"` and `"nano"` under `CFBundleURLSchemes`.
- **Web**: `navigator.registerProtocolHandler()` has partial and inconsistent browser support for custom schemes; treat as supplementary, not primary. This is a distinct integration surface from the W3C Payment Request / Payment Handler API path and is out of scope here.

## Compatibility Matrix

To be populated via a community survey (tracking issue TBD) rather than unilateral reverse-engineering. Wallet maintainers should confirm current behavior directly.

| Wallet | `payto://` (double-slash) | `payto:` (single-slash) | `receiver-name` | `receiver_name` | raw integer amount | `XNO:`float amount | `nano:` companion | Source / notes |
|---|---|---|---|---|---|---|---|---|
| Nautilus | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Cake Wallet | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Natrium | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Nault | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |

## Open Questions

- Single-slash vs. double-slash authority delimiter — resolve empirically via the compatibility matrix before this leaves Draft.
- Whether `sender-name` and `instruction` (defined by RFC 8905, unused so far in Nano wallets) should be given Nano-specific semantics in v1 or explicitly deferred.
- Whether a future NanoNym-based `payto:` target type (building on ORIS-002/ORIS-005) belongs in this document or a successor.

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

Note the underscore is raw in the `payto:` form and percent-encoded (`%5F`) in the CAIP-10 form — both decode to the identical canonical address `nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn`.

Further vectors — in particular for the [open questions](#open-questions) around slash count and option-name casing — should be added once the compatibility matrix confirms the canonical forms in production use.

## Reference Implementation

No reference implementation is nominated yet.

## References

- [RFC 8905 — The 'payto' URI Scheme for Payments](https://www.rfc-editor.org/rfc/rfc8905)
- [docs.nano.org — URI and QR Code Standards](https://docs.nano.org/integration-guides/the-basics/#uri-and-qr-code-standards)
- [nano.community — Integrations / URI Scheme Standards](https://nano.community/getting-started-devs/integrations#uri-scheme-standards)
- [ORIS-006 — Nano CAIP Identifiers](./ORIS-006.md)
- [ORIS-007 — Nano Application-Level Metadata, Correlation, and Signaling Patterns](./ORIS-007.md)
