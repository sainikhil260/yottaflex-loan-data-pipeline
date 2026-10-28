
"""Generate reproducible synthetic credit scores for applicants."""

import random
import sqlite3

from config import RANDOM_SEED
from database import DATABASE_PATH


MIN_CREDIT_SCORE = 300
MAX_CREDIT_SCORE = 900


def add_credit_scores():
    """Add one deterministic credit score to each applicant."""
    rng = random.Random(RANDOM_SEED + 7)

    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(applicants)"
            ).fetchall()
        }

        if "credit_score" not in columns:
            connection.execute(
                "ALTER TABLE applicants ADD COLUMN credit_score INTEGER"
            )

        applicants = connection.execute(
            """
            SELECT applicant_id
            FROM applicants
            ORDER BY applicant_id
            """
        ).fetchall()

        records = [
            (
                rng.randint(MIN_CREDIT_SCORE, MAX_CREDIT_SCORE),
                applicant_id,
            )
            for (applicant_id,) in applicants
        ]

        connection.executemany(
            """
            UPDATE applicants
            SET credit_score = ?
            WHERE applicant_id = ?
            """,
            records,
        )

        invalid_scores = connection.execute(
            """
            SELECT COUNT(*)
            FROM applicants
            WHERE credit_score IS NULL
               OR credit_score < ?
               OR credit_score > ?
            """,
            (MIN_CREDIT_SCORE, MAX_CREDIT_SCORE),
        ).fetchone()[0]

        total = connection.execute(
            "SELECT COUNT(*) FROM applicants"
        ).fetchone()[0]

        connection.commit()

    print(f"Applicants with generated credit scores: {len(records)}")
    print(f"Total applicants: {total}")
    print(f"Missing or invalid scores: {invalid_scores}")

    if invalid_scores:
        raise RuntimeError("Credit score validation failed.")


if __name__ == "__main__":
    add_credit_scores()
