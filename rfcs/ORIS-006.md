```
OpenRai Initiative Standard: 006
```

# Nano CAIP Identifiers

> Status: Draft\
> Category: Application Interface

## Abstract

This document defines the CAIP identifiers applications SHOULD use when referring to Nano in CAIP-based wallet and application protocols.

It defines:

- the CAIP-2 namespace and chain ID for Nano mainnet
- the CAIP-10 account ID form for Nano accounts

## Motivation

Wallets and applications increasingly use CAIP identifiers to negotiate multi-chain sessions without hard-coding chain-specific transport behavior.

Nano needs one small, stable reference for those identifiers. This avoids each application choosing its own namespace, chain reference, or account string format.

Nano test and beta networks serve development, staging, and release-testing purposes, but they are out of scope for public wallet interoperability in this document. Because Nano is feeless, public wallet interoperability does not require a fee-bearing-chain-style public testnet identifier for ordinary payment and signing integration testing. This document therefore defines only Nano mainnet.

## Rationale

> [!NOTE]
> Future CAIP Evolution
>
> This document uses percent-encoding of the `_` character to comply with the current CAIP-10 account address grammar. The Chain Agnostic community should consider a future CAIP-10 revision that natively includes `_`, and potentially other common safe characters, in the `account_address` production.
>
> Such an update would improve human readability and reduce encoding overhead for multiple namespaces, including Nano.

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

- the chain ID prefix MUST be `nano:mainnet`
- the account component MUST conform to the CAIP-10 account-address grammar
- the underscore in a Nano address prefix MUST be percent-encoded as `%5F`
- emitters SHOULD use a `nano%5F` address prefix
- wallets MAY accept equivalent legacy `xrb%5F` account addresses for compatibility
- implementations that accept `xrb%5F` input MUST treat it as equivalent to the corresponding `nano%5F` account ID after validating that both forms decode to the same public key
- implementations MAY accept unencoded `nano_` or `xrb_` account addresses as non-strict legacy input, but MUST NOT emit them as CAIP-10 account IDs
- implementations MUST NOT place a raw public key, private key, seed, wallet ID, representative, or account index in the account component

After percent-decoding the account component, the decoded value is the ordinary Nano address:

```text
nano_3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn
```

> [!TIP]
> **Implementation Guidance**
>
> Wallets and libraries MAY store and process the native `nano_` or `xrb_` prefixed address internally. Percent-encoding to `nano%5F...` MUST be applied when constructing a CAIP-10 account ID for use in any protocol expecting strict CAIP-10 compliance, including future session protocols.
>
> On receipt of a CAIP-10 Nano account ID, implementations SHOULD percent-decode the address component and validate it as a valid Nano address, including prefix, length, and checksum. Systems that key accounts, permissions, sessions, or balances by CAIP-10 account ID MUST apply the canonicalization rules below before comparison or storage.

### Canonicalization

The canonical CAIP-10 form for a Nano account is:

```text
nano:mainnet:nano%5F<account-body>
```

Where `<account-body>` is the 60-character Nano address body after the `nano_` prefix.

For internal storage, indexing, permission checks, session matching, and account comparison, implementations MUST map all accepted equivalent forms to the canonical CAIP-10 form before comparison or persistence.

This includes:

- replacing an accepted `xrb_` or `xrb%5F` prefix with `nano_` or `nano%5F`
- percent-encoding the underscore when emitting a CAIP-10 account ID
- rejecting any form that fails Nano address validation after decoding

### Session Protocols

This document does not define a CAIP-25, WalletConnect, or other session-protocol profile for Nano. Future ORIS documents MAY define Nano session scope keys, request and response shapes, method names, notification or event names, and account encoding rules for specific session protocols.

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

If future applications require additional Nano chain references, they SHOULD be standardized in a new ORIS document before being used in production protocols.

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

Open Wallet Standard uses `nano:mainnet` for Nano chain identification:

https://github.com/OpenRai/ows-core/blob/84fd50ad1760653cdc66dfa4c5ced229555adbb8/ows/crates/ows-core/src/chain.rs

Reference implementations are informative only and do not override the normative requirements in this document.

## Summary

Nano CAIP integrations use:

- CAIP-2 namespace: `nano`
- CAIP-2 chain ID: `nano:mainnet`
- CAIP-10 account ID: `nano:mainnet:<percent-encoded-nano-address>`

No Nano testnet or beta-network identifier is defined by this standard.
