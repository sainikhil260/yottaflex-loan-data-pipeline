
"""Generate reproducible synthetic loan applications."""

import random
import sqlite3
from datetime import datetime, timedelta

from config import NUM_LOAN_APPLICATIONS, RANDOM_SEED
from database import DATABASE_PATH


APPLICATION_STATUSES = [
    "SUBMITTED",
    "UNDER_REVIEW",
    "APPROVED",
    "REJECTED",
    "MANUAL_REVIEW",
]


def generate_applications():
    """Generate deterministic loan application records."""
    rng = random.Random(RANDOM_SEED + 4)
    records = []

    with sqlite3.connect(DATABASE_PATH) as connection:
        applicants = [
            row[0]
            for row in connection.execute(
                "SELECT applicant_id FROM applicants ORDER BY applicant_id"
            ).fetchall()
        ]

        products = connection.execute(
            """
            SELECT product_id, min_principal, max_principal,
                   min_term_months, max_term_months
            FROM loan_products
            ORDER BY product_id
            """
        ).fetchall()

    if not applicants or not products:
        raise RuntimeError(
            "Applicants or loan products are missing. "
            "Generate master data first."
        )

    # Deliberately create repeat applications for some applicants.
    # This makes duplicate-application anomaly testing reproducible.
    applicant_pool = applicants.copy()
    rng.shuffle(applicant_pool)

    for number in range(1, NUM_LOAN_APPLICATIONS + 1):
        application_id = f"LOAN-2026-{number:06d}"

        if number % 4 == 0:
            applicant_id = applicant_pool[(number - 1) % len(applicant_pool)]
        else:
            applicant_id = rng.choice(applicants)

        product_id, min_amount, max_amount, min_term, max_term = (
            rng.choice(products)
        )

        # Select a valid principal within the product's limits.
        min_amount = int(min_amount)
        max_amount = int(max_amount)
        step = 5000

        first_valid_amount = (
            (min_amount + step - 1) // step
        ) * step

        if first_valid_amount <= max_amount:
            valid_amounts = range(
                first_valid_amount,
                max_amount + 1,
                step,
            )
            principal = rng.choice(valid_amounts)
        else:
            principal = rng.randint(min_amount, max_amount)

        term_months = rng.randint(int(min_term), int(max_term))
        status = "SUBMITTED"

        applied_at = (
            datetime(2026, 10, 1, 9, 0, 0)
            + timedelta(days=rng.randint(0, 21))
        ).isoformat()

        records.append(
            (
                application_id,
                applicant_id,
                product_id,
                principal,
                term_months,
                status,
                applied_at,
            )
        )

    return records


def insert_applications(records):
    """Insert or update generated applications by stable application ID."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO loan_applications (
                application_id,
                applicant_id,
                product_id,
                principal,
                term_months,
                application_status,
                applied_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(application_id) DO UPDATE SET
                applicant_id = excluded.applicant_id,
                product_id = excluded.product_id,
                principal = excluded.principal,
                term_months = excluded.term_months,
                application_status = excluded.application_status,
                applied_at = excluded.applied_at
            """,
            records,
        )


def main():
    records = generate_applications()
    insert_applications(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM loan_applications"
        ).fetchone()[0]

        breakdown = connection.execute(
            """
            SELECT application_status, COUNT(*)
            FROM loan_applications
            GROUP BY application_status
            ORDER BY application_status
            """
        ).fetchall()

        duplicate_applicants = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT applicant_id
                FROM loan_applications
                GROUP BY applicant_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

    print(f"Loan applications generated: {len(records)}")
    print(f"Total applications in database: {total}")
    print(f"Applicants with multiple applications: {duplicate_applicants}")
    print("Application status breakdown:")

    for status, count in breakdown:
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
