```
OpenRai Initiative Standard: 008
```

# Nano Integration and Reliable Payment Processing Standard

> Status: Draft
> Category: Informational / Application Guidance

## Abstract

This document standardizes payment system designs, validation rules, transactional state management, and edge-case handling for applications integrating with the Nano distributed ledger. It establishes normative patterns to prevent common ledger integration hazards—such as double-withdrawal exploits, transaction double-counting, race conditions in feeless environments, and synchronization lag—providing third-party developers and exchanges with a blueprint for building highly secure and resilient financial integrations.

## Motivation

Nano utilizes a unique block-lattice architecture where every account maintains its own independent blockchain, and consensus is achieved asynchronously via Open Representative Voting (ORV). Unlike standard UTXO or smart-contract systems, Nano has two major operational traits:

1.  **Strictly Feeless Transactions:** Nano transfers have zero network fees, eliminating economic barriers to high-frequency or spam-like API queries.
2.  **Asynchronous Split-Action Ledger:** Transactions are split into separate `send` and `receive` blocks. A transfer is initiated by the sender but only completed when the receiver publishes a matching receive block.

These characteristics offer unparalleled speed and user experience but introduce distinct software integration hazards. In traditional proof-of-work or account-based systems, network transaction fees and blocks-to-confirm rules provide natural rate-limiting and transaction grouping. In Nano, a lack of strict transactional bounds in application databases can lead to catastrophic balance double-crediting or concurrent double-withdrawal race conditions (commonly referred to historically as the BitGrail vulnerabilities).

This standard addresses these risks by formalizing standard guidelines for validation, transaction safety, and lifecycle state machines.

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document indicate application integration guidance where they appear.

- `send block` refers to the ledger-visible block initiating a value transfer.
- `receive block` refers to the ledger-visible block securing the incoming value transfer on the destination chain.
- `cementing` or `confirmation` refers to the point where a block is confirmed by network quorum and permanently locked on the ledger by the node.
- `idempotence` refers to the property of an API or database process where executing it multiple times has the same outcome as executing it once.

## Specification & Integration Guidelines

### 1. Confirm Before Acting (Quorum Finality vs. Local Observation)

Applications MUST NOT trigger irreversible off-chain actions (such as crediting user accounts, launching automated withdrawals, or shipping goods) based solely on the local observation of unconfirmed blocks.

In Nano's ORV consensus model, a node may receive and insert a block into its local ledger ledger state before it has reached network-wide consensus. If a network fork or double-spend attempt occurs, only the block that achieves quorum will be permanently cemented.

*   **Rule:** Integrations MUST verify block confirmation state via active confirmation WebSockets or by querying the `block_info` RPC command and checking that `confirmed` is `true`.
*   **Safety Threshold:** A block is considered fully irreversible *only* when its height is less than or equal to the account's confirmed/cemented height (confirmation height).

---

### 2. Transactional Isolation and Idempotency (The Anti-BitGrail Patterns)

Because Nano processes transactions at sub-second speeds with zero network fees, database race conditions represent a high-value vector for malicious exploits. 

```
[Concurrent Withdrawal Requests] ───► [Thread 1] ───► Check Balance (e.g., 10 XNO) ───┐
                                    ► [Thread 2] ───► Check Balance (e.g., 10 XNO) ───┼──► Exploited double-send!
                                    ► [Thread 3] ───► Check Balance (e.g., 10 XNO) ───┘
```

To eliminate concurrent double-withdrawal exploits and API double-processing, applications MUST enforce strict server-side transaction isolation:

#### A. Lock and Debit Before Broadcast
Applications MUST deduct the user's database balance and commit that change *before* commanding the Nano node to sign and broadcast the withdrawal `send` block to the network.

If the node's block broadcast fails, the application can safely rollback or credit back the user's database balance. If the system does not debit first, concurrent client threads can execute multiple withdrawals simultaneously before the database balance is updated.

#### B. Enforce Database Concurrency Controls
Applications MUST use strict row-level database locking (e.g., `SELECT ... FOR UPDATE` in SQL) or ACID-compliant transactional isolation when checking and updating user balances. Client-side browser checks MUST NOT be trusted to enforce balance limits.

