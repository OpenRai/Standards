```
OpenRai Initiative Standard: 007
```

## Nano Application-Level Metadata, Correlation, and Signaling Patterns

> Status: Draft
> Category: Informational / Application Guidance

### Abstract

Nano has a minimal block-lattice design with no native memo, smart-contract, or arbitrary-data fields. To correlate payments, pass metadata, or signal state, developers historically and continuously reach for "common hacks" that assign application-level meaning to ordinary ledger behavior. 

This document catalogs and classifies these signaling and correlation patterns to establish a **shared vocabulary** and document **common failure modes**—guiding developers toward safer, more network-friendly integrations.

Inclusion of a pattern here does not imply endorsement, protocol support, or wallet compatibility.

---

### Conventions & Terminology

*   `nano_`: A standard Nano account address.
*   `raw`: The smallest indivisible Nano unit ($1\ \text{XNO} = 10^{30}\ \text{raw}$).
*   `XNO`: The user-facing unit of account.
*   `application-level meaning`: Meaning assigned by software above the protocol layer.
*   `signal`: A ledger event or state interpreted by an application.
*   `off-chain`: Data exchanged outside the Nano P2P network.

---

### Risk Classification System

This catalog uses broad **risk** and **compatibility** labels to describe how each pattern interacts with general wallets, user expectations, privacy, infrastructure, and network health:

*   **Low-Risk**: Preserves ordinary payment semantics and imposes no unusual burden on wallets, representatives, or indexers.
*   **Context-Dependent**: Workable in bounded, application-controlled environments, but relies on specific assumptions (wallet precision, user consent, scale) that fail in general use.
*   **Harmful if Generalized**: High risk of user confusion, privacy loss, wallet misbehavior, ledger bloat, or excessive indexing overhead if used broadly.

---

### Payment Correlation Patterns

Payment correlation is the most common reason developers look for Nano signaling techniques. Since Nano has no native memo field, applications often need to determine which invoice, order, customer, session, or application event a payment belongs to.

Recommended triage:

1. If the receiver can generate a unique destination account, use an Invoice Deposit Account.
2. If payment context can be exchanged off-chain, use an Off-chain Payment Reference.
3. If the payer has an authenticated source account, Source Account Attribution may be acceptable.
4. If both sides use controlled application-specific wallet code, Raw Dust Tagging may be possible, but remains fragile.
5. Avoid representative-field signaling, arbitrary address payloads, burn signals, and unsolicited dust for payment correlation.

The Payment Correlation Guidance section near the end of this document provides the normative summary; the list above is intended as a quick triage when reading the catalogue.

#### Off-chain Payment Reference

Classification: Low-risk convention

Other names:

- Out-of-band Payment Reference
- OOB Reference
- Signed Payment Reference
- External Invoice Reference

Problem addressed:

An application needs to associate a Nano payment with an invoice, order, session, account, or other off-chain business object.

Mechanism:

The application exchanges payment context off-chain. The context may include a destination account, amount, invoice identifier, nonce, expiration time, payer identity, or application-specific terms.

If authenticity is required, the context can be signed by the payer, receiver, or both.

Useful properties:

- Preserves ordinary Nano payment semantics.
- Does not require memo fields or ledger overloading.
- Can carry rich structured metadata.
- Can include replay protection, expiration, and audience binding.
- Does not require unusual wallet behavior if the payment itself is ordinary.

Failure modes:

- Off-chain metadata can be lost if the application does not persist it.
- Unsigned references may be spoofed or replayed.
- Payment and metadata may become inconsistent if not bound carefully.
- Reconstruction of full application context requires access to the off-chain database.

Recommendation:

Applications SHOULD prefer off-chain payment references for most payment-correlation and metadata needs. When security matters, the reference SHOULD include nonce, amount, destination, expiration, and application audience, and SHOULD be authenticated with an appropriate signature scheme.

#### Invoice Deposit Account

Classification: Low-risk convention

Other names:

- Unique Deposit Account
- Per-invoice Account
- Payment Request Account
- One-time Destination Account

Problem addressed:

A receiver needs to identify which invoice or payment request a Nano payment satisfies without relying on memos or amount tags.

Mechanism:

The receiver generates a unique Nano destination account for a specific invoice, order, session, or payment request. Any payment to that account is interpreted in the context of that invoice.

Useful properties:

- Preserves ordinary payment semantics.
- Works with normal wallets.
- Does not require exact amount tagging.
- Allows simple indexer logic.
- Avoids address reuse for distinct invoices.
- Can be combined with off-chain invoices and signed references.

