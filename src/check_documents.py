
"""Validate and summarize generated loan documents."""

import sqlite3

from database import DATABASE_PATH


VALID_DOCUMENT_TYPES = {
    "IDENTITY_PROOF",
    "INCOME_PROOF",
    "BANK_STATEMENT",
}

VALID_DOCUMENT_STATUSES = {
    "SUBMITTED",
    "VERIFIED",
    "REJECTED",
    "MISSING",
}


def check_documents():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

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

        invalid_types = connection.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE document_type IS NULL
               OR document_type NOT IN (
                   'IDENTITY_PROOF',
                   'INCOME_PROOF',
                   'BANK_STATEMENT'
               )
            """
        ).fetchone()[0]

        invalid_statuses = connection.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE document_status IS NULL
               OR document_status NOT IN (
                   'SUBMITTED',
                   'VERIFIED',
                   'REJECTED',
                   'MISSING'
               )
            """
        ).fetchone()[0]

        invalid_timestamps = connection.execute(
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

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    print(f"Documents: {total}")
    print(f"Missing income proof: {missing_income}")
    print(f"Invalid document types: {invalid_types}")
    print(f"Invalid document statuses: {invalid_statuses}")
    print(f"Invalid document timestamps: {invalid_timestamps}")
    print(f"Foreign-key errors: {len(foreign_key_errors)}")

    if (
        invalid_types
        or invalid_statuses
        or invalid_timestamps
        or foreign_key_errors
    ):
        raise RuntimeError("Document validation FAILED.")

    print("Document validation PASSED.")


if __name__ == "__main__":
    check_documents()
