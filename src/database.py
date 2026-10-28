
"""Database schema and initialization for the YottaFlex loan pipeline."""

import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Use a custom database path when configured; otherwise use the default.
DATABASE_PATH = Path(
    os.environ.get(
        "YOTTAFLEX_DB_PATH",
        str(PROJECT_ROOT / "data" / "yottaflex.db"),
    )
).resolve()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    applicant_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employment (
    employment_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    employer_name TEXT NOT NULL,
    employment_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    employment_status TEXT NOT NULL,
    FOREIGN KEY (applicant_id) REFERENCES applicants(applicant_id)
);

CREATE TABLE IF NOT EXISTS income_records (
    income_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    monthly_income REAL NOT NULL,
    income_source TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    FOREIGN KEY (applicant_id) REFERENCES applicants(applicant_id)
);

CREATE TABLE IF NOT EXISTS credit_facilities (
    facility_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    outstanding_balance REAL NOT NULL,
    monthly_payment REAL NOT NULL,
    credit_status TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    credit_score INTEGER CHECK (
        credit_score IS NULL OR credit_score BETWEEN 300 AND 900
    ),
    FOREIGN KEY (applicant_id) REFERENCES applicants(applicant_id)
);

CREATE TABLE IF NOT EXISTS loan_products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    min_principal REAL NOT NULL,
    max_principal REAL NOT NULL,
    annual_interest_rate REAL NOT NULL,
    min_term_months INTEGER NOT NULL,
    max_term_months INTEGER NOT NULL,
    CHECK (min_principal > 0),
    CHECK (max_principal >= min_principal),
    CHECK (annual_interest_rate >= 0),
    CHECK (min_term_months > 0),
    CHECK (max_term_months >= min_term_months)
);

CREATE TABLE IF NOT EXISTS loan_applications (
    application_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    principal REAL NOT NULL,
    term_months INTEGER NOT NULL,
    application_status TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    FOREIGN KEY (applicant_id) REFERENCES applicants(applicant_id),
    FOREIGN KEY (product_id) REFERENCES loan_products(product_id),
    CHECK (principal > 0),
    CHECK (term_months > 0)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_status TEXT NOT NULL,
    submitted_at TEXT,
    verified_at TEXT,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id)
);

CREATE TABLE IF NOT EXISTS affordability_checks (
    check_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    monthly_income REAL NOT NULL,
    existing_monthly_debt REAL NOT NULL,
    proposed_monthly_payment REAL NOT NULL,
    dti_ratio REAL NOT NULL,
    affordable INTEGER NOT NULL,
    checked_at TEXT NOT NULL,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id),
    CHECK (monthly_income > 0),
    CHECK (existing_monthly_debt >= 0),
    CHECK (proposed_monthly_payment >= 0),
    CHECK (affordable IN (0, 1))
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    decision_status TEXT NOT NULL,
    decision_reason TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    reviewer_type TEXT NOT NULL,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id)
);

CREATE TABLE IF NOT EXISTS repayment_schedules (
    schedule_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    installment_number INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    principal_component REAL NOT NULL,
    interest_component REAL NOT NULL,
    total_payment REAL NOT NULL,
    remaining_balance REAL NOT NULL,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id),
    UNIQUE (application_id, installment_number),
    CHECK (installment_number > 0),
    CHECK (principal_component >= 0),
    CHECK (interest_component >= 0),
    CHECK (total_payment >= 0),
    CHECK (remaining_balance >= 0)
);

CREATE TABLE IF NOT EXISTS application_events (
    event_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    event_details TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id)
);

CREATE TABLE IF NOT EXISTS anomaly_labels (
    anomaly_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    ground_truth INTEGER NOT NULL,
    details TEXT NOT NULL,
    FOREIGN KEY (application_id)
        REFERENCES loan_applications(application_id),
    CHECK (ground_truth IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_employment_applicant
    ON employment(applicant_id);

CREATE INDEX IF NOT EXISTS idx_income_applicant
    ON income_records(applicant_id);

CREATE INDEX IF NOT EXISTS idx_credit_applicant
    ON credit_facilities(applicant_id);

CREATE INDEX IF NOT EXISTS idx_applications_applicant
    ON loan_applications(applicant_id);

CREATE INDEX IF NOT EXISTS idx_applications_product
    ON loan_applications(product_id);

CREATE INDEX IF NOT EXISTS idx_documents_application
    ON documents(application_id);

CREATE INDEX IF NOT EXISTS idx_affordability_application
    ON affordability_checks(application_id);

CREATE INDEX IF NOT EXISTS idx_decisions_application
    ON decisions(application_id);

CREATE INDEX IF NOT EXISTS idx_repayments_application
    ON repayment_schedules(application_id);

CREATE INDEX IF NOT EXISTS idx_events_application
    ON application_events(application_id);

CREATE INDEX IF NOT EXISTS idx_anomalies_application
    ON anomaly_labels(application_id);
"""


def initialize_database():
    """Create missing tables and indexes without deleting existing data."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_SQL)

    print(f"Database initialized successfully: {DATABASE_PATH}")
    print("Required tables and indexes are available.")


def reset_database():
    """Delete and recreate the selected database.

    WARNING: All records in DATABASE_PATH will be deleted.
    Back up important data before calling this function.
    """
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print("Existing database deleted.")

    initialize_database()


if __name__ == "__main__":
    initialize_database()
