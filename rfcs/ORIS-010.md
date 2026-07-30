```
OpenRai Initiative Standard: 010
```

# API-Key Authentication for Nano RPC

> Status: Working Draft
> Category: Application Interface

## Abstract

This document defines one API-key authentication method for Nano RPC:

```http
Authorization: Bearer <API_KEY>
```

It applies to wallets, SDKs, backend services, hosted RPC gateways, and
proof-of-work providers. A client may accept a credential-bearing URL as
configuration, but it always sends the key in the HTTP `Authorization` header.

## Motivation

Hosted Nano RPC services use incompatible authentication conventions. A client
may currently need a JSON `key`, a custom header, Basic authentication, URL
credentials, or a Bearer token.

One header lets the same client authenticate account queries, block
publication, and `work_generate` requests:

```http
Authorization: Bearer <API_KEY>
```

Legacy methods may remain available, but they are outside ORIS-010.

## Conventions

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **RECOMMENDED** are to be interpreted as described in RFC 2119 and RFC 8174.

Definitions:

- **Client:** Software that sends Nano RPC requests.
- **RPC provider:** A service that receives Nano RPC-compatible requests.
- **API key:** A bearer credential issued by an RPC provider.
- **Credential-bearing URL:** A configuration URL with an API key in its
  username component, such as `https://API_KEY@rpc.example`.

## Specification

### 1. Scope

This document covers API-key transport, optional URL configuration, TLS, secret
handling, and authentication errors. It does not define key issuance, account
management, authorization scopes, quotas, or Nano RPC actions.

### 2. Required On-Wire Authentication Method

Clients MUST send the API key in the HTTP `Authorization` header:

```http
Authorization: Bearer <API_KEY>
```

Example:

```http
POST / HTTP/1.1
Host: rpc.example
Content-Type: application/json
Authorization: Bearer nano_rpc_key_example

{"action":"block_count"}
```

Providers MUST issue keys compatible with the RFC 6750 `b64token` grammar:

```abnf
b64token = 1*( ALPHA / DIGIT / "-" / "." / "_" / "~" / "+" / "/" ) *"="
```

Clients MUST place the issued value in the header without transformation.

### 3. Provider Requirements

An RPC provider implementing ORIS-010:

- MUST accept `Authorization: Bearer <API_KEY>`.
- MUST use the same method for `work_generate` when it offers authenticated
  proof-of-work generation.
- MUST NOT require the key in the JSON body, a custom header, Basic
  authentication, or the request URL.

A provider MAY support legacy methods in addition to Bearer authentication.

### 4. Client Requirements

A client implementing ORIS-010:

- MUST send `Authorization: Bearer <API_KEY>`.
- SHOULD configure the endpoint and key separately.
- MUST NOT add the key to the Nano RPC JSON object.
- MUST NOT depend on automatic Basic authentication from URL userinfo.

### 5. Optional Credential-Bearing URL Shorthand

Clients MAY accept this configuration form:

```text
https://API_KEY@rpc.example
```

A supporting client MUST extract:

```text
RPC URL: https://rpc.example
API key: API_KEY
```

It then sends:

```http
Authorization: Bearer API_KEY
```

The URL is a configuration shorthand. It is not the request authentication
method, and the provider never needs to parse URL credentials.

### 6. Credential-Bearing URL Processing

When a client supports the shorthand, it MUST:

1. Parse the URL without making a request.
2. Reject an empty username.
3. Reject a non-empty password.
4. Percent-decode the username exactly once.
5. Validate the decoded key against the `b64token` grammar.
6. Remove all userinfo from the endpoint URL.
7. Store the endpoint and key separately.
8. Add the Bearer header to each authenticated request.

The client MUST remove userinfo before passing the endpoint to an HTTP library.
It MUST NOT depend on automatic Basic authentication.

### 7. URL Username and Password Handling

The username component contains the API key. A client MAY accept an explicitly
empty password:

```text
https://API_KEY:@rpc.example
```

A client MUST reject a non-empty password:

```text
https://USERNAME:PASSWORD@rpc.example
```

This document does not define password authentication.

### 8. URL Credential Exposure

Clients SHOULD prefer separate fields:

```text
RPC URL
RPC API key
```

