
"""Generate reproducible synthetic employment records."""

import random
import sqlite3
from datetime import date, timedelta

from config import NUM_APPLICANTS, RANDOM_SEED
from database import DATABASE_PATH


EMPLOYERS = [
    "TechNova Solutions",
    "BrightPath Services",
    "Apex Industries",
    "GreenField Technologies",
    "Metro Business Group",
    "FutureWorks India",
]

EMPLOYMENT_TYPES = ["FULL_TIME", "CONTRACT", "PART_TIME"]
REFERENCE_DATE = date(2026, 10, 22)


def generate_employment():
    """Generate deterministic employment records."""
    rng = random.Random(RANDOM_SEED + 1)
    records = []

    for number in range(1, NUM_APPLICANTS + 1):
        applicant_id = f"APP-2026-{number:06d}"

        if number % 10 == 0:
            start_date = REFERENCE_DATE - timedelta(
                days=rng.randint(30, 300)
            )
            employment_status = "UNSTABLE"
        else:
            start_date = REFERENCE_DATE - timedelta(
                days=rng.randint(365, 3650)
            )
            employment_status = "ACTIVE"

        records.append(
            (
                f"EMP-{number:06d}",
                applicant_id,
                rng.choice(EMPLOYERS),
                rng.choice(EMPLOYMENT_TYPES),
                start_date.isoformat(),
                None,
                employment_status,
            )
        )

    return records


def insert_employment(records):
    """Insert or update generated employment records."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO employment (
                employment_id,
                applicant_id,
                employer_name,
                employment_type,
                start_date,
                end_date,
                employment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employment_id) DO UPDATE SET
                applicant_id = excluded.applicant_id,
                employer_name = excluded.employer_name,
                employment_type = excluded.employment_type,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                employment_status = excluded.employment_status
            """,
            records,
        )


def main():
    records = generate_employment()
    insert_employment(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM employment"
        ).fetchone()[0]

        unstable = connection.execute(
            "SELECT COUNT(*) FROM employment "
            "WHERE employment_status = 'UNSTABLE'"
        ).fetchone()[0]

    print(f"Employment records generated: {len(records)}")
    print(f"Total employment records in database: {total}")
    print(f"Unstable employment records: {unstable}")


if __name__ == "__main__":
    main()
