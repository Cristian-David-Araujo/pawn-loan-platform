# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands assume the repository root unless noted. The root `.env` is the single source of truth for both apps (`vite.config.ts` sets `envDir: '../..'`; the API resolves the nearest parent `.env` in `settings.py`).

```bash
# Full stack (containers)
docker compose up --build -d
docker compose up --build api-server        # single service

# Recommended hybrid: DB in Docker, apps local
docker compose up -d postgres
```

Backend (`apps/api-server`), requires env vars exported from root `.env` and `DATABASE_URL` pointing at `localhost` (not `DATABASE_URL_DOCKER`):

```bash
pip install -e ".[dev]"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
pytest                                       # whole suite
pytest tests/test_payments.py::test_name -v  # single test
ruff check .                                 # line-length 100
alembic upgrade head
alembic revision --autogenerate -m "describe_change"
python -m src.infrastructure.tasks.bootstrap_db --seed [--force-seed]
```

Frontend (`apps/web-client`):

```bash
npm run dev -- --host 0.0.0.0 --port 5173
npm run typecheck    # vue-tsc -b — the only automated frontend gate (no tests, no ESLint)
npm run build        # typecheck + vite build; build:ci skips typecheck
```

Dev URLs: web `:5173`, Swagger `:8000/docs`, health `:8000/health`. Default dev admin is `admin` / `admin123`.

## Architecture

Monorepo: `apps/api-server` (FastAPI + SQLAlchemy 2.0, Python 3.12), `apps/web-client` (Vue 3 + Vite + TS), PostgreSQL 16.

### Backend layout — where code actually lives

The tree contains clean-architecture placeholder packages (`src/application/`, `src/domain/entities/`, `src/domain/rules/`, `src/domain/value_objects/`, `src/api/v1/routes/`) that are **empty**. Real code is in:

- `src/modules/<domain>/` — one package per domain (`authentication`, `customers`, `loans`, `collateral`, `payments`, `finance`, `reporting`, `settings`, `backup`), each with `router.py` (routes + business logic inline) and `schemas.py` (Pydantic). Business logic mostly lives in the routers; the extracted service modules are all under `finance/`: [interest_generation.py](apps/api-server/src/modules/finance/interest_generation.py), [interest_balance.py](apps/api-server/src/modules/finance/interest_balance.py) and [loan_status.py](apps/api-server/src/modules/finance/loan_status.py). `reporting` has no `schemas.py` — its four `/reports/*` endpoints return plain dicts.
- `src/infrastructure/persistence/models.py` — **all** SQLAlchemy models in one file.
- `src/domain/enums/` — `LoanType`, `LoanStatus`, `UserRole` only.
- `src/shared/dependencies/` — `get_db`, `get_current_user`, `require_roles(*roles)`.
- `src/api/v1/router.py` — aggregates module routers under `/api/v1`.

Routers carry their own prefix (`/customers`, `/payments`, `/collateral-items`, `/reports`, `/settings`); `authentication`, `loans`, and `finance` declare no prefix and spell paths out (`/auth/login`, `/loans`, `/loan-applications`, `/interest/generate`, `/loans/{id}/balance`, `/loans/{id}/ledger`).

There is **no `users` module** — user management (`GET/POST/PUT /users`) lives in [authentication/router.py](apps/api-server/src/modules/authentication/router.py) alongside login, refresh, and the forgot/reset-password pair.

Adding an endpoint: new route in the module's `router.py` + schemas in `schemas.py`; a role dependency on every route; `write_audit(db, ...)` from [shared/utils/audit.py](apps/api-server/src/shared/utils/audit.py) after any financial or collateral mutation (it commits).

**Who may call what** — `UserRole` is `administrator` / `loan_officer` / `collector`, and the split is a policy, not an accident:

