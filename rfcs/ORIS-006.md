```
OpenRai Initiative Standard: 006
```

# Nano CAIP Identifiers

> Status: Implementation Draft
> Category: Application Interface

## Abstract

This document defines Nano identifiers for Chain Agnostic Improvement Proposals
(CAIP). It specifies the CAIP-2 chain ID for Nano mainnet and the canonical
CAIP-10 form for Nano accounts.

## Motivation

Multi-chain protocols need a common string for each chain and account. Without
one Nano profile, applications can choose incompatible namespaces, chain
references, or account encodings.

This document defines only Nano mainnet. Test, beta, development, and local
networks remain out of scope until an interoperability use case requires shared
identifiers for them.

## Rationale

### Choice of Account ID Format

CAIP-10 does not allow `_` in its `account_address` production. This document
therefore percent-encodes the underscore as `%5F` and preserves the rest of the
native Nano address.

Two alternatives were rejected:

1. A 64-character public key fits the grammar, but removes the Nano address
   checksum and the form users recognize.
2. Removing the prefix or underscore creates a non-standard Nano address that
   existing address parsers cannot validate directly.

The selected `nano%5F...` form keeps the prefix, address body, and checksum. It
also converts back to the native address without a separate mapping.

> **Possible CAIP evolution:**
>
> A future CAIP-10 revision could permit `_` in `account_address`. Nano could
> then use its native address without percent-encoding.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated, all strings are case-sensitive.

## Specification

### CAIP-2 Chain ID

The CAIP-2 namespace for Nano is:

```text
nano
```

The CAIP-2 chain ID for Nano mainnet is:

```text
nano:mainnet
```

Applications and wallets that need to identify Nano mainnet in a CAIP-2 field MUST use `nano:mainnet`.

This document does not define any Nano testnet, beta network, devnet, or local network CAIP-2 chain ID.

### CAIP-10 Account ID

A Nano CAIP-10 account ID is:

```text
nano:mainnet:<account>
```

Where `<account>` is a CAIP-10-compatible encoding of a Nano account address.

Example:

```text
nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

Requirements:

- The chain ID MUST be `nano:mainnet`.
- The account component MUST satisfy the CAIP-10 `account_address` grammar.
- The prefix underscore MUST be encoded as uppercase `%5F`.
- Emitters SHOULD use the `nano%5F` prefix.
- Parsers MAY accept `xrb%5F` for compatibility.
- A parser that accepts `xrb%5F` MUST canonicalize it to `nano%5F` after
  validating the address.
- Parsers MAY accept native `nano_` or `xrb_` input, but emitters MUST NOT
  produce those forms in a CAIP-10 account ID.
- The account component MUST NOT contain a raw key, seed, wallet ID,
  representative, or account index.

After percent-decoding the account component, the decoded value is the ordinary Nano address:

```text
nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

> **Implementation guidance:**
>
> Wallets and libraries MAY use native `nano_` or `xrb_` addresses internally.
> They MUST apply the canonical form when producing a CAIP-10 account ID.
>
> A parser SHOULD percent-decode the account component and validate the Nano
> prefix, length, alphabet, and checksum. Systems MUST canonicalize accepted
> input before using it as a storage or permission key.

### Canonicalization

The canonical CAIP-10 form for a Nano account is:

```text
nano:mainnet:nano%5F<account-body>
```

Where `<account-body>` is the 60-character Nano address body after the `nano_` prefix.

Implementations MUST canonicalize every accepted form before comparison or
storage.

This includes:

- Replace an accepted `xrb_` or `xrb%5F` prefix with `nano%5F`.
- Encode the prefix underscore as `%5F`.
- Reject a decoded address with an invalid prefix, length, alphabet, or
  checksum.

### Session Protocols

This document does not define a CAIP-25, WalletConnect, or other session
profile. A later ORIS may define scopes, methods, events, and request or response
objects for a specific protocol.

Protocols that carry Nano accounts in strict CAIP-10 fields MUST use the canonical CAIP-10 form defined above.

### Reserved Identifiers

The following identifiers are not defined by this document and SHOULD NOT be used for public wallet interoperability:

```text
nano:testnet
nano:beta
nano:devnet
nano:local
xno:mainnet
nanocurrency:mainnet
```

Applications SHOULD standardize any additional public chain references before
using them in production protocols.

## Published Test Vectors

These vectors use the same account body:

```text
3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

The corresponding public key is:

```text
d2b3c9d00ffb55e84e7979d67308a515fb07ca79e40a77eb1aafe62881781783
```

### Vector 1 - Native Nano Address

Input:

```text
nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

Canonical CAIP-10 output:

```text
nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 2 - Legacy Native Address

Input:

```text
xrb_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

Canonical CAIP-10 output:

```text
nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

### Vector 3 - Legacy CAIP-10 Input

Input:

```text
nano:mainnet:xrb%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

Canonical CAIP-10 output:

```text
nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

## Reference Implementation

[Open Wallet Standard](https://github.com/OpenRai/ows-core/blob/84fd50ad1760653cdc66dfa4c5ced229555adbb8/ows/crates/ows-core/src/chain.rs)
uses `nano:mainnet`.

Reference implementations are informative. This document defines the
interoperability requirements.