Failure modes:

- Requires account generation and monitoring infrastructure.
- Unbounded account creation can burden wallet scanning and application state.
- Reuse of a supposedly unique invoice account can create ambiguity.
- Recovery requires deterministic derivation, stored metadata, or both.
- Sweeping funds may link invoice accounts together; see Account Sweep Linkage.

Network-health considerations:

Invoice accounts are generally safe when bounded and application-controlled. Applications SHOULD avoid generating large numbers of unused accounts or requiring broad ecosystem scanning of arbitrary derivation paths.

Recommendation:

Applications SHOULD use Invoice Deposit Accounts when they can generate and monitor unique destination accounts. This is one of the simplest and least surprising Nano payment-correlation patterns.

#### Customer Deposit Account

Classification: Low-risk convention

Other names:

- User Deposit Account
- Per-customer Account
- Static Customer Address

Problem addressed:

A service wants to identify payments from a known customer or account over time.

Mechanism:

The service assigns one Nano destination account to a customer. Payments to that account are attributed to the customer.

Useful properties:

- Works with ordinary wallets.
- Simple for repeated deposits.
- Does not require exact amounts or source-account assumptions.
- Easy to index.

Failure modes:

- Address reuse links the customer's payments.
- Anyone who knows the address may send funds to it.
- Payments from exchanges or custodians may still require additional attribution.
- Customer privacy is weaker than with one-time deposit accounts.
- Account compromise or database leakage can reveal historical customer activity.

Classification note:

This pattern becomes context-dependent when privacy and address reuse matter. Do not use a stable customer deposit account as a reusable public identity without explicit consent and linkability analysis.

Recommendation:

Customer Deposit Accounts are operationally simple, but applications SHOULD prefer Invoice Deposit Accounts when payment-level unlinkability or precise invoice correlation matters.

#### Source Account Attribution

Classification: Context-dependent convention

Other names:

- Sender Account Attribution
- Payer Address Identification
- Registered Source Account

Problem addressed:

A receiver wants to identify the payer based on the source account that sent funds.

Mechanism:

The payer first registers or authenticates a Nano account with the application. Later payments from that account are attributed to the registered payer.

Useful properties:

- Does not require unique destination accounts for every payment.
- Works when the payer controls the source account.
- Can be combined with off-chain signatures proving control of the source account.

Failure modes:

- Exchange and custodial withdrawals may originate from accounts not controlled by the user.
- Custodial hot wallets, tip bots, and similar shared-source services route many users through a single source account; attribution against that account is meaningless and may be actively misleading.
- Users may change wallets or source accounts.
- Source accounts may be shared, rotated, or swept.
- Observers can link all attributed payments from the same source.
- Attribution is unsafe unless the source account was explicitly registered or authenticated.

Classification note:

This pattern is context-dependent because its safety depends entirely on the assumption that the source account is controlled by, and uniquely identifies, the registered payer. That assumption fails by default for any payer who uses an exchange, custodial wallet, or shared infrastructure.

Recommendation:

Applications MAY use Source Account Attribution only when the source account is explicitly registered, authenticated, and expected. Applications SHOULD NOT assume that a source account identifies a human payer without prior agreement.

#### Raw Dust Tagging

Classification: Context-dependent convention

Other names:

- Raw Amount Tagging
- Amount Tagging
- Dust Tagging
- Raw Encoding
- Amount-as-Metadata
- Value-as-Message

Problem addressed:

A receiver wants to distinguish payments or encode a small application-level value without generating separate destination accounts or exchanging off-chain metadata.

Mechanism:

The sender varies the exact raw amount, or a very small fractional XNO suffix, so that the receiver can infer application-level meaning from the precise amount received.

Example:

```text
1.000000000000000000000000000123 XNO
```

Because $1\ \text{XNO} = 10^{30}\ \text{raw}$, the trailing fractional digits in this example correspond to the three least-significant raw units (decimal value 123). Application-specific code may interpret this suffix as a tag, invoice discriminator, or small state value.

Useful properties:

- Does not require a native memo field.
- Can be observed from payment amount alone.
- May work in tightly controlled systems where both sender and receiver use application-specific wallet code.
- Can distinguish otherwise similar payments to the same destination.

Wallet compatibility:

Raw Dust Tagging is poorly supported by ordinary user-facing wallets.

Many user-facing wallets limit display and input precision to a smaller number of XNO decimal places, commonly around six decimal places. A user may therefore see or enter only an approximation of the intended amount, even if the underlying Nano protocol can represent raw-level precision.

