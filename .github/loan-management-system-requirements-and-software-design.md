# Software Requirements Specification

## Pawn and Personal Loan Management Platform

**FastAPI + Vue + PostgreSQL + Docker**

| Item | Definition |
| --- | --- |
| Repository Scope | Modular monorepo with web client, API server, database assets, infrastructure, and documentation. |
| Core Business Modes | Pawn-backed loans and personal loans with monthly interest charging. |
| Primary Stack | Python FastAPI backend, Vue web client, PostgreSQL database, Docker-based deployment. |
| Target Architecture | Dockerized modular backend prepared for future service extraction, while remaining simple for initial delivery. |

**Version 1.0**  \|  **Date: March 30, 2026**

## Document Overview

This document defines the functional requirements, non-functional requirements, architecture, technology stack, repository structure, domain model, API scope, and delivery roadmap for a loan management platform that supports both pawn-backed and personal loans.

## 1. Executive Summary

The platform will digitize the complete loan lifecycle for businesses that lend money to individuals. It must support customer onboarding, loan applications, collateral registration for pawn operations, monthly interest accrual, payment registration, overdue management, renewal workflows, closure, collateral release, and operational reporting.

The software will be delivered as a Dockerized modular platform composed of a Vue-based web client, a FastAPI-based API server, and PostgreSQL as the system of record. The initial release will use one backend deployment with strong internal domain modularity, allowing future extraction into separate services if the business or scale requires it.

## 2. Product Scope

- Manage pawn-backed loans secured by one or more collateral items.
- Manage personal loans without physical collateral.
- Charge interest on a monthly basis according to configurable business rules.
- Track balances, payments, penalties, renewals, closures, and audit history.
- Provide a secure operations interface for staff members with role-based access control.

## 3. Objectives

- Provide a reliable and auditable lending operations system.
- Reduce manual handling errors in interest calculation and payment allocation.
- Preserve traceability for regulated and high-risk financial operations.
- Support future scalability without introducing unnecessary early complexity.

## 4. Stakeholders and User Roles

| Role | Primary Responsibilities | Key Permissions |
| --- | --- | --- |
| Administrator | Configure the platform, manage users and roles, supervise operations. | Full access, configuration changes, user administration, audit access. |
| Loan Officer | Register customers, create applications, evaluate and approve loans. | Customer management, application handling, loan creation. |
| Cashier | Register payments, print receipts, support loan settlement. | Payment intake, receipt issuance, limited reversals if allowed. |
| Collections Agent | Monitor overdue loans and collection actions. | Overdue portfolio view, collection notes, promise-to-pay records. |
| Auditor | Review sensitive operations and traceability. | Read-only access to audits, logs, balances, and critical actions. |

## 5. Business Domain Definition

### 5.1 Loan Types

**Pawn-backed loan:** a loan issued against one or more collateral items physically held in custody until the obligation is settled or the collateral is liquidated under the defined business rules.

**Personal loan:** a loan issued without physical collateral, managed through customer records, repayment obligations, and overdue controls.

### 5.2 Core Loan Lifecycle

1. Customer registration
2. Loan application creation
3. Review and approval or rejection
4. Collateral intake, when applicable
5. Loan disbursement
6. Monthly interest generation
7. Payment registration and allocation
8. Overdue and penalty processing
9. Renewal or restructuring, if allowed
10. Closure and collateral release or liquidation

## 6. Functional Requirements

### 6.1 Customer Management

- The system shall create, update, archive, and retrieve customer profiles.
- The system shall prevent duplicate customers based on document type and document number.
- The system shall keep a chronological history of the customer’s loans and major actions.
- The system shall store contact and identification data required for operations.

### 6.2 Loan Application Management

- The system shall support the creation of loan applications for both pawn-backed and personal loans.
- The system shall allow draft, submitted, under-review, approved, rejected, and cancelled application states.
- The system shall record who created, reviewed, approved, or rejected an application.
- The system shall allow notes and document attachments associated with each application.

### 6.3 Collateral Management

- The system shall register one or more collateral items for pawn-backed loans.
- The system shall store item description, condition, appraised value, serial/reference data, storage location, and item images.
- The system shall assign an internal custody code to each collateral item.
- The system shall prevent collateral release while a linked loan has outstanding debt unless an authorized liquidation process applies.