- `require_roles(administrator)` — user management, `PUT /settings`, and the whole `backup` module.
- `require_roles(administrator, loan_officer)` — everything that creates or changes credit: loan create/update/delete/renew/close/foreclose, application approval, customer writes, collateral, and **all four `/reports/*`** endpoints.
- `require_roles(administrator, loan_officer, collector)` — reads plus the payment-taking routes. A collector can take money and see the balances behind it, but cannot open a loan, release a pledge, or pull a report.
- The `finance` module is the deliberate exception: `/interest/generate`, `/loans/{id}/balance` and `/loans/{id}/ledger` take plain `get_current_user`, so any authenticated role can trigger a generation cycle. `GET /settings` is the same.

**Loan applications are an API-only surface.** `POST/GET /loan-applications` and `/loan-applications/{id}/approve` exist and write audit rows, but nothing in the web client references them — the frontend creates loans directly, and `Loan.application_id` is nullable and stays `NULL`. Approval sets a varchar `status` and stamps `reviewed_by`/`approved_by`; it does **not** create the loan. Don't assume an approval gate exists in front of loan creation.

### Startup side effects

[main.py](apps/api-server/src/main.py) on startup runs `alembic upgrade head` + `init_database()` when `DB_INIT_ON_STARTUP`, then starts an in-process thread scheduler for interest generation when `AUTO_INTEREST_GENERATION_ENABLED`. `init_database()` takes a PG advisory lock so multiple workers can't race on enum creation/seed. Bootstrap never overwrites the admin password unless `ADMIN_PASSWORD_RESET_ON_STARTUP=true`.

Every uvicorn worker starts its own scheduler thread, so `run_interest_generation_cycle` guards itself with `pg_try_advisory_lock(INTEREST_CYCLE_LOCK_ID)` and silently skips the cycle when another worker holds it — nothing at the DB level rejects a duplicate billing period, so losing that lock means double-charging customers. Both lock helpers in [interest_scheduler.py](apps/api-server/src/infrastructure/tasks/interest_scheduler.py) short-circuit to "acquired" on non-PostgreSQL dialects so the SQLite test suite still runs; the backup restore takes the same lock id.

### Financial model — the core invariants

Two-table payment record: `Payment` is the money received; `PaymentEvent` is the append-only allocation ledger (`payment_type`, optional `interest_charge_id`, per-bucket allocations). Reversal is explicit and flagged on both rows (`Payment.is_reversed` and `PaymentEvent.is_reversed`), never a delete.

**"Deleting" a payment means reversing it.** There is no `DELETE /payments/{id}` and there should not be — the ledger is the evidence of what was collected and given back. `POST /payments/{id}/reverse` requires a `reason` (min 3 chars) and stamps `reversed_at` / `reversed_by` / `reversal_reason` on the row, because the audit table has no read path in the application: without those columns you could see that money had been taken back but not by whom, when, or why. The reversal restores principal **per ledger row**, not from `Payment.allocated_to_principal` — one payment can pay down several loans, so crediting the flat total to `Payment.loan_id` over-restored that loan and left the others short. Only loans whose principal this reversal put back above zero are reopened.

**A `closed` loan can still owe interest.** `pay_principal` closes a loan the instant its principal hits zero, so a payment made with `allow_with_unpaid_interest` leaves a closed loan with live `InterestCharge` rows. `pending_interest_for_customer` therefore includes closed loans *that still owe*, and `principal-context` carries them so printed balances report the real figures — it used to filter every closed loan out, which made that debt uncollectable (absent from the interest screen and from allocation) and made the receipt print "settled in full, nothing pending" over a live debt. Closed-and-settled loans stay excluded, which is what keeps history out of the collection views. Consumers that act on principal (the payment tab, `_resolve_principal_targets`) filter on `outstanding_principal > 0` rather than on status.

**Every read of pending interest must go through [interest_balance.py](apps/api-server/src/modules/finance/interest_balance.py)** — it is the single canonical calculation, shared by the collection endpoints, `Loan.interest_due` and the overdue transition job. It derives balances from non-reversed `PaymentEvent` rows against `InterestCharge.amount`; `InterestCharge.status` is a denormalized cache (kept in sync by `sync_interest_charge_statuses`) and must never be treated as the source of truth. Do not add a second inline pending-interest computation — that divergence was a live bug.

