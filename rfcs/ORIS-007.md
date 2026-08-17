```
OpenRai Initiative Standard: 007
```

# Nano Application-Level Metadata, Correlation, and Signaling Patterns

> Status: Working Draft
> Category: Informational / Application Guidance

## Abstract

Nano blocks have no memo or arbitrary-data field. Applications nevertheless
assign meaning to destinations, amounts, representatives, and block sequences.

This document names those patterns, explains their failure modes, and recommends
safer choices. Listing a pattern does not imply support from Nano, wallets, or
this document.

## Risk Classification

- **Low risk:** Preserves ordinary payment behavior and does not create unusual
  work for wallets, representatives, or indexers.
- **Context-dependent:** Works only when the application controls the relevant
  accounts, software, scale, or user consent.
- **Harmful if generalized:** Creates material risks such as user confusion,
  privacy loss, unwanted ledger state, or infrastructure load.

## Payment Correlation Patterns

Applications often need to match a payment to an invoice, order, or session.

> Bob asks Alice to pay him 1 XNO for an invoice, order, or service. Alice sends
> the payment, and Bob must determine which invoice it settles.

Each pattern below shows how Bob can make that correlation.

Choose the approach that matches what the payer and receiver can actually do.
When several are available, prefer them in this order:

1. If the payer can receive an authenticated request and report the confirmed
   block hash, use an **[Off-chain Payment Reference](#off-chain-payment-reference)**
   with **[Block Hash Commitment](#block-hash-commitment)**. The reference
   identifies the invoice; the hash identifies the exact ledger event.
2. If the receiver can derive or generate a unique destination account, use an
   **[Invoice Deposit Account](#invoice-deposit-account)**.
3. If repeat deposits are needed and address reuse is acceptable, use a
   **[Customer Deposit Account](#customer-deposit-account)**.
4. If the payer has an authenticated source account, **[Source Account Attribution](#source-account-attribution)** may be acceptable.
5. Use **[Raw Dust Tagging](#raw-dust-tagging)** only when both applications
   preserve exact raw amounts.
6. If none of these anchors is available, redesign the flow. Do not use
   representative-field signaling, pending receivable markers, arbitrary
   address payloads, burn signals, or unsolicited dust for payment correlation.

For a condensed summary of this priority order, see [Payment Correlation Guidance](#payment-correlation-guidance).

### Off-chain Payment Reference

Create an off-chain payment request containing the destination, amount, invoice
ID, and expiration. The receiver later matches a reported confirmed block to that
stored request. This is the same basic flow as two people agreeing on a transfer
out of band, then confirming which payment was sent.

> Bob sends Alice a request with the destination, amount, invoice ID, and
> expiration; Alice pays, reports the payment, and Bob verifies and associates
> it with the invoice.

**Classification:** Low-risk · **AKA:** Signed Payment Reference, External
Invoice Reference

**How it works:** The application sends the payer a destination and exact
amount. It stores the invoice ID, a unique server-generated nonce for that
payment request, and the expiration *outside* the ledger. The application
retrieves that context after matching the payment.

**Risks:**

- If the reference is not signed, a man-in-the-middle can substitute their own
  destination account.
- If nonce and expiration are omitted, the same reference can be replayed.
- Losing the off-chain mapping can make invoice recovery impossible.

**Recommendation:** Use this as the invoice-context layer when the payer can
receive an authenticated request and report the confirmed block hash. Pair it
with a block hash or another concrete ledger anchor. Sign the request when it
crosses an untrusted channel. Include the destination, amount, nonce, and
expiration in the signature.

### Block Hash Commitment

A confirmed block hash is a compact reference to one ledger event. Applications
can store it with a receipt, audit record, or reconciliation entry.

> After Alice's payment confirms, Bob receives and records its block hash and
> uses the hash to identify the exact ledger event.

**Classification:** Low-risk · **AKA:** Block Reference, Hash Anchor

**How it works:** After a payment confirms, the application stores the block
hash in its own database or communicates it off-chain. The hash identifies the
exact ledger event.

**Risks:**

- The hash identifies a ledger event but carries no application meaning. Store
  the invoice or receipt context separately.
- An application that needs the historical block body must have access to an
  archive-capable node; experimental pruning may remove that history.

**Recommendation:** Use a block hash as an off-chain receipt or reference. Store
the application meaning separately and document how the application retrieves
the historical block when it needs the block body.

### Invoice Deposit Account

Generate one Nano account for each invoice. The destination then identifies the
invoice without an on-chain memo.

> Bob derives or generates a unique account for the invoice, sends that
> destination to Alice, and credits the invoice when Bob detects any payment
> there.

**Classification:** Low-risk · **AKA:** Per-invoice Account, One-time
Destination Account

**How it works:** The receiver derives or generates a unique Nano address for a
specific invoice, order, or session. The payer sends to that address. The
application monitors the address for incoming payments and attributes them to
the corresponding invoice.

**Risks:**

- Each invoice adds an account that the application must monitor and recover.
- Reusing a supposedly one-time account creates ambiguity about which invoice
  was paid.
- Sweeping many invoice accounts into one hot wallet links them on-chain.
- Recovery requires either deterministic derivation or stored metadata mapping
  accounts to invoices.
- Unbounded account generation increases wallet and application state.
- If an unauthenticated request can create an invoice, a crawler or attacker can
  force the application to create and monitor vast numbers of accounts without
  making any payment.

**Recommendation:** Use this only when invoice creation is authenticated or
tightly rate-limited, and the application can limit how many destinations it
derives, monitors, and recovers.

### Customer Deposit Account

Assign one deposit account to each customer. Every payment to that destination
is then associated with the same customer record.

> Bob assigns Alice a reusable deposit account, and Bob attributes every payment
> received at that account to Alice.

**Classification:** Low-risk · **AKA:** Per-user Account, User Deposit Account

**How it works:** The service assigns one Nano address to each user. The user
sends to that address whenever they want to deposit. The application monitors
the address and credits the corresponding user.

**Risks:**

- All of a user's deposits are linked on the public ledger. Anyone who knows the
  address can see the user's deposit history.
- Anyone who knows the address can send funds to it, creating attribution
  problems.
- Payments from exchanges or custodial wallets may come from a shared hot
  wallet, requiring additional attribution logic.

**Recommendation:** Use this for repeat deposits when address reuse is
acceptable and customers need unannounced top-ups. Do not use it when each
payment needs a separate destination.

### Source Account Attribution

Register and authenticate a payer's source account. Later payments from that
account can then be associated with the same application identity.

> Alice registers and authenticates her source account with Bob, then Bob
> attributes later payments from that account to Alice.

**Classification:** Context-dependent · **AKA:** Sender Account Attribution

**How it works:** The payer registers or authenticates a Nano account with the
application. Later, when funds arrive from that account, the application
attributes the payment to the registered payer.

**Risks:**

- Exchange and custodial withdrawals come from shared hot wallets, not the
  user's own account. Attribution against a shared source is meaningless and may
  be actively misleading.
- Wallet changes, account rotation, and sweeps can break attribution.
- All payments from the same source account are linkable on the public ledger.
- Without explicit registration and authentication, a source account does not
  identify a person.

**Recommendation:** Use this only for an authenticated source account. This can
complement Web3-style authentication schemes that prove control of the source
account. Account control does not by itself prove the controller's real-world
identity.

### Raw Dust Tagging

Encode a small tag in the least-significant raw digits of the payment amount.
The receiver extracts the suffix and maps it to application state.

> Bob assigns a tag to the invoice, Alice sends an exact raw amount containing
> that tag, and Bob extracts it to identify the invoice.

**Classification:** Context-dependent · **AKA:** Amount Tagging,
Amount-as-Metadata, Raw Encoding

**How it works:**

Exact amounts use the following conversion:

```text
1 XNO = 10^30 raw
```

```text
1.000000000000000000000000000123 XNO
```

The trailing digits encode the value 123 in raw units. The receiver extracts the
suffix and maps it to application meaning.

**Risks:**

- Most wallets display \~6 decimal places. A raw-level suffix is invisible to
  users and may be rounded or truncated in unpredictable and uncontrollable ways
  by the sender's wallet implementation.
- Wallet limitations can prevent the recipient from creating, receiving,
  publishing a receive block for, or returning a dust amount immediately, even
  though Nano transfers are feeless.
- Amount-suffix patterns fingerprint payments on the public ledger, linking them
  to a specific application.
- The tag becomes public when the send block confirms. If redemption treats the
  tag or receipt as a bearer credential, an observer may race or replay it to
  claim the associated receipt; exploitability depends on the redemption flow.
- Refunds, partial payments, and exchange withdrawals destroy the tag.

**Wallet compatibility:** Applications MUST NOT assume that a general-purpose
wallet can display, preserve, send, or receive raw-level tags.

**Recommendation:** Use this only when both applications preserve exact raw
amounts. Do not use it when general wallet compatibility is required.

## State Signaling Patterns

These patterns treat a receive, open block, balance, or frontier as application
state. Wallet automation can trigger the same ledger event without user intent.

> Bob's application controls a Nano wallet or an account chain. Alice (through
> her application-specific wallet) or another party causes a ledger event, and
> Bob decides whether that event should advance application state.

Each pattern below shows how Bob can interpret a ledger event and where that
interpretation can fail.

### Receive Acknowledgement

Treat a receive block as acceptance of a ticket, acceptance of a deposit, or a
signal of an application state transition. This has meaning only when the
application controls when the account receives.

**Classification:** Context-dependent · **AKA:** Receive-as-Commit, Claim Signal

**How it works:** The application sends funds to a dedicated account it
controls. It monitors for the receive block and treats it as the "acceptance"
event in its state machine.

**Risks:**

- Most user wallets auto-receive, so a receive block on a normal account means
  nothing about user intent.
- Even application-controlled wallets may delay or batch receives, making timing
  unreliable.
- A pending send received hours later can trigger a stale state transition.
- Auto-receive can publish the signal without user intent.

**Recommendation:** Use this only with a dedicated application account and
deterministic receive behavior. Never treat a normal wallet's receive block as
consent.

### Pending Receivable Marker

Send a small amount and treat the resulting receivable as a notification. The
recipient did not request this ledger state.

**Classification:** Harmful if generalized · **AKA:** Pending-as-Message,
Receivable Notification

**How it works:** The sender sends a tiny amount to a recipient account and does
not require (or expect) a receive block. Indexers and the recipient's wallet can
see the pending amount.

**Risks:**

- Creates unwanted receivables that clutter wallets and account state.
- Wallets with auto-receive will convert the pending amount into a receive
  block, destroying the intended "unreceived" signal.
- Sending tiny amounts to many accounts ("dust spray probing") is not a reliable
  way to detect wallet activity: wallets may ignore, hide, or auto-receive
  amounts below their practical threshold.
- Easily abused for spam, harassment, and tracking.
- Does not establish consent or awareness.

**Recommendation:** Do not use this pattern. It creates unsolicited account
state, can be indistinguishable from spam, and can enable tracking.

### Open Block as Registration

Use the first block on a dedicated, derived account as a one-time activation
signal for a user, session, or resource. The account may be controlled by the
application or by the user's application-specific wallet.

**Classification:** Context-dependent · **AKA:** Account Activation Signal

**How it works:** The application derives a deterministic account and sends
funds to it. The application or client wallet publishes the account's first
(open) block. The application and its clients watch the account chain and mark
the mapped user, session, or resource active when that block appears.

**Risks:**

- An unsolicited sender can create a pending receivable at the derived address.
  If the application automatically opens the account, that receivable can
  trigger activation without the intended party's consent.
- Sequential derivation indexes leak business volume (e.g., order count).
- Recovery depends on the same derivation scheme and gap-limit assumptions.
- Wallet account discovery can delay or miss the derived account.

**Recommendation:** Use this only when the application controls derivation and
funding. Require separate consent before recording registration.

### Balance State Signal

Assign application states to exact account balances or balance ranges. Any send
or receive can change the encoded value.

**Classification:** Harmful if generalized · **AKA:** Balance-as-State

**How it works:** The application controls an account and sets its balance to a
specific value that encodes application state. Observers read the balance and
interpret it.

**Risks:**

- Any incoming payment can change the state without authorization.
- Requires exact balance tracking and confirmation at every step.
- Filtering events by sender does not make the balance reliable; the application
  must reconcile every relevant block and effectively maintain a parallel ledger.
- Wallet operations may alter balances in unexpected ways.

**Recommendation:** Do not use balance as an application state signal. Store the
state off-chain and use ledger events as inputs to explicit reconciliation.

### Frontier Signal

Use the latest block on a dedicated account as a pointer to the current
off-chain state. Observers watch the frontier for changes.

**Classification:** Context-dependent · **AKA:** Head Block Signal

**How it works:** The application publishes blocks on a dedicated account chain.
Each new block references the current off-chain state (e.g., by including a hash
of the metadata). Observers track the frontier to discover the latest state.

**Risks:**

- Unrelated wallet activity on the same account changes the frontier, confusing
  observers.
- High-frequency updates create unnecessary ledger activity.
- Historical interpretation requires archival nodes or indexers.
- The block contains no metadata unless the application defines a separate
  commitment convention.

**Recommendation:** Use only for low-frequency commitments on a dedicated
application account. Do not interpret a user's normal frontier as a message.

## Representative-Based Patterns

The representative field controls delegated voting. Application metadata in this
field competes with that protocol purpose.
None of the patterns in this section is recommended for application signaling.

### Representative Tagging

Set the representative to an account that encodes a tag, state, or pointer. This
changes the account's delegated vote weight as a side effect.

**Classification:** Harmful if generalized · **AKA:** Rep-as-Message

**How it works:** The application sets the account representative to an account
chosen to encode a tag, state value, or pointer. Observers interpret the
representative as application data.

**Risks:**

- The selected representative may not reflect the account owner's voting choice.
- Wallets may warn, hide, restrict, or auto-manage representative changes.
- Repeated changes create unnecessary account-chain activity.
- Representative accounts used as tags may be mistaken for legitimate
  representatives.

**Network effect:** Widespread use changes vote-weight distribution for reasons
unrelated to representative performance.

**Recommendation:** Do not use the representative field as metadata, a memo, or
an invoice tag.

### Representative as dApp Tag

Ask users to select a project-controlled representative as an opt-in or
affiliation signal. The project then enumerates delegators as participants.

**Classification:** Harmful if generalized · **AKA:** Project Rep Opt-in,
Affiliation Rep

**How it works:** The project publishes a representative address. Users change
their representative to that address to indicate participation. The project
scans delegator lists to build the participant set.

**Risks:**

- Concentrates vote weight on the project operator.
- Couples application eligibility to a consensus choice.
- Lookalike representative accounts can spoof the opt-in signal.
- Multiple applications cannot use the same field independently.

**Recommendation:** Do not use representative selection for opt-in. Use
off-chain registration or a signed message.

### Representative Change Pulse

Change an account's representative between known values and treat each change as
an event.

**Classification:** Harmful if generalized · **AKA:** Rep Churn Signal

**How it works:** The application changes the account's representative, possibly
back and forth between known addresses. Observers treat the change event as a
signal.

**Risks:**

- Changes delegated vote weight without a governance reason.
- Adds blocks solely for application signaling.
- Can be abused as a low-capacity message channel.

**Recommendation:** Do not use representative changes as signals or messages.

## Address and Data Encoding

These patterns encode meaning in an address, derivation index, timing, block
order, or proof of work. None is suitable as a general-purpose data channel.

### Address Payload Encoding

Search for an address containing chosen characters, or interpret arbitrary bytes
as a public key. The second form can create an address with no known private
key.

**Classification:** Harmful if generalized · **AKA:** Address-as-Data

**How it works:** The application generates or selects destination accounts
whose address characters encode application-level data. The encoded value is
visible in the address.

**Risks:**

- An arbitrary payload does not provide the private key needed to spend funds.
- Generating meaningful vanity addresses is computationally expensive.
- Users may mistake encoded addresses for ordinary payment addresses.
- Encourages treating addresses as a data store rather than as spendable
  accounts.

**Recommendation:** Do not encode payloads as destination addresses. Every
payment destination must belong to the intended receiver.

### Vanity Prefix as Identity

Generate a spendable address with a recognizable prefix for branding. An
attacker can generate a similar prefix.

**Classification:** Context-dependent · **AKA:** Branded Address

**How it works:** The operator generates an account whose address contains a
recognizable prefix or substring. The address is published through authenticated
channels as the canonical destination.

**Risks:**

- Lookalike addresses are a well-known phishing vector. A prefix like
  `nano_1proj` can be approximated with a different suffix.
- Users may rely on prefix recognition and skip full-address verification.
- Wallets that truncate addresses may hide the discriminating portion.

**Recommendation:** Publish vanity addresses through an authenticated channel.
Do not treat a recognizable prefix as authentication.

### Burn Signal

Send funds to an address for which no private key is known, then interpret the
payment as a commitment or sacrifice. Observers cannot prove that nobody knows
the private key.
Nano documents a known burn address in its [distribution and units documentation](https://docs.nano.org/protocol-design/distribution-and-units/).

**Classification:** Harmful if generalized · **AKA:** Proof-of-Burn Signal

**How it works:** The sender sends Nano to an unspendable address. Observers
interpret the payment as proof of intentional value destruction.

**Risks:**

- Wastes funds.
- Cannot prove that no party controls the address.
- Encourages value destruction as a signaling mechanism.
- Can confuse users and explorers.

**Recommendation:** Do not use burn payments as routine signals. Use a signed
off-chain commitment instead.

### Account Index Signal

Assign application meaning to deterministic derivation indexes, such as account
roles or invoice ranges.

**Classification:** Context-dependent · **AKA:** Derivation Index Signal

**How it works:** The wallet derives accounts at specific indexes, and the index
number maps to application-level meaning (e.g., index 0 = main account, index
1–1000 = invoice pool).

**Risks:**

- Observable derivation sequences can reveal account or invoice counts.
- Gaps in the index sequence break automatic account discovery.
- Recovery depends on the wallet's exact derivation scheme.

**Recommendation:** Keep index meaning internal. Documenting derivation paths and
gap limits is imperative for recovery.

### Timing Signal

Nano blocks do not contain timestamps or a global cross-account order. A node may
receive a later block before an earlier block and hold it until the earlier block
arrives. Nodes can also record different arrival and confirmation times for the
same block.

**Classification:** Context-dependent · **AKA:** Temporal Encoding

**How it works:** The application treats the local publication, observation, or
confirmation order of selected blocks as application data.

**Risks:**

- No authoritative block timestamp exists.
- Network delays, wallet batching, and user behavior introduce unpredictable
  timing variation.
- Timing signals are fragile and hard to audit.

**Recommendation:** Do not use observed timing as a primary signal. Put a
timestamp and expiration in signed off-chain data.

### Multi-send Ordering Signal

Encode data in a sequence of sends, amounts, or destinations.

**Classification:** Harmful if generalized · **AKA:** Send Ordering Signal

**How it works:** The sender publishes several sends in sequence. Observers
interpret the ordering, amount sequence, or destination sequence as an encoded
message.

**Risks:**

- One account chain has a defined order, but blocks across accounts have no
  shared total order.
- Partial failure corrupts the message.
- Multiple devices sharing a key can race for the next block position. Incoming
  payments to the sender's own account mutate its balance between sends,
  altering block ordering.
- Creates unnecessary ledger activity.

**Recommendation:** Do not use send sequences as a data encoding.

### Arbitrary Data Encoding

Combine amounts, addresses, representatives, work values, accounts, and block
order into a custom data encoding. Every write adds permanent ledger state.

**Classification:** Harmful if generalized · **AKA:** Ledger Data Storage

**How it works:** The application encodes data through combinations of block
fields, transaction patterns, and account creation. The data is visible to
observers who know the encoding scheme.

**Risks:**

- Creates permanent ledger growth and infrastructure burden.
- Degrades wallet, explorer, and indexer usability.
- Data capacity is extremely low and encoding is fragile.
- Application meaning is lost without the custom decoder.

**Recommendation:** Store metadata outside the ledger. Use a cryptographic
commitment when the application must bind that metadata to a ledger event.

### Work-field / Overwork Signaling

Select a proof-of-work value with a chosen pattern, or compute more work than
the network requires. Work is not part of the block hash and can be replaced
without changing the block identity.

**Classification:** Harmful if generalized · **AKA:** Proof-of-work Tagging

**How it works:** The sender selects a specific work value, or computes
unusually high work, and observers interpret the work pattern as data.

**Risks:**

- Wastes computation for negligible data capacity.
- Another implementation can replace the work value.
- Poor wallet and tooling support.
- Observers may ignore or discard the distinction.

**Recommendation:** Do not use work values as a signaling channel.

## Payment Correlation Guidance

This section is a decision summary of [Payment Correlation Patterns](#payment-correlation-patterns).
Choose based on what the payer and receiver can actually do:

- If the payer's application can report the confirmed block hash, use an
  [Off-chain Payment Reference](#off-chain-payment-reference) with a [Block Hash Commitment](#block-hash-commitment). The reference supplies invoice context;
  the hash supplies the ledger anchor.
- If the receiver can provide a unique destination for each invoice, and can
  authenticate or rate-limit invoice creation and limit how many accounts it
  monitors, use an [Invoice Deposit Account](#invoice-deposit-account).
- If the receiver needs a reusable destination for repeat deposits, use a
  [Customer Deposit Account](#customer-deposit-account) when address reuse is
  acceptable.
- If the payer has an authenticated source account, use [Source Account Attribution](#source-account-attribution).
- If both applications preserve exact raw amounts, [Raw Dust Tagging](#raw-dust-tagging)
  may be used as a controlled integration technique.

An off-chain reference without a concrete ledger anchor is request context, not
proof that a particular payment settles an invoice. Its invoice ID, nonce,
amount, and expiration do not appear in the Nano payment and cannot resolve
collisions by themselves.

Applications SHOULD NOT use [Representative Tagging](#representative-tagging),
[Representative as dApp Tag](#representative-as-dapp-tag), [Representative Change Pulse](#representative-change-pulse), [Pending Receivable Markers](#pending-receivable-marker), [Burn Signals](#burn-signal), [Address Payload Encoding](#address-payload-encoding), [Multi-send Ordering Signals](#multi-send-ordering-signal), or [Arbitrary Data Encoding](#arbitrary-data-encoding) for ordinary invoice correlation.

ORIS-008 covers confirmation, idempotency, reconciliation, and payment lifecycle
handling after the application chooses a correlation method. For finality and
processing rules, see [ORIS-008 confirmation and absolute finality](ORIS-008.md#confirmation-and-absolute-finality).

## Glossary

These definitions describe how this document uses Nano terms.

- **Account chain:** The strictly serial sequence of blocks belonging to a single
  Nano account. Each account maintains its own chain.
- **Application-level meaning:** Meaning assigned by software above the protocol
  layer.
- **Archival node:** A node configuration that retains full block history for all
  account chains, rather than pruning to frontiers only.
- **Block lattice:** The overall data structure formed by all individual account
  chains in Nano.
- **Change block:** A block that changes an account's representative without
  changing the account balance.
- **Dust:** An amount small enough that an application treats it as uneconomical or
  unwanted. The threshold is application-specific.
- **Frontier:** The latest block on an account chain. A confirmed frontier is
  the latest block at the account's confirmation height. A node configured for
  pruning may discard older block bodies.
- **Nano block fields:** State blocks include `type`, `account`, `previous`,
  `representative`, `balance`, `link`, `work`, and `signature`. There is no
  generic data, memo, or payload field.
- **Off-chain:** Data or state maintained outside the Nano ledger and P2P
  protocol.
- **Open block:** The first block on an account chain, which receives the account's
  initial incoming send and establishes its first representative.
- **Open Representative Voting (ORV):** Nano's consensus mechanism, in which
  representatives vote with weight delegated to them to confirm blocks.
- **Raw:** The smallest indivisible Nano unit.
- **Receivable (formerly pending):** An incoming send published by the sender
  but not yet acknowledged by a receive block on the destination account.
- **Receive block:** A block that claims a receivable and credits the balance to
  the receiving account.
- **Representative:** The account designated to vote with an account holder's
  delegated weight.
- **Send block:** A block that debits an account balance and creates a receivable
  on a destination account.
- **Signal:** A ledger event or state interpreted by an application.
- **XNO:** Nano's user-facing unit of account.
