# Loan Management System Requirements and Software Design

## 1. Project Overview

The software is a loan management system designed to support two lending models:

- Pawn-backed loans
- Personal loans without collateral

The platform must manage the full loan lifecycle, including customer registration, loan requests, collateral registration, approval workflow, monthly interest charging, payment tracking, delinquency handling, renewals, and reporting.

The system must be built as a microservices-based application, containerized with Docker, using the following technology stack:

- Backend: Python + FastAPI
- Frontend: Vue
- Database: PostgreSQL

## 2. Business Goal

The goal of the software is to provide an operational platform for businesses that issue loans to individuals, especially under pawn lending and direct lending models, where interest is charged monthly.

The platform should help operators:

- register and manage customers
- create and approve loans
- control collateral items
- calculate and charge monthly interest
- receive and allocate payments
- track overdue loans
- manage renewals and closures
- generate operational and financial reports

## 3. Functional Requirements

### 3.1 Customer Management

The system must allow users to:

- create, update, and view customer profiles
- store personal and contact information
- validate uniqueness by identification number
- review customer loan history
- add notes and observations
- enable or disable customer accounts

Customer data fields:

- first name
- last name
- document type
- document number
- phone number
- email
- address
- city
- status
- created date
- updated date

### 3.2 Loan Application Management

The system must allow users to:

- create loan applications
- define the loan type:
  - pawn-backed loan
  - personal loan
- enter requested amount
- enter monthly interest rate
- define initial term
- attach observations or supporting documents
- approve or reject applications
- track who created, reviewed, and approved the application

Loan application states:

- draft
- submitted
- under review
- approved
- rejected
- cancelled

### 3.3 Pawn Collateral Management

For pawn-backed loans, the system must allow users to:

- register one or multiple collateral items
- capture item description
- save serial number or reference
- register appraised value
- store physical condition
- upload item photos
- assign an internal custody code
- track storage location
- manage release or liquidation of collateral

Collateral item states:

- received
- in custody
- released
- under liquidation
- sold
- written off

### 3.4 Loan Creation and Disbursement

The system must allow users to:

- generate a loan from an approved application
- define:
  - loan amount
  - monthly interest rate
  - disbursement date
  - monthly due date
  - loan term
- link collateral when applicable
- record disbursement method:
  - cash
  - bank transfer
  - other
- activate the loan and start the financial cycle

Loan states:

- approved
- disbursed
- active
- overdue
- renewed
- closed
- defaulted
- liquidated

### 3.5 Monthly Interest Calculation

The system must support monthly interest charging.

It must allow:

- configurable monthly interest rate
- automatic monthly interest generation
- definition of the calculation base:
  - original principal
  - outstanding principal
  - current balance
- generation of monthly charges
- interest history per loan
- recalculation after capital payments or renewals when business rules require it

Minimum business rule:

- Interest must be generated once per monthly cycle for active loans.

### 3.6 Payment Management

The system must allow users to:

- register payments
- support partial payments
- support full settlement
- split payments into:
  - penalty interest
  - regular interest
  - principal
  - fees
- define payment allocation order
- generate payment receipts
- reverse payments with permission and audit trail

Recommended payment allocation order:

- penalties
- accrued interest
- fees
- principal

### 3.7 Delinquency and Penalty Handling

The system must allow users to:

- identify overdue loans
- apply grace periods
- calculate penalty interest
- apply additional fees if needed
- track collection actions
- show aging buckets of overdue loans

Aging examples:

- 1-30 days overdue
- 31-60 days overdue
- 61-90 days overdue
- 90+ days overdue

### 3.8 Loan Renewals

The system must allow users to renew loans based on business rules.

Renewal features must include:

- creating a new cycle for an existing loan
- carrying forward the same collateral in pawn-backed loans
- recalculating dates
- settling required charges before renewal if applicable
- preserving traceability between original loan and renewed loan

### 3.9 Loan Closure

The system must allow users to close loans when all balances are fully settled.