Credential-bearing URLs can leak through shell history, logs, crash reports,
screenshots, analytics, proxy logs, and copied configuration. A client that
accepts them MUST redact the username in display, logs, diagnostics, and error
messages.

### 9. Legacy Authentication Methods

An ORIS-010 client MUST NOT put the key in the Nano RPC JSON object:

```json
{
  "action": "work_generate",
  "hash": "718CC2121C3E641059BC1C2CFC45666C99E8AE922F7A807B7D07B62C995D79E2",
  "key": "API_KEY"
}
```

It also MUST NOT use a provider-specific header:

```http
Key: API_KEY
```

An ORIS-010 client SHOULD NOT use HTTP Basic authentication. Providers MAY keep
any of these methods for legacy clients, but MUST also support Bearer
authentication.

### 10. Wallet UI Guidance

Wallet UIs SHOULD provide separate fields for:

```text
RPC endpoint
RPC API key
PoW endpoint
PoW API key
```

Wallet UIs MAY additionally accept credential-bearing URLs as an advanced shortcut, but SHOULD normalize them into separate endpoint and API-key values.

After configuration, a wallet SHOULD show only a redacted key and a URL without
userinfo.

### 11. Server-Side Configuration

Use separate secrets when the deployment system supports them:

```env
NANO_RPC_URL=https://rpc.example
NANO_RPC_API_KEY=test_api_key
```

An application MAY also accept:

```env
NANO_RPC_URL=https://test_api_key@rpc.example
```

It MUST normalize that value before making a request.

### 12. Transport Security

Clients MUST use HTTPS when connecting to remote RPC providers.

Plain HTTP MAY be used only for a loopback endpoint:

```text
http://127.0.0.1
http://[::1]
http://localhost
```

Public providers MUST support HTTPS and MUST NOT accept ORIS-010 credentials
over plain HTTP.

### 13. API Key Handling

Anyone who obtains the key can use its permissions.

Clients:

- MUST treat keys as secrets.
- MUST redact keys from logs, diagnostics, and errors.
- SHOULD hide keys after entry.
- SHOULD NOT export a key without an explicit user action.

Providers:

- SHOULD support revocation and rotation.
- SHOULD let operators restrict a key's permissions.
- SHOULD rate-limit requests.
- SHOULD record enough usage data to investigate abuse.

### 14. Error Responses

When the request has no credentials, the provider MUST return:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="nano-rpc"
```

For an invalid or revoked key, the provider SHOULD return:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="nano-rpc", error="invalid_token"
```

For insufficient permission, the provider SHOULD return:

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer realm="nano-rpc", error="insufficient_scope"
```

An error MUST NOT echo the key or reveal whether another specific key exists.

## Published Test Vectors

This document has no cryptographic vectors. The following examples define
observable interoperability behavior.

### Example 1: Separate URL and API Key

Configuration:

```text
RPC URL: https://rpc.example
API key: test_api_key
```

Request:

```http
POST / HTTP/1.1
Host: rpc.example
Content-Type: application/json
Authorization: Bearer test_api_key

{"action":"block_count"}
```

The provider authenticates the request with the Bearer token.

### Example 2: Credential-Bearing URL Shorthand

Configuration:

```text
RPC URL: https://test_api_key@rpc.example
```

Client normalization:

```text
RPC URL: https://rpc.example
API key: test_api_key
```

Request:

```http
POST / HTTP/1.1
Host: rpc.example
Content-Type: application/json
Authorization: Bearer test_api_key

{"action":"block_count"}
```

The client extracts the key, removes userinfo from the URL, and sends the
Bearer header.

### Example 3: Authenticated PoW Request

Configuration:

```text
PoW URL: https://rpc.example
PoW API key: test_api_key
```

Request:

```http
POST / HTTP/1.1
Host: rpc.example
Content-Type: application/json
Authorization: Bearer test_api_key

{
  "action": "work_generate",
  "hash": "718CC2121C3E641059BC1C2CFC45666C99E8AE922F7A807B7D07B62C995D79E2"
}
```

The provider authenticates the request before processing `work_generate`.

## Reference Implementation

No reference implementation is nominated yet.

## References

- [RFC 6750 — OAuth 2.0 Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750)
- [Nano RPC protocol](https://docs.nano.org/commands/rpc-protocol/)