Some wallets may also refuse to create, hide, ignore, deprioritize, or fail to present receive actions for extremely small pending amounts. As a result, dust-level tags may be visible only to application-specific wallet code, node RPC integrations, explorers, or custom indexers.

Applications MUST NOT assume that a human-operated general-purpose wallet can accurately display, preserve, send, or receive raw-level tags.

Failure modes:

- The sender's wallet may round, truncate, or reject the requested amount.
- The receiver's wallet may display a rounded amount and hide the embedded tag.
- The receiver may not publish a receive block for very small pending amounts.
- Automatic receive behavior may differ across wallets.
- A user may manually alter the amount and destroy the tag.
- Multiple payments with similar tagged amounts may be ambiguous.
- Refunds, partial payments, overpayments, and exchange withdrawals can destroy the intended correlation.
- Application logic may accidentally treat a dust-tagged payment as an ordinary payment or vice versa.
- Using very small amounts as tags can create unwanted receivables and indexing noise.

Privacy considerations:

Raw Dust Tagging can fingerprint payments through amount-suffix patterns, exposing user interaction with specific applications across the public ledger.

Classification note:

Raw Dust Tagging can become harmful if generalized for broad correlation, messaging, or unsolicited notifications. Do not use dust-level amount tags as a public application messaging layer.

Recommendation:

Raw Dust Tagging is appropriate only in controlled contexts where both sender and receiver explicitly support the convention, exact raw amounts are preserved, ordinary wallet UI precision is not relied upon, and failure cases are handled. For ordinary invoice correlation, applications SHOULD prefer Invoice Deposit Accounts or Off-chain Payment References.

### Receive and Account-State Signaling Patterns

#### Receive Acknowledgement

Classification: Context-dependent convention

Other names:

- Receive Block Acknowledgement
- Receive-as-Commit
- Acceptance Receive
- Claim Signal

Problem addressed:

An application wants to interpret the receiver's publication of a receive block as an acknowledgement, acceptance, or state transition.

Mechanism:

A sender sends funds to an account. The application treats the receiver's later receive block as a signal that the receiver has accepted, consumed, acknowledged, or committed to something.

Useful properties:

- Uses ordinary Nano account-chain behavior.
- Can be meaningful when the receiving account is controlled by the application.
- May model simple state transitions, such as "ticket claimed" or "deposit accepted."

Failure modes:

- Many wallets auto-receive without user intent. This can involuntarily promote a Pending Receivable Marker into a Receive Acknowledgement, collapsing the two patterns into each other.
- Some wallets delay, batch, or hide receive behavior.
- A receive block may indicate wallet behavior, not application consent.
- Users may receive funds accidentally.
- The same pending send may be received long after the intended application context expired.
- Indexers must track both send and receive sides.

Classification note:

Receive Acknowledgement is context-dependent because its semantic value depends entirely on whether the receiving account is application-controlled and whether the wallet's receive behavior is known to the application. It drifts toward "harmful if generalized" when applied to ordinary user accounts.

Recommendation:

Receive Acknowledgement MAY be used only with dedicated accounts and controlled receive behavior. Applications SHOULD NOT interpret a normal user's receive block as consent unless the user and wallet explicitly support that application convention.

#### Pending Receivable Marker

Classification: Harmful if generalized

Other names:

- Pending Marker
- Unreceived Send Signal
- Receivable Notification
- Pending-as-Message

Problem addressed:

An application wants to signal something to an account by creating a pending receivable without requiring the recipient to receive it.

Mechanism:

A sender sends a small amount to a recipient account. The application interprets the existence of the unreceived pending amount as a marker, notification, or message.

Useful properties:

- The signal can be visible to indexers before the recipient receives it.
- The recipient does not need to publish a receive block for the marker to exist.
- Technically easy to create.

Failure modes:

- Creates unwanted receivables for users.
- May clutter wallets and account state.
- May be hidden or ignored by wallets.
- Can be abused for spam, harassment, or tracking.
- Forces recipients and infrastructure to deal with unsolicited state.
- Does not reliably convey consent or awareness.
- Wallets with aggressive auto-receive behavior will convert the marker into a published receive block, eliminating the intended "unreceived" property and conflating this pattern with Receive Acknowledgement.

Recommendation:

Applications SHOULD NOT use pending receivables as a general signaling mechanism. This pattern is especially problematic when sent to accounts that have not opted into the application.

#### Open Block as Registration

Classification: Context-dependent convention

Other names:

- First-block Registration
- Account Activation Signal
- Open-as-Enrollment

Problem addressed:

An application wants to treat the existence of an open block on a derived or designated account as proof that the account holder has activated, enrolled in, or registered with the application.

Mechanism:

The application instructs the user (or its own derivation logic) to open a specific account, often at a deterministic derivation index, and then watches the ledger for the open block. The presence of that block is interpreted as activation.

Useful properties:

- Uses ordinary Nano account-opening behavior.
- Can be deterministic if combined with a known derivation scheme.
- Avoids requiring a separate registration channel.

Failure modes:

- An open block can only be published once the account receives funds; the application or user must arrange for an initial send.
- Wallet account-discovery behavior varies; the open block may not be discovered or surfaced in time.
- Anyone who can send to the deterministic address can effectively force activation against the account holder's intent.
- Sequential derivation indexes may leak business volume; see Account Index Signal.
- Recovery requires the same derivation scheme and gap-limit assumptions used at registration.

Recommendation:

Open Block as Registration MAY be used when both the derivation scheme and the funding flow are application-controlled, and when activation has no security-critical consequences that an arbitrary third-party send could trigger inappropriately. Applications SHOULD combine the on-chain signal with off-chain consent to avoid involuntary registration.

#### Balance State Signal

Classification: Context-dependent convention

Other names:

- Balance Encoding
- Account Balance State
- Balance-as-State

Problem addressed:

An application wants to infer state from the exact balance of an account.

Mechanism:

The account's balance is treated as a state value. Specific balances or balance ranges correspond to application-level states.

Useful properties:

- Observable from account state.
- Does not require parsing arbitrary metadata.
- May work in closed systems where all sends and receives are controlled by the application.

Failure modes:

- Although Nano has no fees, partial sends and receives still mutate balance, so any unexpected incoming payment corrupts the encoded state.
- Wallet operations may alter balances in ways the application did not expect.
- Requires exact balance tracking and confirmation.
- Poorly suited to ordinary user wallets.

Recommendation:

Balance State Signal SHOULD be limited to application-controlled accounts where all account activity is controlled and audited. It SHOULD NOT be used with ordinary user accounts.

#### Frontier Signal

Classification: Context-dependent convention

Other names:

- Frontier-as-State
- Head Block Signal
- Account-chain Pointer
- Publication Frontier

Problem addressed:

An application wants to use the latest confirmed block of an account as a state pointer, publication marker, or low-frequency update signal.

Mechanism:

The application publishes a block on a dedicated account chain. Observers interpret the current frontier as the latest application state marker, often while resolving actual metadata off-chain.

Useful properties:

- Provides an ordered account-local publication point.
- Can anchor off-chain state by referencing a block hash.
- May be useful for low-frequency application-controlled updates.

Failure modes:

- Frontier changes may be caused by unrelated wallet activity.
- Requires observers to track account frontier state.
- High-frequency updates create unnecessary ledger activity.
- Historical interpretation may require archival or indexer support.
- The block itself carries only ordinary Nano fields.

Classification note:

Frontier Signal can approach low-risk when a dedicated publisher account anchors infrequent off-chain state. It drifts toward "harmful if generalized" when used as a high-rate message bus.

Recommendation:

Frontier Signal MAY be acceptable for low-frequency, application-controlled anchoring. Applications SHOULD NOT use ordinary user account frontiers or rapid frontier updates as a messaging system.

#### Reply-with-Send Receipt

Classification: Context-dependent convention

Other names:

- Echo Send
- Acknowledgement Send
- Send-back Receipt

Problem addressed:

An application wants to acknowledge a received payment by sending a small amount back to the original payer's source account.

Mechanism:

When the application receives a payment, it issues a small send to the source account of the incoming send, treating that send as an on-chain receipt.

Useful properties:

- Visible to the original payer and to indexers.
- Does not require an off-chain channel.

Failure modes:

- Inherits all failure modes of Source Account Attribution: the source account may be a custodial hot wallet, an exchange, or a shared service, in which case the "receipt" is delivered to the wrong party.
- Inherits the involuntary-receive failure modes of Receive Acknowledgement and Pending Receivable Marker.
- Creates unsolicited receivables for the source-account controller.
- May be misinterpreted as a refund or a fresh payment.

Recommendation:

Applications SHOULD NOT use Reply-with-Send Receipts as a default acknowledgement mechanism. Where on-chain acknowledgement is genuinely required, applications SHOULD restrict it to source accounts that have explicitly registered as the payer's identity, and SHOULD prefer an off-chain signed receipt otherwise.