- **Interest accrual**: monthly `InterestCharge` rows anchored on `loan.disbursement_date`'s day-of-month, amount = `outstanding_principal * monthly_interest_rate / 100`. Generated on loan creation (if disbursement is in the past), by the scheduler, and via `POST /interest/generate`. `GlobalSettings.interest_generation_lead_days` (default 10) is added to "today" so upcoming periods appear early. Existing `(period_start, period_end)` pairs are never duplicated.
- `generate_missing_...` only adds; `recalculate_interest_charges_for_loan` (used by `PUT /loans/{id}`) refreshes amounts, deletes obsolete unpaid periods, and pins periods that already have linked `PaymentEvent`s to `paid` so historical links survive.
- **Grace days are portfolio policy, not a loan property.** A charge's due date is `period_end + grace_days`, where grace comes from `GlobalSettings.default_grace_days` via `grace_days_for_loan()`. It used to come from `Loan.due_day`, which the create form filled with the *day-of-month of the disbursement date* — so a loan signed on the 25th silently got 25 days of grace and one signed on the 3rd got three. `due_day` is still stored and kept aligned with the setting on create/update/renew, but nothing reads it for penalties. A loan with `late_penalty_rate == 0` gets **zero** grace: grace only postpones the penalty, so on a penalty-free loan it would just park the debt as "upcoming" and hide it from the collection screens. Past the due date, penalty = `pending * late_penalty_rate / 100`.
- **One charge per billing period is enforced by the database** (`uq_interest_charge_period` on `loan_id, period_start, period_end`). The advisory lock only makes the collision rare: `POST /interest/generate` used to run without it while the scheduler held it, both read "period missing", both inserted, and customers were billed — and in two cases paid — twice. The endpoint now takes the same lock and returns 409 when the cycle is already running, but the constraint is what makes the duplicate impossible.
- **Interest payments are always allocated oldest-charge-first** — selection hints from the client are accepted but deliberately ignored ([payments/router.py](apps/api-server/src/modules/payments/router.py)). Within a charge: penalty before interest. Leftover money becomes an `interest_advance_payment` event with `interest_charge_id = NULL`; that advance pool is then netted against future pending charges when computing balances.
- **Principal payments** are blocked while accrued interest is unpaid unless `allow_with_unpaid_interest`, can't exceed `outstanding_principal`, and auto-close the loan at zero. `POST /payments/principal` takes either `loan_id` (one loan) or `customer_id` + `selected_loan_ids` / `pay_all_outstanding`, and spreads the money over the targets oldest-disbursement-first, one `PaymentEvent` per loan under a single `Payment`. Two deliberate asymmetries with interest: **the client's loan selection is honoured** (an operator settling a specific loan must not have the money sent elsewhere), and there is **no advance pool** — money that cannot be fully applied is a 400, validated up front so a rejected payment writes nothing.
- **`active` ↔ `overdue` is automatic**, owned by `refresh_overdue_loan_statuses` and run inside the interest cycle (scheduler and `POST /interest/generate`). `closed` and `defaulted` are terminal states set only by explicit operator actions; the job never touches them.
- **Renewal** (`POST /loans/{id}/renew`) never mutates the source loan's numbers: it closes the source and inserts a *new* `Loan` whose `principal_amount` and `outstanding_principal` are the source's outstanding, `disbursement_date` is today (so the interest anchor day moves), and `renewal_of` points back at the source. Rate and `due_day` are inherited unless overridden in the payload.
- **Foreclosure** (pawn loans only) sets `LoanStatus.defaulted` and flips `in_custody` collateral to `for_sale`.
- **Custody hand-back is never automatic.** `POST /collateral-items/{id}/release` and `POST /collateral-items/loans/{id}/release` flip `in_custody` → `released`, and both require the loan to owe *nothing* — zero principal **and** zero pending interest via `pending_interest_total_for_loan`. Principal alone is not enough: a loan closed with `force` can sit at zero principal with interest still owed, and returning the pledge then gives away the only leverage to collect it. Settling a loan only *offers* the hand-back, because handing over goods is a counter action — a customer may pay today and collect next week, and auto-releasing would make the custody report claim an empty vault. The offer is a checkbox in the principal collection form (shown only when the entered amount would actually free pledges, default off) plus a permanent action on the custody tab of `CollateralsView`; it is deliberately not a modal, since the payment flow already spends its one confirmation on the money. When a payment releases pledges, the receipt prints them with a signature line so the document doubles as the delivery record.
- Customers with loans or applications cannot be deleted — 409 `"related credit records"`; the frontend matches on that substring to show an archive-instead message.
- **A loan is blocked by *live* money, not by history.** `DELETE /loans/{id}` refuses (409) only while a non-reversed `Payment`/`PaymentEvent` exists, when the loan was renewed into another, or when a payment on it also touches another loan (unwinding one side would leave that payment describing money it no longer accounts for). Reversed rows do **not** block: a loan paid off by mistake, reversed, and then removed is the whole point — blocking it left operators with a phantom loan they could neither collect nor delete. Each refusal has its own message and its own store-mapped translation, because "cannot be deleted" gave no hint that reversing the payments first would work.
- When a loan *is* deletable the delete cascades to its `PaymentEvent`, `Payment`, `CollateralItem` and `InterestCharge` rows (children first — events reference both payments and charges), so the `delete_loan` audit entry carries a full snapshot: customer, amounts, rate, dates, every pledge with its custody code and value, every accrued period, and every reversed payment with its reversal reason. It is written **in the same transaction** as the delete — an audit row that can be lost while the delete survives reads as "this never existed".
- Use `get_local_date(db)` / `get_local_datetime(db)` (reads `GlobalSettings.timezone`, default `America/Bogota`) for "today" — not `date.today()`.
- **`GlobalSettings` is a single row, `id=1`**, created on demand by `_ensure_global_settings` — never query it as a collection. It is where portfolio-wide policy lives (`default_grace_days`, `interest_generation_lead_days`, `default_late_penalty_rate`, `timezone`, `date_format`, `currency_code`, plus the company identity printed on documents), so a knob that should apply to the whole book belongs here rather than as a new `Loan` column — that is exactly the mistake grace days made.

