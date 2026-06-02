```
OpenRai Initiative Standard: 008
```

# Nano Integration and Reliable Payment Processing Standard

> Status: Draft
> Category: Informational / Application Guidance

## Abstract

This document tells you how to build a reliable payment integration with Nano. If you're coming from UTXO (Bitcoin) or EVM (Ethereum) systems, Nano's block-lattice architecture will feel unfamiliar — there are no fees, no mempool in the traditional sense, and transactions are split into two separate blocks. This document explains what that means for your code, and provides the patterns, decision trees, and checklists you need to build a system that credits deposits correctly, handles withdrawals safely, and doesn't lose money.

## Motivation

Nano is fast and feeless, but those properties create integration hazards that don't exist in fee-based systems:

- **No fees = no natural rate limiting.** In Bitcoin or Ethereum, transaction fees make spam expensive. In Nano, a malicious user can flood your system with withdrawal requests at zero cost. Your database must handle concurrent requests safely.
- **Two-phase transactions.** A Nano transfer has two blocks: a `send` (sender creates it) and a `receive` (receiver creates it). If you're scanning for both, you'll double-count deposits.
- **Confirmation = cemented, not "included in a block."** There's no "wait for 6 confirmations." A block is either cemented (irreversible) or it isn't. You must check the `confirmed` field.
- **No mempool.** Blocks are processed immediately. There's no "pending in the mempool" state to monitor.

This document shows you how to handle all of these correctly.

## Nano for UTXO/EVM Developers

If you're coming from Bitcoin or Ethereum, here's what's different:

| Concept | UTXO/EVM | Nano |
|---|---|---|
| Transaction fee | Required (gas/miner fee) | Zero |
| Transaction structure | Single atomic transaction | Two separate blocks: `send` + `receive` |
| Confirmation | "Included in a block with N confirmations" | "Cemented by ORV consensus" — check `confirmed` field |
| Mempool | Transactions wait in mempool | No mempool — blocks are processed immediately |
| Account model | UTXO set or account state | Each account has its own blockchain |
| Pending transactions | Visible in mempool | "Pending receivables" — sends that haven't been received yet |
| Block finality | Probabilistic (more confirmations = more final) | Deterministic — once cemented, irreversible |

**The key mental shift:** In Bitcoin/Ethereum, you wait for confirmations. In Nano, you check if a block is cemented. In Bitcoin/Ethereum, a transaction is atomic. In Nano, a transfer has two halves — the send and the receive — and you must only credit the deposit when you see the confirmed send block, not the receive block.

## Conventions

- `send block` — the block the sender creates to transfer value
- `receive block` — the block the receiver creates to claim the value
- `cemented` / `confirmed` — permanently locked by network consensus
- `idempotent` — running the same operation twice has the same result as running it once

## Reference Documentation

This document assumes you're familiar with:

