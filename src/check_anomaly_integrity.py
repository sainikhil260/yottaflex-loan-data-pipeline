
"""Validate anomaly-label integrity and references."""

import sqlite3

from database import DATABASE_PATH


VALID_ISSUE_TYPES = {
    "MISSING_INCOME_PROOF",
    "HIGH_DEBT_BURDEN",
    "UNSTABLE_EMPLOYMENT",
    "BORDERLINE_CREDIT_SCORE",
    "DUPLICATE_APPLICATION",
}


def check_anomaly_integrity():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        duplicate_ids = connection.execute(
            """
            SELECT anomaly_id, COUNT(*)
            FROM anomaly_labels
            GROUP BY anomaly_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        invalid_applications = connection.execute(
            """
            SELECT a.anomaly_id, a.application_id
            FROM anomaly_labels AS a
            LEFT JOIN loan_applications AS l
                ON a.application_id = l.application_id
            WHERE l.application_id IS NULL
            """
        ).fetchall()

        invalid_issue_types = connection.execute(
            """
            SELECT anomaly_id, issue_type
            FROM anomaly_labels
            WHERE issue_type IS NULL
               OR issue_type NOT IN (
                   'MISSING_INCOME_PROOF',
                   'HIGH_DEBT_BURDEN',
                   'UNSTABLE_EMPLOYMENT',
                   'BORDERLINE_CREDIT_SCORE',
                   'DUPLICATE_APPLICATION'
               )
            """
        ).fetchall()

        invalid_ground_truth = connection.execute(
            """
            SELECT anomaly_id, ground_truth
            FROM anomaly_labels
            WHERE ground_truth IS NULL
               OR ground_truth NOT IN (0, 1)
            """
        ).fetchall()

        checks = {
            "Foreign-key errors": foreign_key_errors,
            "Duplicate anomaly IDs": duplicate_ids,
            "Invalid application references": invalid_applications,
            "Invalid issue types": invalid_issue_types,
            "Invalid ground-truth labels": invalid_ground_truth,
        }

        for check_name, errors in checks.items():
            print(f"{check_name}: {len(errors)}")

        failed_checks = [
            name for name, errors in checks.items() if errors
        ]

        if failed_checks:
            raise RuntimeError(
                "Anomaly integrity check FAILED: "
                + ", ".join(failed_checks)
            )

        print("Anomaly integrity check PASSED.")


if __name__ == "__main__":
    check_anomaly_integrity()
