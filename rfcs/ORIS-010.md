```
OpenRai Initiative Standard: 010
```

# Nano RPC API-Key Authentication

> Status: Working Draft
> Category: Application Interface

## Abstract

ORIS-010 defines a minimal API-key authentication convention for Nano RPC clients and Nano RPC providers.

The normative authentication method is HTTP Bearer authentication:

```http
Authorization: Bearer <API_KEY>
```

This standard applies to wallets, wallet UIs, SDKs, server-side applications, hosted services, proof-of-work providers, and other applications communicating with Nano RPC-compatible endpoints.

Credential-bearing URLs, such as:

```text
https://API_KEY@rpc.example
```

MAY be supported as an optional configuration shorthand, but they are not the normative HTTP authentication method. Clients that support this shorthand SHOULD extract the API key from the URL and send it using the Bearer authentication method.

## Motivation

Nano applications commonly communicate with hosted RPC providers instead of directly operating a local node.

Common use cases include:

- wallet account lookup;
- block lookup;
- block broadcasting;
- representative lookup;
- network status checks;
- application backend RPC access;
- proof-of-work generation using`work_generate`.

Today, RPC provider authentication is inconsistent. Providers may support one or more of:

- adding`"key": "<API_KEY>"` to the JSON RPC body;
- sending a custom HTTP header such as`Key: <API_KEY>`;
- using HTTP Basic authentication;
- embedding credentials in the endpoint URL;
- using HTTP Bearer authentication.

This creates interoperability problems across wallets, SDKs, browser applications, mobile applications, and server-side applications.

ORIS-010 standardizes the interoperable on-wire authentication method:

```http
Authorization: Bearer <API_KEY>
```

Credential-bearing URLs MAY be accepted by clients for configuration convenience, but they are only a shorthand for configuring Bearer authentication.

## Conventions

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **RECOMMENDED** are to be interpreted as described in RFC 2119 and RFC 8174.

Definitions:

- **Client**: Any wallet, wallet UI, SDK, application, backend service, script, or tool making Nano RPC requests.
- **Wallet UI**: A user-facing wallet client, including web, desktop, mobile, and browser-extension wallets.
- **Server-side application**: A backend service, worker, indexer, exchange service, merchant service, automation script, or other non-user-facing application.
- **RPC provider**: A hosted Nano RPC endpoint, proof-of-work provider, gateway, or service compatible with Nano RPC requests.
- **API key**: An opaque credential issued by an RPC provider.
- **Credential-bearing URL**: A URL containing an API key in the userinfo component, such as`https://API_KEY@rpc.example`.
- **PoW RPC**: Proof-of-work generation using Nano RPC, especially the`work_generate` action.

## Specification

### 1. Scope

ORIS-010 applies to any Nano RPC-compatible client or provider that wants a simple interoperable API-key authentication method.

This includes, but is not limited to:

- wallet UIs;
- wallet backends;
- SDKs;
- command-line tools;
- application servers;
- hosted services;
- proof-of-work providers;
- exchanges;
- merchant services;
- explorers;
- monitoring tools.

Wallet UI interoperability is a primary goal, but the standard is not limited to wallets.

### 2. Required On-Wire Authentication Method

Clients implementing ORIS-010 MUST authenticate by sending the API key using the HTTP`Authorization` header with the Bearer scheme:

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

The API key is an opaque provider-issued string.

Clients MUST NOT transform, hash, sign, or otherwise modify the API key before placing it in the Bearer header unless explicitly required by the provider outside this standard.

### 3. Provider Requirements

An RPC provider implementing ORIS-010:

- MUST accept`Authorization: Bearer <API_KEY>`;
- MUST support Bearer authentication for general authenticated RPC requests;
- MUST support Bearer authentication for`work_generate` if authenticated proof-of-work generation is offered;
- MUST NOT require the API key to be present in the JSON RPC body;
- MUST NOT require a custom`Key` header;
- MUST NOT require HTTP Basic authentication;
- MUST NOT require credentials embedded in the URL.

A provider MAY support additional legacy authentication methods, but the Bearer method is the required interoperable ORIS-010 method.

### 4. Client Requirements

A client implementing ORIS-010:

- MUST be able to send`Authorization: Bearer <API_KEY>`;
- SHOULD allow the API key to be configured separately from the RPC URL;
- MUST NOT inject the API key into the Nano RPC JSON body for ORIS-010 authentication;
- SHOULD NOT rely on HTTP Basic authentication;
- SHOULD NOT rely on the underlying HTTP client automatically converting URL credentials into Basic authentication.

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
