#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE identity_db;
    CREATE DATABASE customer_db;
    CREATE DATABASE loan_db;
    CREATE DATABASE collateral_db;
    CREATE DATABASE finance_db;
    CREATE DATABASE payment_db;
EOSQL

echo "All databases created successfully."
