
"""Generate reproducible synthetic existing credit facilities."""

import random
import sqlite3
from datetime import date

from config import NUM_APPLICANTS, RANDOM_SEED
from database import DATABASE_PATH


FACILITY_TYPES = ["PERSONAL_LOAN", "CAR_LOAN", "CREDIT_CARD"]
REFERENCE_DATE = date(2026, 10, 22)


def generate_credit_facilities():
    """Generate deterministic synthetic credit facility records."""
    rng = random.Random(RANDOM_SEED + 3)
    records = []

    for number in range(1, NUM_APPLICANTS + 1):
        applicant_id = f"APP-2026-{number:06d}"

        # Every eighth applicant has a high monthly debt payment.
        if number % 8 == 0:
            monthly_payment = rng.randint(18_000, 30_000)
            outstanding_balance = rng.randint(100_000, 400_000)
        else:
            monthly_payment = rng.randint(1_000, 12_000)
            outstanding_balance = rng.randint(10_000, 150_000)

        records.append(
            (
                f"CRD-{number:06d}",
                applicant_id,
                rng.choice(FACILITY_TYPES),
                outstanding_balance,
                monthly_payment,
                "ACTIVE",
                REFERENCE_DATE.isoformat(),
                None,
            )
        )

    return records


def insert_credit_facilities(records):
    """Insert or update generated credit facilities."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO credit_facilities (
                facility_id,
                applicant_id,
                facility_type,
                outstanding_balance,
                monthly_payment,
                credit_status,
                effective_from,
                effective_to
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(facility_id) DO UPDATE SET
                applicant_id = excluded.applicant_id,
                facility_type = excluded.facility_type,
                outstanding_balance = excluded.outstanding_balance,
                monthly_payment = excluded.monthly_payment,
                credit_status = excluded.credit_status,
                effective_from = excluded.effective_from,
                effective_to = excluded.effective_to
            """,
            records,
        )


def main():
    records = generate_credit_facilities()
    insert_credit_facilities(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM credit_facilities"
        ).fetchone()[0]

        high_debt = connection.execute(
            """
            SELECT COUNT(*)
            FROM credit_facilities
            WHERE monthly_payment >= 18000
            """
        ).fetchone()[0]

    print(f"Credit facilities generated: {len(records)}")
    print(f"Total credit facilities in database: {total}")
    print(f"High monthly debt records: {high_debt}")


if __name__ == "__main__":
    main()
