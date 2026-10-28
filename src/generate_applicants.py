"""Generate reproducible synthetic applicant master data."""

import random
import sqlite3
from datetime import date, timedelta

from config import NUM_APPLICANTS, RANDOM_SEED
from database import DATABASE_PATH


FIRST_NAMES = [
    "Aarav", "Aditya", "Ananya", "Arjun", "Divya",
    "Isha", "Kiran", "Meera", "Neha", "Rahul",
    "Rohan", "Sai", "Sneha", "Varun", "Priya",
]

LAST_NAMES = [
    "Sharma", "Reddy", "Rao", "Kumar", "Patel",
    "Gupta", "Verma", "Singh", "Nair", "Das",
]

CITIES = [
    "Hyderabad", "Bengaluru", "Chennai", "Pune",
    "Mumbai", "Delhi", "Vijayawada", "Visakhapatnam",
]

REFERENCE_DATE = date(2026, 10, 22)


def generate_applicants():
    """Generate deterministic synthetic applicant records."""
    rng = random.Random(RANDOM_SEED)
    records = []

    for number in range(1, NUM_APPLICANTS + 1):
        applicant_id = f"APP-2026-{number:06d}"
        full_name = (
            f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        )

        birth_date = date(1970, 1, 1) + timedelta(
            days=rng.randint(0, 12500)
        )

        city = rng.choice(CITIES)

        records.append(
            (
                applicant_id,
                full_name,
                birth_date.isoformat(),
                city,
                REFERENCE_DATE.isoformat(),
            )
        )

    return records


def insert_applicants(records):
    """Insert applicants without overwriting existing credit scores."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO applicants (
                applicant_id,
                full_name,
                date_of_birth,
                city,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(applicant_id) DO UPDATE SET
                full_name = excluded.full_name,
                date_of_birth = excluded.date_of_birth,
                city = excluded.city,
                created_at = excluded.created_at
            """,
            records,
        )


def main():
    records = generate_applicants()
    insert_applicants(records)

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM applicants"
        ).fetchone()[0]

    print(f"Applicant records generated: {len(records)}")
    print(f"Total applicants in database: {total}")

    if total < NUM_APPLICANTS:
        raise RuntimeError(
            f"Expected at least {NUM_APPLICANTS} applicants; found {total}."
        )


if __name__ == "__main__":
    main()