### Representative-Based Patterns

#### Representative Tagging

Classification: Harmful if generalized

Other names:

- Representative Field Abuse
- Rep Tagging
- Representative-as-Metadata
- Rep-as-Message

Problem addressed:

An application wants to store or signal a value using the representative field.

Mechanism:

The account representative is set to an account chosen to encode application-level meaning. Observers interpret the representative account as a tag, state value, or pointer.

Useful properties:

- Representative changes are visible on-chain.
- The field is persistent in account state.
- It may appear to provide a convenient account-level metadata slot.

Failure modes:

- The representative field has voting and governance meaning.
- Misuse can confuse users about their representative choice.
- It can interfere with representative UX and vote-weight distribution.
- Wallets may warn, hide, restrict, or automatically manage representative changes.
- Representative accounts used as tags may be mistaken for legitimate representatives.
- Repeated changes create unnecessary account-chain activity; see also Representative Change Pulse.

Network-health considerations:

Representative behavior affects the social and operational layer of Nano's delegated voting model. Application-level overloading of this field can create ecosystem confusion even when consensus remains valid.

Recommendation:

Applications SHOULD NOT use the representative field as metadata, a memo substitute, an invoice tag, or a general signaling channel.

#### Representative as dApp Tag

Classification: Harmful if generalized

Other names:

- Project Rep Opt-in
- Branded Representative
- Affiliation Rep

Problem addressed:

An application wants users to signal opt-in, affiliation, eligibility for an airdrop, or membership in a project by setting their representative to a project-controlled account.

Mechanism:

The project publishes a representative account address. Users change their representative to that account to indicate participation. The application enumerates delegators of the chosen representative to determine the participant set.

Useful properties:

- Requires no token, no smart contract, and no separate registration system.
- Lets users opt in or out by an action they can take in any wallet.
- Is visible to anyone scanning vote weight or delegator lists.

Failure modes:

- Concentrates vote weight on a non-consensus-oriented operator. Even with small individual delegations, large participant sets can shift effective voting weight in ways that conflict with users' actual governance preferences.
- Pressures users to choose between governance hygiene and application participation.
- Can be copied or spoofed by lookalike representative accounts.
- May induce wallet warnings about non-principal or non-voting representatives.
- Encourages further overloading of the representative field across the ecosystem.

Classification note:

This is a specific subcase of Representative Tagging that some communities have argued is legitimate because it requires explicit user action. The view taken here is that the governance externalities still make it harmful if generalized, regardless of consent: a per-application convention scales poorly when many applications adopt it simultaneously.

Recommendation:

Applications SHOULD NOT use representative selection as an affiliation or opt-in mechanism. Off-chain registration, signed messages, or token-style opt-in on a dedicated application-controlled account chain are all preferable.

#### Representative Change Pulse

Classification: Harmful if generalized

Other names:

- Rep Change Pulse
- Representative Pulse
- Change Block Signal
- Rep Churn Signal

Problem addressed:

An application wants to signal an event by publishing a representative-change block.

Mechanism:

The account changes its representative, possibly back and forth between known representatives, and observers treat the change event itself as a signal.

Useful properties:

- Produces a visible account-chain event.
- Does not require value transfer.
- Can be generated by the account owner.

Failure modes:

- Creates unnecessary representative churn; see also the network-health considerations under Representative Tagging.
- Confuses wallet representative history.
- May interfere with user expectations around voting.
- Produces ledger activity solely for signaling.
- Can be abused as a low-capacity message channel.

Recommendation:

Applications SHOULD NOT use representative-change events as pulses, messages, or state transitions.

### Address, Amount, and Hash-Based Conventions

#### Block Hash Commitment

Classification: Low-risk convention

Other names:

- Block Reference
- Transaction Hash Reference
- Payment Hash Commitment
- Hash Anchor

Problem addressed:

An application needs to refer to a specific confirmed Nano payment or account-chain event from off-chain metadata.

Mechanism:

The application stores or communicates the hash of a confirmed Nano block off-chain. The hash identifies the relevant ledger event.

Useful properties:

- Does not alter Nano payment semantics.
- Provides a compact reference to a confirmed block.
- Works well with off-chain receipts, invoices, and audit logs.
- Avoids encoding arbitrary metadata into the ledger.

Failure modes:

- Default Nano node configurations may retain only the frontier of each account chain. Intermediate block bodies may become unavailable from non-archival nodes even shortly after confirmation; consumers that require historical resolution MUST arrange access to archival nodes, explorers, or indexers.
- A block hash alone does not describe application meaning; off-chain metadata must still be preserved.
- Pruning and indexer availability vary across deployments.

