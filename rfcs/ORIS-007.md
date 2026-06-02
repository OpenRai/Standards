```
OpenRai Initiative Standard: 007
```

## Nano Application-Level Metadata, Correlation, and Signaling Patterns

> Status: Draft
> Category: Informational / Application Guidance

### Abstract

Nano has a minimal block-lattice design with no native memo, smart-contract, or arbitrary-data fields. To correlate payments, pass metadata, or signal state, developers have repeatedly found ways to assign application-level meaning to ordinary ledger behavior. 

This document catalogs and classifies these signaling and correlation patterns to establish a **shared vocabulary** and document **common failure modes**—guiding developers toward safer, more network-friendly integrations.

Inclusion of a pattern here does not imply endorsement, protocol support, or wallet compatibility.

---

### Conventions

Addresses use the `nano_` prefix. Amounts are given in `XNO` (the user-facing unit) or `raw` (the smallest indivisible unit, $1\ \text{XNO} = 10^{30}\ \text{raw}$). See the [Glossary](#glossary) for block-level terms.

---

### Risk Classification System

This catalog uses broad **risk** and **compatibility** labels to describe how each pattern interacts with general wallets, user expectations, privacy, infrastructure, and network health:

*   **Low-Risk**: Preserves ordinary payment semantics and imposes no unusual burden on wallets, representatives, or indexers.
*   **Context-Dependent**: Workable in bounded, application-controlled environments, but relies on specific assumptions (wallet precision, user consent, scale) that fail in general use.
*   **Harmful if Generalized**: High risk of user confusion, privacy loss, wallet misbehavior, ledger bloat, or excessive indexing overhead if used broadly.

---

### Payment Correlation Patterns

Nano has no memo field, so correlating an incoming payment to an invoice, order, or session is the most common signaling challenge developers face. The patterns below are ordered by preference.

1. If payment context can be exchanged off-chain, use an [**Off-chain Payment Reference**](#off-chain-payment-reference).
2. If the receiver can generate a unique destination account, use an [**Invoice Deposit Account**](#invoice-deposit-account).
3. If the payer has an authenticated source account, [**Source Account Attribution**](#source-account-attribution) may be acceptable.
4. If both sides use controlled wallet code or [`nano:` URIs](https://docs.nano.org/integration-guides/the-basics/#uri-and-qr-code-standards) with embedded `amount`, [**Raw Dust Tagging**](#raw-dust-tagging) may work, but remains fragile.
5. Avoid representative-field signaling, arbitrary address payloads, burn signals, and unsolicited dust for payment correlation.

#### Off-chain Payment Reference

Nano has no memo field, so there's no way to attach an invoice number to a payment on-chain. The simplest workaround: don't try. Instead, generate a payment request off-chain — with a destination account, amount, invoice ID, and optional expiration — and have the payer send to that request. Match the incoming payment by destination and amount. If you need to prove the request came from you, sign it.

**Classification:** Low-risk · **AKA:** Signed Payment Reference, External Invoice Reference

**How it works:** The application generates a payment context (destination, amount, invoice ID, nonce, expiration) and delivers it to the payer off-chain. The payer sends Nano to the specified destination. The application matches the incoming payment by destination and amount, then retrieves the full invoice context from its own database.

**Risks:**
- If the reference is not signed, a man-in-the-middle can substitute their own destination account.
- If nonce and expiration are omitted, the same reference can be replayed.
- The off-chain database is the single source of truth — if it's lost, payment-to-invoice mapping is unrecoverable.

**Verdict:** Use this as the default approach for invoice correlation. Always sign the reference and include nonce, amount, destination, and expiration.

#### Block Hash Commitment

Every confirmed Nano block has a unique hash. Storing that hash off-chain gives you a compact, immutable reference to a specific payment or account-chain event — useful for receipts, audit logs, and reconciliation.

**Classification:** Low-risk · **AKA:** Block Reference, Hash Anchor

**How it works:** After a payment confirms, the application stores the block hash in its own database or communicates it off-chain. The hash identifies the exact ledger event.

**Risks:**
- Default node configurations retain only the frontier of each account chain. Intermediate block bodies may become unavailable from non-archival nodes shortly after confirmation.
- A block hash identifies a block but carries no application meaning — the metadata must be preserved separately.

**Verdict:** Safe and useful as an off-chain reference. Document your archival assumptions if you need to resolve historical block bodies.

#### Invoice Deposit Account

When you can't coordinate a payment reference off-chain, or when you want the ledger itself to carry the correlation, generate a fresh Nano account for each invoice. Any payment to that account is payment for that invoice — no ambiguity, no amount-matching, no memo field needed.

**Classification:** Low-risk · **AKA:** Per-invoice Account, One-time Destination Account

**How it works:** The receiver derives or generates a unique Nano address for a specific invoice, order, or session. The payer sends to that address. The application monitors the address for incoming payments and attributes them to the corresponding invoice.

**Risks:**
- Each invoice creates a new account that must be monitored and eventually swept. Unbounded account creation burdens wallet scanning and application state.
- Reusing a supposedly one-time account creates ambiguity about which invoice was paid.
- Sweeping funds from many invoice accounts into a hot wallet links them on-chain; see [Account Sweep Linkage](#account-sweep-linkage).
- Recovery requires either deterministic derivation or stored metadata mapping accounts to invoices.
- Generating large numbers of unused accounts burdens node scanning. Keep account generation bounded.

**Verdict:** One of the simplest and most reliable correlation patterns. Use it when you can generate and monitor unique destinations.

#### Customer Deposit Account

Some services need to identify repeat deposits from the same user over time. Instead of generating a new account per invoice, assign each user a single deposit address. Payments to that address are always attributed to that user.

**Classification:** Low-risk · **AKA:** Per-user Account, User Deposit Account

**How it works:** The service assigns one Nano address to each user. The user sends to that address whenever they want to deposit. The application monitors the address and credits the corresponding user.

**Risks:**
- All of a user's deposits are linked on the public ledger. Anyone who knows the address can see the user's deposit history.
- Anyone who knows the address can send funds to it, creating attribution problems.
- Payments from exchanges or custodial wallets may come from a shared hot wallet, requiring additional attribution logic.
- If the address leaks or the mapping database is compromised, historical activity is exposed.

**Verdict:** Simple and effective for repeated deposits, but offers weaker privacy than per-invoice accounts. Use [Invoice Deposit Accounts](#invoice-deposit-account) when unlinkability matters. Do not use a stable deposit address as a reusable public identity without explicit consent.

#### Account Sweep Linkage

When you consolidate funds from many invoice or user deposit accounts into a single hot wallet, the sweep transactions publicly link all those accounts to one controller. This retroactively defeats the unlinkability you gained by using per-invoice accounts in the first place.

**Classification:** Harmful if generalized · **AKA:** Sweep Correlation

**How it works:** The service periodically transfers balances from many deposit accounts to one or a few destination accounts. The sweep transactions are visible on-chain and link all source accounts to the same entity.

**Risks:**
- Retroactively links all swept accounts on a fully transparent ledger.
- Reveals aggregate business volume and timing to any observer.
- Combined with timing analysis, can deanonymize individual customers.

This is not a technique to adopt — it is an unavoidable consequence of consolidating per-invoice accounts that applications must actively mitigate.

**Verdict:** If you consolidate funds, minimize linkability. Options: batch consolidations, use multiple sweep destinations, separate user-facing deposit accounts from internal accounting.

#### Source Account Attribution

If you know which Nano account a user controls, you can attribute incoming payments by watching where the funds come from. The user registers their source account with your application once; subsequent payments from that account are attributed to them.

**Classification:** Context-dependent · **AKA:** Sender Account Attribution

**How it works:** The payer registers or authenticates a Nano account with the application. Later, when funds arrive from that account, the application attributes the payment to the registered payer.

**Risks:**
- Exchange and custodial withdrawals come from shared hot wallets, not the user's own account. Attribution against a shared source is meaningless and may be actively misleading.
- Users may change wallets, rotate accounts, or have their accounts swept — breaking attribution silently.
- All payments from the same source account are linkable on the public ledger.
- Without explicit registration and authentication, a source account does not identify a person.

**Verdict:** Only use when the source account is explicitly registered and authenticated. Never assume a source account identifies a human — most exchange withdrawals come from shared wallets.

#### Reply-with-Send Receipt

When your application receives a payment, you might want to send a small amount back to the payer as an on-chain "receipt." The problem: you're sending to the source account of the incoming payment, which may be a custodial hot wallet, an exchange, or a shared service — not the actual payer.

**Classification:** Context-dependent · **AKA:** Echo Send, Send-back Receipt

**How it works:** The application receives a payment, identifies the source account, and sends a small amount back to that account as an on-chain confirmation.

**Risks:**
- Inherits all failure modes of [Source Account Attribution](#source-account-attribution): the source account may not be the payer.
- Creates unsolicited receivables for the source-account controller.
- May be misinterpreted as a refund or a fresh payment.
- Inherits the auto-receive problems of [Receive Acknowledgement](#receive-acknowledgement) and [Pending Receivable Marker](#pending-receivable-marker).

**Verdict:** Do not use as a default acknowledgement mechanism. If on-chain acknowledgement is required, restrict to explicitly registered source accounts. Prefer off-chain signed receipts.

#### Raw Dust Tagging

Nano's raw unit is incredibly small ($1\ \text{XNO} = 10^{30}\ \text{raw}$). By varying the last few digits of a payment amount, you can encode a small tag — an invoice number, a discriminator, a state value — directly in the amount field. The receiver reads the suffix and interprets it.

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

**Verdict:** Viable only when both sides use application-controlled wallet code and exact raw amounts are preserved. For most invoice correlation, prefer [Invoice Deposit Accounts](#invoice-deposit-account) or [Off-chain Payment References](#off-chain-payment-reference). Do not use dust-level amount tags as a public messaging layer.

### State Signaling Patterns

These patterns use ledger events — receive blocks, open blocks, balance changes, frontier updates — as application-level signals. They all share a common risk: wallet behavior (auto-receive, batching, delay) can make the signal meaningless or involuntary.

#### Receive Acknowledgement

In Nano, incoming funds sit as "pending" until the receiver publishes a receive block. Some applications interpret that receive block as more than a balance update — as a signal that the receiver has accepted a ticket, claimed a deposit, or committed to something. This only works if the receiving account is application-controlled and the wallet's receive behavior is predictable.

**Classification:** Context-dependent · **AKA:** Receive-as-Commit, Claim Signal

**How it works:** The application sends funds to a dedicated account it controls. It monitors for the receive block and treats it as the "acceptance" event in its state machine.

**Risks:**
- Most user wallets auto-receive, so a receive block on a normal account means nothing about user intent.
- Even application-controlled wallets may delay or batch receives, making timing unreliable.
- A pending send received hours later can trigger a stale state transition.
- Auto-receive can collapse this pattern into a [Pending Receivable Marker](#pending-receivable-marker) — the receive happens without intent, making the signal meaningless.

**Verdict:** Only use with dedicated application-controlled accounts where receive behavior is deterministic. Never interpret a normal user's receive as consent.

#### Pending Receivable Marker

You can send a small amount to someone's account and leave it pending — unreceived. The idea is that the existence of the pending amount itself is the signal, and the recipient doesn't need to do anything. In practice, this is spam.

**Classification:** Harmful if generalized · **AKA:** Pending-as-Message, Receivable Notification

**How it works:** The sender sends a tiny amount to a recipient account and does not require (or expect) a receive block. Indexers and the recipient's wallet can see the pending amount.

**Risks:**
- Creates unwanted receivables that clutter wallets and account state.
- Wallets with auto-receive will convert the pending amount into a receive block, destroying the intended "unreceived" signal.
- Easily abused for spam, harassment, and tracking.
- Does not convey consent or awareness — the recipient never agreed to receive a signal.

**Verdict:** Do not use. This pattern pushes unsolicited state onto accounts that didn't opt in.

#### Open Block as Registration

The first block on a Nano account is the "open" block. Some applications use this as a registration signal: if a derived account publishes an open block, the application interprets it as the user activating or enrolling. The catch: an open block requires incoming funds, so someone has to send to the account first — and anyone can do that, forcing registration against the user's intent.

**Classification:** Context-dependent · **AKA:** Account Activation Signal

**How it works:** The application derives a deterministic account for the user (e.g., at a specific HD index). When the user (or the application) funds that account and the open block is published, the application treats it as registration.

**Risks:**
- Anyone who can send to the deterministic address can force an open block, triggering registration against the user's intent.
- Sequential derivation indexes leak business volume (e.g., order count).
- Recovery depends on the same derivation scheme and gap-limit assumptions.
- Wallet account-discovery behavior varies; the open block may not surface in time.

**Verdict:** Only use when both the derivation and funding flow are application-controlled. Always pair with off-chain consent to prevent involuntary registration.

#### Balance State Signal

Some applications encode state directly in an account's balance — specific balance values or ranges correspond to application states. This is extremely fragile: any send or receive changes the balance, so a single unwanted incoming payment irreversibly corrupts the encoded state.

**Classification:** Context-dependent · **AKA:** Balance-as-State

**How it works:** The application controls an account and sets its balance to a specific value that encodes application state. Observers read the balance and interpret it.

**Risks:**
- Any incoming payment — even an unwanted one — changes the balance and corrupts the state irreversibly.
- Requires exact balance tracking and confirmation at every step.
- Wallet operations may alter balances in unexpected ways.

**Verdict:** Only viable for fully application-controlled accounts where every send and receive is audited. Do not use with user accounts.

#### Frontier Signal

The frontier is the latest block on an account chain. Some applications use it as a publication pointer: each new block is a new "version" of the application state, and observers watch the frontier for updates. The actual metadata lives off-chain; the frontier just anchors it.

**Classification:** Context-dependent · **AKA:** Head Block Signal

**How it works:** The application publishes blocks on a dedicated account chain. Each new block references the current off-chain state (e.g., by including a hash of the metadata). Observers track the frontier to discover the latest state.

**Risks:**
- Unrelated wallet activity on the same account changes the frontier, confusing observers.
- High-frequency updates create unnecessary ledger activity.
- Historical interpretation requires archival nodes or indexers.
- The block itself carries only ordinary Nano fields — the actual data is off-chain.

**Verdict:** Acceptable for low-frequency, application-controlled anchoring on a dedicated account. Do not use ordinary user account frontiers as a messaging channel.

### Representative-Based Patterns

#### Representative Tagging

Nano accounts have a representative field used for voting. Some applications abuse this field as a metadata slot — setting the representative to a specific account that encodes application-level meaning. This is harmful because the representative field has governance meaning, and overloading it confuses wallets, users, and vote-weight distribution.

**Classification:** Harmful if generalized · **AKA:** Rep-as-Message

**How it works:** The application sets the account representative to an account chosen to encode a tag, state value, or pointer. Observers interpret the representative as application data.

**Risks:**
- Misrepresents the account's governance intent — wallets and users may be confused about the representative choice.
- Wallets may warn, hide, restrict, or auto-manage representative changes.
- Repeated changes create unnecessary account-chain activity.
- Representative accounts used as tags may be mistaken for legitimate representatives.

**Network-health considerations:** Application-level overloading of the representative field creates ecosystem confusion around governance, even when consensus remains valid.

**Verdict:** Do not use the representative field as metadata, a memo substitute, or an invoice tag.

#### Representative as dApp Tag

A variant of [Representative Tagging](#representative-tagging) where a project asks users to set their representative to a project-controlled account as a signal of opt-in or affiliation. The project then enumerates delegators to determine the participant set. This concentrates vote weight on a non-consensus operator and pressures users to choose between governance hygiene and application participation.

**Classification:** Harmful if generalized · **AKA:** Project Rep Opt-in, Affiliation Rep

**How it works:** The project publishes a representative address. Users change their representative to that address to indicate participation. The project scans delegator lists to build the participant set.

**Risks:**
- Concentrates vote weight on an operator that may not be a competent or trustworthy representative.
- Pressures users to choose between good governance and application eligibility.
- Lookalike representative accounts can spoof the opt-in signal.
- Scales poorly: if many applications adopt this, the representative field becomes meaningless.

**Verdict:** Do not use representative selection as an opt-in mechanism. Use off-chain registration, signed messages, or token-style opt-in on a dedicated account chain.

#### Representative Change Pulse

Some applications signal events by changing the account's representative — toggling between known representatives to create a visible on-chain "pulse." This creates unnecessary representative churn, clutters wallet history, and produces ledger activity solely for signaling.

**Classification:** Harmful if generalized · **AKA:** Rep Churn Signal

**How it works:** The application changes the account's representative, possibly back and forth between known addresses. Observers treat the change event as a signal.

**Risks:**
- Creates unnecessary representative churn that confuses wallet history and vote-weight tracking.
- Produces ledger activity solely for signaling — no value transfer, no governance intent.
- Can be abused as a low-capacity message channel.

**Verdict:** Do not use representative-change events as signals, pulses, or messages.

### Address and Data Encoding

These patterns try to encode application-level meaning in addresses, amounts, timing, proof-of-work, or transaction ordering. None of them are recommended for general use.

#### Address Payload Encoding

Nano addresses are derived from public keys. Some applications try to encode data into the address itself — by searching for vanity addresses whose characters spell out a payload, or by constructing addresses from arbitrary bytes. This is fragile, low-capacity, and risks sending funds to addresses with no known private key.

**Classification:** Harmful if generalized · **AKA:** Address-as-Data

**How it works:** The application generates or selects destination accounts whose address characters encode application-level data. The encoded value is visible in the address.

**Risks:**
- Constructing addresses from arbitrary payload bytes almost certainly produces an address with no known private key. Funds sent there are permanently lost.
- Generating meaningful vanity addresses is computationally expensive.
- Users may mistake encoded addresses for ordinary payment addresses.
- Encourages treating addresses as a data store rather than as spendable accounts.

**Verdict:** Do not encode arbitrary data into addresses. If an address is used, it must correspond to a spendable account controlled by the intended receiver.

#### Vanity Prefix as Identity

A recognizable address prefix (e.g., `nano_1project...`) gives users a visual cue that an address belongs to a specific organization. Unlike [Address Payload Encoding](#address-payload-encoding), the address is a real spendable account — the vanity is just branding. The risk: adversaries can generate lookalike prefixes for phishing.

**Classification:** Context-dependent · **AKA:** Branded Address

**How it works:** The operator generates an account whose address contains a recognizable prefix or substring. The address is published through authenticated channels as the canonical destination.

**Risks:**
- Lookalike addresses are a well-known phishing vector. A prefix like `nano_1proj` can be approximated with a different suffix.
- Users may rely on prefix recognition and skip full-address verification.
- Wallets that truncate addresses may hide the discriminating portion.

**Verdict:** Acceptable for branding when published through authenticated channels. Never rely on vanity prefixes as a substitute for cryptographic authentication of payment destinations.

#### Burn Signal

Sending funds to an address with no known private key destroys them — provably, irreversibly (as far as anyone knows). Some applications use this as proof of commitment or sacrifice. The problem: you can never prove no private key exists, and the funds are genuinely wasted.

**Classification:** Harmful if generalized · **AKA:** Proof-of-Burn Signal

**How it works:** The sender sends Nano to an unspendable address. Observers interpret the payment as proof of intentional value destruction.

**Risks:**
- Wastes funds.
- It's impossible to prove that no private key exists for a given address.
- Encourages value destruction as a signaling mechanism.
- Can confuse users and explorers.

**Verdict:** Do not use burn payments as routine signals. If proof of commitment is needed, use signed off-chain commitments or ordinary payments to controlled accounts.

#### Account Index Signal

If you use deterministic key derivation (like HD wallets), the index number itself can carry meaning — account type, invoice sequence, role. This is convenient but leaks information: sequential indexes reveal business volume, and gaps break account discovery.

**Classification:** Context-dependent · **AKA:** Derivation Index Signal

**How it works:** The wallet derives accounts at specific indexes, and the index number maps to application-level meaning (e.g., index 0 = main account, index 1–1000 = invoice pool).

**Risks:**
- Sequential indexes leak business volume (e.g., order count, user signups).
- Gaps in the index sequence break automatic account discovery.
- Different wallets use different derivation schemes — recovery depends on documenting the exact scheme.
- Publishing extended public keys exposes future addresses.

**Verdict:** Use internally if needed, but document derivation paths, gap limits, and privacy consequences. Do not expose sensitive derivation structure.

#### Timing Signal

Nano blocks don't carry timestamps. The observed confirmation time depends on network propagation, node arrival order, and vote duration — two observers may disagree on when the same block was confirmed. Encoding meaning in timing or ordering between blocks is fragile and unauditable.

**Classification:** Context-dependent · **AKA:** Temporal Encoding

**How it works:** The application assigns meaning to when blocks are published, confirmed, or observed relative to each other.

**Risks:**
- No authoritative timestamp exists — observation time differs across nodes, wallets, and indexers.
- Network delays, wallet batching, and user behavior introduce unpredictable timing variation.
- Timing signals are fragile and hard to audit.

**Verdict:** Do not rely on timing as a primary signal. Include timestamps and expirations in off-chain signed metadata instead.

#### Multi-send Ordering Signal

Some applications encode data in the sequence of multiple sends — the order, amounts, or destinations carry meaning. This creates unnecessary ledger activity, is fragile under partial failure, and encourages using the ledger as a message bus.

**Classification:** Harmful if generalized · **AKA:** Send Ordering Signal

**How it works:** The sender publishes several sends in sequence. Observers interpret the ordering, amount sequence, or destination sequence as an encoded message.

**Risks:**
- Ordering assumptions may differ across observers and indexers.
- Partial failure corrupts the message.
- Multiple devices sharing a key can race for the next block position. Incoming payments to the sender's own account mutate its balance between sends, altering block ordering.
- Creates unnecessary ledger activity.

**Verdict:** Do not use multi-send ordering as a general-purpose encoding mechanism.

#### Dust Spray Signaling

Sending tiny amounts to many accounts at once — a "dust spray" — forces those accounts to deal with unsolicited pending receivables. It's spam. It clutters wallets, enables tracking, and can deanonymize users when they sweep the dust into their main accounts.

**Classification:** Harmful if generalized · **AKA:** Dust Spam

**How it works:** The sender sends tiny amounts to many accounts. The existence, amount, timing, or source of the sends is interpreted as a signal.

**Risks:**
- Creates unwanted pending receivables that clutter wallets and histories.
- Enables spam, harassment, and tracking.
- When recipients sweep the dust into their main accounts, it links those accounts on-chain (see [Account Sweep Linkage](#account-sweep-linkage)).
- Burdens wallets, indexers, explorers, and users.

**Verdict:** Do not use dust spray for notifications, messaging, marketing, tracking, or application state.

#### Arbitrary Data Encoding

Nano's block lattice is not a data storage system. Some applications try to encode arbitrary data through combinations of amounts, addresses, representative fields, work values, account creation patterns, and transaction ordering. This creates ledger bloat, degrades infrastructure, and produces encoding that's fragile, low-capacity, and meaningless without custom decoders.

**Classification:** Harmful if generalized · **AKA:** Ledger Data Storage

**How it works:** The application encodes data through combinations of block fields, transaction patterns, and account creation. The data is visible to observers who know the encoding scheme.

**Risks:**
- Creates permanent ledger growth and infrastructure burden.
- Degrades wallet, explorer, and indexer usability.
- Data capacity is extremely low and encoding is fragile.
- Application meaning is lost without the custom decoder.

**Verdict:** Do not use the block lattice as a data storage layer. Store metadata off-chain and reference it via cryptographic commitments.

#### Work-field / Overwork Signaling

Each Nano block includes a proof-of-work value. Some applications try to encode meaning in that value — selecting specific work values or computing work beyond what's required. This wastes computation, has extremely low data capacity, and critically: the work value is not part of the block hash. It can be recomputed by nodes or wallets when republishing, destroying any "signal" placed in it.

**Classification:** Harmful if generalized · **AKA:** Proof-of-work Tagging

**How it works:** The sender selects a specific work value, or computes unusually high work, and observers interpret the work pattern as data.

**Risks:**
- Wastes computation for negligible data capacity.
- The work value has no cryptographic binding to the block — it can be recomputed at any time.
- Poor wallet and tooling support.
- Observers may ignore or discard the distinction.

**Verdict:** Do not use work values as a signaling channel.

### Payment Correlation Guidance

This section is the normative summary referenced by the triage list under Payment Correlation Patterns.

For ordinary payment correlation, applications SHOULD prefer:

1. [Off-chain Payment References](#off-chain-payment-reference), especially when rich metadata or authentication is required.
2. [Invoice Deposit Accounts](#invoice-deposit-account), especially when the receiver can generate unique destination accounts.
3. [Customer Deposit Accounts](#customer-deposit-account), when repeated deposits are needed and address reuse is acceptable.

Applications MAY use [Source Account Attribution](#source-account-attribution) only after authenticating or registering the payer's source account, and only when the payer is not expected to send from custodial or shared infrastructure.

Applications SHOULD treat [Raw Dust Tagging](#raw-dust-tagging) as a controlled integration technique, not as a general wallet-compatible convention.

Applications SHOULD NOT use [Representative Tagging](#representative-tagging), [Representative as dApp Tag](#representative-as-dapp-tag), [Representative Change Pulse](#representative-change-pulse), [Pending Receivable Markers](#pending-receivable-marker), [Burn Signals](#burn-signal), [Dust Spray Signaling](#dust-spray-signaling), [Address Payload Encoding](#address-payload-encoding), [Multi-send Ordering Signals](#multi-send-ordering-signal), or [Arbitrary Data Encoding](#arbitrary-data-encoding) for ordinary invoice correlation.

While correlation conventions map payments to invoices, secure transaction processing requires rigorous software engineering guidelines. Developers and exchanges building payment integration systems SHOULD consult [ORIS-008 (Nano Integration and Reliable Payment Processing Standard)](./ORIS-008.md) for normative requirements on transaction isolation, idempotency constraints, database concurrency, automated reconciliation audits, and payment lifecycle edge-case handling (underpayments, overpayments, duplicate payments, indexer lag).

### Glossary

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
