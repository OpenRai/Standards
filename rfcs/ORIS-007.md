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

## Conventions

Addresses use the `nano_` prefix. Amounts use either XNO or raw:

```text
1 XNO = 10^30 raw
```

The [Glossary](#glossary) defines Nano ledger terms.

## Risk Classification

- **Low risk:** Preserves ordinary payment behavior and does not create unusual
  work for wallets, representatives, or indexers.
- **Context-dependent:** Works only when the application controls the relevant
  accounts, software, scale, or user consent.
- **Harmful if generalized:** Creates material risks such as user confusion,
  privacy loss, unwanted ledger state, or infrastructure load.

## Payment Correlation Patterns

Applications often need to match a payment to an invoice, order, or session.
Use these options in order:

1. If payment context can be exchanged off-chain, use an [**Off-chain Payment Reference**](#off-chain-payment-reference).
2. If the receiver can generate a unique destination account, use an [**Invoice Deposit Account**](#invoice-deposit-account).
3. If the payer has an authenticated source account, [**Source Account Attribution**](#source-account-attribution) may be acceptable.
4. Use [**Raw Dust Tagging**](#raw-dust-tagging) only when both applications
   preserve exact raw amounts.
5. Avoid representative-field signaling, arbitrary address payloads, burn signals, and unsolicited dust for payment correlation.

### Off-chain Payment Reference

Create an off-chain payment request containing the destination, amount, invoice
ID, and expiration. The receiver later matches the confirmed payment to that
stored request.

**Classification:** Low-risk · **AKA:** Signed Payment Reference, External Invoice Reference

**How it works:** The application sends the payer a destination and exact amount.
It stores the invoice ID, nonce, and expiration outside the ledger. The
application retrieves that context after matching the payment.

**Risks:**
- If the reference is not signed, a man-in-the-middle can substitute their own destination account.
- If nonce and expiration are omitted, the same reference can be replayed.
- Losing the off-chain mapping can make invoice recovery impossible.

**Recommendation:** Use this as the default when the payer can receive payment
context. Sign the request when it crosses an untrusted channel. Include the
destination, amount, nonce, and expiration in the signature.

### Block Hash Commitment

A confirmed block hash is a compact reference to one ledger event. Applications
can store it with a receipt, audit record, or reconciliation entry.

**Classification:** Low-risk · **AKA:** Block Reference, Hash Anchor

**How it works:** After a payment confirms, the application stores the block hash in its own database or communicates it off-chain. The hash identifies the exact ledger event.

**Risks:**
- A pruned node may not retain the historical block body.
- The hash carries no application meaning. Store that meaning separately.

**Recommendation:** Use a block hash as an off-chain reference. Document how the
application retrieves historical blocks.

### Invoice Deposit Account

Generate one Nano account for each invoice. The destination then identifies the
invoice without an on-chain memo.

**Classification:** Low-risk · **AKA:** Per-invoice Account, One-time Destination Account

**How it works:** The receiver derives or generates a unique Nano address for a specific invoice, order, or session. The payer sends to that address. The application monitors the address for incoming payments and attributes them to the corresponding invoice.

**Risks:**
- Each invoice adds an account that the application must monitor and recover.
- Reusing a supposedly one-time account creates ambiguity about which invoice was paid.
- Sweeping funds from many invoice accounts into a hot wallet links them on-chain; see [Account Sweep Linkage](#account-sweep-linkage).
- Recovery requires either deterministic derivation or stored metadata mapping accounts to invoices.
- Unbounded account generation increases wallet and application state.

**Recommendation:** Use this when the application can derive, monitor, and
recover unique destinations.

### Customer Deposit Account

Assign one deposit account to each customer. Every payment to that destination
is then associated with the same customer record.

**Classification:** Low-risk · **AKA:** Per-user Account, User Deposit Account

**How it works:** The service assigns one Nano address to each user. The user sends to that address whenever they want to deposit. The application monitors the address and credits the corresponding user.

**Risks:**
- All of a user's deposits are linked on the public ledger. Anyone who knows the address can see the user's deposit history.
- Anyone who knows the address can send funds to it, creating attribution problems.
- Payments from exchanges or custodial wallets may come from a shared hot wallet, requiring additional attribution logic.
- If the address leaks or the mapping database is compromised, historical activity is exposed.

**Recommendation:** Use this for repeat deposits when address reuse is
acceptable. Prefer an [Invoice Deposit Account](#invoice-deposit-account) when
payments should not share one public destination.

### Account Sweep Linkage

Consolidating many deposit accounts into one account creates a public
many-to-one ownership signal.

**Classification:** Harmful if generalized · **AKA:** Sweep Correlation

**How it works:** The service periodically transfers balances from many deposit accounts to one or a few destination accounts. The sweep transactions are visible on-chain and link all source accounts to the same entity.

**Risks:**
- Retroactively links all swept accounts on a fully transparent ledger.
- Reveals aggregate business volume and timing to any observer.
- Combined with timing analysis, can deanonymize individual customers.

**Recommendation:** Treat sweep linkage as a privacy cost in the account model.
No sweep schedule can remove the public transfers. Separate operational funds
only when that separation has a real accounting or security purpose.

### Source Account Attribution

Register and authenticate a payer's source account. Later payments from that
account can then be associated with the same application identity.

**Classification:** Context-dependent · **AKA:** Sender Account Attribution

**How it works:** The payer registers or authenticates a Nano account with the application. Later, when funds arrive from that account, the application attributes the payment to the registered payer.

**Risks:**
- Exchange and custodial withdrawals come from shared hot wallets, not the user's own account. Attribution against a shared source is meaningless and may be actively misleading.
- Wallet changes, account rotation, and sweeps can break attribution.
- All payments from the same source account are linkable on the public ledger.
- Without explicit registration and authentication, a source account does not identify a person.

**Recommendation:** Use this only for an authenticated source account. Do not
infer a person's identity from an unregistered source account.

### Reply-with-Send Receipt

Send a small amount back to the source account as an on-chain receipt. That
source may belong to an exchange or custodian rather than the payer.

**Classification:** Context-dependent · **AKA:** Echo Send, Send-back Receipt

**How it works:** The application receives a payment, identifies the source account, and sends a small amount back to that account as an on-chain confirmation.

**Risks:**
- Inherits all failure modes of [Source Account Attribution](#source-account-attribution): the source account may not be the payer.
- Creates unsolicited receivables for the source-account controller.
- May be misinterpreted as a refund or a fresh payment.
- Inherits the auto-receive problems of [Receive Acknowledgement](#receive-acknowledgement) and [Pending Receivable Marker](#pending-receivable-marker).

**Recommendation:** Prefer an off-chain signed receipt. Send an on-chain receipt
only to an explicitly registered source account.

### Raw Dust Tagging

Encode a small tag in the least-significant raw digits of the payment amount.
The receiver extracts the suffix and maps it to application state.

**Classification:** Context-dependent · **AKA:** Amount Tagging, Amount-as-Metadata, Raw Encoding

**How it works:**

```text
1.000000000000000000000000000123 XNO
```

The trailing digits encode the value 123 in raw units. The receiver extracts the suffix and maps it to application meaning.

**Risks:**
- Most wallets display ~6 decimal places. A raw-level suffix is invisible to users and may be rounded or truncated by the sender's wallet.
- Some wallets refuse to create or receive extremely small amounts.
- The receiver may not publish a receive block for dust-level pending amounts.
- Amount-suffix patterns fingerprint payments on the public ledger, linking them to a specific application.
- Refunds, partial payments, and exchange withdrawals destroy the tag.

**Wallet compatibility:** Applications MUST NOT assume that a general-purpose wallet can display, preserve, send, or receive raw-level tags.

**Recommendation:** Use this only when both applications preserve exact raw
amounts. Prefer an [Invoice Deposit Account](#invoice-deposit-account) or
[Off-chain Payment Reference](#off-chain-payment-reference) for general wallet
compatibility.

## State Signaling Patterns

These patterns treat a receive, open block, balance, or frontier as application
state. Wallet automation can trigger the same ledger event without user intent.

### Receive Acknowledgement

Treat a receive block as acceptance of a ticket, deposit, or state transition.
This has meaning only when the application controls when the account receives.

**Classification:** Context-dependent · **AKA:** Receive-as-Commit, Claim Signal

**How it works:** The application sends funds to a dedicated account it controls. It monitors for the receive block and treats it as the "acceptance" event in its state machine.

**Risks:**
- Most user wallets auto-receive, so a receive block on a normal account means nothing about user intent.
- Even application-controlled wallets may delay or batch receives, making timing unreliable.
- A pending send received hours later can trigger a stale state transition.
- Auto-receive can publish the signal without user intent.

**Recommendation:** Use this only with a dedicated application account and
deterministic receive behavior. Never treat a normal wallet's receive block as
consent.

### Pending Receivable Marker

Send a small amount and treat the resulting receivable as a notification. The
recipient did not request this ledger state.

**Classification:** Harmful if generalized · **AKA:** Pending-as-Message, Receivable Notification

**How it works:** The sender sends a tiny amount to a recipient account and does not require (or expect) a receive block. Indexers and the recipient's wallet can see the pending amount.

**Risks:**
- Creates unwanted receivables that clutter wallets and account state.
- Wallets with auto-receive will convert the pending amount into a receive block, destroying the intended "unreceived" signal.
- Easily abused for spam, harassment, and tracking.
- Does not establish consent or awareness.

**Recommendation:** Do not use this pattern. It creates unsolicited account
state and can be used for spam or tracking.

### Open Block as Registration

Treat the first block on a derived account as registration. An open block
requires a receivable, and another party can create that receivable.

**Classification:** Context-dependent · **AKA:** Account Activation Signal

**How it works:** The application derives a deterministic account for the user (e.g., at a specific HD index). When the user (or the application) funds that account and the open block is published, the application treats it as registration.

**Risks:**
- Anyone who can send to the deterministic address can force an open block, triggering registration against the user's intent.
- Sequential derivation indexes leak business volume (e.g., order count).
- Recovery depends on the same derivation scheme and gap-limit assumptions.
- Wallet account discovery can delay or miss the derived account.

**Recommendation:** Use this only when the application controls derivation and
funding. Require separate consent before recording registration.

### Balance State Signal

Assign application states to exact account balances or balance ranges. Any send
or receive can change the encoded value.

**Classification:** Context-dependent · **AKA:** Balance-as-State

**How it works:** The application controls an account and sets its balance to a specific value that encodes application state. Observers read the balance and interpret it.

**Risks:**
- Any incoming payment can change the state without authorization.
- Requires exact balance tracking and confirmation at every step.
- Wallet operations may alter balances in unexpected ways.

**Recommendation:** Use only on an application-controlled account where every
block is checked. Do not use a user account.

### Frontier Signal

Use the latest block on a dedicated account as a pointer to the current
off-chain state. Observers watch the frontier for changes.

**Classification:** Context-dependent · **AKA:** Head Block Signal

**How it works:** The application publishes blocks on a dedicated account chain. Each new block references the current off-chain state (e.g., by including a hash of the metadata). Observers track the frontier to discover the latest state.

**Risks:**
- Unrelated wallet activity on the same account changes the frontier, confusing observers.
- High-frequency updates create unnecessary ledger activity.
- Historical interpretation requires archival nodes or indexers.
- The block contains no metadata unless the application defines a separate
  commitment convention.

**Recommendation:** Use only for low-frequency commitments on a dedicated
application account. Do not interpret a user's normal frontier as a message.

## Representative-Based Patterns

The representative field controls delegated voting. Application metadata in
this field competes with that protocol purpose.

### Representative Tagging

Set the representative to an account that encodes a tag, state, or pointer.
This changes the account's delegated vote weight as a side effect.

**Classification:** Harmful if generalized · **AKA:** Rep-as-Message

**How it works:** The application sets the account representative to an account chosen to encode a tag, state value, or pointer. Observers interpret the representative as application data.

**Risks:**
- The selected representative may not reflect the account owner's voting choice.
- Wallets may warn, hide, restrict, or auto-manage representative changes.
- Repeated changes create unnecessary account-chain activity.
- Representative accounts used as tags may be mistaken for legitimate representatives.

**Network effect:** Widespread use changes vote-weight distribution for reasons
unrelated to representative performance.

**Recommendation:** Do not use the representative field as metadata, a memo, or
an invoice tag.

### Representative as dApp Tag

Ask users to select a project-controlled representative as an opt-in or
affiliation signal. The project then enumerates delegators as participants.

**Classification:** Harmful if generalized · **AKA:** Project Rep Opt-in, Affiliation Rep

**How it works:** The project publishes a representative address. Users change their representative to that address to indicate participation. The project scans delegator lists to build the participant set.

**Risks:**
- Concentrates vote weight on the project operator.
- Couples application eligibility to a consensus choice.
- Lookalike representative accounts can spoof the opt-in signal.
- Multiple applications cannot use the same field independently.

**Recommendation:** Do not use representative selection for opt-in. Use
off-chain registration or a signed message.

### Representative Change Pulse

Change an account's representative between known values and treat each change
as an event.

**Classification:** Harmful if generalized · **AKA:** Rep Churn Signal

**How it works:** The application changes the account's representative, possibly back and forth between known addresses. Observers treat the change event as a signal.

**Risks:**
- Changes delegated vote weight without a governance reason.
- Adds blocks solely for application signaling.
- Can be abused as a low-capacity message channel.

**Recommendation:** Do not use representative changes as signals or messages.

## Address and Data Encoding

These patterns try to encode application-level meaning in addresses, amounts, timing, proof-of-work, or transaction ordering. None of them are recommended for general use.

### Address Payload Encoding

Nano addresses are derived from public keys. Some applications try to encode data into the address itself — by searching for vanity addresses whose characters spell out a payload, or by constructing addresses from arbitrary bytes. This is fragile, low-capacity, and risks sending funds to addresses with no known private key.

**Classification:** Harmful if generalized · **AKA:** Address-as-Data

**How it works:** The application generates or selects destination accounts whose address characters encode application-level data. The encoded value is visible in the address.

**Risks:**
- Constructing addresses from arbitrary payload bytes almost certainly produces an address with no known private key. Funds sent there are permanently lost.
- Generating meaningful vanity addresses is computationally expensive.
- Users may mistake encoded addresses for ordinary payment addresses.
- Encourages treating addresses as a data store rather than as spendable accounts.

**Verdict:** Do not encode arbitrary data into addresses. If an address is used, it must correspond to a spendable account controlled by the intended receiver.

### Vanity Prefix as Identity

A recognizable address prefix (e.g., `nano_1project...`) gives users a visual cue that an address belongs to a specific organization. Unlike [Address Payload Encoding](#address-payload-encoding), the address is a real spendable account — the vanity is just branding. The risk: adversaries can generate lookalike prefixes for phishing.

**Classification:** Context-dependent · **AKA:** Branded Address

**How it works:** The operator generates an account whose address contains a recognizable prefix or substring. The address is published through authenticated channels as the canonical destination.

**Risks:**
- Lookalike addresses are a well-known phishing vector. A prefix like `nano_1proj` can be approximated with a different suffix.
- Users may rely on prefix recognition and skip full-address verification.
- Wallets that truncate addresses may hide the discriminating portion.

**Verdict:** Acceptable for branding when published through authenticated channels. Never rely on vanity prefixes as a substitute for cryptographic authentication of payment destinations.

### Burn Signal

Sending funds to an address with no known private key destroys them — provably, irreversibly (as far as anyone knows). Some applications use this as proof of commitment or sacrifice. The problem: you can never prove no private key exists, and the funds are genuinely wasted.

**Classification:** Harmful if generalized · **AKA:** Proof-of-Burn Signal

**How it works:** The sender sends Nano to an unspendable address. Observers interpret the payment as proof of intentional value destruction.

**Risks:**
- Wastes funds.
- It's impossible to prove that no private key exists for a given address.
- Encourages value destruction as a signaling mechanism.
- Can confuse users and explorers.

**Verdict:** Do not use burn payments as routine signals. If proof of commitment is needed, use signed off-chain commitments or ordinary payments to controlled accounts.

### Account Index Signal

If you use deterministic key derivation (like HD wallets), the index number itself can carry meaning — account type, invoice sequence, role. This is convenient but leaks information: sequential indexes reveal business volume, and gaps break account discovery.

**Classification:** Context-dependent · **AKA:** Derivation Index Signal

**How it works:** The wallet derives accounts at specific indexes, and the index number maps to application-level meaning (e.g., index 0 = main account, index 1–1000 = invoice pool).

**Risks:**
- Sequential indexes leak business volume (e.g., order count, user signups).
- Gaps in the index sequence break automatic account discovery.
- Different wallets use different derivation schemes — recovery depends on documenting the exact scheme.
- Publishing extended public keys exposes future addresses.

**Verdict:** Use internally if needed, but document derivation paths, gap limits, and privacy consequences. Do not expose sensitive derivation structure.

### Timing Signal

Nano blocks don't carry timestamps. The observed confirmation time depends on network propagation, node arrival order, and vote duration — two observers may disagree on when the same block was confirmed. Encoding meaning in timing or ordering between blocks is fragile and unauditable.

**Classification:** Context-dependent · **AKA:** Temporal Encoding

**How it works:** The application assigns meaning to when blocks are published, confirmed, or observed relative to each other.

**Risks:**
- No authoritative timestamp exists — observation time differs across nodes, wallets, and indexers.
- Network delays, wallet batching, and user behavior introduce unpredictable timing variation.
- Timing signals are fragile and hard to audit.

**Verdict:** Do not rely on timing as a primary signal. Include timestamps and expirations in off-chain signed metadata instead.

### Multi-send Ordering Signal

Some applications encode data in the sequence of multiple sends — the order, amounts, or destinations carry meaning. This creates unnecessary ledger activity, is fragile under partial failure, and encourages using the ledger as a message bus.

**Classification:** Harmful if generalized · **AKA:** Send Ordering Signal

**How it works:** The sender publishes several sends in sequence. Observers interpret the ordering, amount sequence, or destination sequence as an encoded message.

**Risks:**
- Ordering assumptions may differ across observers and indexers.
- Partial failure corrupts the message.
- Multiple devices sharing a key can race for the next block position. Incoming payments to the sender's own account mutate its balance between sends, altering block ordering.
- Creates unnecessary ledger activity.

**Verdict:** Do not use multi-send ordering as a general-purpose encoding mechanism.

### Dust Spray Signaling

Sending tiny amounts to many accounts at once — a "dust spray" — forces those accounts to deal with unsolicited pending receivables. It's spam. It clutters wallets, enables tracking, and can deanonymize users when they sweep the dust into their main accounts.

**Classification:** Harmful if generalized · **AKA:** Dust Spam

**How it works:** The sender sends tiny amounts to many accounts. The existence, amount, timing, or source of the sends is interpreted as a signal.

**Risks:**
- Creates unwanted pending receivables that clutter wallets and histories.
- Enables spam, harassment, and tracking.
- When recipients sweep the dust into their main accounts, it links those accounts on-chain (see [Account Sweep Linkage](#account-sweep-linkage)).
- Burdens wallets, indexers, explorers, and users.

**Verdict:** Do not use dust spray for notifications, messaging, marketing, tracking, or application state.

### Arbitrary Data Encoding

Nano's block lattice is not a data storage system. Some applications try to encode arbitrary data through combinations of amounts, addresses, representative fields, work values, account creation patterns, and transaction ordering. This creates ledger bloat, degrades infrastructure, and produces encoding that's fragile, low-capacity, and meaningless without custom decoders.

**Classification:** Harmful if generalized · **AKA:** Ledger Data Storage

**How it works:** The application encodes data through combinations of block fields, transaction patterns, and account creation. The data is visible to observers who know the encoding scheme.

**Risks:**
- Creates permanent ledger growth and infrastructure burden.
- Degrades wallet, explorer, and indexer usability.
- Data capacity is extremely low and encoding is fragile.
- Application meaning is lost without the custom decoder.

**Verdict:** Do not use the block lattice as a data storage layer. Store metadata off-chain and reference it via cryptographic commitments.

### Work-field / Overwork Signaling

Each Nano block includes a proof-of-work value. Some applications try to encode meaning in that value — selecting specific work values or computing work beyond what's required. This wastes computation, has extremely low data capacity, and critically: the work value is not part of the block hash. It can be recomputed by nodes or wallets when republishing, destroying any "signal" placed in it.

**Classification:** Harmful if generalized · **AKA:** Proof-of-work Tagging

**How it works:** The sender selects a specific work value, or computes unusually high work, and observers interpret the work pattern as data.

**Risks:**
- Wastes computation for negligible data capacity.
- The work value has no cryptographic binding to the block — it can be recomputed at any time.
- Poor wallet and tooling support.
- Observers may ignore or discard the distinction.

**Verdict:** Do not use work values as a signaling channel.

## Payment Correlation Guidance

This section is the normative summary referenced by the triage list under Payment Correlation Patterns.

For ordinary payment correlation, applications SHOULD prefer:

1. [Off-chain Payment References](#off-chain-payment-reference), especially when rich metadata or authentication is required.
2. [Invoice Deposit Accounts](#invoice-deposit-account), especially when the receiver can generate unique destination accounts.
3. [Customer Deposit Accounts](#customer-deposit-account), when repeated deposits are needed and address reuse is acceptable.

Applications MAY use [Source Account Attribution](#source-account-attribution) only after authenticating or registering the payer's source account, and only when the payer is not expected to send from custodial or shared infrastructure.

Applications SHOULD treat [Raw Dust Tagging](#raw-dust-tagging) as a controlled integration technique, not as a general wallet-compatible convention.

Applications SHOULD NOT use [Representative Tagging](#representative-tagging), [Representative as dApp Tag](#representative-as-dapp-tag), [Representative Change Pulse](#representative-change-pulse), [Pending Receivable Markers](#pending-receivable-marker), [Burn Signals](#burn-signal), [Dust Spray Signaling](#dust-spray-signaling), [Address Payload Encoding](#address-payload-encoding), [Multi-send Ordering Signals](#multi-send-ordering-signal), or [Arbitrary Data Encoding](#arbitrary-data-encoding) for ordinary invoice correlation.

While correlation conventions map payments to invoices, secure transaction processing requires rigorous software engineering guidelines. Developers and exchanges building payment integration systems SHOULD consult [ORIS-008 (Nano Integration and Reliable Payment Processing Standard)](./ORIS-008.md) for normative requirements on transaction isolation, idempotency constraints, database concurrency, automated reconciliation audits, and payment lifecycle edge-case handling (underpayments, overpayments, duplicate payments, indexer lag).

## Glossary

Definitions are intentionally brief; consult current Nano protocol documentation for authoritative definitions.

- Account chain: The strictly serial sequence of blocks belonging to a single Nano account. Each account maintains its own chain.
- Application-level meaning: Meaning assigned by software above the protocol layer.
- Archival node: A node configuration that retains full block history for all account chains, rather than pruning to frontiers only.
- Block lattice: The overall data structure formed by all individual account chains in Nano.
- Change block: A block that changes an account's representative without transferring value.
- Dust: A negligibly small amount of Nano (typically less than ~0.000001 XNO). The exact threshold is application-dependent.
- Frontier: The latest confirmed block on a given account chain. Many node configurations retain only the frontier and discard or prune older block bodies.
- Nano block fields: Each block contains `account`, `previous`, `representative`, `balance`, `link`, `work`, and `signature`. There is no generic data, memo, or payload field.
- Off-chain: Data exchanged outside the Nano P2P network.
- Open block: The first block on an account chain, which receives the account's initial incoming send and establishes its first representative.
- Open Representative Voting (ORV): Nano's consensus mechanism, in which representatives weighted by delegated balance vote to confirm blocks.
- Raw: The smallest indivisible Nano unit, with $1\ \text{XNO} = 10^{30}\ \text{raw}$.
- Receivable (pending): An incoming send that has been published by the sender but not yet acknowledged by a receive block on the destination account.
- Receive block: A block that claims a pending send and credits the balance to the receiving account.
- Representative: The voting account designated by an account holder; representatives participate in Open Representative Voting on behalf of their delegators.
- Send block: A block that debits a balance from an account and creates a pending receivable on a destination account.
- Signal: A ledger event or state interpreted by an application.
- XNO: The Nano user-facing unit.

Some patterns include optional subsections: **Network-health considerations** describes impact on Nano consensus or infrastructure; **Classification note** clarifies edge cases or rationale for the assigned risk level.
