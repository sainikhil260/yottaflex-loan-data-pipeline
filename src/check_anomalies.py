
"""Display and validate anomaly-label counts."""

import sqlite3

from database import DATABASE_PATH


def check_anomalies():
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT issue_type, ground_truth, COUNT(*)
            FROM anomaly_labels
            GROUP BY issue_type, ground_truth
            ORDER BY issue_type, ground_truth
            """
        ).fetchall()

        invalid_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly_labels
            WHERE issue_type IS NULL
               OR issue_type NOT IN (
                   'MISSING_INCOME_PROOF',
                   'HIGH_DEBT_BURDEN',
                   'UNSTABLE_EMPLOYMENT',
                   'BORDERLINE_CREDIT_SCORE',
                   'DUPLICATE_APPLICATION'
               )
               OR ground_truth IS NULL
               OR ground_truth NOT IN (0, 1)
            """
        ).fetchone()[0]

        total_count = connection.execute(
            "SELECT COUNT(*) FROM anomaly_labels"
        ).fetchone()[0]

    print("Anomaly labels:")
    for issue_type, ground_truth, count in rows:
        print(
            f"{issue_type}: {count} "
            f"(ground_truth={ground_truth})"
        )

    print(f"\nTotal anomaly labels: {total_count}")
    print(f"Invalid labels: {invalid_count}")

    if invalid_count:
        raise RuntimeError("Anomaly validation FAILED.")

    print("Anomaly validation PASSED.")


if __name__ == "__main__":
    check_anomalies()
