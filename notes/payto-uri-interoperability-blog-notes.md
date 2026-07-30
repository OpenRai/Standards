# Draft Notes: Nano URI Scheme Interoperability and the `payto:` Bridge

> Potential future blog/article material, not an OpenRai Initiative Standard draft.

## Abstract

This document analyzes the landscape of URI schemes used for payment invocation, signing-intent, and authentication across blockchain ecosystems, with particular focus on RFC 8905 (`payto://`), Bitcoin BIPs (21, 70, 72, 75), LNURL (LUD-04, LUD-06, LUD-17, LUD-18), Ethereum ERC-681, and existing Nano-specific schemes (`nano:`, `nanopay:`, `nanoauth:`, `nanosub:`, `nanorep:`, `nanoblock:`, `nanoseed:`, `nanokey:`).

It defines:

- a mapping between the existing `nano:` URI scheme and the RFC 8905 `payto://` URI scheme
- a `payto://nano/` payment target type registration proposal
- a signing-intent URI framework (`nanoauth://`) informed by LNURL-auth and the Nautilus `nanoauth:` scheme
- bidirectional conversion rules, custom parameter extensions, and coexistence guidance

The goal is to position Nano for cross-system payment interoperability while preserving the existing ecosystem conventions that wallets, block explorers, and integrations already rely on.

## Motivation

### The URI Scheme Fragmentation Problem

Every major blockchain ecosystem has defined its own URI scheme:

| Ecosystem | Scheme | Year | Status |
|---|---|---|---|
| Bitcoin | `bitcoin:` (BIP-21) | 2012 | Final, widely deployed |
| Bitcoin | `bitcoin:?r=` (BIP-72) | 2013 | Deployed, deprecated in Core |
| Ethereum | `ethereum:` / `ethereum:pay-` (ERC-681) | 2017 | Active |
| Lightning | `lnurlp://`, `keyauth://`, `lnurlw://`, `lnurlc://` (LUD-17) | 2021 | Active |
| Nano | `nano:` | ~2018 | Widely deployed |
| Nano (Nautilus) | `nanopay:`, `nanoauth:`, `nanosub:` | 2022 | Deployed (Nautilus) |
| Nano (NanChat) | `nanauth://sign` | ~2025 | Deployed (NanChat) |

RFC 8905 (`payto://`) was published in 2020 as an Informational RFC attempting to unify payment URIs across all systems. It already registered `bitcoin` as a payment target type. Despite this, adoption in the blockchain space has been effectively zero. This document investigates why, identifies the specific shortcomings, and proposes a practical bridge for Nano.

### Why RFC 8905 Has Not Been Adopted by Blockchain Ecosystems

**1. Timing and incumbency.** BIP-21 was finalized in 2012, eight years before RFC 8905. By 2020, every major chain had shipped its own scheme with deep ecosystem integration. The switching cost is high and the benefit is unclear to individual chains.

**2. Informational status.** RFC 8905 is not a Standards Track document. It was published as an independent submission at the RFC Editor's discretion, carrying no IETF consensus. This gives it significantly less normative weight than a Standards Track RFC.

**3. Registry governance.** The "Payto Payment Target Types" registry is maintained by GANA (GNUnet Assigned Numbers Authority), a body associated with the GNUnet privacy networking project. GANA is not recognized as an authority in the blockchain space, and the registry endpoint has exhibited availability issues.

**4. Blockchain transaction semantics do not map cleanly.** The `payto://` model assumes a single push payment: specify a target, amount, and the payment happens. Blockchains have fundamentally different semantics:
- **Nano**: Two-phase (send + receive), no fees, block-lattice architecture, representative delegation, raw-unit precision ($10^{30}$ raw per XNO), signing-intent, and subscription patterns.
- **Bitcoin**: UTXO model, fees, replace-by-fee, PSBT workflows, multiple output types (P2PKH, P2SH, P2WPKH, P2TR), Lightning Network off-chain channels.
- **Ethereum**: Contract calls, ERC-20 transfers, gas limits, data fields, ENS names, multi-chain (L2s).