### 6.4 Loan Creation and Disbursement

- The system shall create a loan from an approved application.
- The system shall record principal amount, monthly interest rate, disbursement date, due day, and initial term.
- The system shall support cash, bank transfer, and other configured disbursement methods.
- The system shall activate the financial lifecycle immediately after disbursement.

### 6.5 Monthly Interest Accrual

- The system shall generate monthly interest charges for active loans.
- The monthly interest rate shall be configurable at product level and overridable at loan level when authorized.
- The system shall keep a historical ledger of generated interest charges.
- The system shall support recalculation after principal reductions, renewals, or defined financial adjustments.

### 6.6 Payment Management

- The system shall register partial and full payments.
- The system shall allocate payments across penalty, accrued interest, fees, and principal according to configurable allocation rules.
- The system shall generate a receipt or proof of payment.
- The system shall support controlled payment reversal with audit trail and permissions.

### 6.7 Delinquency and Collections

- The system shall identify overdue loans automatically.
- The system shall support grace periods, penalty interest, and administrative fees according to business policy.
- The system shall classify delinquency by aging ranges.
- The system shall allow collection notes, follow-up actions, and promise-to-pay records.

### 6.8 Renewals and Restructuring

- The system shall support loan renewal under business policy.
- The system shall preserve traceability between the original loan and the renewed loan cycle.
- The system shall optionally require accrued charges to be paid before renewal.
- The system shall support refinancing scenarios when principal, rate, or term changes are authorized.

### 6.9 Loan Closure

- The system shall mark a loan as closed only when principal, interest, penalties, and fees are fully settled.
- The system shall record the closure timestamp and responsible user.
- The system shall allow collateral release only after successful closure or through a dedicated authorized workflow.

### 6.10 Reporting

- The system shall provide operational reports for active loans, overdue loans, collateral custody, released collateral, liquidated collateral, payments, and cash collections.
- The system shall allow filtering by date range, loan type, status, and responsible operator.
- The system shall provide basic export support for at least CSV or spreadsheet-compatible formats.

## 7. Business Rules

| Rule | Definition |
| --- | --- |
| Interest Charging Frequency | Interest is charged per monthly cycle. Each active loan must generate one interest charge per cycle according to its configured due-day or anniversary rule. |
| Interest Base | The financial engine must support charging interest on either original principal, outstanding principal, or another approved calculation base. The selected approach must be fixed by business policy before production use. |
| Payment Allocation | Recommended default allocation order: penalties, accrued interest, fees, then principal. |
| Overdue Status | A loan becomes overdue when the due condition is reached and the minimum required payment has not been fulfilled after any configured grace period. |
| Pawn Restriction | Collateral cannot be released while any linked balance remains unpaid unless an exception flow is executed by an authorized role. |
| Renewal Policy | A renewed loan must preserve reference to its source loan and must produce a new financial cycle with updated dates and balances. |
| Audit Requirement | Every critical financial or collateral action must generate an audit entry. |

## 8. Non-Functional Requirements

### Architecture

- The platform shall be Dockerized and deployable in a repeatable way.
- The initial release shall use one API server deployment with internal modular separation by domain.
- The backend structure shall allow future extraction of modules into standalone services without rewriting business rules.

### Security

- The platform shall use secure authentication and role-based authorization.
- Passwords shall be hashed using approved algorithms.
- Tokens or session credentials shall be protected and configurable by environment.
- Sensitive operations shall require explicit authorization checks.

### Performance

- Operational screens and main APIs should respond quickly under normal business load.
- The design should support indexing and query optimization for portfolio and payment operations.

### Auditability

- Critical actions shall preserve who did what, when, and what changed.
- Financial records shall be immutable where legally or operationally necessary, with reversals represented explicitly instead of silent overwrites.

### Maintainability

- The codebase shall follow consistent naming, separation of concerns, and documented conventions.
- The project shall include automated tests, migrations, linting, formatting, and environment templates.

### Observability

- The backend shall expose health endpoints.
- The platform should support structured logs and metrics collection.

## 9. Recommended Technical Architecture

