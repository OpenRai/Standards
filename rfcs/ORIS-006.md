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
- the CAIP-25 namespace key used in session proposals and approvals

## Motivation

Wallets and applications increasingly use CAIP identifiers to negotiate multi-chain sessions without hard-coding chain-specific transport behavior.

Nano needs one small, stable reference for those identifiers. This avoids each application choosing its own namespace, chain reference, or account string format.

Nano does not currently have a maintained end-user testnet that wallet applications should treat as a parallel public environment. Because Nano is feeless, a public testnet is also less important for ordinary payment and signing integration testing than it is for fee-bearing chains. This document therefore defines only Nano mainnet.

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
> Wallets and libraries MAY store and process the native `nano_` or `xrb_` prefixed address internally. Percent-encoding to `nano%5F...` MUST be applied when constructing a CAIP-10 account ID for use in CAIP-25 sessions or any other protocol expecting strict CAIP-10 compliance.
>
> On receipt of a CAIP-10 Nano account ID, implementations SHOULD percent-decode the address component and validate it as a valid Nano address, including prefix, length, and checksum. Systems that key accounts, permissions, sessions, or balances by CAIP-10 account ID SHOULD canonicalize accepted legacy `xrb_` forms to the equivalent `nano_` address before comparison or storage.

### CAIP-25 Namespace

For CAIP-25 session proposals and approvals, the namespace key for Nano is:

```text
nano
```

A session proposal that requests Nano support SHOULD place Nano chains, methods, and events under the `nano` namespace.

Example proposal shape:

```json
{
  "nano": {
    "chains": ["nano:mainnet"],
    "methods": ["nano_signMessage"],
    "events": ["accountsChanged"]
  }
}
```

A session approval MUST return Nano accounts in CAIP-10 form.

Example approval shape:

```json
{
  "nano": {
    "accounts": [
      "nano:mainnet:nano%5F3noms9a1zytox399kygpge6cc7hu1z79ms1cgzojodz8741qi7w5u3nzb8mn"
    ],
    "methods": ["nano_signMessage"],
    "events": ["accountsChanged"]
  }
}
```

This document does not standardize Nano JSON-RPC method names or event names. Future ORIS documents MAY define those names. Until then, applications and wallets MUST negotiate method and event support explicitly inside the `nano` namespace.

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

None. This document defines textual identifiers only.

## Reference Implementation

Open Wallet Standard uses `nano:mainnet` for Nano chain identification:

https://github.com/OpenRai/ows-core/blob/84fd50ad1760653cdc66dfa4c5ced229555adbb8/ows/crates/ows-core/src/chain.rs

Reference implementations are informative only and do not override the normative requirements in this document.

## Summary

Nano CAIP integrations use:

- namespace: `nano`
- CAIP-2 chain ID: `nano:mainnet`
- CAIP-10 account ID: `nano:mainnet:<percent-encoded-nano-address>`
- CAIP-25 namespace key: `nano`

No public end-user Nano testnet identifier is defined by this standard.
