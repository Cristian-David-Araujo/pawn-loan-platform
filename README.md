# Pawn Loan Platform

A microservices-based loan management platform for pawn-backed and personal loans, built with **FastAPI**, **Vue 3**, **PostgreSQL**, and **Docker**.

## Features

- **Customer Management** – Register and manage customer profiles
- **Loan Applications** – Create, submit, approve, and reject loan applications
- **Loan Lifecycle** – Disbursement, tracking, renewals, and closures
- **Pawn Collateral** – Register, track, release, and liquidate collateral items
- **Finance / Interest** – Monthly interest generation and balance tracking
- **Payment Management** – Register payments, allocation, and reversals
- **Reporting** – Active loans, overdue, collateral, cash summary reports
- **Authentication** – JWT-based auth with role-based access control

## Architecture

```
Frontend (Vue 3) → API Gateway (port 8000)
                          ↓
       ┌──────────────────────────────────┐
       │           Microservices          │
       ├──────────────────────────────────┤
       │ Identity Service    :8001        │
       │ Customer Service    :8002        │
       │ Loan Service        :8003        │
       │ Collateral Service  :8004        │
       │ Finance Service     :8005        │
       │ Payment Service     :8006        │
       │ Reporting Service   :8007        │
       └──────────────────────────────────┘
                          ↓
                    PostgreSQL :5432
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, TypeScript, Pinia, Vue Router, Axios |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic v2 |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose) |
| Infrastructure | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional, for convenience commands)

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env to set a strong SECRET_KEY
```

### 2. Start all services

```bash
docker compose up -d
# or
make up
```

### 3. Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| API Gateway | http://localhost:8000 |
| Identity Service (docs) | http://localhost:8001/docs |
| Customer Service (docs) | http://localhost:8002/docs |
| Loan Service (docs) | http://localhost:8003/docs |
| Collateral Service (docs) | http://localhost:8004/docs |
| Finance Service (docs) | http://localhost:8005/docs |
| Payment Service (docs) | http://localhost:8006/docs |
| Reporting Service (docs) | http://localhost:8007/docs |

### 4. Create the first admin user

```bash
# POST to identity service to register
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"admin123","full_name":"Administrator"}'
```

## Development

### Running Tests

```bash
# All services
make test

# Single service
cd backend/loan-service && python -m pytest tests/ -v
```

### Project Structure

```
pawn-loan-platform/
├── frontend/
│   └── web-app/              # Vue 3 application
├── backend/
│   ├── gateway/              # API Gateway (port 8000)
│   ├── identity-service/     # Auth + Users (port 8001)
│   ├── customer-service/     # Customer CRUD (port 8002)
│   ├── loan-service/         # Loans + Applications (port 8003)
│   ├── collateral-service/   # Collateral Items (port 8004)
│   ├── finance-service/      # Interest + Penalties (port 8005)
│   ├── payment-service/      # Payments (port 8006)
│   └── reporting-service/    # Reports (port 8007)
├── database/
│   └── init/                 # PostgreSQL init scripts
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

## API Overview

All APIs follow REST conventions and are versioned under `/api/v1/`.

### Authentication
```
POST /api/v1/auth/login       # Login (returns JWT)
POST /api/v1/auth/register    # Register user
GET  /api/v1/users/me         # Current user profile
```

### Customers
```
GET  /api/v1/customers        # List customers
POST /api/v1/customers        # Create customer
GET  /api/v1/customers/{id}   # Get customer
PUT  /api/v1/customers/{id}   # Update customer
```

### Loans
```
POST /api/v1/loan-applications               # Create application
POST /api/v1/loan-applications/{id}/approve  # Approve
POST /api/v1/loans                           # Create loan from application
GET  /api/v1/loans/{id}                      # Get loan details
POST /api/v1/loans/{id}/renew                # Renew loan
POST /api/v1/loans/{id}/close                # Close loan
```

### Payments
```
POST /api/v1/payments               # Register payment
GET  /api/v1/payments               # List payments
POST /api/v1/payments/{id}/reverse  # Reverse payment
```

### Collateral
```
POST /api/v1/collateral-items                  # Register item
GET  /api/v1/collateral-items/{id}             # Get item
POST /api/v1/collateral-items/{id}/release     # Release
POST /api/v1/collateral-items/{id}/liquidate   # Liquidate
```

## License

MIT