#### C. Unique Constraint Keying
Integrations MUST implement unique transaction keys. Every withdrawal or payment event MUST be bound to a unique database transaction identifier (UUID, invoice ID, or block hash). If the withdrawal request is retried, the application MUST return the existing transaction record rather than issuing a new block.

---

### 3. Separation of Send/Receive Ledger State

In a block-lattice system, a transfer consists of both a `send` block and a `receive` block. These blocks represent two distinct events on two separate blockchains.

*   **The Hazard:** A naive integration script scanning all block types on its managed accounts might capture both the incoming `send` block and the self-generated `receive` block, mistakenly registering them as two separate deposit events—thereby double-crediting the customer's balance.
*   **Rule:** Integrations MUST explicitly separate the parsing of deposit blocks. An incoming deposit MUST be identified solely by a confirmed `send` block destined for the application's controlled address. The subsequent `receive` block generated by the application's hot wallet MUST NOT trigger deposit-crediting logic.

---

### 4. Real-Time Balance Reconciliation

To detect exploits, software bugs, or ledger drift before they cause catastrophic loss, applications handling custody of user funds SHOULD implement a continuous, automated **real-time balance reconciliation engine**.

```
┌────────────────────────────────────────────────────────┐
│             Reconciliation Audit Engine                │
├────────────────────────────────────────────────────────┤
│  Is Sum(All DB User Balances) == Total On-Chain Hot    │
│  and Cold Wallet Balances (including pending)?         │
└───────────────┬──────────────────────────┬─────────────┘
                │                          │
               Yes                         No
                ▼                          ▼
      [Continue Operation]        [TRIGGER CIRCUIT BREAKER]
                                  • Halt all automated sends
                                  • Alert system engineers
```

*   **Mechanism:** At regular intervals (e.g., every 60 seconds), the engine computes:
    $$\text{Total On-chain Assets} = \sum(\text{Confirmed balances of all active addresses}) + \sum(\text{Confirmed pending receivables})$$
    The engine then compares this with the sum of all customer ledger balances in the SQL database.
*   **Circuit Breaker:** If $\text{Total On-chain Assets} < \sum(\text{Database User Balances})$, the system MUST instantly trigger an automated circuit breaker that:
    1.  Halts all outbound withdrawal processing immediately.
    2.  Flags the mismatch in the system logs.
    3.  Pings security administrators.

---

### 5. Normative Payment Lifecycle Guidance

Applications accepting payments MUST explicitly define, implement, and test their behavior for each of the following payment-lifecycle scenarios:

| Scenario | Definition | Expected Application Behavior |
| :--- | :--- | :--- |
| **Exact Payment** | An incoming confirmed `send` matching the exact requested amount. | Credit invoice as "Fully Paid", trigger success hook, and publish the `receive` block. |
| **Underpayment** | An incoming confirmed `send` that is less than the requested invoice amount. | MUST NOT mark invoice as complete. SHOULD allow user to send the remainder, or flag for automated/manual partial refund minus administrative dust constraints. |
| **Overpayment** | An incoming confirmed `send` that exceeds the requested invoice amount. | SHOULD complete the invoice. The excess amount MUST be tracked separately, allowing the customer to withdraw the overpaid balance or request a refund. |
| **Duplicate Payment** | A second confirmed `send` to a one-time invoice account or transaction reference. | MUST NOT double-credit the invoice state. The duplicate funds MUST be routed to a pending queue for manual review or automated return. |
| **Late Payment** | A payment block confirmed after the invoice's specified expiration timeout. | The system MUST NOT auto-fulfill the order. It SHOULD queue the payment and prompt the user to either reinstate the order (if inventory is available) or request a refund. |
| **Expired Invoice** | The time window for a payment has elapsed without a confirmed block. | Mark the invoice status as "Expired" and stop active monitoring. If funds arrive late, refer to Late Payment behavior. |
| **Partial Payment** | Multiple smaller transfers accumulating toward the total invoice price. | Define an expiration timeout for accumulation. If the total is not met before timeout, transition to Underpayment rules. |
| **Refund Flow** | Returning funds to a payer due to underpayment, overpayment, or cancellation. | Refund blocks SHOULD NOT be sent automatically to the incoming `send`'s source address unless that address has been cryptographic-registered as owned by the user (to avoid refunding exchange hot wallets). Otherwise, request a verified refund destination address off-chain. |
| **Exchange/Custodial Sources** | User depositing from a shared hot wallet (e.g., Binance or a tip bot). | The application MUST NOT assume the source address represents a unique individual. Never issue refunds to incoming source addresses without explicit customer verification. |
| **Indexer Downtime** | The application's database, indexer, or local node sync lags behind the network. | The system MUST buffer incoming block notifications and process them sequentially once sync is restored. Use idempotent state updates so reprocessed blocks do not cause duplicate balance changes. |
| **Receive Delay** | Delay between observing a confirmed `send` and publishing the `receive` block. | Hot wallets SHOULD process receives promptly to secure funds. However, the system's database credit MUST rely on the confirmed `send` block rather than the `receive` block timing. |
| **Confirmation Delay** | A transaction remains in the local node's "unconfirmed" queue during network backlogs or spam. | Do not credit the user database. The UI should display the transaction as "Pending network confirmation" but keep the funds locked until the block is fully cemented. |