Classification note:

Block Hash Commitment is low-risk as an identifier but becomes context-dependent when consumers require archival history or specific indexer behavior. Do not treat a block hash as carrying data beyond identifying a confirmed block.

Recommendation:

Applications SHOULD use block hashes as references to confirmed ledger events where useful, but SHOULD keep application meaning and metadata off-chain, and SHOULD document their archival assumptions.

#### Address Payload Encoding

Classification: Harmful if generalized

Other names:

- Vanity Payload Encoding
- Address-as-Data
- Encoded Destination
- Public-key Payload

Problem addressed:

An application wants to encode data into a Nano account address or public key.

Mechanism:

The application searches for, constructs, or selects destination accounts whose address characters or public key bytes encode an application-level payload.

Useful properties:

- The encoded value may be visible in the address or public key.
- Does not require a memo field.
- Can be discovered by observers without additional metadata.

Failure modes:

- Funds may be sent to accounts with unknown or unavailable private keys.
- Payload addresses may be unspendable.
- Users may mistake encoded addresses for ordinary payment addresses.
- Generating meaningful addresses may be computationally expensive or constrained.
- Address encoding is low-capacity and fragile.
- Encourages treating addresses as a data store.

Recommendation:

Applications SHOULD NOT encode arbitrary data into destination addresses. If an address is used, it SHOULD correspond to a spendable account controlled by the intended receiver.

#### Vanity Prefix as Identity

Classification: Context-dependent convention

Other names:

- Branded Address
- Vanity Branding
- Recognizable Prefix

Problem addressed:

An application or organization wants users to be able to visually recognize an address as belonging to it, without relying on out-of-band verification.

Mechanism:

The operator generates an account whose address contains a recognizable prefix, suffix, or substring (for example, a project name fragment). The address is published as the canonical destination, and users are expected to verify the visible vanity component.

Useful properties:

- Provides a lightweight visual identity cue.
- Does not encode data; the address is a real spendable account.
- Works with any wallet that displays the full address.

Failure modes:

- Vanity components can be copied or approximated by adversaries; close-lookalike addresses are a well-known phishing vector.
- Users may rely on prefix recognition alone and skip full-address verification.
- Wallets that truncate addresses for display may hide the discriminating portion of the address.
- Generation cost grows rapidly with the length of the desired pattern.

Classification note:

Vanity Prefix as Identity is distinct from Address Payload Encoding: it uses the address as a recognizable label rather than as a data channel, and the address remains spendable. The risks are user-interface and anti-phishing risks rather than data-storage risks.

Recommendation:

Applications MAY use vanity prefixes for branding when the address is published through authenticated channels and users are not expected to verify the address by prefix alone. Applications SHOULD NOT rely on vanity prefixes as a substitute for cryptographic authentication of payment destinations.

#### Burn Signal

Classification: Harmful if generalized

Other names:

- Burn Address Signal
- Proof-of-Burn Signal
- Unspendable Destination Signal

Problem addressed:

An application wants to prove commitment, sacrifice, or state transition by sending funds to an unspendable or effectively unowned account.

Mechanism:

The sender sends Nano to an address for which no private key is known, or to an address treated by convention as unspendable. Observers interpret the payment as a signal.

Useful properties:

- Creates a visible and irreversible-looking event.
- May be used as proof that value was intentionally destroyed.

Failure modes:

- Wastes funds.
- May be impossible to prove that no private key exists.
- Can confuse users and explorers.
- Encourages value destruction as application signaling.
- May be copied by applications that do not need irreversible sacrifice.

Recommendation:

Applications SHOULD NOT use burn payments as routine application signals. If proof of commitment is needed, applications SHOULD prefer signed off-chain commitments or ordinary payments to controlled accounts.

#### Account Index Signal

Classification: Context-dependent convention

Other names:

- Derivation Index Signal
- HD Index Encoding
- Account Number Signal

Problem addressed:

An application wants to assign meaning to deterministic account indexes or derivation paths.

Mechanism:

The wallet or application derives accounts at specific indexes, and the index number carries application-level meaning such as account type, invoice sequence, or role.

Useful properties:

- Can be deterministic and recoverable.
- Avoids storing every private key independently.
- May be convenient for application-controlled wallets.

Failure modes:

- Index meaning may leak business or user information (e.g., leaking sequential order volumes or user signup sequences).
- Gaps can break account discovery.
- Different wallets may use different derivation schemes.
- Publishing extended public derivation material can expose future addresses.
- Poorly designed derivation can cause recovery or privacy failures.

