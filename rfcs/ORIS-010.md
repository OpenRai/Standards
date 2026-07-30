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

Clients MAY support credential-bearing URLs as a configuration convenience.

The following form MAY be accepted by clients:

```text
https://API_KEY@rpc.example
```

A client that supports this shorthand SHOULD interpret it as:

```text
RPC URL: https://rpc.example
API key: API_KEY
```

and then send the request using Bearer authentication:

```http
Authorization: Bearer API_KEY
```

Credential-bearing URLs are supported optional configuration shorthand, not the normative HTTP authentication method.

In other words, this:

```text
https://API_KEY@rpc.example
```

is only a shorthand for configuring this:

```http
Authorization: Bearer API_KEY
```

### 6. Credential-Bearing URL Processing

If a client supports credential-bearing URLs, it SHOULD process them as follows.

Given:

```text
https://API_KEY@rpc.example/path
```

the client extracts:

```text
API key: API_KEY
RPC URL: https://rpc.example/path
```

The client then sends:

```http
Authorization: Bearer API_KEY
```

The client SHOULD remove the credential from the URL before:

- storing the normalized endpoint URL;
- displaying the endpoint URL;
- logging the endpoint URL;
- passing the URL to a lower-level HTTP client;
- showing diagnostics or error messages.

The client SHOULD NOT rely on the runtime, browser, standard library, or HTTP client to handle URL userinfo automatically.

### 7. URL Username and Password Handling

For maximum compatibility with existing API-key URL formats, ORIS-010 defines the API key as the URL username component.

The following form is the RECOMMENDED credential-bearing URL shorthand:

```text
https://API_KEY@rpc.example
```

The following form MAY also be accepted:

```text
https://API_KEY:@rpc.example
```

Clients MAY reject URLs that contain both a username and a non-empty password:

```text
https://USERNAME:PASSWORD@rpc.example
```

If a client chooses to accept this form, the behavior is implementation-defined and outside the scope of ORIS-010.

ORIS-010 does not define password-based RPC provider authentication.

### 8. Credential-Bearing URLs Are Configuration Only

Credential-bearing URLs are intended only as a convenience for configuration.

They SHOULD NOT be considered a provider authentication requirement.

An ORIS-010-compliant provider is not required to receive or parse credentials from the URL.

An ORIS-010-compliant client that accepts a credential-bearing URL SHOULD convert it into a Bearer-authenticated request before sending the HTTP request.

This avoids depending on inconsistent behavior across URL parsers, browsers, runtimes, SDKs, and HTTP clients.

### 9. Security Considerations for URL Credentials

Embedding credentials in URLs is convenient but risky.

Clients and applications SHOULD prefer separate configuration fields:

```text
RPC URL
RPC API key
```

over a single credential-bearing URL.

Credential-bearing URLs may leak through:

- logs;
- shell history;
- crash reports;
- browser history;
- screenshots;
- analytics;
- proxy logs;
- error messages;
- copied configuration files.

Wallet UIs SHOULD avoid encouraging end users to paste API keys into URLs unless there is a clear UX reason.

Server-side applications MAY choose to support credential-bearing URLs for deployment convenience, but SHOULD normalize and redact them as early as possible.

### 10. JSON Body Authentication

Clients implementing ORIS-010 MUST NOT add the API key to the Nano RPC JSON body for authentication.

This form is not ORIS-010-compliant:

```json
{
  "action": "work_generate",
  "hash": "718CC2121C3E641059BC1C2CFC45666C99E8AE922F7A807B7D07B62C995D79E2",
  "key": "API_KEY"
}
```

Providers MAY continue accepting JSON-body API keys for legacy compatibility, but clients SHOULD NOT generate this format when using ORIS-010.

### 11. Custom Headers

Clients implementing ORIS-010 MUST NOT rely on custom provider-specific authentication headers such as:

```http
Key: API_KEY
```

Providers MAY support such headers for legacy compatibility, but they MUST support Bearer authentication to claim ORIS-010 compatibility.

### 12. HTTP Basic Authentication

HTTP Basic authentication is not the ORIS-010 authentication method.

A provider MAY support Basic authentication for backwards compatibility.