- [Block Confirmation Tracking](https://docs.nano.org/integration-guides/block-confirmation-tracking/) — how to verify block confirmation
- [WebSockets](https://docs.nano.org/integration-guides/websockets/) — real-time block notifications
- [RPC Protocol](https://docs.nano.org/commands/rpc-protocol/) — node API commands

## Specification & Integration Guidelines

### 1. Confirm Before Acting

**Never credit a deposit or ship goods based on an unconfirmed block.**

A Nano node may see a block before the network has confirmed it. If there's a fork (rare but possible), only the cemented block survives.

**How to confirm:**

Subscribe to the WebSocket `confirmation` topic. When a confirmation arrives, check:

```json
{
  "action": "subscribe",
  "topic": "confirmation",
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

**Fallback:** If the WebSocket misses a confirmation (network issues, node restart), poll with the `block_info` RPC:

```json
{"action": "block_info", "hash": "ABC123..."}
```

Response includes `"confirmed": "true"` when cemented.

**Reference:** [Block Confirmation Tracking](https://docs.nano.org/integration-guides/block-confirmation-tracking/), [WebSockets Confirmations](https://docs.nano.org/integration-guides/websockets/#confirmations), [RPC block_info](https://docs.nano.org/commands/rpc-protocol/#block_info)

### 2. Transactional Isolation and Idempotency

Nano is fast and feeless. If your database has race conditions, attackers will exploit them.

```
[Thread 1] ──► Check Balance (10 XNO) ──┐
[Thread 2] ──► Check Balance (10 XNO) ──┼──► Double-send!
[Thread 3] ──► Check Balance (10 XNO) ──┘
```

**Three rules:**

**A. Lock and debit before broadcast.** Deduct the user's balance in your database, commit the transaction, *then* tell the Nano node to send. If the node fails, rollback the database.

**B. Use database locks.** Use `SELECT ... FOR UPDATE` (PostgreSQL) or equivalent. Never trust client-side balance checks.

**C. Unique transaction keys.** Every withdrawal must have a unique ID (UUID, invoice ID). If the same request comes twice, return the existing record — don't send again.

### 3. Separation of Send/Receive Ledger State

**Only credit deposits when you see a confirmed `send` block. Do NOT credit when you see a `receive` block.**

Why: Your hot wallet will publish `receive` blocks to claim incoming sends. If your code processes both sends and receives as deposits, you'll double-credit.

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

**Filter rule:** Only process confirmations where `message.block.subtype == "send"` and `message.block.link_as_account` is one of your deposit accounts.

**Reference:** [WebSockets — Confirmation sample results](https://docs.nano.org/integration-guides/websockets/#sample-results)

### 4. Real-Time Balance Reconciliation

Run this every 60 seconds:

```
1. Get all on-chain balances:
   for each wallet in [hot_wallet, cold_wallet, ...]:
       on_chain += account_info(wallet).balance
       on_chain += receivable(wallet).pending

2. Get all database balances:
   db_total = sum(user.balance for all users)

3. Compare:
   if on_chain < db_total:
       TRIGGER CIRCUIT BREAKER
       - Halt all withdrawals
       - Alert engineering
       - Log the deficit
```

**RPC calls:**

```json
// Get account balance
{"action": "account_info", "account": "nano_1hotwallet..."}
```

Response includes `"balance"` in raw units.

```json
// Get pending receivables
{"action": "receivable", "account": "nano_1hotwallet...", "source": true}
```

Response includes a list of pending send block hashes and their amounts.

**Reference:** [RPC account_info](https://docs.nano.org/commands/rpc-protocol/#account_info), [RPC receivable](https://docs.nano.org/commands/rpc-protocol/#receivable)

### 5. Normative Payment Lifecycle Guidance

Every scenario your system must handle:

| Scenario | What happens | What to do |
|---|---|---|
| **Exact Payment** | Confirmed send matches invoice amount | Credit invoice, publish receive, dispatch |
| **Underpayment** | Confirmed send is less than invoice | Hold, notify user, await remainder or timeout |
| **Overpayment** | Confirmed send exceeds invoice | Credit invoice, track excess for refund |
| **Duplicate Payment** | Second send to one-time invoice account | Do NOT double-credit, route to manual review |
| **Late Payment** | Send confirmed after invoice expiration | Do not auto-fulfill, queue for user decision |
| **Expired Invoice** | No payment before expiration | Mark as "Expired", stop monitoring |
| **Partial Payment** | Multiple sends accumulating | Track total, apply underpayment rules on timeout |
| **Refund** | Returning funds | Do NOT refund to source address (may be exchange), request verified address off-chain |
| **Exchange Source** | Deposit from shared hot wallet | Do NOT assume source address = user |
| **Indexer Downtime** | Your system missed blocks | Buffer notifications, process idempotently on recovery |
| **Receive Delay** | Delay between send confirmation and your receive | Credit based on confirmed send, not on your receive timing |
| **Confirmation Delay** | Block not yet cemented | Do NOT credit, show "Pending confirmation" in UI |

**Publishing a receive block:**

```json
{
  "action": "process",
  "json_block": true,
  "subtype": "receive",
  "block": {
    "type": "state",
    "account": "nano_1yourdeposit...",
    "previous": "...",
    "representative": "nano_1rep...",
    "balance": "...",
    "link": "ABC123..."
  }
}
```

**Reference:** [RPC process](https://docs.nano.org/commands/rpc-protocol/#process)

### 6. End-to-End Deposit Flow

Complete walkthrough of one deposit, from invoice to dispatch:

**Step 1: Create invoice**
- Generate unique deposit account (see ORIS-007: Invoice Deposit Account)
- Store invoice in database: `{invoice_id, deposit_account, amount, status: "pending"}`

**Step 2: Subscribe to confirmations**
```json
{"action": "subscribe", "topic": "confirmation", "options": {"accounts": ["<deposit_account>"]}}
```

**Step 3: Confirmation arrives**
- Check `message.block.subtype == "send"`
- Check `message.block.link_as_account == deposit_account`
- Check `message.hash` not already processed (idempotency)

**Step 4: Verify amount**
- Compare `message.block.amount` to invoice amount
- Apply Section 5 lifecycle rules

**Step 5: Credit and receive**
- Begin database transaction
- Update invoice status
- Credit user balance
- Commit transaction
- Publish receive block via `process` RPC

**Step 6: Dispatch**
- Trigger application event (ship goods, grant access, etc.)

**Fallback: RPC polling**
If WebSocket misses a confirmation, poll `block_info` for pending invoice hashes every 5–10 seconds.

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

6. Compare message.block.amount to invoice amount:
   Exact → credit, publish receive, dispatch
   Under → hold, notify user, await remainder
   Over → credit invoice, track excess

7. Publish receive block via "process" RPC
8. Trigger application event
```

**RPC fallback (if WebSocket missed it):**
```
For each pending invoice (status == "pending", created > 5 seconds ago):
    Call block_info(invoice.expected_block_hash)
    If confirmed == true:
        Process via steps 4–8 above
```

### 8. Integration Checklist

Before going live:

- [ ] WebSocket subscription to `confirmation` topic with `ack: true`
- [ ] Account filtering enabled (`options.accounts` set to deposit accounts)
- [ ] Idempotent handler (duplicate `message.hash` ignored)
- [ ] Subtype filter (only process `subtype: "send"`)
- [ ] Lock-and-debit-before-broadcast for withdrawals (Section 2)
- [ ] Unique constraint on withdrawal transaction keys (Section 2)
- [ ] Handlers for all 12 payment lifecycle scenarios (Section 5)
- [ ] Reconciliation engine running every 60 seconds (Section 4)
- [ ] Circuit breaker triggers halt + alert on deficit
- [ ] RPC fallback polling for missed WebSocket confirmations
- [ ] Refund logic handles exchange/custodial sources (Section 5)
- [ ] Never refund to incoming source address without verification

## Architectural Hygiene and Privacy Guidelines

**Bound ledger footprint.** Don't create massive pools of unused accounts. Don't generate unsolicited dust.

**Keep metadata off-chain.** Invoices, user data, and order details belong in your database, not on the ledger. Bind them to ledger events via block hashes or deposit accounts.

**Design for wallet diversity.** Your users' wallets may display only 6 decimal places, may auto-receive, may delay receives, and may hide dust amounts. Base your credit logic on confirmed send blocks, not on the user's receive behavior.

**Prevent on-chain linkage.** When consolidating deposits from per-invoice accounts to your hot wallet, the sweep transactions link all those accounts on-chain. Use batched sweeps and multiple destinations to reduce linkability. Never expose your extended public keys to clients.

## Glossary

- **Block lattice** — Nano's data structure where each account has its own blockchain
- **Cemented** / **Confirmed** — permanently locked by network consensus; check via WebSocket or `block_info` RPC
- **Circuit breaker** — automated halt of withdrawals when reconciliation detects a deficit
- **Cold wallet** — offline storage for the majority of funds
- **Confirmation height** — the cemented chain length; only blocks at or below this height are irreversible
- **Hot wallet** — online wallet used for automated deposits/withdrawals
- **Pending receivable** — a confirmed send that hasn't been claimed by a receive block
- **Receive block** — the block the receiver publishes to claim a pending send
- **Send block** — the block the sender publishes to initiate a transfer
- **`account_info`** — RPC command returning account balance, frontier, and representative
- **`block_info`** — RPC command returning block details including `confirmed` status
- **`receivable`** — RPC command listing pending incoming sends for an account
- **`process`** — RPC command that publishes a signed block to the network
- **WebSocket confirmation topic** — real-time notifications of confirmed blocks