Recommendation:

Applications MAY use deterministic account indexes internally, but SHOULD document derivation paths, account discovery rules, gap limits, and privacy consequences. Applications SHOULD NOT expose sensitive derivation structure unnecessarily.

#### Account Sweep Linkage

Classification: Harmful if generalized

Other names:

- Hot-wallet Consolidation Linkage
- Sweep Correlation
- Consolidation Fingerprint

Problem addressed:

This entry catalogues the cross-cutting privacy anti-pattern that arises when funds from many distinct Invoice Deposit Accounts or Customer Deposit Accounts are consolidated into a small number of hot wallets.

Mechanism:

The service periodically sweeps balances from many accounts to one or a few destination accounts. The sweep blocks publicly link all swept accounts to a single controller.

Useful properties:

This pattern is not a useful technique; it is documented here to make its risks visible to applications that rely on per-invoice or per-customer accounts for unlinkability.

Failure modes:

- Retroactively links all swept accounts on a fully transparent ledger.
- Defeats much of the per-invoice unlinkability gained by using Invoice Deposit Accounts in the first place.
- Reveals aggregate business volume and timing to any observer.
- Can be combined with timing analysis to deanonymize customers.

Recommendation:

Applications that consolidate funds SHOULD minimize the linkability introduced by sweeps. Options include batching consolidations, using multiple sweep destinations, separating user-visible deposit accounts from internal accounting accounts, and disclosing the linkability risk to users where relevant.

#### Timing Signal

Classification: Context-dependent convention

Other names:

- Time-based Signal
- Confirmation Timing Signal
- Delay Encoding
- Temporal Encoding

Problem addressed:

An application wants to infer meaning from when a block is published, confirmed, received, or observed.

Mechanism:

Meaning is assigned to timing, delay, ordering, or relative spacing between ledger events.

Useful properties:

- Does not require additional data fields.
- May be useful for coarse application sequencing in controlled systems.

Failure modes:

- Nano blocks do not provide a strong application-level timestamp primitive.
- Observation time differs across nodes, wallets, and indexers.
- Network delays can alter apparent timing.
- User wallet behavior can introduce unpredictable delays.
- Timing signals are fragile and hard to audit.

Recommendation:

Applications SHOULD NOT rely on precise timing as a primary signal. If timing matters, applications SHOULD include timestamps and expirations in off-chain signed metadata.

#### Multi-send Ordering Signal

Classification: Harmful if generalized

Other names:

- Ordered Send Encoding
- Transaction Sequence Encoding
- Multi-payment Message
- Send Ordering Signal

Problem addressed:

An application wants to encode a value or state transition using the order, grouping, or count of multiple sends.

Mechanism:

The sender publishes several Nano sends, and observers interpret their order, amount sequence, destination sequence, or grouping as an encoded message.

Useful properties:

- Can encode more information than a single payment amount.
- Uses ordinary send blocks.

Failure modes:

- Creates unnecessary ledger activity.
- Ordering assumptions may differ across observers and indexers.
- Partial failure can corrupt the message.
- Nano account chains are strictly serial, but multiple devices or services sharing a key can race for the next position in the chain, and interleaved receives can reorder events relative to the sender's intent.
- Encourages use of the ledger as a message bus.

Recommendation:

Applications SHOULD NOT use multi-send ordering as a general-purpose encoding or signaling mechanism.

### Harmful or Abusive Patterns

#### Dust Spray Signaling

Classification: Harmful if generalized

Other names:

- Dust Notifications
- Dust Messaging
- Spray Signaling
- Dust Spam

Problem addressed:

An application wants to notify, mark, track, or message many accounts.

Mechanism:

The sender sends tiny amounts to many accounts. The existence, amount, timing, or source of the sends is interpreted as a signal.

Useful properties:

- Visible to recipients, indexers, and observers.
- Does not require recipient participation before the send.
- Technically easy to automate.

Failure modes:

- Creates unwanted pending receivables.
- Clutters wallets and account histories.
- Enables spam and harassment.
- Can be used for tracking and deanonymizing users by forcing them to link their accounts on sweeping.
- Burdens wallets, indexers, explorers, and users.
- May cause recipients to accidentally link accounts when sweeping; see Account Sweep Linkage.

Recommendation:

Applications MUST NOT use Dust Spray Signaling as a routine notification, messaging, marketing, tracking, or application-state mechanism.

#### Arbitrary Data Encoding