The recommended implementation model is a modular monorepo with one frontend application and one backend application. The backend is not split into many deployables at the beginning; instead, it is organized by domain modules using clean boundaries and modern layering. This keeps delivery simple while preserving long-term scalability.

| Layer | Technology | Purpose | Notes |
| --- | --- | --- | --- |
| Web Client | Vue 3 + Vite + TypeScript | Operations UI for business users | Consumes the API through HTTP/JSON. |
| API Server | Python FastAPI | Business rules, REST API, auth, domain workflows | Single deployable backend, internally modularized. |
| Database | PostgreSQL | System of record for operational and financial data | Use migrations and explicit schema evolution. |
| Runtime | Docker + Docker Compose | Local and server deployment consistency | Prepared for later orchestration if needed. |

## 10. Professional Repository Structure

Recommended top-level repository layout:

```text
pawn-loan-platform/
├── apps/
│   ├── web-client/
│   └── api-server/
├── database/
├── infrastructure/
├── docs/
├── .github/
├── docker-compose.yml
├── Makefile
├── README.md
├── .gitignore
└── .editorconfig
```

### 10.1 Web Client Structure

```text
apps/web-client/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   ├── composables/
│   ├── layouts/
│   ├── modules/
│   │   ├── authentication/
│   │   ├── customers/
│   │   ├── loans/
│   │   ├── collateral/
│   │   ├── payments/
│   │   └── reporting/
│   ├── router/
│   ├── stores/
│   ├── services/
│   ├── types/
│   ├── utils/
│   ├── views/
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── Dockerfile
```

### 10.2 API Server Structure

```text
apps/api-server/
├── src/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       └── router.py
│   ├── application/
│   │   ├── dtos/
│   │   ├── interfaces/
│   │   └── use_cases/
│   ├── domain/
│   │   ├── entities/
│   │   ├── enums/
│   │   ├── exceptions/
│   │   ├── rules/
│   │   └── value_objects/
│   ├── infrastructure/
│   │   ├── config/
│   │   ├── logging/
│   │   ├── persistence/
│   │   ├── security/
│   │   └── tasks/
│   ├── modules/
│   │   ├── authentication/
│   │   ├── customers/
│   │   ├── loans/
│   │   ├── collateral/
│   │   ├── payments/
│   │   ├── finance/
│   │   └── reporting/
│   ├── shared/
│   │   ├── constants/
│   │   ├── dependencies/
│   │   ├── middleware/
│   │   ├── schemas/
│   │   └── utils/
│   └── main.py
├── tests/
├── pyproject.toml
├── alembic.ini
├── Dockerfile
└── .env.example
```

## 11. Backend Module Responsibilities

| Module | Responsibilities | Examples |
| --- | --- | --- |
| authentication | Users, login, token handling, role enforcement | login, user CRUD, role checks |
| customers | Customer records and customer history view | create customer, update profile |
| loans | Applications, approvals, loan lifecycle, renewals, closure | approve application, create loan |
| collateral | Collateral intake, custody tracking, release, liquidation | register item, release item |
| payments | Payment registration, reversal, receipt generation | register payment, reverse payment |
| finance | Interest generation, balances, delinquency logic | monthly accrual, balance view |
| reporting | Aggregated queries, exports, operational dashboards | overdue loans report |

## 12. Data Model - Core Entities

| Entity | Main Fields |
| --- | --- |
| Customer | id, first_name, last_name, document_type, document_number, phone, email, address, city, status, created_at, updated_at |
| LoanApplication | id, customer_id, loan_type, requested_amount, monthly_interest_rate, term_months, notes, status, reviewed_by, approved_by, created_at |
| Loan | id, application_id, customer_id, loan_type, principal_amount, outstanding_principal, monthly_interest_rate, disbursement_date, due_day, status, renewal_of, created_at |
| CollateralItem | id, loan_id, item_type, description, serial_number, appraised_value, physical_condition, custody_code, storage_location, status, created_at |
| InterestCharge | id, loan_id, period_start, period_end, charge_date, amount, status, created_at |
| Payment | id, loan_id, payment_date, total_amount, allocated_to_penalty, allocated_to_interest, allocated_to_fees, allocated_to_principal, payment_method, received_by |
| AuditLog | id, user_id, action, entity_type, entity_id, old_data, new_data, created_at |

