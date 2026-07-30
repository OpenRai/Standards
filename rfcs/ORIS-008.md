```
OpenRai Initiative Standard: 008
```

# Reliable Nano Payment Integration

> Status: Working Draft
> Category: Informational / Application Guidance

## Abstract

This document explains how to process Nano deposits and withdrawals without
double-crediting, double-spending application balances, or losing events. It
covers confirmation tracking, idempotency, reconciliation, and common payment
exceptions.

## Motivation

Nano differs from UTXO and EVM systems in ways that affect application code:

- A transfer uses one send block and one receive block.
- Applications act on confirmed blocks rather than a confirmation count.
- A receivable is a confirmed send that the destination has not received.
- Feeless transfers do not replace application-level rate limits.
- WebSocket delivery can be duplicated or missed.

The database must remain correct when requests race, the node is unavailable,
or the same confirmation arrives more than once.

## Nano for UTXO/EVM Developers

The closest concepts are:

| Concept | UTXO/EVM | Nano |
|---|---|---|
| Transaction fee | Required (gas/miner fee) | Zero |
| Transaction structure | Single atomic transaction | Two separate blocks: `send` + `receive` |
| Confirmation | "Included in a block with N confirmations" | "Cemented by ORV consensus" — check `confirmed` field |
| Unconfirmed work | Transactions wait in a public mempool | Nodes track blocks and active elections |
| Account model | UTXO set or account state | Each account has its own blockchain |
| Pending transactions | Visible in mempool | Receivables: sends not yet received |
| Application finality | Usually based on a confirmation count | Based on Nano confirmation |

For deposits, act on the confirmed send to a managed destination. The later
receive block changes the destination account chain but does not create a second
deposit.

## Conventions

- **Send block:** The sender's block that creates a receivable.
- **Receive block:** The destination account's block that claims a receivable.
- **Confirmed or cemented:** Accepted by Nano consensus and recorded in
  confirmation height.
- **Idempotent:** Repeating an operation has the same effect as running it once.

## Reference Documentation

This document assumes you're familiar with:

- [Block Confirmation Tracking](https://docs.nano.org/integration-guides/block-confirmation-tracking/) — how to verify block confirmation
- [WebSockets](https://docs.nano.org/integration-guides/websockets/) — real-time block notifications
- [RPC Protocol](https://docs.nano.org/commands/rpc-protocol/) — node API commands

## Integration Guidelines

### 1. Confirm Before Acting

Credit a deposit only after its send block is confirmed.

A node can observe a block before confirmation. WebSocket `confirmation` events
provide the primary signal.

Subscribe with acknowledgements enabled:

```json
{
  "action": "subscribe",
  "topic": "confirmation",
  "ack": true,
  "options": {
    "accounts": ["nano_1depositaccount..."]
  }
}
```

The confirmation message looks like:

```json
{
  "topic": "confirmation",
  "message": {
    "hash": "ABC123...",
    "account": "nano_1sender...",
    "amount": "1000000000000000000000000000000",
    "block": {
      "subtype": "send",
      "link_as_account": "nano_1depositaccount...",
      "balance": "...",
      "previous": "...",
      "representative": "...",
      "signature": "...",
      "work": "..."
    }
  }
}
```

WebSockets do not guarantee delivery and can repeat an event. Persist processed
block hashes. When the application already knows a block hash, use `block_info`
as a fallback:

```json
{"action": "block_info", "hash": "ABC123..."}
```

The response contains `"confirmed": "true"` after confirmation.

**Reference:** [Block Confirmation Tracking](https://docs.nano.org/integration-guides/block-confirmation-tracking/), [WebSockets Confirmations](https://docs.nano.org/integration-guides/websockets/#confirmations), [RPC block_info](https://docs.nano.org/commands/rpc-protocol/#block_info)

### 2. Transactional Isolation and Idempotency

Serialize withdrawals that spend the same application balance or Nano account.

```
[Thread 1] ──► Check Balance (10 XNO) ──┐
[Thread 2] ──► Check Balance (10 XNO) ──┼──► Double-send!
[Thread 3] ──► Check Balance (10 XNO) ──┘
```

Use three rules:

**A. Reserve before broadcast.** In one database transaction, lock the user
balance, create a withdrawal with a unique key, and reserve or debit the amount.
Commit that state before asking the node to send.

If the node call fails, do not roll back an already committed transaction.
Record a retryable failure or restore the balance in a new transaction. The
withdrawal key MUST prevent a retry from creating another send.

**B. Lock application balances.** Use `SELECT ... FOR UPDATE` or an equivalent
serializable update. A client-side balance check provides no concurrency
control.

**C. Require an idempotency key.** Every withdrawal MUST have a unique request
key. A repeated key returns the existing withdrawal record.

### 3. Separation of Send/Receive Ledger State

Credit only a confirmed send whose `link_as_account` is a managed deposit
account. Ignore receive blocks for deposit accounting.

The WebSocket confirmation message includes a `subtype` field:

```json
{
  "topic": "confirmation",
  "message": {
    "hash": "ABC123...",
    "block": {
      "subtype": "send",
      "link_as_account": "nano_1yourdeposit...",
      ...
    }
  }
}
```

```json
{
  "topic": "confirmation",
  "message": {
    "hash": "DEF456...",
    "block": {
      "subtype": "receive",
      ...
    }
  }
}
```

Use these fields:

```text
message.block.subtype == "send"
message.block.link_as_account in managed_deposit_accounts
message.amount
message.hash
```

`message.amount` is the transferred amount. It is not nested inside `block`.

**Reference:** [WebSockets — Confirmation sample results](https://docs.nano.org/integration-guides/websockets/#sample-results)

### 4. Real-Time Balance Reconciliation

Reconcile on a fixed interval chosen for the integration's risk and volume. The
job must run independently of WebSocket handling.

```
1. Calculate controlled assets:
   for each managed account:
       assets += confirmed balance
       assets += confirmed receivables

2. Calculate recorded liabilities:
   liabilities = user balances
   liabilities += other withdrawable application balances

3. Compare:
   if assets < liabilities:
       TRIGGER CIRCUIT BREAKER
       - pause withdrawals
       - record the measured deficit
       - alert the operator
```

The exact asset and liability sets depend on custody design. Define them once
and test the accounting equation. Do not silently add an unknown account or
exclude a pending withdrawal to make a discrepancy disappear.

Use `account_info` for confirmed balances:

```json
{"action": "account_info", "account": "nano_1hotwallet..."}
```

Use `receivable` for unclaimed incoming sends:

```json
{"action": "receivable", "account": "nano_1hotwallet...", "source": true}
```

The response maps send-block hashes to amounts. Include only confirmed
receivables in credited assets.

**Reference:** [RPC account_info](https://docs.nano.org/commands/rpc-protocol/#account_info), [RPC receivable](https://docs.nano.org/commands/rpc-protocol/#receivable)

### 5. Payment Lifecycle

Define application policy for at least these cases:

| Scenario | What happens | What to do |
|---|---|---|
| **Exact payment** | Confirmed send matches invoice amount | Credit once, queue receive, then fulfill |
| **Underpayment** | Confirmed send is less than invoice | Hold, notify user, await remainder or timeout |
| **Overpayment** | Confirmed send exceeds invoice | Credit invoice, track excess for refund |
| **Duplicate Payment** | Second send to one-time invoice account | Do NOT double-credit, route to manual review |
| **Late Payment** | Send confirmed after invoice expiration | Do not auto-fulfill, queue for user decision |
| **Expired invoice** | No payment before expiration | Stop fulfillment, but retain late-payment detection |
| **Partial Payment** | Multiple sends accumulating | Track total, apply underpayment rules on timeout |
| **Refund** | Returning funds | Do NOT refund to source address (may be exchange), request verified address off-chain |
| **Exchange Source** | Deposit from shared hot wallet | Do NOT assume source address = user |
| **Notification downtime** | WebSocket events were missed | Rescan managed accounts and process idempotently |
| **Receive Delay** | Delay between send confirmation and your receive | Credit based on confirmed send, not on your receive timing |
| **Confirmation delay** | Block is not confirmed | Do not credit. Show pending state |

Crediting and receiving are separate operations. Commit the credit and enqueue
the receive task in one database transaction. A worker can then create, sign,
and publish the receive block. Retry that worker by send-block hash.

**Reference:** [RPC process](https://docs.nano.org/commands/rpc-protocol/#process)

### 6. End-to-End Deposit Flow

One deposit moves through these steps.

**Step 1: Create the invoice.**

- Choose a correlation method from ORIS-007.
- Store the expected destination, amount, expiration, and status.

**Step 2: Subscribe to confirmations.**

```json
{"action": "subscribe", "topic": "confirmation", "ack": true, "options": {"accounts": ["<deposit_account>"]}}
```

Request an acknowledgement and verify that the node accepted the subscription.

**Step 3: Validate the confirmation.**

- Require `message.block.subtype == "send"`.
- Match `message.block.link_as_account` to the invoice destination.
- Reject a `message.hash` that was already processed.
- Compare `message.amount` with the expected amount.

**Step 4: Commit the application state.**

- Begin one database transaction.
- Insert the unique send-block hash.
- Apply the lifecycle policy.
- Credit the application balance when applicable.
- Enqueue receive and fulfillment work.
- Commit.

**Step 5: Run side effects.**

Workers publish the receive block and fulfill the order. Each worker uses its own
idempotency key and records success or a retryable failure.

**Fallback: rescan managed accounts.**

An invoice does not reveal its future send-block hash, so `block_info` alone
cannot discover a missed payment. Use `receivable` and account history to find
unseen sends to managed destinations. Use `block_info` after a block hash is
known.

### 7. Confirmation Tracking Decision Tree

When a WebSocket message arrives:

```
1. Is topic == "confirmation"?
   No → ignore (votes, elections, etc.)

2. Is message.block.subtype == "send"?
   No → ignore (this is your own receive/change/open)

3. Is message.block.link_as_account one of your deposit accounts?
   No → log unknown deposit, alert operator

4. Has message.hash already been processed?
   Yes → skip (idempotency)

5. Is the invoice for this deposit account still active?
   No → route to duplicate/late payment queue (Section 5)

6. Compare message.amount to invoice amount:
   Exact → credit, publish receive, dispatch
   Under → hold, notify user, await remainder
   Over → credit invoice, track excess

7. Commit credit and enqueue receive/fulfillment work
8. Run queued side effects idempotently
```

**RPC fallback:**

```
For each managed deposit account:
    list confirmed receivables and recent account history
    for each unseen send hash:
        validate with block_info
        process via steps 4–8 above
```

### 8. Integration Checklist

Before going live:

- [ ] WebSocket subscription to `confirmation` topic with `ack: true`
- [ ] Account filtering enabled (`options.accounts` set to deposit accounts)
- [ ] Idempotent handler (duplicate `message.hash` ignored)
- [ ] Subtype filter (only process `subtype: "send"`)
- [ ] Lock-and-debit-before-broadcast for withdrawals (Section 2)
- [ ] Unique constraint on withdrawal transaction keys (Section 2)
- [ ] Policy for every payment lifecycle case in Section 5
- [ ] Reconciliation running on a documented interval
- [ ] Circuit breaker triggers halt + alert on deficit
- [ ] RPC fallback polling for missed WebSocket confirmations
- [ ] Refund logic handles exchange/custodial sources (Section 5)
- [ ] Never refund to incoming source address without verification

## Architectural Hygiene and Privacy Guidelines

**Bound ledger footprint.** Keep unused account pools bounded. Do not generate
unsolicited dust.

**Keep metadata off-chain.** Store invoices, users, and orders in the application
database. Bind them to ledger events with block hashes or deposit accounts.

**Design for wallet diversity.** Wallets can round displayed amounts,
auto-receive, or delay receives. Base credit logic on confirmed sends rather
than the recipient's receive timing.

**Account for public linkage.** Sweeping invoice accounts into a hot wallet
links those accounts on-chain. Scheduling or splitting sweeps does not remove
that linkage. Do not expose extended public keys to clients.

## Glossary

- **Block lattice:** Nano's collection of per-account chains.
- **Confirmed or cemented:** Accepted by Nano consensus and recorded in
  confirmation height.
- **Circuit breaker:** An automated pause triggered by an accounting deficit.
- **Cold wallet:** Key storage kept outside the automated payment service.
- **Confirmation height:** The confirmed length of one account chain.
- **Hot wallet:** An online wallet used by the payment service.
- **Receivable:** A send that the destination account has not claimed.
- **Receive block:** A block that claims a receivable.
- **Send block:** A block that creates a receivable.
- **`account_info`:** Returns account balance, frontier, and representative.
- **`block_info`:** Returns block details and confirmation status.
- **`receivable`:** Lists unclaimed sends for an account.
- **`process`:** Publishes a signed block to the node.
- **WebSocket confirmation topic:** Emits notifications for confirmed blocks.
