# ORIS-001 machine-readable fixtures

`suite.json` is the canonical fixture corpus for the strict verification profile
defined by [ORIS-001](../../rfcs/ORIS-001.md). The specification remains normative;
fixture changes must identify the corresponding rule.

Each case has a stable `id`, an `operation`, concrete `input`, an `expected`
result, a specification `rule`, and a requirement `scope`:

- `protocol`: required ORIS-001 behavior.
- `reference_policy`: local reference-implementation policy, such as 16 MiB.
- `compatibility`: optional accepted forms supported by both reference libraries.

Rejecting optional `xrb_` or uppercase-hex inputs does not violate ORIS-001.
The reference profile executes all three scopes because both libraries declare
those capabilities. Other implementations should report optional capabilities
and policy limits separately from protocol conformance.

Operations are `derive`, `inspect`, `sign`, and `verify`. Keys and signatures are
hexadecimal strings; messages are strings, explicit UTF-8 hex, UTF-16 code units,
or a bounded repeated-text descriptor. Exactly one message source is supplied.
Expected results contain `status` plus the byte-level results for successful
derivation, inspection, or signing. Verification results are `valid`, `invalid`,
or `input_error`. Exceptions, panics, missing results, and unknown cases do not
count as a rejection result.

The `parse_frame` operation accepts `payload_hex`, the hexadecimal encoding of
a complete NOMS frame. Its rejection cases expect `input_error`. These cases
apply only to implementations that accept framed input. Implementations without
a frame parser may report this operation as unsupported.

The fixture generator is `scripts/noms/generate_vectors.py`, invoked through
the Standards Makefile target `noms-vectors`. It uses Python integers and
`hashlib`, independently of the TypeScript and Rust crypto dependencies. It is
a deliberately slow test-data model and must never be used with real secrets.
Its outputs are checked against both libraries and the pinned Nano C oracle;
Nano's more permissive acceptance rules are documented separately.
