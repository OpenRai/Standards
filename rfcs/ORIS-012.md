```
OpenRai Initiative Standard: 012
```

# The `rai` Sub-Unit and Safe Amount Serialization for Nano Applications

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines `rai`, an application-level Nano (XNO) unit equal to
`10^-6 XNO` (`10^24 raw`). It defines exact amount serialization rules for
`raw`, `XNO`, and whole `rai` amounts in JSON and binary64-backed formats.

The rules apply to application payloads such as API responses, webhooks, and
analytics events. They do not change Nano ledger or Nano RPC representations.

## Motivation

`1 XNO = 10^30 raw`. JSON permits decimal numbers of arbitrary length, but
common JSON receivers use IEEE 754 binary64. This is also the numeric type of
JavaScript `Number` and many languages' default float type. Binary64
represents integers exactly only up to `2^53 - 1 = 9,007,199,254,740,991`
([`Number.MAX_SAFE_INTEGER`](#references)). A `raw` amount exceeds this range
for essentially every transaction of practical size. Only amounts below
roughly `9 × 10^-9 rai` (`9 × 10^-15 XNO`) would fit. In practice, that means:
**a bare JSON number is not a safe general-interchange representation for a
`raw` amount.**

An amount that is rounded in transit can produce an incorrect balance,
invoice, or payout. A format contract must therefore state both the unit and
the permitted representation.

A second, related problem is the lack of a standardized name for the common
six-decimal XNO display precision. This document calls that quantity `rai`.
The name has earlier third-party precedent at the same value, but it is an
ORIS-defined unit here. It does not change Nano's documented `nano`/XNO and
`raw` units or standardize an SI-prefixed denomination ladder.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
indicate normative requirements.

Unless otherwise stated:

- `1 XNO = 10^30 raw`.
- A **producer** generates or serializes an amount.
- A **consumer** parses or displays an amount.
- **Safe integer range** means the closed interval
  `[-(2^53 - 1), 2^53 - 1]`, per [RFC 8259 §6](#references).
- A **whole `rai` amount** is a non-negative integer number of `rai`.
- An amount defined by this document is non-negative.

## Specification

### Scope

This document covers:

- the definition of the `rai` unit,
- its relationship to `raw` and `XNO`,
- normative serialization rules for `raw`, `XNO`, and `rai` amounts in JSON
  and comparable interchange formats, and
- field-naming and conversion-arithmetic requirements for producers and
  consumers of such amounts.

This document does not cover:

- the Nano block format or Nano RPC action contracts,
- wallet UI default-denomination policy, or
- the `payto:` or `nano:` URI amount parameters, which [ORIS-009](./ORIS-009.md)
  already specifies.

### Unit Definition

| Unit  | Value in `raw`      | Value in `XNO` | Value in `rai` |
|-------|----------------------|----------------|-----------------|
| `raw` | `1`                  | `10^-30`       | `10^-24`        |
| `rai` | `10^24`              | `10^-6`        | `1`             |
| `XNO` | `10^30`              | `1`            | `10^6`          |

`1 rai = 0.000001 XNO = 1,000,000,000,000,000,000,000,000 raw`.

`amount_rai` represents whole `rai` only. An XNO value with at most six
fractional digits is representable as a whole number of `rai`.

### The Float64 / JSON Safe-Integer Problem

`2^53 - 1 = 9,007,199,254,740,991`. Expressed in each unit:

| Unit  | Approximate value below which a bare JSON/float64 number is exact |
|-------|---------------------------------------------------------------------|
| `raw` | `~9 × 10^-9 rai` (`~9 × 10^-15 XNO`) |
| `rai` | `~9.0 × 10^15 rai` (`~9.0 × 10^9 XNO`) |
| `XNO` | depends on required fractional precision, described below |

The largest whole `rai` amount representable by a Nano `uint128` raw value is
`floor((2^128 - 1) / 10^24) = 340,282,366,920,938 rai`. This is less than
`2^53 - 1`. Therefore, a valid whole `rai` amount is always exactly
representable as a binary64 integer. This establishes the `rai` allowance in
[Serialization Requirements](#serialization-requirements) without depending
on the current circulating supply.

The XNO integer component alone does not establish safety. A value with raw
precision can require 30 decimal places. Binary64 does not preserve that
precision. RFC 8259 and RFC 7493 therefore do not guarantee that such a JSON
number round-trips. Encode a fractional XNO value as a decimal string.

### Amount Syntax

```abnf
unsigned-integer = "0" / ( nonzero-digit *DIGIT )
nonzero-digit    = %x31-39
xno-decimal      = unsigned-integer [ "." 1*30DIGIT ]
```

The grammar does not validate the applicable maximum value or whether an XNO
decimal converts to a whole `raw` amount.

### Serialization Requirements

#### Producer Requirements

A producer:

- MUST encode `amount_raw` as an `unsigned-integer` string no greater than
  `2^128 - 1`.
- MUST NOT encode `amount_raw` as a JSON number.
- MUST encode an `amount_xno` value with a fractional part as an
  `xno-decimal` string.
- MAY encode a whole `amount_xno` value as a JSON integer.
- MUST encode `amount_rai` as a whole `rai` amount no greater than
  `340282366920938`.
- MAY encode `amount_rai` as a JSON integer or an `unsigned-integer` string.
- MUST NOT round or truncate a `raw` amount to produce `amount_rai`.
- MUST use `amount_raw` or decimal-string `amount_xno` when a raw amount is
  not divisible by `10^24`.

A producer MUST ensure that an `amount_xno` value converts exactly to a
non-negative raw amount no greater than `2^128 - 1`.

#### Consumer Requirements

A consumer:

- MUST reject an `amount_raw` JSON number.
- MUST reject an `amount_xno` JSON number with a fractional part.
- MUST reject a fractional `amount_rai` value.
- MUST reject an amount that fails its syntax, range, or exact-conversion
  requirement.
- MUST accept a valid whole `amount_rai` encoded as either a JSON integer or
  an `unsigned-integer` string.

These rules apply to binary64 or narrower formats. Examples include JSON
receivers, JSON-compatible YAML numbers, float64 MessagePack values, and
spreadsheet cells. They do not apply to native arbitrary-precision numeric
types.

### Field Naming Convention

A field carrying a Nano amount SHOULD name its unit explicitly rather than
using a bare `amount` whose unit is only established by external context,
consistent with the `amount`/`nano-raw` disambiguation already adopted in
[ORIS-009](./ORIS-009.md):

```text
amount_raw   — `unsigned-integer` string, raw
amount_rai   — whole rai: JSON integer or `unsigned-integer` string
amount_xno   — `xno-decimal` string, or JSON integer for whole XNO
```

A payload SHOULD carry one amount unit. A payload with multiple amount units
MUST use values that convert exactly under [Conversion Arithmetic](#conversion-arithmetic).

### Conversion Arithmetic

Conversion between `raw`, `rai`, and `XNO` MUST use exact integer or
arbitrary-precision decimal arithmetic. A producer or consumer MUST NOT use
binary floating-point arithmetic for a conversion that preserves raw value.

Conversion from `raw` to a whole `rai` amount MUST reject a value that is not
divisible by `10^24`. It MUST NOT round or truncate the value.

### Display Guidance (Informative)

Wallet and application UIs MAY label a six-decimal XNO display as `rai`.
This document does not require a default display denomination.

## Relationship to Other ORIS Documents

- [ORIS-003](./ORIS-003.md) (NanoNyms Payment Event Schema) defines
  `amount_raw` as a decimal string.
- [ORIS-008](./ORIS-008.md) (Reliable Nano Payment Integration) applies these
  rules to amount fields in reconciliation records.
- [ORIS-009](./ORIS-009.md) (Nano Payment Targets for `payto:`) defines
  `amount=NANO:...` and `nano-raw=...` for URI parameters.

## Non-Goals

- This document does not change native Nano block or Nano RPC amount
  representations.
- This document does not mandate a default display denomination for any
  wallet or application.
- This document does not deprecate any existing Nano denomination. It defines
  one additional application-level unit.

## Open Questions

- Whether `rai` should be formally proposed for inclusion in
  `docs.nano.org`'s own unit documentation, or remain an ORIS-scoped
  convention referenced by name.
- Whether wallet maintainers are willing to adopt `rai` as a labeled unit
  given existing six-decimal `XNO` display conventions, and if so, on what
  timeline.

## Published Test Vectors

### Vector 1 — Unit Conversion

```text
1 XNO  = 1,000,000 rai
1 XNO  = 1000000000000000000000000000000 raw   (10^30)
1 rai  = 1000000000000000000000000 raw          (10^24)
1 raw  = 0.000001 rai
1 raw  = 0.000000000000000000000000000001 XNO   (10^-30)
```

### Vector 2 — Six-Decimal Display Amount

Input (`XNO`, six decimal places):

```json
{ "amount_xno": "1.500000" }
```

Equivalent whole `rai` amount:

```json
{ "amount_rai": 1500000 }
```

Equivalent `raw` amount:

```json
{ "amount_raw": "1500000000000000000000000000000" }
```

### Vector 3 — Full-Precision Amount (Unsafe as a Bare Number)

A payment of exactly `133248297 raw` above one whole `XNO`:

```text
raw = 1000000000000000000000133248297
```

Correct (decimal string):

```json
{ "amount_raw": "1000000000000000000000133248297" }
```

Incorrect (bare JSON number — silently rounds under IEEE 754 binary64):

```json
{ "amount_raw": 1000000000000000000000133248297 }
```

### Vector 4 — Maximum Whole `rai` Amount

```text
floor((2^128 - 1) / 10^24) = 340282366920938 rai
```

`340282366920938 < 2^53 - 1 (9007199254740991)` — safe as a bare JSON
integer, illustrating that a whole `rai` amount cannot overflow float64
precision for any amount that can exist on the Nano ledger.

## Reference Implementation

No reference implementation is nominated yet.

## References

- [RFC 8259 §6 — The JavaScript Object Notation (JSON) Data Interchange Format, Numbers](https://www.rfc-editor.org/rfc/rfc8259#section-6)
- [RFC 7493 — The I-JSON Message Format](https://www.rfc-editor.org/rfc/rfc7493)
- [MDN — `Number.MAX_SAFE_INTEGER`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER)
- [docs.nano.org — Distribution and Units](https://docs.nano.org/protocol-design/distribution-and-units/)
- [`nano.conversion` — nano-python (originally `raiblocks-python`), Daniel Dourvaris](https://raiblocks-python.readthedocs.io/en/latest/_modules/nano/conversion.html) — third-party prior art for `rai = 10^24 raw`
- [ORIS-003 — NanoNyms Payment Event Schema](./ORIS-003.md)
- [ORIS-008 — Reliable Nano Payment Integration](./ORIS-008.md)
- [ORIS-009 — Nano Payment Targets for `payto:`](./ORIS-009.md)
