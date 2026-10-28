
"""Generate deterministic anomaly labels from stored loan application data."""

import sqlite3

from config import (
    MAX_BORDERLINE_SCORE,
    MAX_DTI_RATIO,
    MIN_BORDERLINE_SCORE,
)
from database import DATABASE_PATH


def generate_anomalies():
    """Detect known synthetic anomalies and rebuild their labels."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        applications = connection.execute(
            """
            SELECT
                la.application_id,
                la.applicant_id,
                ac.dti_ratio,
                (
                    SELECT e.employment_status
                    FROM employment e
                    WHERE e.applicant_id = la.applicant_id
                    ORDER BY e.start_date DESC, e.employment_id DESC
                    LIMIT 1
                ) AS employment_status,
                ap.credit_score
            FROM loan_applications la
            LEFT JOIN affordability_checks ac
                ON ac.application_id = la.application_id
            LEFT JOIN applicants ap
                ON ap.applicant_id = la.applicant_id
            ORDER BY la.application_id
            """
        ).fetchall()

        labels = []

        for (
            application_id,
            applicant_id,
            dti,
            employment_status,
            score,
        ) in applications:

            # Missing income proof.
            missing_proof = connection.execute(
                """
                SELECT COUNT(*)
                FROM documents
                WHERE application_id = ?
                  AND document_type = 'INCOME_PROOF'
                  AND document_status = 'MISSING'
                """,
                (application_id,),
            ).fetchone()[0]

            if missing_proof:
                labels.append(
                    (
                        f"ANOM-{application_id}-MISSING",
                        application_id,
                        "MISSING_INCOME_PROOF",
                        1,
                        "Income proof document is missing.",
                    )
                )

            # High debt-to-income ratio.
            if dti is not None and dti > MAX_DTI_RATIO:
                labels.append(
                    (
                        f"ANOM-{application_id}-DEBT",
                        application_id,
                        "HIGH_DEBT_BURDEN",
                        1,
                        (
                            f"Debt-to-income ratio is {dti:.3f}, "
                            f"above {MAX_DTI_RATIO:.0%}."
                        ),
                    )
                )

            # Unstable employment.
            if employment_status == "UNSTABLE":
                labels.append(
                    (
                        f"ANOM-{application_id}-EMP",
                        application_id,
                        "UNSTABLE_EMPLOYMENT",
                        1,
                        "Applicant has an unstable employment record.",
                    )
                )

            # Borderline credit score from the applicant master record.
            if (
                score is not None
                and MIN_BORDERLINE_SCORE
                <= score
                <= MAX_BORDERLINE_SCORE
            ):
                labels.append(
                    (
                        f"ANOM-{application_id}-SCORE",
                        application_id,
                        "BORDERLINE_CREDIT_SCORE",
                        1,
                        f"Stored synthetic credit score is {score}.",
                    )
                )

        # Label later applications from applicants who applied more than once.
        duplicate_groups = connection.execute(
            """
            SELECT applicant_id
            FROM loan_applications
            GROUP BY applicant_id
            HAVING COUNT(*) > 1
            ORDER BY applicant_id
            """
        ).fetchall()

        for (applicant_id,) in duplicate_groups:
            applicant_applications = connection.execute(
                """
                SELECT application_id
                FROM loan_applications
                WHERE applicant_id = ?
                ORDER BY applied_at, application_id
                """,
                (applicant_id,),
            ).fetchall()

            for (application_id,) in applicant_applications[1:]:
                labels.append(
                    (
                        f"ANOM-{application_id}-DUP",
                        application_id,
                        "DUPLICATE_APPLICATION",
                        1,
                        (
                            "Additional application from an applicant "
                            "with multiple applications; review required."
                        ),
                    )
                )

        # Rebuild labels in a transaction so stale labels are not retained.
        connection.execute("DELETE FROM anomaly_labels")

        connection.executemany(
            """
            INSERT INTO anomaly_labels (
                anomaly_id,
                application_id,
                issue_type,
                ground_truth,
                details
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            labels,
        )

        invalid_labels = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly_labels
            WHERE ground_truth NOT IN (0, 1)
            """
        ).fetchone()[0]

        total_labels = connection.execute(
            "SELECT COUNT(*) FROM anomaly_labels"
        ).fetchone()[0]

        breakdown = connection.execute(
            """
            SELECT issue_type, COUNT(*)
            FROM anomaly_labels
            GROUP BY issue_type
            ORDER BY issue_type
            """
        ).fetchall()

        if invalid_labels:
            raise RuntimeError(
                f"Found {invalid_labels} invalid ground-truth labels."
            )

        print(f"Applications checked: {len(applications)}")
        print(f"Anomaly labels generated: {total_labels}")
        print("Anomaly breakdown:")

        for issue_type, count in breakdown:
            print(f"  {issue_type}: {count}")

        print("Ground-truth validation: PASS")


if __name__ == "__main__":
    generate_anomalies()