Classification: Harmful if generalized

Other names:

- On-chain Data Storage
- Ledger Data Encoding
- Block-lattice Data Storage
- Metadata Abuse

Problem addressed:

An application wants to store arbitrary data on the Nano block lattice.

Mechanism:

The application encodes data through combinations of amounts, addresses, representative fields, work values, account creation, send ordering, receive behavior, or repeated transactions.

Useful properties:

- Data may become visible to observers.
- Does not require a separate storage network.
- May appear attractive because Nano is feeless to users.

Failure modes:

- Nano is not designed as arbitrary data storage.
- Creates ledger growth and infrastructure burden.
- Encourages spam-like behavior.
- May degrade wallet, explorer, and indexer usability.
- Data capacity is low and encoding is fragile.
- Application meaning may be lost without custom decoders.

Recommendation:

Applications MUST NOT use the Nano block lattice as a general-purpose data storage layer. Arbitrary metadata SHOULD be stored off-chain and referenced or authenticated using explicit cryptographic commitments where needed.

#### Work-field / Overwork Signaling

Classification: Harmful if generalized

Other names:

- Work Signaling
- Overwork Encoding
- Proof-of-work Tagging
- Work-as-Message

Problem addressed:

An application wants to encode meaning in the work value attached to a block, or in the amount of proof-of-work performed beyond what is required.

Mechanism:

The sender selects a work value, or computes unusually high work, and observers interpret the work pattern as application-level data.

Useful properties:

- Does not alter the amount or destination.
- May be visible to low-level parsers.

Failure modes:

- Wastes computation.
- Very low data capacity.
- Poor wallet and tooling support.
- Observers may ignore or discard the distinction.
- Encourages inefficient signaling.
- Can create misleading incentives around proof-of-work generation.
- The work value is not part of the block hash and may be recomputed by representatives or wallets when republishing. Any "signal" placed in the work field therefore has no cryptographic binding to the block itself.

Recommendation:

Applications SHOULD NOT use work values or overwork as an application signaling channel.

### Payment Correlation Guidance

This section is the normative summary referenced by the triage list under Payment Correlation Patterns.

For ordinary payment correlation, applications SHOULD prefer:

1. Off-chain Payment References, especially when rich metadata or authentication is required.
2. Invoice Deposit Accounts, especially when the receiver can generate unique destination accounts.
3. Customer Deposit Accounts, when repeated deposits are needed and address reuse is acceptable.

Applications MAY use Source Account Attribution only after authenticating or registering the payer's source account, and only when the payer is not expected to send from custodial or shared infrastructure.

Applications SHOULD treat Raw Dust Tagging as a controlled integration technique, not as a general wallet-compatible convention.

Applications SHOULD NOT use Representative Tagging, Representative as dApp Tag, Representative Change Pulse, Pending Receivable Markers, Burn Signals, Dust Spray Signaling, Address Payload Encoding, Multi-send Ordering Signals, or Arbitrary Data Encoding for ordinary invoice correlation.

While correlation conventions map payments to invoices, secure transaction processing requires rigorous software engineering guidelines. Developers and exchanges building payment integration systems SHOULD consult [ORIS-008 (Nano Integration and Reliable Payment Processing Standard)](file:///Users/conny/Developer/nano/OpenRai/Standards/rfcs/ORIS-008.md) for normative requirements on transaction isolation, idempotency constraints, database concurrency, automated reconciliation audits, and payment lifecycle edge-case handling (underpayments, overpayments, duplicate payments, indexer lag).

### Glossary

The following terms are used throughout this document. Definitions are intentionally brief; consult current Nano protocol documentation for authoritative definitions.

- Account chain: The strictly serial sequence of blocks belonging to a single Nano account. Each account maintains its own chain.
- Block lattice: The overall data structure formed by all individual account chains in Nano.
- Frontier: The latest confirmed block on a given account chain. Many node configurations retain only the frontier and discard or prune older block bodies.
- Open block: The first block on an account chain, which receives the account's initial incoming send and establishes its first representative.
- Receivable (pending): An incoming send that has been published by the sender but not yet acknowledged by a receive block on the destination account.
- Representative: The voting account designated by an account holder; representatives participate in Open Representative Voting on behalf of their delegators.
- Open Representative Voting (ORV): Nano's consensus mechanism, in which representatives weighted by delegated balance vote to confirm blocks.
- Raw: The smallest indivisible Nano unit, with $1\ \text{XNO} = 10^{30}\ \text{raw}$.
- XNO: The Nano user-facing unit.
