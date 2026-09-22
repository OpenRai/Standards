```
OpenRai Initiative Standard: 012
```

# The `rai` Sub-Unit and Safe Amount Serialization for Nano Applications

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines `rai`, a Nano (XNO) display and interchange unit equal
to `10^-6 XNO` (`10^24 raw`), and specifies normative rules for serializing
Nano amounts — in `raw`, `XNO`, and `rai` — in JSON and other IEEE 754
binary64-backed interchange formats without silent precision loss.

It addresses a gap outside the native block/RPC layer, where `raw` is already
an unambiguous, protocol-level BigInt-equivalent integer. Once an amount
leaves that layer — into an API response, a webhook payload, an analytics
event, a browser-side application, or a spreadsheet — it is routinely
represented as a JSON or floating-point number, at which point Nano's
30-decimal magnitude silently breaks.

## Motivation

`1 XNO = 10^30 raw`. IEEE 754 binary64 — the numeric type behind JSON
numbers, JavaScript `Number`, and many languages' default float type —
represents integers exactly only up to `2^53 - 1 = 9,007,199,254,740,991`
([`Number.MAX_SAFE_INTEGER`](#references)). A `raw` amount exceeds this range
for essentially every transaction of practical size; only amounts below
roughly `9 × 10^-9 rai` (`9 × 10^-15 XNO`) would fit. In practice, that means:
**any `raw` value serialized as a bare JSON number should be assumed lossy.**

This is not hypothetical. A backend that computes a `raw` balance, assigns it
to a JSON field as a number rather than a string, and returns it through a
language runtime that parses JSON numbers into `double` (JavaScript, most
JSON libraries in most languages by default, spreadsheet imports, many
webhook consumers) will silently round the value. Because Nano transactions
are irreversible and fee-less, a rounded amount is not a cosmetic bug — it is
a wrong balance, a wrong invoice, or a wrong payout, discovered only when
someone reconciles against the ledger.

A second, related problem is the lack of a standardized small display unit.
Nano/`docs.nano.org`-adjacent tooling documents an SI-prefixed unit ladder on
top of a base "nano" unit (`10^24 raw`): `Gnano` (`10^33`), `Mnano` (`10^30`,
the `XNO` ticker value), `knano` (`10^27`), `nano` (`10^24`), `mnano`
(`10^21`), `unano`/`µnano` (`10^18`). Two practical problems follow:

- **It only usefully goes up.** The ticker value (`XNO`) sits at `Mnano`
  (mega-prefix), so casual references to "a million nano" are actually
  referring to a *single* `XNO` — the SI ladder was built around a base unit
  six orders of magnitude below the coin people actually hold and spend, so
  every everyday quantity ends up needing a `k`- or `M`- prefix instead of a
  fraction. Several self-custodial wallet UIs independently converged on
  showing balances to six decimal places of `XNO` (i.e., `10^-6 XNO`
  granularity) — a unit one order of magnitude *smaller* than the bare
  `nano` unit above, and one the existing ladder has no clean single-word
  name for.
- **It is not case-safe.** `Mnano` (`10^30 raw`, one whole coin) and `mnano`
  (`10^21 raw`, nine orders of magnitude smaller) differ only in the
  capitalization of one letter. Any context that folds case — command-line
  flags, environment variables, URLs, file systems, many database
  collations, casual chat and documentation — collapses these into the same
  token while their values differ by a factor of `10^9`. A ladder whose
  correctness depends on case survival across every transport it crosses is
  a standing interoperability hazard independent of the float64 problem
  above.

This document does not attempt to reform the full SI-style ladder. It
standardizes one specific, already-converged-upon value under a distinct
name that cannot be case-folded into a different magnitude, and pairs that
definition with explicit serialization rules so the underlying precision
problem is addressed at the same time.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
indicate normative requirements.

Unless otherwise stated:

- `1 XNO = 10^30 raw` (as established in [ORIS-009](./ORIS-009.md)).
- A **producer** generates or serializes an amount.
- A **consumer** parses or displays an amount.
- **Safe integer range** means the closed interval
  `[-(2^53 - 1), 2^53 - 1]`, per [RFC 8259 §6](#references).
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

### Relationship to Existing Nano Unit Names

`rai` was arrived at independently in the course of drafting this document,
without prior knowledge of any earlier use of the name at this value. Only
during subsequent research was it discovered that `nano.conversion`, a
module in **nano-python** (originally published as `raiblocks-python`) by
GitHub user `dourvaris`, already defines `1 rai = 10^24 raw` — the same
value specified here — in a docstring dating to the pre-2018, `XRB`-ticker
era of the network. That library is a third-party community client, not an
official Nano Foundation specification, but two independent arrivals at the
same name and the same magnitude, a decade apart, is stronger evidence that
the value is a natural fit than either arrival would be on its own.

That same library's code goes one step further than its docstring: its
unit-population loop applies SI prefixes (`G`, `M`, `k`, none, `m`, `u`) to
`rai` as a base name in parallel with `xrb`, which independently produces
`Mrai` as a working synonym for one whole coin (`10^30 raw`) — the same
SI-consistent answer to "what is 1 XNO once `rai` is the base unit" implied
by this document's own [Unit Definition](#unit-definition) table
(`1 XNO = 10^6 rai`). This document does not adopt `Mrai`, or any further
SI-prefixed ladder on top of `rai`, as normative: doing so would reintroduce
exactly the case-collision hazard described in [Motivation](#motivation)
(`Mrai` vs. `mrai` differing by `10^9`, the same way `Mnano` vs. `mnano`
already does). `rai` is specified here as a single, unprefixed unit for
that reason, so it cannot be case-folded into a different magnitude; the
`Mrai` observation above is noted as further prior art, not as a name this
document endorses for use.

This document also does not reuse the bare, no-prefix `nano` unit from the
SI-style ladder described in [Motivation](#motivation) (also `10^24 raw`),
because it collides with the project's own name and with the currently
unregistered `nano` denomination string in ways that are confusing in
prose, logs, and UI labels — "500 nano" reads as "500 Nano" to nearly every
reader.

### The Float64 / JSON Safe-Integer Problem

`2^53 - 1 = 9,007,199,254,740,991`. Expressed in each unit:

| Unit  | Approximate value below which a bare JSON/float64 number is exact |
|-------|---------------------------------------------------------------------|
| `raw` | `~9 × 10^-9 rai` (`~9 × 10^-15 XNO`) — effectively unreachable for any real amount |
| `rai` | `~9.0 × 10^15 rai` (`~9.0 × 10^9 XNO`) |
| `XNO` | depends on required fractional precision; see below |

Nano's current fixed total supply is approximately `133,248,297 XNO`, i.e.
`133,248,297,000,000 rai` (`~1.332 × 10^14`). Compared against the safe
integer ceiling of `~9.007 × 10^15`, expressing the *entire* circulating
supply as a single integer number of `rai` uses roughly `1/68` of the
available safe-integer headroom. This is the practical basis for the
`rai`-specific allowance in [Serialization Requirements](#serialization-requirements)
below: unlike `raw`, an integer `rai` amount cannot silently exceed the
float64-safe range for any amount that can actually exist on the Nano
ledger today.

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
   This matches the existing `amount_raw` convention in
   [ORIS-003](./ORIS-003.md) and the `nano-raw` parameter in
   [ORIS-009](./ORIS-009.md); this document generalizes that already-proven
   practice as a cross-cutting rule rather than a per-document convention.
2. A producer MUST NOT emit an `XNO` amount carrying more fractional
   precision than the consumer's numeric type can guarantee, as a bare
   number. Where full `raw`-level precision must be preserved, an `XNO`
   amount SHOULD be encoded as a decimal string using the same digit rules
   as above (permitting one decimal point and up to 30 fractional digits).
3. A `rai` amount MAY be encoded as a JSON integer number. Because every
   amount that can exist on the Nano ledger remains within the float64 safe
   integer range when expressed in `rai` (see
   [above](#the-float64--json-safe-integer-problem)), this is exact, not an
   approximation. Producers SHOULD still prefer decimal-string encoding for
   `rai` where a schema mixes `rai` fields with `raw` or high-precision
   `XNO` fields, for consistency and to simplify shared parsing code; a
   consumer MUST accept a `rai` amount encoded as either a JSON integer or
   a decimal string.
4. A consumer MUST reject a `raw` or high-precision `XNO` amount received as
   a bare JSON number rather than silently rounding it, when the value or
   its provenance cannot be independently verified against the ledger.
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
amount_rai   — integer or decimal string, rai
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
- This document does not deprecate `Gnano`, `Mnano`, `knano`, `mnano`, or
  `unano`; it defines one additional, case-collision-resistant unit at a
  value several existing tools and UIs already use informally.

## Open Questions

- Whether `rai` should be formally proposed for inclusion in
  `docs.nano.org`'s own unit documentation, or remain an ORIS-scoped
  convention referenced by name.
- Whether a `Xrai`-style large-value prefix is worth standardizing, or
  whether amounts above `~9 × 10^9 rai` are rare enough in practice
  (exceeding total supply) not to need one.
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

### Vector 4 — Total Supply Expressed in `rai`

```text
133248297 XNO = 133248297000000 rai
```

`133248297000000 < 2^53 - 1 (9007199254740991)` — safe as a bare JSON
integer with headroom to spare, illustrating that `rai` cannot overflow
float64 precision for any amount that can exist on the Nano ledger.

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
- [docs.nano.org — Integration Guides / The Basics](https://docs.nano.org/integration-guides/the-basics/)
- [`nano.conversion` — nano-python (originally `raiblocks-python`), Daniel Dourvaris](https://raiblocks-python.readthedocs.io/en/latest/_modules/nano/conversion.html) — third-party pre-2018 client library; source of the `rai`/`Mrai` prior-art observation in [Relationship to Existing Nano Unit Names](#relationship-to-existing-nano-unit-names)
- [ORIS-003 — NanoNyms Payment Event Schema](./ORIS-003.md)
- [ORIS-008 — Reliable Nano Payment Integration](./ORIS-008.md)
- [ORIS-009 — Nano Payment Targets for `payto:`](./ORIS-009.md)