---

### 6. Architectural Hygiene and Privacy Guidelines

To ensure network health (good ledger citizenship) and preserve user privacy, integrations SHOULD adhere to the following systemic guidelines:

#### A. Bound Ledger Footprint
Because Nano is feeless to users, the marginal cost of publishing a transaction or opening an account is zero to the client, but non-zero to the network consensus, indexers, and archival nodes. Integrations MUST limit unnecessary ledger growth:
*   **Account Generation:** Avoid creating massive pools of unused or short-lived accounts. Limit deterministic derivation index spans where possible.
*   **Dust Control:** Do not generate unsolicited or excessive dust outputs that create unreceived pending receivables across the network.
*   **State Pruning Support:** Do not build system dependencies that rely on scanning the complete archival history of accounts; design services to operate purely on cemented frontiers.

#### B. Keep Ledger Semantics Minimal (Off-Chain Priority)
*   **Prefer Off-Chain Metadata:** Keep invoices, authentication challenges, user messages, order details, and receipts off-chain. Bind them to ledger events via explicit off-chain communication or lightweight transaction references.
*   **Avoid On-Chain Encoding:** Do not attempt to store arbitrary state or message payloads on-chain (e.g., abusing representative fields, PoW values, or amount suffixes to represent structured data). 

#### C. Design for Wallet Diversity
Integrations MUST NOT assume that third-party customer wallets interact with the ledger in the exact same manner as the application hot wallet.
*   **Display and Input Precision:** Many consumer wallets display or allow input only up to 6 decimal places of `XNO`, while the node handles $10^{30}$ `raw` units. Avoid relying on users manually entering raw-level amount suffixes.
*   **Auto-Receive Delays:** Consumer wallets may delay publishing receive blocks, auto-receive selectively, or completely hide very small pending dust amounts. Base credit and invoice-processing state machines on confirmed incoming *send* blocks, not on the customer's *receive* block publishing.

#### D. Prevent On-Chain Identity Linkage
Because the Nano ledger is fully transparent, public tracking of deposit/withdrawal patterns exposes users to financial privacy loss.
*   **Address Reuse:** Avoid using a single static deposit address for all customers or all transactions of a customer. Utilize unique, per-invoice deposit accounts.
*   **Sweep Linkage:** When consolidating customer deposits from unique addresses to a primary application hot wallet, be aware that the sweep transactions permanently link otherwise unrelated customer addresses in the public record. 
*   **Derivation-Structure Leakage:** Do not expose deterministic wallet public seeds or extended public keys (`xpub`) to clients. Sequential account index generation can leak transactional volume or customer registration metrics to outside observers.

## Glossary

- **Confirmation Height:** The length of the cemented chain segment of a Nano account. Only blocks at or below this height are fully confirmed.
- **Circuit Breaker:** An automated safety protocol that stops critical business operations when an structural inconsistency is detected.
- **Hot Wallet:** A cryptocurrency wallet connected to the internet and integrated into the application's automated deposit/withdrawal engine.
- **Cold Wallet:** An offline, highly secure storage address holding the majority of application funds, requiring manual intervention to access.