Export/import (`GET /backup/export`, `POST /backup/import`, admin only) discover tables and columns from `Base.metadata.sorted_tables` rather than a hand-written list, so **a new model column is carried automatically**. Keep it that way — never hardcode field lists in [backup/service.py](apps/api-server/src/modules/backup/service.py) or [backup/restore.py](apps/api-server/src/modules/backup/restore.py), or backups start silently losing data. Live password-reset tokens are the only redacted fields.

The import is a **full replace**, not a merge: it wipes every table and reloads from the archive in one transaction, so a mid-restore failure leaves the data untouched. Its guards are load-bearing — refuses on a schema-revision mismatch, on column drift, on a missing table, and on an archive without an active administrator; requires the typed phrase `REPLACE ALL DATA`; takes the interest-cycle advisory lock so the scheduler cannot write mid-restore; and realigns PostgreSQL identity sequences afterwards (without that, the next insert collides with a restored id). `validate_only=true` returns the plan without writing.

`Loan.interest_due`, `Loan.collaterals_count`, and the `CollateralItem.loan_*` properties issue queries via `object_session`, so they only work on session-attached instances and are N+1 by nature in list endpoints. When you need balances for many loans at once, call `pending_interest_for_loans` (fixed query count) instead of the per-row property.

### Frontend patterns