For pawn-backed loans, closure must also allow:

- collateral release
- delivery confirmation
- release timestamp
- responsible operator tracking

### 3.10 Collateral Liquidation

For defaulted pawn-backed loans, the system must allow:

- marking collateral as eligible for liquidation
- registering liquidation status
- recording sale amount if sold
- linking liquidation to the final loan settlement outcome
- preserving complete audit history

### 3.11 Reporting

The platform must provide reports for:

- active loans
- overdue loans
- loans by type
- total outstanding principal
- total accrued interest
- payments by date range
- delinquent customers
- collateral in custody
- released collateral
- liquidated collateral
- operator activity
- cash collection summary

### 3.12 User and Role Management

The system must support authentication and authorization with roles.

Suggested roles:

- administrator
- loan officer
- cashier
- collections agent
- auditor

Permissions must control access to:

- approvals
- payment reversal
- collateral release
- liquidation actions
- user administration
- rate changes
- report access

## 4. Non-Functional Requirements

### 4.1 Architecture

The system must be built as a microservices-based platform.

Each service must:

- have a clear bounded responsibility
- expose REST APIs
- run inside Docker containers
- be independently deployable

### 4.2 Performance

The system should support daily business operations with multiple concurrent users.

Operational pages such as:

- customer lookup
- loan details
- payment registration
- active loan listing

should respond quickly under normal load.

### 4.3 Scalability

The system should allow independent horizontal scaling of critical services such as:

- loan service
- payment service
- reporting service

### 4.4 Security

The system must include:

- secure authentication
- role-based authorization
- password hashing
- token-based access control
- data validation
- audit logs for critical operations
- secure document and image handling

### 4.5 Auditability

All critical actions must be auditable, including:

- loan creation
- approval
- disbursement
- interest generation
- payment registration
- payment reversal
- collateral release
- collateral liquidation
- user changes

Each audit record should contain:

- user
- timestamp
- action
- entity type
- entity id
- old value
- new value

### 4.6 Availability and Reliability

The platform should be resilient enough for business operations and include:

- service health checks
- structured logging
- graceful failure handling
- database backup strategy
- restart policy for containers

### 4.7 Maintainability

The codebase should be:

- modular
- well documented
- versioned
- testable
- consistent in naming and structure

### 4.8 Observability

The platform should support:

- centralized logs
- request tracing
- metrics collection
- error monitoring
- health and readiness endpoints

## 5. Recommended Microservices

A practical first design would include the following services.

### 5.1 API Gateway

Responsible for:

- single entry point
- request routing
- authentication forwarding
- rate limiting if needed

### 5.2 Identity Service

Responsible for:

- authentication
- user accounts
- roles
- permissions
- token issuance

### 5.3 Customer Service

Responsible for:

- customer records
- customer profile updates
- customer history reference

### 5.4 Loan Service

Responsible for:

- loan applications
- approvals
- loan creation
- loan states
- renewals
- closure workflow

### 5.5 Collateral Service

Responsible for:

- collateral item registration
- appraisal data
- item images
- custody tracking
- release and liquidation

### 5.6 Finance Service

Responsible for:

- interest calculation
- accrual rules
- penalties
- outstanding balances
- financial ledger per loan

### 5.7 Payment Service

Responsible for:

- payment registration
- allocation logic
- receipts
- payment reversals
- cash operation records

### 5.8 Reporting Service

Responsible for:

- aggregated queries
- exports
- dashboards
- business-level reporting

### 5.9 Notification Service

Responsible for:

- due date reminders
- overdue alerts
- customer notifications by email, SMS, or messaging integrations

## 6. Technology Stack

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy or SQLModel
- Alembic for migrations
- Pydantic for validation
- Uvicorn / Gunicorn
- Celery or background workers if needed
- Redis for caching and async jobs if needed

### Frontend

- Vue 3
- Vite
- Vue Router
- Pinia
- Axios
- UI framework optional:
  - Vuetify
  - Element Plus
  - Naive UI