## 13. API Scope

### Authentication

- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/users
- POST /api/v1/users

### Customers

- GET /api/v1/customers
- POST /api/v1/customers
- GET /api/v1/customers/{id}
- PUT /api/v1/customers/{id}

### Loans

- POST /api/v1/loan-applications
- GET /api/v1/loan-applications
- POST /api/v1/loan-applications/{id}/approve
- POST /api/v1/loans
- GET /api/v1/loans/{id}
- POST /api/v1/loans/{id}/renew
- POST /api/v1/loans/{id}/close

### Collateral

- POST /api/v1/collateral-items
- GET /api/v1/collateral-items/{id}
- POST /api/v1/collateral-items/{id}/release
- POST /api/v1/collateral-items/{id}/liquidate

### Finance and Payments

- POST /api/v1/interest/generate
- GET /api/v1/loans/{id}/balance
- GET /api/v1/loans/{id}/ledger
- POST /api/v1/payments
- POST /api/v1/payments/{id}/reverse

### Reporting

- GET /api/v1/reports/active-loans
- GET /api/v1/reports/overdue-loans
- GET /api/v1/reports/collateral-custody
- GET /api/v1/reports/cash-summary

## 14. Docker and Deployment Requirements

- Each runnable application shall have its own Dockerfile.
- The repository shall provide a docker-compose.yml file for local development and integration testing.
- The compose configuration shall at minimum start the web client, API server, PostgreSQL, and any optional reverse proxy.
- Environment variables shall be externalized and documented through .env.example templates.
- Database migrations shall be executed through controlled commands or startup scripts, not manual schema edits.

## 15. Recommended Development Standards

| Area | Standard | Recommendation |
| --- | --- | --- |
| Backend code quality | Linting and formatting | Ruff and consistent import ordering; optional Black if the team prefers. |
| Backend testing | Automated tests | pytest for unit and integration tests. |
| Migrations | Schema change management | Alembic migrations with peer-reviewed migration scripts. |
| Frontend quality | Linting and type safety | ESLint, Prettier, and TypeScript checks. |
| Version control | Branching and reviews | Feature branches with pull requests and CI validation. |
| Documentation | Living technical documentation | README, ADRs, API overview, business rules, setup instructions. |

## 16. MVP Scope

The first release should focus on the minimum operational feature set required to run the lending business safely.

- Authentication and role-based access control
- Customer management
- Loan application workflow
- Loan creation and activation
- Pawn collateral registration and custody tracking
- Monthly interest generation
- Payment registration and receipts
- Loan balance tracking
- Overdue loan listing
- Basic operational reporting
- Audit logging for critical actions

## 17. Delivery Roadmap

| Phase | Expected Outcome |
| --- | --- |
| Phase 1 - Business Definition | Confirm interest logic, overdue rules, renewal policy, payment allocation policy, and collateral release policy. |
| Phase 2 - Architecture and Repository Setup | Create the monorepo scaffold, Docker setup, coding standards, CI, and environment templates. |
| Phase 3 - Core Backend | Implement authentication, customers, loans, collateral, finance, and payments. |
| Phase 4 - Web Client | Build the operator interface for day-to-day workflows. |
| Phase 5 - Reporting and Audit | Add reporting screens, export support, and audit visibility. |
| Phase 6 - Hardening | Add monitoring, logging, backups, and production environment improvements. |

## 18. Open Decisions to Resolve Before Development

- Should monthly interest be charged on original principal or outstanding principal?
- Should interest be prorated when the customer pays early?
- What is the exact overdue trigger and grace-period policy?
- Can customers make principal-only prepayments at any time?
- What minimum payment is required to avoid delinquency?
- How long can collateral remain overdue before liquidation begins?
- Which actions require dual control or supervisor approval?

## 19. Final System Statement

This project will deliver a professional loan management platform for pawn-backed and personal lending operations. The system will be implemented with a Vue web client, a FastAPI API server, PostgreSQL as the primary database, and Docker for consistent deployment. The repository will follow a professional modular monorepo structure and modern development practices, while keeping the initial architecture simple, maintainable, and ready for future evolution.
