```
OpenRai Initiative Standard: 012
```

# The `rai` Sub-Unit and Safe Amount Serialization for Nano Applications

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines `rai`, a Nano (XNO) display and interchange unit equal
to `10^-6 XNO` (`10^24 raw`), and specifies normative rules for serializing
Nano amounts — in `raw`, `XNO`, and `rai` — for JSON and other interchange
formats with IEEE 754 binary64 receivers, without silent precision loss.

It addresses a gap outside the native block/RPC layer, where `raw` is already
an unambiguous, protocol-level BigInt-equivalent integer. Once an amount
leaves that layer — into an API response, a webhook payload, an analytics
event, a browser-side application, or a spreadsheet — it is routinely
represented as a JSON or floating-point number, at which point Nano's
30-decimal magnitude silently breaks.

## Motivation

`1 XNO = 10^30 raw`. JSON permits decimal numbers of arbitrary length, but
common JSON receivers use IEEE 754 binary64. This is also the numeric type of
JavaScript `Number` and many languages' default float type. Binary64
represents integers exactly only up to `2^53 - 1 = 9,007,199,254,740,991`
([`Number.MAX_SAFE_INTEGER`](#references)). A `raw` amount exceeds this range
for essentially every transaction of practical size; only amounts below
roughly `9 × 10^-9 rai` (`9 × 10^-15 XNO`) would fit. In practice, that means:
**a bare JSON number is not a safe general-interchange representation for a
`raw` amount.**

This is not hypothetical. A backend that computes a `raw` balance, assigns it
to a JSON field as a number rather than a string, and returns it through a
language runtime that parses JSON numbers into `double` (JavaScript, most
JSON libraries in most languages by default, spreadsheet imports, many
webhook consumers) will silently round the value. Because Nano transactions
are irreversible and fee-less, a rounded amount is not a cosmetic bug — it is
a wrong balance, a wrong invoice, or a wrong payout, discovered only when
someone reconciles against the ledger.

A second, related problem is the lack of a standardized name for the common
six-decimal XNO display precision. This document calls that quantity `rai`.
The name has earlier third-party precedent at the same value, but it is an
ORIS-defined unit here. It does not change Nano's documented `nano`/XNO and
`raw` units or standardize an SI-prefixed denomination ladder.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
indicate normative requirements.

Unless otherwise stated:

- `1 XNO = 10^30 raw` (as established in [ORIS-009](./ORIS-009.md)).
- A **producer** generates or serializes an amount.
- A **consumer** parses or displays an amount.
- **Safe integer range** means the closed interval
  `[-(2^53 - 1), 2^53 - 1]`, per [RFC 8259 §6](#references).
- A **whole `rai` amount** is a non-negative integer number of `rai`.
- Amounts in this document are assumed non-negative; Nano balances and
  transaction amounts cannot be negative.

## Specification

### Scope

This document covers:

- the definition of the `rai` unit,
- its relationship to `raw`, `XNO`, and the existing informal unit ladder,
- normative serialization rules for `raw`, `XNO`, and `rai` amounts in JSON
  and comparable interchange formats, and
- field-naming and conversion-arithmetic requirements for producers and
  consumers of such amounts.

This document does not cover:

- the Nano block or RPC wire format, where `raw` is already an unambiguous
  string/integer at the protocol level and is out of scope for this
  document,
- wallet UI default-denomination policy (this document standardizes a name
  and value; it does not mandate what a wallet displays by default), or
- the `payto:` or `nano:` URI amount parameters, which [ORIS-009](./ORIS-009.md)
  already specifies.

### Unit Definition

| Unit  | Value in `raw`      | Value in `XNO` | Value in `rai` |
|-------|----------------------|----------------|-----------------|
| `raw` | `1`                  | `10^-30`       | `10^-24`        |
| `rai` | `10^24`              | `10^-6`        | `1`             |
| `XNO` | `10^30`              | `1`            | `10^6`          |

`1 rai = 0.000001 XNO = 1,000,000,000,000,000,000,000,000 raw`.

`rai` is an integer-valued unit at the granularity already shown by wallet
UIs that truncate or round `XNO` display to six decimal places. Any amount
representable as a decimal `XNO` value with no more than six fractional
digits is representable as a whole number of `rai`.

### The Float64 / JSON Safe-Integer Problem

`2^53 - 1 = 9,007,199,254,740,991`. Expressed in each unit:

| Unit  | Approximate value below which a bare JSON/float64 number is exact |
|-------|---------------------------------------------------------------------|
| `raw` | `~9 × 10^-9 rai` (`~9 × 10^-15 XNO`) — effectively unreachable for any real amount |
| `rai` | `~9.0 × 10^15 rai` (`~9.0 × 10^9 XNO`) |
| `XNO` | depends on required fractional precision; see below |

The largest whole `rai` amount representable by a Nano `uint128` raw value is
`floor((2^128 - 1) / 10^24) = 340,282,366,920,938 rai`. This is less than
`2^53 - 1`. Therefore, a valid whole `rai` amount is always exactly
representable as a binary64 integer. This establishes the `rai` allowance in
[Serialization Requirements](#serialization-requirements) without depending
on the current circulating supply.

`XNO` itself is not automatically safe just because its integer part is
small: a fractional `XNO` value carrying `raw`-level precision needs up to
30 significant decimal digits, and per
[RFC 8259 §6](#references) and [RFC 7493](#references), a JSON number
carrying more precision than binary64 provides (roughly 15–17 significant
decimal digits) is not guaranteed to round-trip. A displayed value like
`"1.234567"` (six decimal places, i.e. exactly representable as an integer
number of `rai`) is unproblematic; a value carrying its full native
precision, such as `"1.234567891234567891234567891234"`, is not safe as a
bare JSON number regardless of how small its integer part is.

### Serialization Requirements

1. A producer MUST NOT emit a `raw` amount as a bare JSON (or other
   float64-typed) number. A `raw` amount MUST be encoded as a decimal
   string: base-10 digits only, no leading zeros except a standalone `"0"`,
   no sign, no decimal point, no exponent, no digit-grouping separators.
   The value MUST NOT exceed `2^128 - 1`.
   This matches the existing `amount_raw` convention in
   [ORIS-003](./ORIS-003.md) and the `nano-raw` parameter in
   [ORIS-009](./ORIS-009.md); this document generalizes that already-proven
   practice as a cross-cutting rule rather than a per-document convention.
2. A producer MUST encode an `XNO` amount with a fractional part as a decimal
   string. The string MUST use base-10 digits and no sign, exponent, or digit
   grouping separator. Its integer component MUST be `0` or a nonzero digit
   followed by digits. When it contains a decimal point, the point MUST be
   followed by one through 30 digits. The parsed value MUST correspond exactly
   to a non-negative `raw` amount no greater than `2^128 - 1`.
   A producer MAY encode a whole `XNO` amount as a JSON integer.
3. An `amount_rai` field represents a whole `rai` amount. A producer MUST
   NOT round or truncate a `raw` amount to produce `amount_rai`. When the
   raw amount is not divisible by `10^24`, a producer MUST use `amount_raw`
   or a decimal-string `amount_xno` instead. A decimal-string `amount_rai`
   MUST use the same integer syntax as `amount_raw`. Its value MUST NOT
   exceed `340282366920938`. A whole `rai` amount MAY be encoded as a JSON
   integer or a decimal string. Because every
   amount that can exist on the Nano ledger remains within the float64 safe
   integer range when expressed in `rai` (see
   [above](#the-float64--json-safe-integer-problem)), this is exact, not an
   approximation. Producers SHOULD still prefer decimal-string encoding for
   `rai` where a schema mixes `rai` fields with `raw` or fractional `XNO`
   fields, for consistency and to simplify shared parsing code; a
   consumer MUST accept a `rai` amount encoded as either a JSON integer or
   a decimal string.
4. A consumer MUST reject a `raw` amount received as a bare JSON number. A
   consumer MUST reject an `XNO` amount with a fractional part received as a
   bare JSON number. A consumer MUST reject a fractional `rai` amount. A
   consumer MUST reject any amount that fails the applicable syntax, range,
   or exact-conversion rule.
5. These rules apply to any interchange format backed by IEEE 754 binary64
   or narrower (JSON, YAML with a JSON-compatible number model, MessagePack
   using its float64 number type, many RPC/serialization frameworks'
   default number types, spreadsheet cell values). They do not apply to
   formats with native arbitrary-precision decimal or integer types.

### Field Naming Convention

A field carrying a Nano amount SHOULD name its unit explicitly rather than
using a bare `amount` whose unit is only established by external context,
consistent with the `amount`/`nano-raw` disambiguation already adopted in
[ORIS-009](./ORIS-009.md):

```text
amount_raw   — decimal string, raw
amount_rai   — whole rai: JSON integer or decimal string
amount_xno   — decimal string (or integer where the value is known to be
               a whole number of XNO), XNO
```

A single payload SHOULD carry an amount in exactly one of these units. A
payload that carries the same amount in more than one unit for convenience
MUST ensure the values are exactly consistent, computed as described in
[Conversion Arithmetic](#conversion-arithmetic).

### Conversion Arithmetic

Conversion between `raw`, `rai`, and `XNO` MUST use exact integer or
arbitrary-precision decimal arithmetic (e.g., a `BigInt`/`bigint` type, an
arbitrary-precision decimal library, or equivalent integer division/
multiplication by the exact powers of ten in the
[Unit Definition](#unit-definition) table). Conversion MUST NOT be performed
using native binary floating-point division or multiplication, since doing
so reintroduces the precision loss this document exists to prevent, even
when the input and output are both subsequently encoded as strings.

Conversion from `raw` to a whole `rai` amount MUST reject a value that is not
divisible by `10^24`. It MUST NOT round or truncate the value.

### Display Guidance (Informative)

Wallet and application UIs that already round or truncate `XNO` display to
six decimal places are, in effect, already displaying `rai`-granularity
values without naming the unit. Such interfaces SHOULD consider adopting
`rai` as the labeled unit for that display mode — either as the primary
display denomination or as an explicit, switchable alternative to `XNO` —
rather than leaving the truncation unnamed and denomination-implicit.

## Relationship to Other ORIS Documents

- [ORIS-003](./ORIS-003.md) (NanoNyms Payment Event Schema) already encodes
  `amount_raw` as a decimal string; a future revision MAY add an optional
  `amount_rai` field following the rules in this document.
- [ORIS-008](./ORIS-008.md) (Reliable Nano Payment Integration) covers
  confirmation tracking and reconciliation; implementations following
  ORIS-008 SHOULD apply this document's serialization rules to any amount
  fields in their reconciliation records.
- [ORIS-009](./ORIS-009.md) (Nano Payment Targets for `payto:`) already
  distinguishes `amount=NANO:...` from `nano-raw=...`; the precision
  requirements in this document apply equally to both parameters and MAY be
  cited by reference rather than restated in future revisions of ORIS-009.

## Non-Goals

- This document does not change the native Nano block format, RPC
  responses, or any wire-level representation, all of which already
  represent `raw` as an unambiguous integer or decimal string outside of
  JSON's number type constraints.
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

Input (`XNO`, six decimal places — safely representable as an integer `rai`
value or a decimal string):

```json
{ "amount_xno": "1.500000" }
```

Equivalent, safe as a bare JSON integer:

```json
{ "amount_rai": 1500000 }
```

Equivalent, required as a decimal string (unsafe as a bare JSON number):

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

No reference implementation is nominated yet. Implementers adding `rai`
support to an existing conversion utility (for example, one already
handling `raw`/`knano`/`Mnano`) SHOULD add it as an additional named unit at
`10^24 raw` alongside the existing ladder, using the exact-arithmetic
requirement in [Conversion Arithmetic](#conversion-arithmetic).

## References

- [RFC 8259 §6 — The JavaScript Object Notation (JSON) Data Interchange Format, Numbers](https://www.rfc-editor.org/rfc/rfc8259#section-6)
- [RFC 7493 — The I-JSON Message Format](https://www.rfc-editor.org/rfc/rfc7493)
- [MDN — `Number.MAX_SAFE_INTEGER`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER)
- [docs.nano.org — Distribution and Units](https://docs.nano.org/protocol-design/distribution-and-units/)
- [`nano.conversion` — nano-python (originally `raiblocks-python`), Daniel Dourvaris](https://raiblocks-python.readthedocs.io/en/latest/_modules/nano/conversion.html) — third-party prior art for `rai = 10^24 raw`
- [ORIS-003 — NanoNyms Payment Event Schema](./ORIS-003.md)
- [ORIS-008 — Reliable Nano Payment Integration](./ORIS-008.md)
- [ORIS-009 — Nano Payment Targets for `payto:`](./ORIS-009.md)