### Database

- PostgreSQL 16+

### Infrastructure

- Docker
- Docker Compose for local development
- Nginx or Traefik as gateway/reverse proxy
- Optional future orchestration with Kubernetes

### Messaging / Async

- RabbitMQ or Redis Streams or Kafka if event-driven communication grows

### Monitoring

- Prometheus
- Grafana
- Loki or ELK
- Sentry optional

## 7. Suggested Monorepo Structure

```text
loan-management-platform/
├── apps/
│   ├── frontend/
│   │   ├── src/
│   │   ├── public/
│   │   ├── package.json
│   │   └── Dockerfile
│   ├── gateway/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── services/
│       ├── identity/
│       │   ├── app/
│       │   │   ├── api/
│       │   │   ├── core/
│       │   │   ├── models/
│       │   │   ├── schemas/
│       │   │   ├── services/
│       │   │   └── repositories/
│       │   ├── alembic/
│       │   ├── tests/
│       │   ├── requirements.txt
│       │   └── Dockerfile
│       ├── customer/
│       ├── loan/
│       ├── collateral/
│       ├── finance/
│       ├── payment/
│       ├── reporting/
│       └── notification/
├── packages/
│   ├── contracts/
│   │   ├── openapi/
│   │   └── events/
│   ├── shared-python/
│   │   ├── auth/
│   │   ├── db/
│   │   ├── logging/
│   │   └── utils/
│   └── shared-ts/
│       ├── api-client/
│       └── ui-types/
├── ops/
│   ├── docker/
│   │   ├── compose/
│   │   │   ├── docker-compose.local.yml
│   │   │   └── docker-compose.prod.yml
│   │   └── images/
│   ├── k8s/
│   ├── nginx/
│   ├── monitoring/
│   └── scripts/
├── database/
│   ├── local-init/
│   ├── seed/
│   └── backups/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── adr/
│   ├── runbooks/
│   └── business-rules/
├── .github/
│   ├── workflows/
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── .editorconfig
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

### Why this structure is simpler and still microservices-ready

- One single place for runnable apps: `apps/`
- One single place for reusable code/contracts: `packages/`
- One single place for infrastructure/operations: `ops/`
- Every service follows the same internal template (lower learning curve)
- Shared code is explicit and controlled, avoiding hidden coupling
- Works for local Docker today and Kubernetes later

## 8. High-Level Architecture

### Frontend

The Vue frontend is the user interface for operators and administrators.

Responsibilities:

- login
- dashboard
- customer management
- loan workflow screens
- collateral registration
- payment registration
- reporting views

The frontend should consume APIs through the gateway rather than calling internal services directly.

### Backend

Each FastAPI service should be responsible for one business domain.

Recommended backend layers per service:

- `api/` for routes
- `schemas/` for request and response models
- `models/` for database entities
- `services/` for business logic
- `repositories/` for data access
- `core/` for config and security
- `workers/` for async jobs if needed

### Database

Use PostgreSQL as the main persistence layer.

Recommended approach:

- one database instance for local development
- separate database or separate schema per microservice
- avoid tight coupling between services at database level

Preferred long-term rule:

- each service owns its data
- cross-service access should occur through APIs or events, not direct table joins

## 9. Core Domain Entities

### Customer

- id
- first_name
- last_name
- document_type
- document_number
- phone
- email
- address
- city
- status
- created_at
- updated_at

### LoanApplication

- id
- customer_id
- loan_type
- requested_amount
- monthly_interest_rate
- term_months
- notes
- status
- reviewed_by
- approved_by
- created_at
- updated_at

### Loan

- id
- application_id
- customer_id
- loan_type
- principal_amount
- outstanding_principal
- monthly_interest_rate
- disbursement_date
- due_day
- status
- renewal_of
- created_at
- updated_at

### CollateralItem

- id
- loan_id
- item_type
- description
- serial_number
- appraised_value
- physical_condition
- custody_code
- storage_location
- status
- created_at
- updated_at

### InterestCharge

- id
- loan_id
- period_start
- period_end
- charge_date
- amount
- status
- created_at

### Payment

- id
- loan_id
- payment_date
- total_amount
- allocated_to_penalty
- allocated_to_interest
- allocated_to_fees
- allocated_to_principal
- payment_method
- received_by
- status
- created_at

### AuditLog

- id
- user_id
- action
- entity_type
- entity_id
- old_data
- new_data
- created_at

## 10. Business Rules to Define Explicitly

Before development begins, these rules must be fixed clearly.

### Interest rules

- Is monthly interest charged on original principal or outstanding principal?
- Is interest charged as a full month even if the customer pays early?
- Is prorated interest allowed?
- Is the interest generated on a fixed day or based on loan anniversary date?

### Payment rules

- What is the exact payment allocation order?
- Are partial interest-only payments allowed?
- Can customers make direct principal prepayments?
- What happens if the payment is less than accrued interest?

### Delinquency rules

- When exactly does a loan become overdue?
- Is there a grace period?
- How is penalty interest calculated?
- Are penalty fees fixed or percentage-based?

### Renewal rules

- Must all accrued interest be paid before renewal?
- Can principal be increased during renewal?
- Does the renewed loan keep the same collateral record or create a new linked loan cycle?

### Pawn rules

- Can multiple items back one loan?
- Can one collateral item back more than one loan?
- What documentation is required on item release?
- After how many overdue days can liquidation begin?

## 11. API Design Guidelines

All services should expose versioned APIs.

Example:

- /api/v1/customers
- /api/v1/loans
- /api/v1/payments

Recommended standards:

- RESTful endpoints
- JSON request/response
- OpenAPI documentation generated by FastAPI
- standardized error responses
- request validation through Pydantic
- pagination for list endpoints
- filtering and sorting support for operational listings

## 12. Example Service Endpoints

### Identity Service

- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/users
- POST /api/v1/users
- GET /api/v1/roles

### Customer Service

- GET /api/v1/customers
- POST /api/v1/customers
- GET /api/v1/customers/{id}
- PUT /api/v1/customers/{id}

### Loan Service

- POST /api/v1/loan-applications
- GET /api/v1/loan-applications
- POST /api/v1/loan-applications/{id}/approve
- POST /api/v1/loans
- GET /api/v1/loans/{id}
- POST /api/v1/loans/{id}/renew
- POST /api/v1/loans/{id}/close

### Collateral Service

- POST /api/v1/collateral-items
- GET /api/v1/collateral-items/{id}
- POST /api/v1/collateral-items/{id}/release
- POST /api/v1/collateral-items/{id}/liquidate

### Finance Service

- POST /api/v1/interest/generate
- GET /api/v1/loans/{id}/ledger
- GET /api/v1/loans/{id}/balance

### Payment Service

- POST /api/v1/payments
- GET /api/v1/payments/{id}
- POST /api/v1/payments/{id}/reverse

### Reporting Service

- GET /api/v1/reports/active-loans
- GET /api/v1/reports/overdue-loans
- GET /api/v1/reports/collateral-custody
- GET /api/v1/reports/cash-summary

## 13. How to Build the Software

### Phase 1: Requirements and Business Rules

Define and validate:

- loan types
- monthly interest logic
- overdue logic
- payment allocation rules
- collateral handling rules
- roles and permissions
- reporting needs

This phase should end with:

- functional requirements
- non-functional requirements
- domain glossary
- workflow diagrams

### Phase 2: Architecture Design

Design:

- service boundaries
- API contracts
- database ownership
- authentication model
- synchronous vs asynchronous communication
- audit strategy
- deployment topology

Deliverables:

- architecture diagram
- service interaction diagram
- entity models
- API drafts

### Phase 3: Repository Setup

Create the monorepo with:

- frontend folder
- backend services
- database scripts
- shared docs
- docker compose
- environment config templates

Set up:

- linting
- formatting
- Git hooks
- CI basics
- branch strategy

### Phase 4: MVP Backend Development

Build the minimum viable backend services in this order:

- Identity Service
- Customer Service
- Loan Service
- Collateral Service
- Finance Service
- Payment Service

Minimum backend capabilities:

- authentication
- customer CRUD
- loan application and approval
- loan creation
- collateral registration
- monthly interest generation
- payment registration
- loan balance view

### Phase 5: MVP Frontend Development

Build Vue screens for:

- login
- dashboard
- customer list and detail
- loan application form
- loan detail page
- collateral registration
- payment registration
- overdue loans view

Recommended frontend modules:

- auth
- customers
- loans
- collateral
- payments
- reports

### Phase 6: Reporting and Operational Enhancements

Add:

- overdue reports
- cash summary
- collateral inventory report
- renewal workflows
- payment reversal
- audit log view

### Phase 7: Observability and Hardening

Add:

- structured logs
- health endpoints
- Prometheus metrics
- request tracing
- error tracking
- backups
- environment separation:
  - local
  - staging
  - production

## 14. Docker Strategy

Each service should have its own Dockerfile.

Example runtime components:

- frontend container
- gateway container
- identity-service container
- customer-service container
- loan-service container
- collateral-service container
- finance-service container
- payment-service container
- reporting-service container
- postgres container
- redis container optional
- nginx or traefik container

### Example Docker Compose Responsibilities

docker-compose.yml should:

- build all services
- create internal network
- mount environment variables
- expose required ports
- start PostgreSQL
- manage dependencies
- support local development

## 15. Suggested Development Standards

### Backend standards

- FastAPI per service
- Pydantic models for validation
- SQLAlchemy/SQLModel for persistence
- Alembic migrations
- pytest for testing
- black + ruff for formatting/linting
- environment settings via .env

### Frontend standards

- Vue 3 + Vite
- TypeScript recommended
- Pinia store
- Axios service layer
- reusable UI components
- route guards for auth
- form validation

### Database standards

- migration-based schema control
- explicit indexes
- foreign key discipline within each service boundary
- timestamps on operational tables
- soft delete only where justified

## 16. Recommended MVP Scope

The first release should include:

- authentication and user roles
- customer management
- loan application workflow
- loan creation and activation
- pawn collateral registration
- monthly interest generation
- payment registration
- loan balance tracking
- overdue loan view
- basic reporting
- audit log for critical actions

This MVP is enough to operate the core business.

## 17. Risks and Design Warnings

You should be careful with these areas from the beginning:

- Over-splitting microservices
  - Too many services too early can slow development. For the first version, keep service boundaries practical.
- Financial inconsistency
  - Loan balances, accrued interest, and payment allocation must be deterministic and auditable.
- Direct database coupling
  - Do not let one service manipulate another service's tables directly.
- Missing audit trail
  - In financial systems, lack of traceability becomes a serious operational problem.
- Ambiguous interest rules
  - If the monthly interest model is not precisely defined, the system will produce disputes.

## 18. Recommended Build Order

This is the order I would use:

1. Define business rules precisely
2. Set up monorepo and Docker base
3. Build Identity Service
4. Build Customer Service
5. Build Loan Service
6. Build Collateral Service
7. Build Finance Service
8. Build Payment Service
9. Build Vue frontend
10. Add reporting
11. Add monitoring and production hardening

## 19. Short System Description

You can use this as a formal project description:

> A microservices-based loan management platform for pawn-backed and personal loans, built with FastAPI, Vue, PostgreSQL, and Docker, supporting customer management, collateral control, monthly interest charging, payment tracking, delinquency handling, and operational reporting.

## 20. Recommended Next Deliverables

The most useful next step is to convert this into:

- User stories with acceptance criteria
- Detailed microservice architecture
- Database model
- API contract draft
- Docker Compose starter structure

The best immediate next artifact would be a Software Requirements Specification (SRS) followed by the initial microservice folder structure.