A client MAY support Basic authentication in an explicit legacy compatibility mode.

However, ORIS-010 clients SHOULD NOT rely on Basic authentication for interoperability.

In particular, clients SHOULD NOT depend on this URL form being passed unchanged to an HTTP library:

```text
https://API_KEY@rpc.example
```

because some HTTP clients may strip, ignore, reject, mask, or reinterpret URL credentials.

### 13. General RPC Example

Request:

```http
POST / HTTP/1.1
Host: rpc.example
Content-Type: application/json
Authorization: Bearer test_api_key

{"action":"account_info","account":"nano_..."}
```

### 14. Proof-of-Work Example

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

### 15. Credential-Bearing URL Example

A client MAY allow this configuration value:

```text
https://test_api_key@rpc.example
```

The client SHOULD internally normalize it to:

```text
RPC URL: https://rpc.example
API key: test_api_key
```

and send:

```http
Authorization: Bearer test_api_key
```

The provider receives a normal Bearer-authenticated request.

### 16. Wallet UI Guidance

Wallet UIs SHOULD provide separate fields for:

```text
RPC endpoint
RPC API key
PoW endpoint
PoW API key
```

Wallet UIs MAY additionally accept credential-bearing URLs as an advanced shortcut, but SHOULD normalize them into separate endpoint and API-key values.

Wallet UIs SHOULD redact API keys after entry.

Wallet UIs SHOULD NOT display credential-bearing URLs containing API keys after configuration.

### 17. Server-Side Application Guidance

Server-side applications MAY support either of the following configuration styles.

Separate configuration:

```env
NANO_RPC_URL=https://rpc.example
NANO_RPC_API_KEY=test_api_key
```

Credential-bearing URL shorthand:

```env
NANO_RPC_URL=https://test_api_key@rpc.example
```

If the credential-bearing URL shorthand is used, the application SHOULD extract the API key and send:

```http
Authorization: Bearer test_api_key
```

The application SHOULD NOT pass the credential-bearing URL directly to an HTTP client and rely on automatic Basic authentication behavior.

### 18. Transport Security

Clients MUST use HTTPS when connecting to remote RPC providers.

Plain HTTP MAY be used for local development or local node access, such as:

```text
http://127.0.0.1
http://localhost
```

Providers offering authenticated public RPC endpoints MUST support HTTPS.

### 19. API Key Handling

API keys are bearer credentials.

Any party with access to the API key may be able to use the associated RPC provider account.

Clients:

- MUST treat API keys as secrets;
- SHOULD redact API keys in logs and diagnostics;
- SHOULD avoid displaying full API keys after entry;
- SHOULD avoid exporting API keys unless the user explicitly requests it.

Providers:

- SHOULD allow API keys to be revoked;
- SHOULD allow API keys to be rotated;
- SHOULD rate-limit authenticated requests;
- SHOULD avoid revealing whether a specific API key exists;
- SHOULD provide users with visibility into API key usage where practical.

### 20. Error Responses

If authentication is missing or invalid, providers SHOULD return:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
```

If authentication succeeds but the authenticated key is not authorized for the requested action, providers SHOULD return:

```http
HTTP/1.1 403 Forbidden
```

Providers SHOULD avoid returning error messages that reveal sensitive information about API keys, account status, or internal authentication rules.

## Published Test Vectors

This standard does not define cryptographic test vectors.

The following are interoperability examples.

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

Expected behavior:

```text
Provider authenticates using the Bearer token.
```

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

Expected behavior:

```text
Client extracts the API key from the URL.
Client removes the credential from the URL.
Client sends the API key using Authorization: Bearer.
Provider authenticates using the Bearer token.
```

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

Expected behavior:

```text
Provider authenticates using the Bearer token.
Provider processes the request as an authenticated work_generate request.
```

## Reference Implementation

A reference implementation SHOULD demonstrate:

- sending Bearer-authenticated Nano RPC requests;
- configuring an RPC URL and API key separately;
- optionally parsing`https://API_KEY@rpc.example` as a configuration shorthand;
- normalizing credential-bearing URLs;
- redacting API keys in logs;
- making a general Nano RPC request;
- making an authenticated`work_generate` request.
```