The `payto://` scheme does not accommodate: fees, nonces, gas, multi-step transactions, smart contract interactions, token standards, staking, delegation, or signing-intent patterns.

**5. Amount format is ISO 4217-centric.** RFC 8905's `amount=currency:unit.fraction` format assumes ISO 4217 3-letter currency codes and limits fractions to 8 decimal digits. Nano's $10^{30}$ raw precision exceeds this by 22 orders of magnitude. The spec permits payment target types to define "semantics beyond ISO 4217 for currency codes that are not 3 characters," but this is a workaround, not first-class support.

**6. No ecosystem advocacy.** The Taler project (the authors' employer) focuses on privacy-preserving digital cash, not blockchain. There has been no push from the payto community to onboard blockchain projects, and no pull from blockchain projects to adopt payto.

### Where RFC 8905 Provides Genuine Value

Despite the above, RFC 8905 addresses a real problem: **cross-system payment routing**. Specific use cases where `payto://` adds value:

- Multi-chain payment processors accepting both bank transfers and cryptocurrency
- Point-of-sale systems with heterogeneous payment method support
- Invoicing software generating payment links for multiple payment rails
- Wallet-connect and deep-link aggregation layers
- Universal QR code standards for multi-ecosystem scanners

The `payto://` scheme's extensibility via the `authority` component and `authority-specific-opt` query parameters makes it technically possible to accommodate blockchain-specific extensions without breaking the generic parser.

### Existing Nano URI Landscape

Nano currently has the following URI schemes in use:

| Scheme | Purpose | Defined By | Status |
|---|---|---|---|
| `nano:` | Payment invocation | Nano docs | Widely deployed |
| `nanorep:` | Representative change | Nano docs | Widely deployed |
| `nanokey:` | Private key import | Nano docs | Widely deployed |
| `nanoseed:` | Seed import | Nano docs | Deployed |
| `nanoblock:` | JSON block processing | Nano docs | Niche |
| `nanopay:` | Signed payment request with handoff method | Nautilus (`perishllc/nano-uri`) | Deployed |
| `nanoauth:` | Signed authentication request | Nautilus (`perishllc/nano-uri`) | Deployed |
| `nanosub:` | Signed subscription request | Nautilus (`perishllc/nano-uri`) | Deployed |
| `nanauth://sign` | Signing-intent for login | NanChat (`yxse/nanchat`) | Deployed |
| `payto:` / `payto://` | Universal payment (RFC 8905) | nano.community, Nautilus | Early adoption |

The Nautilus `nano-uri` library (`perishllc/nano-uri`) and NanChat (`yxse/nanchat`) have independently implemented signing-intent and off-chain payment request patterns that parallel Bitcoin's BIP-70/72/75 and Lightning's LNURL-auth/LUD-06. These represent valuable prior art for standardization.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate normative requirements.

Unless otherwise stated, all strings are case-sensitive.

- `nano_`: A standard Nano account address.
- `raw`: The smallest indivisible Nano unit ($1\ \text{XNO} = 10^{30}\ \text{raw}$).
- `XNO`: The user-facing unit of account.
- `signing-intent`: A URI that requests a wallet to sign a message or construct a transaction, without directly executing it.
- `handoff`: The mechanism by which a signed result is delivered to a callback URL.
- `authority`: The RFC 3986 authority component; in `payto://nano/...`, the authority is `nano`.

## Specification

### `payto://nano/` Payment Target Type

#### Registration

The following payment target type is proposed for registration in the "Payto Payment Target Types" registry:

```text
Name:        nano
Description: Nano cryptocurrency (XNO). The path is a nano_ account
             address. The "amount" option uses raw integer amounts
             to preserve full protocol precision. An optional
             "currency" option MAY specify the unit (XNO or raw);
             if absent, raw is assumed.
Example:     payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000&message=Donate
Contact:     OpenRai Initiative
References:  RFC 8905, ORIS-009
```

#### URI Syntax

The `payto://nano/` URI extends the generic `payto://` ABNF (RFC 8905, Section 2):

```abnf
payto-nano-URI = "payto://nano/" nano-address [ "?" nano-opts ]
nano-address   = ("nano_" / "xrb_") 1*base32char
nano-opts      = nano-opt *( "&" nano-opt )
nano-opt       = generic-opt / nano-specific-opt
nano-specific-opt = nano-opt-name "=" nano-opt-value
nano-opt-name  = "raw-amount" / "currency" / "rep" / "expires"
                / "sign" / "callback" / authority-specific-opt
```

Where `base32char` is the Nano base32 alphabet `[13456789abcdefghijkmnopqrstuwxyz]` and `generic-opt` is defined in RFC 8905 Section 2 (`amount`, `receiver-name`, `sender-name`, `message`, `instruction`).

#### Field Mapping: `nano:` to `payto://nano/`

| `nano:` field | `payto://nano/` field | Conversion rule |
|---|---|---|
| `nano:nano_<addr>` | `payto://nano/nano_<addr>` | Path component = address |
| `amount=<raw>` | `amount=<raw>` | Direct; raw integer. Also set `currency=raw` |
| `label=<label>` | `receiver-name=<label>` | Direct mapping |
| `message=<message>` | `message=<message>` | Direct mapping |
| *(none)* | `sender-name=<name>` | Optional; payto generic field |
| *(none)* | `instruction=<text>` | Optional; maps to ORIS-007 Off-chain Payment Reference |
| *(none)* | `raw-amount=<raw>` | Nano-specific; explicit raw for precision |
| *(none)* | `currency=raw\|XNO` | Nano-specific; unit indicator |
| *(none)* | `rep=<nano_address>` | Nano-specific; suggested representative |
| *(none)* | `expires=<ISO8601>` | Nano-specific; payment request expiry |

#### Amount Handling

The generic `amount` field in `payto://nano/` URIs follows these rules:

1. When `currency=raw` (or omitted), the value MUST be an integer string representing raw units. Example: `amount=1500000000000000000000000000000`.
2. When `currency=XNO`, the value MUST be a decimal string in XNO units. Example: `amount=1.5`. Implementations MUST convert to raw using the factor $10^{30}$.
3. The `raw-amount` parameter, if present, takes precedence over `amount` for precision-critical integrations.
4. Implementations MUST NOT use floating-point arithmetic for amount conversion. Big-integer or arbitrary-precision decimal libraries are REQUIRED.

The RFC 8905 limitation of 8 decimal fraction digits does not apply when `currency=raw`, as the value is an integer. When `currency=XNO`, the 8-digit limit is insufficient for full raw precision; implementations SHOULD use `raw-amount` or `currency=raw` for amounts requiring more than 8 XNO decimal places.

#### Conversion Examples

**Payment with address only:**

```text
nano:nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp

payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp
```

**Payment with amount (raw):**

```text
nano:nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000

payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000&currency=raw
```

**Payment with amount (XNO), label, and message:**

```text
nano:nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=10&label=Developers%20Fund&message=Donate%20Now

payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=10&currency=XNO&receiver-name=Developers%20Fund&message=Donate%20Now
```

**Payment with representative suggestion and expiry:**

```text
payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=500000000000000000000000000000&currency=raw&rep=nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou&expires=2026-06-01T00:00:00Z&message=Invoice%20123
```

#### Bidirectional Conversion

A `nano:` URI can be deterministically converted to `payto://nano/` for the payment subset. The reverse conversion is also deterministic for fields that have `nano:` equivalents.

**`nano:` to `payto://nano/` algorithm:**

1. Extract the address (everything after `nano:` up to `?` or end).
2. Construct `payto://nano/<address>`.
3. For each query parameter in the `nano:` URI:
   - `amount` → `amount` (value unchanged) + `currency=raw`
   - `label` → `receiver-name`
   - `message` → `message`
4. Append any additional `payto://nano/`-specific parameters.

**`payto://nano/` to `nano:` algorithm:**

1. Extract the address from the path.
2. Construct `nano:<address>`.
3. For each query parameter in the `payto://nano/` URI:
   - `amount` → `amount` (if `currency=raw` or omitted; if `currency=XNO`, convert to raw first)
   - `receiver-name` → `label`
   - `message` → `message`
4. Discard parameters without `nano:` equivalents (`sender-name`, `instruction`, `rep`, `expires`, `currency`, `raw-amount`).

**Limitations:** The `nanorep:`, `nanokey:`, `nanoseed:`, and `nanoblock:` schemes have no `payto://` equivalent. They remain Nano-specific and are out of scope for the payto bridge.

### Signing-Intent URI Framework

Signing-intent URIs request a wallet to sign a message, construct a block, or authenticate the user, without directly executing a payment on the URI click. The signed result is delivered to a callback URL.

This section standardizes three signing-intent patterns observed in the Nano ecosystem: authentication, signed payment request, and subscription request.

#### `nanoauth://` Authentication Scheme

**Syntax:**

```abnf
nanoauth-URI    = "nanoauth://" action [ "?" auth-params ]
action          = "sign" / "verify" / authority-specific-action
auth-params     = auth-param *( "&" auth-param )
auth-param      = "message" "=" *pchar
                / "url" "=" *pchar
                / "account" "=" nano-address
                / "nonce" "=" *HEXDIG
                / "separator" "=" *pchar
                / "metadata" "=" *pchar
                / authority-specific-param
```

**Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `message` | Yes | The message to be signed by the user's wallet. SHOULD include a server-generated nonce. |
| `url` | Yes | Callback URL where the wallet POSTs the signed result. |
| `account` | No | The Nano address requesting authentication. If present, the wallet SHOULD verify the user controls this account. |
| `nonce` | No | Hex-encoded random bytes (RECOMMENDED ≥ 128 bits). The server MUST embed or verify this nonce in the `message`. |
| `separator` | No | Separator for the signing format string. Default: `:`. |
| `metadata` | No | URL-encoded JSON object with application-specific metadata. |

**Signing format (V3, fixed):**

The wallet MUST sign the following UTF-8 string, joined by the separator:

```text
<timestamp><separator><label><separator><account>
```

Where:
- `timestamp` is the Unix epoch in seconds (decimal string)
- `label` is the value of the `message` parameter (or a wallet-displayed label)
- `account` is the signing Nano address

With the default separator `:`, a signing string looks like:

```text
1685000000:Login to example.com nonce: abc123:nano_3yxcenuujnn6x7xmg7frakdm5zqu7418n3udquhpqda53oebata1ne9ukipg
```

The wallet signs this UTF-8 string using Ed25519 with Blake2b (the standard Nano signing primitive), producing a 64-byte detached signature.

**Callback payload (POST to `url`):**

```json
{
  "account": "nano_3yxcenuujnn6x7xmg7frakdm5zqu7418n3udquhpqda53oebata1ne9ukipg",
  "signature": "A1B2C3...hex...64bytes",
  "message": "Login to example.com nonce: abc123",
  "timestamp": 1685000000
}
```

**Verification:** The server derives the public key from the account address using `tools.addressToPublicKey(account)` and verifies the signature using `tools.verify(publicKey, signature, message)` (from `nanocurrency-web`) or equivalent Ed25519-Blake2b verification.

**Universal link wrapping:** On mobile, `nanoauth://` URIs SHOULD be wrapped in a universal link for deep-link resolution:

```text
https://nanchat.com/?uri=nanoauth://sign?message=Login%20to%20example.com%20nonce%3A%20abc123&url=https%3A%2F%2Fexample.com%2Fcallback
```

Wallet applications SHOULD register as handlers for both `nanoauth://` and the `nanoauth` parameter within `nano:` or `payto://nano/` URIs.

#### `nanopay://` Signed Payment Request Scheme

**Syntax:**

```abnf
nanopay-URI     = "nanopay://" target [ "?" pay-params ]
target          = nano-address
pay-params      = pay-param *( "&" pay-param )
pay-param       = "amount" "=" 1*DIGIT
                / "label" "=" *pchar
                / "message" "=" *pchar
                / "exact" "=" ("true" / "false")
                / "work" "=" ("true" / "false")
                / "method-type" "=" ("post" / "get")
                / "method-subtype" "=" ("handoff" / authority-specific-subtype)
                / "method-url" "=" *pchar
                / "metadata" "=" *pchar
                / authority-specific-param
```

**Parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `amount` | Yes | — | Amount in raw (integer string). |
| `label` | No | `""` | Human-readable description of the payment. |
| `message` | No | — | Message displayed to the user. |
| `exact` | No | `true` | Whether the amount must match exactly. If `false`, amounts ≥ amount are accepted. |
| `work` | No | `true` | Whether the endpoint supports work generation. |
| `method-type` | Yes | — | Handoff method: `post` (HTTP POST) or `get` (HTTP GET). |
| `method-subtype` | No | `handoff` | The handoff subtype. |
| `method-url` | Yes | — | URL where the wallet sends the signed/constructed block. |
| `metadata` | No | `{}` | URL-encoded JSON object with application-specific metadata. |

**Handoff flow:**

1. Application generates a `nanopay://` URI (optionally signed with the application's private key).
2. User opens the URI in a Nano wallet.
3. Wallet constructs and signs a send block per the URI parameters.
4. Wallet POSTs the signed block JSON to `method-url`.
5. The handoff endpoint broadcasts the block, performs work generation if `work=true`, and returns a response:

**Success response:**

```json
{
  "status": 0,
  "label": "Order #1234",
  "message": "Thank you for your purchase!",
  "metadata": { "order_id": "1234" }
}
```

**Error response:**

```json
{
  "status": 1,
  "message": "Insufficient balance"
}
```

Where `status: 0` indicates success and any non-zero value indicates an error.

#### `nanosub://` Subscription Request Scheme

**Syntax:**

```abnf
nanosub-URI     = "nanosub://" target [ "?" sub-params ]
sub-params      = sub-param *( "&" sub-param )
sub-param       = "amount" "=" 1*DIGIT
                / "frequency" "=" *pchar
                / "label" "=" *pchar
                / "message" "=" *pchar
                / "metadata" "=" *pchar
                / authority-specific-param
```

**Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `amount` | Yes | Amount per payment period in raw. |
| `frequency` | Yes | Payment frequency in cron format (e.g., `0 0 1 * *` for monthly). |
| `label` | No | Human-readable subscription description. |
| `message` | No | Message displayed to the user. |
| `metadata` | No | URL-encoded JSON object with application-specific metadata. |

### Nautilus `nanopay:` / `nanoauth:` Base64-Blob Format

The Nautilus wallet ecosystem (`perishllc/nano-uri`) uses a base64-encoded JSON blob format as an alternative to the URI-parameter format above. This format is compact and suitable for QR codes but opaque to generic URI parsers.

**Format:**

```text
nanopay:<base64-encoded-JSON>
nanoauth:<base64-encoded-JSON>
nanosub:<base64-encoded-JSON>
```

The JSON object contains the same fields as the URI-parameter variants, plus an optional `signature` field containing an Ed25519-Blake2b signature of the JSON string (excluding the signature field itself).

**Backwards-compatible embedding:**

For contexts where the base64 blob is too large for QR codes, the blob can be embedded in a standard `nano:` URI:

```text
nano:<addr>?amount=<raw>&pay=<base64blob>
nano:<addr>?amount=<raw>&auth=<base64blob>
```

Wallets that do not understand the `pay` or `auth` parameter will ignore it and treat the URI as a plain payment.

Implementations SHOULD support both the URI-parameter format and the base64-blob format for maximum interoperability.

### Comparison with Other Blockchain Signing-Intent Patterns

#### Bitcoin BIP-70 / BIP-72 / BIP-75

**BIP-70 (Payment Protocol):** Defines a protobuf-based `PaymentRequest` message with X.509 certificate authentication, expiry, payment URL for callback, and merchant data. The wallet fetches the `PaymentRequest` from a URL specified in the `bitcoin:?r=` parameter (BIP-72).

**Status:** Deprecated in Bitcoin Core 0.18+ (2019) due to multiple security design flaws and implementation bugs in wallet software. Merchants were advised to transition to BIP-21.

**BIP-75:** Extends BIP-70 with sender-signed `InvoiceRequest` messages and encrypted `PaymentRequest` responses, enabling mutual authentication via store-and-forward servers. Uses secp256k1 keypairs for both parties.

**Key takeaways for Nano:**

- BIP-70's X.509 PKI model was overengineered for cryptocurrency; simpler challenge-response (LNURL-auth, nanoauth) is more appropriate.
- The `?r=` fetch-from-URL pattern (BIP-72) is a good model for dynamic payment requests. NanChat's `nanauth://sign?url=<callback>` is the Nano equivalent.
- BIP-75's mutual authentication (sender identifies themselves to the receiver) is directly paralleled by LNURL-auth's `linkingKey` and Nano's `nanoauth:` signing.
- The deprecation of BIP-70 validates the simpler signing-intent approach that Nautilus and NanChat have independently adopted.

#### LNURL-auth (LUD-04)

LNURL-auth enables passwordless login by deriving domain-specific `linkingKey`s from the user's Lightning seed. The service presents a `k1` challenge (32 random bytes), the user's wallet signs it with a domain-derived private key, and the service verifies the signature.

**Key design decisions:**

1. **Domain-derived keys:** `linkingKey = HMAC-SHA256(hashingKey, domain)` → deterministic derivation path. This prevents cross-service identity linkage.
2. **Challenge-response:** Random `k1` prevents replay attacks.
3. **Action enums:** `register | login | link | auth` — explicit intent.
4. **secp256k1 signatures:** Compatible with Bitcoin/Lightning key infrastructure.

**Nano equivalent:** `nanoauth:` (Nautilus) and `nanauth://sign` (NanChat) serve the same purpose but use Ed25519-Blake2b signatures (Nano's native signing primitive) instead of secp256k1.

**Gap:** Neither Nautilus nor NanChat currently derives domain-specific keys. The signing key is the Nano account's private key directly. This means:
- A malicious service could replay a signature to impersonate the user on another service.
- All authenticated services learn the user's Nano address (no unlinkability).

Future work SHOULD define a domain-key derivation scheme analogous to LNURL-auth's `linkingKey` derivation, using HMAC-Blake2b with a Nano-specific derivation path.

#### LNURL-pay (LUD-06)

LNURL-pay defines a two-step callback flow:

1. Service provides metadata (description, image, min/max amounts) at a `lnurlp://` URL.
2. User's wallet specifies an amount and calls the callback URL.
3. Service returns a BOLT-11 invoice with a `descriptionHash` committing to the metadata.

**Key design decisions:**

1. **Metadata commitment:** `descriptionHash = SHA256(metadata + payerData)` ensures the invoice is bound to the payment context.
2. **Payer identity (LUD-18):** Optional `payerData` field allows the payer to include name, pubkey, email, identifier, or auth proof — all committed to the invoice hash.
3. **Dynamic amounts:** Min/max bounds with user-specified amount.

**Nano equivalent:** `nanopay:` (Nautilus) serves a similar purpose but with a simpler model: the payment request is a single signed blob rather than a two-step callback. The `metadata` field in Nautilus nanopay URIs serves the same role as LNURL-pay's metadata array.

**Gap:** Nano's `nanopay:` does not have a metadata commitment hash analogous to BOLT-11's `descriptionHash`. This means a handoff endpoint could theoretically modify metadata between URI generation and block construction. Future work SHOULD define a commitment scheme binding the nanopay metadata to the signed block.

#### LNURL Protocol Schemes (LUD-17)

LUD-17 separated the monolithic `lightning:LNURL...` bech32-encoded scheme into distinct protocol prefixes:

| Prefix | Purpose |
|---|---|
| `lnurlp://` | Payment request |
| `lnurlw://` | Withdraw request |
| `lnurlc://` | Channel request |
| `keyauth://` | Authentication |

This separation allows wallets to implement only the subprotocols they support, and improves iOS URL handling.

**Nano parallel:** Nautilus has already adopted this pattern with `nanopay:`, `nanoauth:`, `nanosub:`. NanChat uses `nanauth://sign`. The current fragmentation (`nanoauth:` vs `nanauth://`) SHOULD be reconciled.

#### Ethereum ERC-681

ERC-681 defines `ethereum:<address>[@chain_id][/function_name]?value=...&gas=...` for payment and contract-call requests.

**Key design decisions:**

1. **Scientific notation for amounts:** `value=2.014e18` — human-readable order-of-magnitude.
2. **Chain ID:** `@1` for mainnet, `@5` for Goerli — multi-network support.
3. **Function calls:** `/transfer?address=...&uint256=...` — ABI-encoded contract interactions.
4. **ENS names:** Hex addresses always take precedence over ENS names.

**Relevance to Nano:** ERC-681's chain ID pattern is already addressed by ORIS-006 (CAIP identifiers). The scientific notation for amounts is worth considering for human-readable payto URIs where `currency=XNO`.

### Reconciliation: `nanoauth:` vs `nanauth://`

Two independent implementations currently exist for Nano authentication signing-intent URIs:

| Aspect | Nautilus `nanoauth:` | NanChat `nanauth://` |
|---|---|---|
| Scheme | `nanoauth:<base64blob>` | `nanauth://sign?message=...&url=...` |
| Format | Base64-encoded JSON | URI query parameters |
| Signing | Ed25519-Blake2b of JSON string | Ed25519-Blake2b of message |
| Callback | POST to `method.url` | POST to `url` parameter |
| Signature scheme | Sign JSON(payload) | Sign message prefixed with "Signed Message: " |
| Verification | `tweetnacl-blake2b` sign.detached.verify | `nanocurrency-web` tools.verify |
| Metadata | Arbitrary JSON `metadata` field | None (nonce in message string) |
| Domain isolation | None (direct key use) | None (direct key use) |

**Recommendation:** Implementations SHOULD support both `nanoauth:` (Nautilus base64-blob format) and `nanoauth://sign` (NanChat query-parameter format). The `nanauth://` scheme SHOULD be aliased to `nanoauth://` for consistency with the `nanoauth:` base64 scheme. The Nautilus signing format (`timestamp:label:account`) SHOULD be preferred for new implementations due to its fixed V3 specification and structured fields.

### Universal Link Wrapping

On mobile platforms that require HTTPS URLs for deep-link resolution, signing-intent URIs SHOULD be wrapped in a universal link:

```text
https://<wallet-domain>/?uri=<encoded-signing-intent-uri>
```

Examples:

```text
https://nanchat.com/?uri=nanoauth://sign?message=...&url=...
https://nanchat.com/?uri=nano:nano_1abc...?amount=1000
```

Wallets SHOULD register their universal link handler to extract and process the `uri` parameter.

### Relationship to ORIS-007 Patterns

The signing-intent URI framework directly supports several ORIS-007 patterns:

| ORIS-007 Pattern | URI Mapping |
|---|---|
| Off-chain Payment Reference | `instruction` field in `payto://nano/` or `metadata` in `nanopay:` |
| Invoice Deposit Account | `payto://nano/<unique_invoice_address>` — standard payto path |
| Raw Dust Tagging | `raw-amount` custom parameter — explicit, not hidden in amount suffix |
| Block Hash Commitment | Post-payment callback response includes block hash |
| Source Account Attribution | `nanoauth:` proves account ownership via signature |

## Published Test Vectors

### Vector 1: `nano:` to `payto://nano/` Conversion

Input:

```text
nano:nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000&label=Developers%20Fund&message=Donate%20Now
```

Output:

```text
payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000&currency=raw&receiver-name=Developers%20Fund&message=Donate%20Now
```

### Vector 2: `payto://nano/` to `nano:` Conversion (Lossy)

Input:

```text
payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=500000000000000000000000000000&currency=raw&receiver-name=Merchant&message=Invoice%20456&rep=nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou&expires=2026-06-01T00:00:00Z
```

Output (lossy — `rep`, `expires`, `sender-name` dropped):

```text
nano:nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=500000000000000000000000000000&label=Merchant&message=Invoice%20456
```

### Vector 3: `nanoauth:` Signing Format

Input parameters:

```text
account:   nano_3yxcenuujnn6x7xmg7frakdm5zqu7418n3udquhpqda53oebata1ne9ukipg
label:     Login with your NANO Account
timestamp: 1685000000
separator: :
```

Signing string (UTF-8):

```text
1685000000:Login with your NANO Account:nano_3yxcenuujnn6x7xmg7frakdm5zqu7418n3udquhpqda53oebata1ne9ukipg
```

## Reference Implementation

- Nautilus `nano-uri` library: https://github.com/perishllc/nano-uri
- NanChat authentication flow: https://nanchat.com/developers
- nano.community payto documentation: https://nano.community/getting-started-devs/integrations
- Nault decentralized aliases: https://github.com/Nault/Nault/pull/587

Reference implementations are informative only and do not override the normative requirements in this document.

## Appendix A: RFC 8905 Registration Template

The following template can be submitted to the GANA "Payto Payment Target Types" registry or to a successor registry:

```text
Name:        nano
Contact:     OpenRai Initiative
Description: Nano cryptocurrency (XNO). The path is a nano_ account
             address (or legacy xrb_ address). The amount option uses
             raw integer amounts by default (currency=raw). An optional
             currency option MAY specify XNO for human-readable amounts.
             Nano-specific options include raw-amount (explicit raw
             override), rep (suggested representative for new accounts),
             and expires (ISO 8601 payment request expiry).
Example:     payto://nano/nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp?amount=1000&message=Donate
References:  RFC 8905, https://docs.nano.org/integration-guides/the-basics/
```

## Appendix B: Signing-Intent Pattern Comparison

| Feature | BIP-70 (deprecated) | LNURL-auth (LUD-04) | Nautilus `nanoauth:` | NanChat `nanauth://` |
|---|---|---|---|---|
| Scheme | `bitcoin:?r=<url>` | `keyauth://` / bech32 | `nanoauth:<base64>` | `nanauth://sign?...` |
| Authentication | X.509 certificates | secp256k1 challenge | Ed25519-Blake2b challenge | Ed25519-Blake2b challenge |
| Domain isolation | Yes (X.509) | Yes (domain-derived key) | No (direct key) | No (direct key) |
| Payer identity | No | No (LUD-18 adds it) | No | No |
| Callback | POST Payment to payment_url | GET with sig+key | POST to method.url | POST to url parameter |
| Metadata | PaymentDetails protobuf | Metadata JSON array | Arbitrary JSON metadata | Nonce in message string |
| Expiry | Yes (expires field) | No | No (timestamp only) | No (nonce freshness) |
| Status | Deprecated 2019 | Active | Deployed | Deployed |

## Appendix C: Gap Analysis — Domain-Derived Key Isolation

Neither Nautilus nor NanChat currently implements domain-derived key isolation for authentication. This means:

1. A service that obtains a `nanoauth:` signature can replay it on another service (if the other service accepts the same signing format).
2. All services learn the user's actual Nano address, enabling cross-service identity linkage.

**Recommended future work:**

Define a `nanoauth:` key derivation scheme analogous to LNURL-auth's `linkingKey`:

1. Derive a `hashingKey` from the user's seed at a reserved derivation index (e.g., `m/138'` per LNURL-auth convention, or a Nano-specific index).
2. For each service domain, derive `linkingKey = HMAC-Blake2b-256(hashingKey, domain)`.
3. Sign challenges with the `linkingKey` instead of the account's primary private key.
4. The service stores the `linkingKey` public key as the user's identity.

This would require coordination between wallet implementations and is out of scope for this document but SHOULD be addressed in a future ORIS.
