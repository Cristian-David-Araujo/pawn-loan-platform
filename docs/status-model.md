# The status model

Every state in the product, in one place. Loans first, then the other entities.

**The rule across all of them: a status the application branches on is a typed enum in
code.** `native_enum=False` where it is new, the way `UserRole` already does it — Python and
Pydantic reject anything outside the list, but adding a value later needs no `ALTER TYPE`,
which is the tax `LoanStatus` pays for being a native Postgres enum. Two columns were plain
`str` with no validation at all, and both had already been exploited: any string could be
stored in a pledge's status, and any string other than `active` renders a customer as
archived.

---

# Loans

`LoanStatus` has four values. This is what each one means, what moves a loan between them, and
who owns each transition — written down because the answer used to be spread across the
interest cycle, three payment routes, four operator actions and a collateral sale, with no
single place saying which was authoritative.

It is also the source for the words shown on screen and on printed documents; see
[§5](#5-what-each-state-is-called).

---

## 1. The four states

| State | Means | Who owns it |
| :--- | :--- | :--- |
| `active` | Open, and **no billing period is past its due date**. The loan may owe interest and principal — it is simply not late. | Derived. `refresh_overdue_loan_statuses` |
| `overdue` | Open, and **at least one billing period is past its due date with a balance outstanding**. | Derived. `refresh_overdue_loan_statuses` |
| `closed` | The debt is finished, or has been declared finished. | An operator action |
| `defaulted` | The lender has stopped collecting through interest and will collect through the pledge. | `POST /loans/{id}/foreclose` |

**`active` and `overdue` are derived, not decided.** Nothing should ever set them by hand: they
are a function of the interest ledger, and the only writer is
[loan_status.py](../apps/api-server/src/modules/finance/loan_status.py). `closed` and
`defaulted` are decisions, and only an operator makes them.

Two facts that are easy to assume and are wrong:

- **A `closed` loan can still owe interest.** `pay_principal` closes a loan the instant its
  principal reaches zero, so paying with `allow_with_unpaid_interest` leaves a closed loan with
  live `InterestCharge` rows. That debt is real and is still collected.
- **`interest_paused` is not a status.** A paused loan is still `active` or `overdue`; the
  pause only stops *new* charges and *new* penalties. Interest already billed stays owed and can
  still turn the loan `overdue` — a pause is an agreement about what comes next, not a way to
  make existing arrears disappear from the reports.

---

## 2. What moves a loan

```mermaid
stateDiagram-v2
    [*] --> active: create, renew

    active --> overdue: a period passes its due date unpaid
    overdue --> active: the past-due balance is settled

    active --> closed: principal reaches zero · close · settle · renew (the source)
    overdue --> closed: principal reaches zero · close · settle · renew (the source)

    active --> defaulted: foreclose
    overdue --> defaulted: foreclose

    closed --> active: payment reversal restores principal
    defaulted --> closed: the pledge sells for enough to cover the debt

    closed --> [*]
    defaulted --> [*]
```

### Every writer of `Loan.status`

| # | Site | Transition | Trigger |
| :-- | :--- | :--- | :--- |
| 1 | `loans/router.py` · `create_loan` | → `active` | A loan is opened |
| 2 | `loans/router.py` · `renew_loan` | → `active` | The new loan |
| 3 | `loans/router.py` · `renew_loan` | → `closed` | The source loan, with its outstanding zeroed |
| 4 | `loans/router.py` · `close_loan` | → `closed` | Operator, with a reason when it still owes |
| 5 | `loans/router.py` · `foreclose_loan` | → `defaulted` | Operator, pawn loans only |
| 6 | `payments/router.py` · `pay_principal` | → `closed` | Principal reached zero |
| 7 | `payments/router.py` · `create_payment` | → `closed` | Principal reached zero (legacy path) |
| 8 | `payments/router.py` · `reverse_payment` | `closed` → `active` | Restored principal put it back above zero |
| 9 | `collateral/router.py` · `sell_collateral` | → `closed` | Proceeds covered the whole debt |
| 10 | `finance/settlement.py` · `settle_loan` | → `closed` | Negotiated settlement |
| 11 | `finance/loan_status.py` | `active` ↔ `overdue` | Derived from the ledger |

Rows 1–10 are decisions or consequences of money moving. Row 11 is the only derivation, and it
is the only one allowed to write `active` or `overdue` on an existing loan.

---

## 3. Neither `closed` nor `defaulted` is terminal

The code used to claim both were, and in two places that was already false. Both exits are
deliberate:

- **`closed` → `active`**, when reversing a payment restores principal above zero. A loan
  closed by a payment that turned out to be a mistake has to come back; the alternative is a
  live debt sitting in a terminal state.
- **`defaulted` → `closed`**, when the pledge sells for enough to cover everything. The credit
  ended up settled, and `closed` describes that better than `defaulted` does.

What *is* guaranteed: the derived sweep never moves a loan out of `closed` or `defaulted`.
`MANAGED_STATUSES` is `(active, overdue)` and everything else is invisible to it — which is what
lets `pay_principal` close a loan and immediately run the refresh without the refresh undoing it.

---

## 4. When the derivation runs

`refresh_overdue_loan_statuses(db, as_of_date, loan_ids=None)` — unscoped it sweeps every managed
loan; scoped it re-examines a known set. Narrowing changes which loans can transition, never how
one is judged: `pending_interest_for_loans` nets each customer's whole book internally, so a loan
reaches the same verdict either way.

| Caller | Scope | Why |
| :--- | :--- | :--- |
| `run_interest_generation_cycle` | everything | Reacting to the calendar, not to an event |
| `POST /interest/generate` | everything | The same cycle, run by hand |
| `pay_interest` | the customer's **whole book** | Allocation is oldest-first across every loan they hold and the advance pool is theirs, so paying on one loan can settle a period on another |
| `pay_principal` | the loans it touched | Principal cannot by itself make a loan overdue; this is here so the rule holds without exception |
| `reverse_payment` | the loans it touched | Putting the debt back must put the label back |

**The rule: every money path leaves the status correct before it commits.**

It used to run only inside the interest cycle, so the label lagged the money by up to
`AUTO_INTEREST_GENERATION_INTERVAL_MINUTES` — **a full day at the default of 1440**. A customer
paid their arrears at the counter, took a receipt, and the loan still read `overdue` until the
next night's run. That is the defect this section exists to prevent returning.

The transition is recorded inside the payment's own audit entry (`to_overdue=[…],to_active=[…]`)
rather than as a separate row, so the change travels with the event that caused it.

---

## 5. What each state is called

One stored value, two audiences, and therefore two vocabularies. Both live in
[utils/loanStatus.ts](../apps/web-client/src/utils/loanStatus.ts); three views had each grown
their own copy before that.

| Stored | On screen (operator) | On a printed document (customer) |
| :--- | :--- | :--- |
| `active` | Activo / Active | **Al día / Up to date** |
| `overdue` | Vencido / Overdue | En mora / Overdue |
| `closed` | Cerrado / Closed | Saldado / Settled |
| `defaulted` | Incumplido / Defaulted | Ejecutado / Foreclosed |

The operator's screens name the **lifecycle** — "active" means open and on the books, which is
the right word beside a filter and a portfolio count.

A printed document is read by the customer, who is not asking which lifecycle state their loan
occupies. They are asking whether they owe anything today, and that is exactly what `active`
asserts: no billing period is past its due date. So the document says **"al día"**. Printing
"Activo" answered a question nobody had and left the real one unanswered.

Neither vocabulary invents a state, and no screen may add a fifth word for a fourth value.

---

## 6. Checks

- [test_loan_status.py](../apps/api-server/tests/test_loan_status.py) — the derived sweep.
- [test_loan_status_after_payment.py](../apps/api-server/tests/test_loan_status_after_payment.py)
  — the money paths: arrears cleared at the counter, a partial payment that must *not* clear,
  one loan cleared by a payment on another, a reversal putting the loan back, and a closed loan
  the sweep must leave alone.


---

# Other entities

## Pledges — `CollateralStatus`

```
in_custody ──> for_sale ──> sold
     │             └──────> liquidated
     └──> released
```

| State | Means | Set by |
| :--- | :--- | :--- |
| `in_custody` | The lender is holding the item. | Registering a pledge |
| `for_sale` | The debt was foreclosed, or a settlement kept the item. | `foreclose`, `settle_loan` |
| `released` | Returned to the customer. **Terminal.** | `release`, `settle_loan` |
| `liquidated` | Written off without proceeds. **Terminal.** | `liquidate`, admin only |
| `sold` | Sold, proceeds applied to the debt. **Terminal.** | `sell`, admin only |

**The field is never edited directly.** `PUT /collateral-items/{id}` refuses a status different
from the stored one, because each move has a precondition only its own endpoint checks — writing
it freely once let a loan officer mark a pledge `released` on a loan with its full principal
outstanding, walking past `_assert_loan_fully_settled`.

There is no `returned`. It lived in the frontend types and one label, but no endpoint ever wrote
it — only the demo seed — and it sat beside the real `released` inviting exactly that confusion.

## Customers — `CustomerStatus`

`active` · `archived`, and it means **visibility only**: whether the customer is offered in the
pickers. A customer with credit records cannot be deleted, so archiving is the alternative.

It is deliberately **not** about whether they may borrow again. Someone in arrears must stay
visible so they can be collected from, and hiding them to stop new lending would hide them from
the screen that chases the debt. If "do not lend to this person" is ever needed, it is a separate
flag — not a third value here.

## Billing periods — derived, three states

Not a column at all. A period's state is its due date against today, plus whether it still owes,
and the middle value is the point: **vence hoy** is what sends someone to the counter.

| State | Means | On screen | On a document |
| :--- | :--- | :--- | :--- |
| `overdue` | Past its due date (period end + grace) with a balance | Vencido | En mora |
| `due_today` | Falls due today | Vence hoy | Vence hoy |
| `upcoming` | Still ahead | Próximo | Por vencer |

`overdue` is the **server's** verdict — it accounts for grace days — and it wins over the date
comparison. Only the other two are decided in the client.

One implementation, in [utils/loanStatus.ts](../apps/web-client/src/utils/loanStatus.ts). There
were three: the customers and payments screens held byte-identical copies, and the printed
statement a cruder inline one with only *two* states, so a period due in ten days read "Próximo"
on screen and "Vigente" on the statement the customer kept.

All three compared `Date` objects, and that was broken wherever it ran. `new Date('2026-08-17')`
parses as UTC midnight, which west of Greenwich is the previous evening, and `setHours(0,0,0,0)`
then lands on the previous day — so in Bogotá the "due today" branch could never be true and the
one state worth showing never appeared. ISO dates compare correctly as strings, which is what it
does now.

## Interest charges — a cache, not a state

`generated` · `partially_paid` · `paid` · `not_billed`

`InterestCharge.status` is a **denormalised summary** of a calculation that lives in
[interest_balance.py](../apps/api-server/src/modules/finance/interest_balance.py), kept in step by
`sync_interest_charge_statuses`. It is never the source of truth for what a period owes.

`not_billed` with amount 0 is the marker for a month that was deliberately never billed — a gap
the generator must not fill later, whether it came from the historical defect
[migration 0010](../apps/api-server/alembic/versions/20260727_0010_close_unbilled_periods.py)
closed or from a loan being paused.

**Voiding is not a fifth value.** `voided_at` is the fact; putting it in the cache too would
create two sources for one truth.

## Payments — no status

`is_reversed`, a boolean, on both `Payment` and `PaymentEvent`. A payment is recorded or it was
reversed; an enum of two values over a boolean is ceremony.

`PaymentEvent.payment_type` is a different axis — not what state the payment is in, but what kind
of movement it was — and it has its own single home in
[utils/paymentTypes.ts](../apps/web-client/src/utils/paymentTypes.ts).

## Users, backups

`User.is_active` is a boolean; `UserRole` is a role, not a state. `BackupRun.status` is
`success` / `failed`, written once per attempt and never updated.

## Removed: loan applications

`submitted` → `approved` used to exist on a `LoanApplication` table with three endpoints. Nothing
ever called them, `Loan.application_id` stayed `NULL` on every row, and approval did not create
the loan. A state machine nobody drives is worse than none: it advertises an approval gate in
front of lending that does not exist. Dropped in
[migration 0018](../apps/api-server/alembic/versions/20260810_0018_drop_loan_applications.py).
