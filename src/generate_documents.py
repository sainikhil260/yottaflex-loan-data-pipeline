
"""Generate reproducible synthetic document records."""

import random
import sqlite3

from config import RANDOM_SEED
from database import DATABASE_PATH


DOCUMENT_TYPES = [
    "IDENTITY_PROOF",
    "INCOME_PROOF",
    "BANK_STATEMENT",
]

DOCUMENT_STATUSES = ["SUBMITTED", "VERIFIED", "REJECTED"]


def generate_documents():
    """Generate deterministic documents for every loan application."""
    rng = random.Random(RANDOM_SEED + 5)
    records = []

    with sqlite3.connect(DATABASE_PATH) as connection:
        applications = connection.execute(
            """
            SELECT application_id
            FROM loan_applications
            ORDER BY application_id
            """
        ).fetchall()

    for (application_id,) in applications:
        application_number = int(application_id[-6:])

        for index, document_type in enumerate(DOCUMENT_TYPES, start=1):
            # Deliberately create missing income-proof cases.
            if index == 2 and application_number % 5 == 0:
                document_status = "MISSING"
                submitted_at = None
                verified_at = None
            else:
                document_status = rng.choice(DOCUMENT_STATUSES)
                submitted_at = "2026-10-22T10:00:00"

                if document_status == "VERIFIED":
                    verified_at = "2026-10-22T12:00:00"
                else:
                    verified_at = None

            document_id = f"DOC-{application_id}-{index:03d}"

            records.append(
                (
                    document_id,
                    application_id,
                    document_type,
                    document_status,
                    submitted_at,
                    verified_at,
                )
            )

    return records


def insert_documents(records):
    """Insert or update generated documents using stable IDs."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO documents (
                document_id,
                application_id,
                document_type,
                document_status,
                submitted_at,
                verified_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                application_id = excluded.application_id,
                document_type = excluded.document_type,
                document_status = excluded.document_status,
                submitted_at = excluded.submitted_at,
                verified_at = excluded.verified_at
            """,
            records,
        )


def main():
    records = generate_documents()
    insert_documents(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]

        missing_income = connection.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE document_type = 'INCOME_PROOF'
              AND document_status = 'MISSING'
            """
        ).fetchone()[0]

        invalid_verified_dates = connection.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE verified_at IS NOT NULL
              AND (
                  submitted_at IS NULL
                  OR verified_at < submitted_at
              )
            """
        ).fetchone()[0]

    print(f"Document records generated: {len(records)}")
    print(f"Total documents in database: {total}")
    print(f"Missing income proof records: {missing_income}")
    print(f"Invalid verification timestamps: {invalid_verified_dates}")

    if invalid_verified_dates:
        raise RuntimeError("Document timestamp validation failed.")


if __name__ == "__main__":
    main()