- **No Pinia/Vuex.** [platformStore.ts](apps/web-client/src/stores/platformStore.ts) is a module-level `reactive()` singleton exported as `usePlatformStore()`; [authState.ts](apps/web-client/src/modules/authentication/authState.ts) is the same pattern for the session.
- The store owns the shared entity cache (customers, loans, collateral, payments, settings) and calls `refreshAll()` after every mutation — a full 5-endpoint refetch, not a local patch. Mutations return `{ ok, messageKey }` for the caller to translate.
- **snake_case → camelCase mapping is manual** in the store's `mapCustomer`/`mapLoan`/`mapCollateral`/`mapPayment`/`mapGlobalSettings` functions, with `BackendXxx` interfaces mirroring API shapes. Adding an API field means touching the `Backend*` interface, the mapper, and `types/domain.ts`. Note `in_custody` ↔ `in-custody` is remapped, and customer `fullName` is split/joined into `first_name`/`last_name`.
- Payment/user/print flows bypass the store and call `apiClient.request` directly (`PaymentsView`, `UsersView`, `CustomersView`, `InvoicePrintView`) with snake_case bodies.
- Payments are listed in three places — `PaymentsView`'s history, the payments tab of the customer detail in `CustomersView`, and the loan payments table in `LoanDetailModal` — and all three delete through [PaymentReversalModal.vue](apps/web-client/src/components/PaymentReversalModal.vue), which owns the reason field, the minimum length, the request and the error display. Put the delete action anywhere new by mounting that component, not by copying the modal: the wording and the enforced minimum are what make a removal answerable the same way everywhere. `LoanDetailModal` refreshes the store itself and emits `payments-changed` so its parent can reload whatever it fetched separately.
- The two collection tabs in `PaymentsView` (interest, principal) are deliberately the same shape and share their moving parts: [useRowSelection.ts](apps/web-client/src/composables/useRowSelection.ts) owns the tick-a-row `Set` (and prunes ids whose row disappears — the hand-rolled version kept the previous customer's selection, which was harmless for interest but would move real money for principal), and [PaymentCollectionForm.vue](apps/web-client/src/components/PaymentCollectionForm.vue) owns the identical amount/method/suggested/print/submit footer, with each tab's summary lines passed through its default slot. Both tabs open with every row ticked and the amount prefilled to that total; typing in the amount field raises a `touched` flag that stops it re-syncing. Put new shared behaviour in those two, not in a third copy.
- **Destructive confirmations are one global modal, not a local `ref`.** [useConfirmDialog.ts](apps/web-client/src/composables/useConfirmDialog.ts) holds its state at module level (same singleton trick as the store), a single `<ConfirmModal>` is mounted once in [App.vue](apps/web-client/src/App.vue), and callers `await confirm(t('...'))` for a boolean — `LoansView`, `CustomersView`, `CollateralsView`, `PaymentsView` and `LoanDetailModal` all go through it. Because the state is shared, only one confirm can be open at a time; don't open a second from inside a resolved handler. Payment removal is the exception and belongs to `PaymentReversalModal` (above), which needs a typed reason rather than a yes/no.
- Long tables pair [usePagination.ts](apps/web-client/src/composables/usePagination.ts) with `Pagination.vue`; the composable resets to page 1 only when the source array's *length* changes, so a same-length re-sort keeps the current page.
- [api.ts](apps/web-client/src/services/api.ts) injects the bearer token, and on 401 logs out and hard-navigates to `/login`; it throws `new Error(await response.text())` so callers pattern-match on message substrings.
- Auth is JWT in `localStorage`; [router/index.ts](apps/web-client/src/router/index.ts) guards on `meta.requiresAuth` / `meta.guestOnly` / `meta.roles` and fetches `/auth/me` lazily.
- **i18n is mandatory**: all UI strings go through `vue-i18n` keys defined in [messages.ts](apps/web-client/src/i18n/messages.ts) — every key must be added to **both** the `en` and `es` blocks. Locale persists to `localStorage`. Note `t()` renders a *missing* key as the key itself, so a typo or an unmapped value silently ships raw text like `common.loading` to the user instead of failing — worth a grep for unresolved `t('ns.key')` references after touching translations.
- `PaymentEvent.payment_type` is translated only through `paymentTypeKey()` in [utils/paymentTypes.ts](apps/web-client/src/utils/paymentTypes.ts). That map used to be copy-pasted into `PaymentsView`, `CustomersView` and `InvoicePrintView`, which had each drifted out of sync with the API — `partial_interest_payment`, `full_settlement` and `collateral_sale` were missing from two of them and leaked out untranslated. Adding a type server-side means adding it there, in one place.
- **Styling is plain CSS with design tokens**, no Tailwind. All tokens (`--accent`, `--surface`, `--radius`, `--shadow-*`, `--transition`) and shared classes (`.modal-backdrop`, `.form-section`, `.empty-state`, tables, buttons) live in [main.css](apps/web-client/src/assets/main.css). Reuse tokens and existing classes; don't introduce hardcoded colors or a CSS framework.
- Date display/parsing goes through [utils/date.ts](apps/web-client/src/utils/date.ts), whose global format is set from `GlobalSettings.dateFormat` on load. Send ISO (`YYYY-MM-DD`) to the API via `toIsoDate`.
- UI conventions from `.agents/skills/`: create/edit forms belong in modals (or a dedicated route), triggered from `PageHeader`'s `#actions` slot — never inline forms above a table; always render an `.empty-state` instead of a bare table header; group fields in `.form-section` with a title; mobile-first with AA contrast and visible focus states.

### Printable documents

All four printable documents are one component, [InvoicePrintView.vue](apps/web-client/src/views/InvoicePrintView.vue), on a single route `/print/invoice/:type/:id` that sits **outside** `AppLayout` (no nav chrome) and calls `window.print()` ~500 ms after mount. `:type` selects the document — `payment` (receipt), `loan` (loan statement), `customer` (customer statement), `history` (payment history) — and the `isLoan` branch is the fallback, so an unknown `:type` renders a loan statement rather than erroring. Callers are plain `<a target="_blank">` links (or `router.push` right after creating a loan/payment) in `LoansView`, `PaymentsView`, `CustomersView`, and `LoanDetailModal`.

Every document is dated the day it is printed; the dates that belong to the fact itself — the loan's disbursement, the payment's date — are printed in the body, so a reprint cannot pass itself off as having been issued back then. The loan document's "payment day" is the day-of-month of the disbursement, which is what anchors the billing cycle — it used to print `dueDay`, and once grace days moved to a global setting that read "payment day: 0 of each month". It is derived by `billingAnchorDay()` in [utils/date.ts](apps/web-client/src/utils/date.ts), shared with `LoanDetailModal`'s pill; anywhere else that wants to show a loan's billing day should call it rather than read `dueDay`, which no longer means anything to a customer.

There is **no HTML-rendering print endpoint on the backend**. The view reads the store for entity data and fetches figures directly: `/payments/customers/{id}/principal-context` (per-loan payoff figures), `/payments/customers/{id}/interest-pending` (the pending periods behind them), `/payments/{id}/allocations` (the receipt's distribution breakdown) and, for `history`, `/payments/customers/{id}/history`. For a `payment` receipt those calls run *after* the payment, so the figures printed are the balances remaining afterwards. A failed fetch is swallowed — the document still prints with whatever the store held.

Because the view destructures those responses by exact field name, renaming one server-side prints zeros instead of failing. [tests/test_printable_statements.py](apps/api-server/tests/test_printable_statements.py) exists solely to pin that contract (field names plus the arithmetic) — update it in the same change as any rename, and don't treat it as a redundant duplicate of the payments tests.

`GET /payments/{id}/allocations` exists because `Payment` alone cannot explain itself: it stores only per-bucket totals and its `loan_id` is just the *first* loan touched, while one payment routinely settles several `InterestCharge`s across several loans (allocation is oldest-first). The endpoint returns the `PaymentEvent` rows in `id` order — the real order the money was applied — enriched with each charge's own amount and due date, so the receipt can print "this $100k covered invoice A in full and invoice B partially". `fully_covered` is derived from the `partial_interest_payment` type stamped at creation, not recomputed. Payments made through the plain `POST /payments` path have no ledger rows, so the list comes back empty and the receipt falls back to the per-bucket summary table.

The `loan` document also prints the pledged items (custody code, description, appraised value, plus an appraised total) from `state.collateralItems` filtered by `loanId` — no extra fetch. Columns appear only when they carry information: `item_type` and `serial_number` default to `general`/empty and have no form field anywhere; `status` is `in_custody` for every item on a freshly issued document, so it shows up only on a reprint after a foreclosure/release/sale.

**`physical_condition` is deliberately not printed.** It defaults to `"good"`, no UI collects it, and `CollateralUpdate` omits it, so it can never be edited — every row in a real database carries the default. Printing it would assert on a customer-facing document that the item was inspected and found in good condition when no such assessment was ever recorded. The test for whether a defaulted field may be printed is whether its fallback reads as "nothing recorded" (empty serial, `general` type — safe to hide) or as a substantive claim (`good` — must not be shown). If a form field for it is ever added, printing it becomes legitimate.

`CollateralItem.status` is a plain varchar, not an enum, and `PUT /collateral-items/{id}` writes `payload.status` through unvalidated. The values endpoints actually produce are `in_custody` (create), `for_sale` (foreclosure), `released`, `liquidated` and `sold`. **`returned` is written only by [seed.py](apps/api-server/src/infrastructure/persistence/seed.py) — no endpoint ever sets it**, yet it is carried in `types/domain.ts` and labelled in `CollateralsView`, sitting confusingly next to the real `released`. Treat it as demo-data residue rather than a domain state.

Print styling is deliberately restrained — whitespace carries the structure. One accent colour, one emphasis weight (`.balance-value`), one hairline, `.doc-section` + `.section-title` for every block in all four documents. No panel fills, no header-row fills, no bordered pills. Columns that would be all zeros are dropped rather than printed empty, and `@media print` forces `print-color-adjust: exact` (browsers drop backgrounds, which would erase every status pill) plus `table-header-group` so long tables repeat their header. When adding to these documents, reuse those two classes instead of introducing another sectioning device.

## Tests

`pytest` only, in `apps/api-server/tests/`, one file per module. [conftest.py](apps/api-server/tests/conftest.py) builds a fresh app per test with `get_db` overridden, plus `auth_headers`, `create_customer`, and `create_loan` fixtures; tests exercise endpoints end-to-end through `TestClient`. The scheduler is disabled in the `app` fixture.

A few files guard cross-cutting invariants rather than one module, and are easy to mistake for duplicates: `test_printable_statements.py` (frontend field contract, above), `test_interest_scheduler_lock.py` (multi-worker cycle lock), `test_payment_reversal.py`, `test_loan_status.py` (the automatic `active` ↔ `overdue` job), and `test_backup_import.py` (the full-replace guards).

The engine is **in-memory SQLite by default**, or PostgreSQL when `TEST_DATABASE_URL` is set — CI sets it, so the suite runs on both. Backend code must therefore stay SQLite-compatible (no PG-only SQL outside the guarded bootstrap). To reproduce the CI run locally:

```bash
docker compose up -d postgres
TEST_DATABASE_URL=postgresql+psycopg://<user>:<pass>@localhost:5432/pawn_loan_db pytest -q
```

## CI, migrations, and branching

- **Quality checks** ([quality-checks.yml](.github/workflows/quality-checks.yml)) gate PRs into `main`/`develop`: `ruff check .` + `pytest` on PostgreSQL, and `vue-tsc` on the web client. Run all three locally before pushing. Migration scripts are excluded from ruff (`extend-exclude` in [pyproject.toml](apps/api-server/pyproject.toml)).
- **Alembic migration guard**: any PR touching `models.py` or `src/domain/enums/*.py` must include a new file in `apps/api-server/alembic/versions/` or CI fails. Generate it with `alembic revision --autogenerate -m "..."` before pushing.
- **GitFlow guard**: PRs into `main` are only accepted from `release/*`, `hotfix/*`, or `develop`. Work lands on `develop` first.
- Merging to `main` auto-tags `vX.Y.Z` (version derived from the branch name) and deploys to DigitalOcean via `docker-compose.prod.yml`. See [docs/ci-cd-digitalocean.md](docs/ci-cd-digitalocean.md) and [docs/deployment-digitalocean.md](docs/deployment-digitalocean.md).
- `LoanType`/`LoanStatus` use native PG enums, so adding a value needs a migration that alters the type; `UserRole` uses `native_enum=False` (varchar).

The functional spec and business-rule table live in [.github/loan-management-system-requirements-and-software-design.md](.github/loan-management-system-requirements-and-software-design.md).
