
"""Generate reproducible synthetic monthly income records."""

import random
import sqlite3
from datetime import date

from config import NUM_APPLICANTS, RANDOM_SEED
from database import DATABASE_PATH


INCOME_SOURCES = ["SALARY", "BUSINESS", "CONTRACT"]
REFERENCE_DATE = date(2026, 10, 22)

# Income is valid from before the earliest loan application date.
# A NULL effective_to means the record remains current.
INCOME_EFFECTIVE_FROM = date(2026, 1, 1)


def generate_income():
    """Generate deterministic monthly income records."""
    rng = random.Random(RANDOM_SEED + 2)
    records = []

    for number in range(1, NUM_APPLICANTS + 1):
        applicant_id = f"APP-2026-{number:06d}"

        # Every tenth applicant has unverified income.
        verification_status = (
            "UNVERIFIED" if number % 10 == 0 else "VERIFIED"
        )

        monthly_income = rng.randrange(15_000, 150_001, 5_000)

        records.append(
            (
                f"INC-{number:06d}",
                applicant_id,
                monthly_income,
                rng.choice(INCOME_SOURCES),
                verification_status,
                INCOME_EFFECTIVE_FROM.isoformat(),
                None,
            )
        )

    return records


def insert_income(records):
    """Insert or update generated income records."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO income_records (
                income_id,
                applicant_id,
                monthly_income,
                income_source,
                verification_status,
                effective_from,
                effective_to
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(income_id) DO UPDATE SET
                applicant_id = excluded.applicant_id,
                monthly_income = excluded.monthly_income,
                income_source = excluded.income_source,
                verification_status = excluded.verification_status,
                effective_from = excluded.effective_from,
                effective_to = excluded.effective_to
            """,
            records,
        )


def main():
    records = generate_income()
    insert_income(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM income_records"
        ).fetchone()[0]

        unverified = connection.execute(
            """
            SELECT COUNT(*)
            FROM income_records
            WHERE verification_status = 'UNVERIFIED'
            """
        ).fetchone()[0]

        average_income = connection.execute(
            "SELECT ROUND(AVG(monthly_income), 2) FROM income_records"
        ).fetchone()[0]

        date_range = connection.execute(
            """
            SELECT MIN(effective_from), MAX(effective_from)
            FROM income_records
            """
        ).fetchone()

    print(f"Income records generated: {len(records)}")
    print(f"Total income records in database: {total}")
    print(f"Unverified income records: {unverified}")
    print(f"Average monthly income: INR {average_income:,.2f}")
    print(f"Income effective-from dates: {date_range[0]} to {date_range[1]}")


if __name__ == "__main__":
    main()
