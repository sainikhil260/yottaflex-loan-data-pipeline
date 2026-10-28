
"""Generate explainable loan decisions and decision-change events."""

import sqlite3

from config import MAX_DTI_RATIO, MIN_BORDERLINE_SCORE
from database import DATABASE_PATH


DECIDED_AT = "2026-10-22T13:00:00"
LOW_CREDIT_SCORE = 600


def decide_applications():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Read source records and credit scores.
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(applicants)"
            ).fetchall()
        }

        if "credit_score" not in columns:
            raise RuntimeError(
                "Credit scores have not been generated. "
                "Run add_credit_scores.py before the decision engine."
            )

        applications = connection.execute(
            """
            SELECT
                l.application_id,
                i.verification_status,
                e.employment_status,
                a.dti_ratio,
                a.affordable,
                ap.credit_score
            FROM loan_applications l
            JOIN income_records i
              ON i.applicant_id = l.applicant_id
             AND i.effective_from <= DATE(l.applied_at)
             AND (
                 i.effective_to IS NULL
                 OR i.effective_to >= DATE(l.applied_at)
             )
            JOIN employment e
              ON e.applicant_id = l.applicant_id
            JOIN affordability_checks a
              ON a.application_id = l.application_id
            JOIN applicants ap
              ON ap.applicant_id = l.applicant_id
            ORDER BY l.application_id
            """
        ).fetchall()

        decisions = []

        for (
            application_id,
            income_status,
            employment_status,
            dti_ratio,
            affordable,
            credit_score,
        ) in applications:

            missing_income_proof = connection.execute(
                """
                SELECT COUNT(*)
                FROM documents
                WHERE application_id = ?
                  AND document_type = 'INCOME_PROOF'
                  AND document_status IN ('MISSING', 'REJECTED')
                """,
                (application_id,),
            ).fetchone()[0] > 0

            if missing_income_proof or income_status != "VERIFIED":
                status = "MANUAL_REVIEW"
                reason = "Income evidence missing, rejected, or unverified"

            elif employment_status != "ACTIVE":
                status = "MANUAL_REVIEW"
                reason = "Employment stability requires review"

            elif credit_score < LOW_CREDIT_SCORE:
                status = "REJECTED"
                reason = f"Credit score below minimum threshold: {credit_score}"

            elif MIN_BORDERLINE_SCORE <= credit_score <= 680:
                status = "MANUAL_REVIEW"
                reason = f"Borderline credit score requires review: {credit_score}"

            elif dti_ratio > MAX_DTI_RATIO or not affordable:
                status = "REJECTED"
                reason = (
                    f"Debt-to-income ratio exceeds {MAX_DTI_RATIO:.0%} "
                    f"(actual: {dti_ratio:.2%})"
                )

            else:
                status = "APPROVED"
                reason = (
                    "Income verified, employment active, credit score "
                    "acceptable, and DTI within limit"
                )

            decisions.append(
                (
                    f"DEC-{application_id}-01",
                    application_id,
                    status,
                    reason,
                    DECIDED_AT,
                    "RULE_ENGINE",
                )
            )

        # Update the current decision if its calculated result has changed.
        # A separate event is recorded only when the status changes.
        for decision in decisions:
            (
                decision_id,
                application_id,
                status,
                reason,
                decided_at,
                reviewer_type,
            ) = decision

            previous = connection.execute(
                """
                SELECT decision_status
                FROM decisions
                WHERE decision_id = ?
                """,
                (decision_id,),
            ).fetchone()

            old_status = previous[0] if previous else None

            connection.execute(
                """
                INSERT INTO decisions (
                    decision_id,
                    application_id,
                    decision_status,
                    decision_reason,
                    decided_at,
                    reviewer_type
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    application_id = excluded.application_id,
                    decision_status = excluded.decision_status,
                    decision_reason = excluded.decision_reason,
                    decided_at = excluded.decided_at,
                    reviewer_type = excluded.reviewer_type
                """,
                decision,
            )

            connection.execute(
                """
                UPDATE loan_applications
                SET application_status = ?
                WHERE application_id = ?
                """,
                (status, application_id),
            )

            if old_status != status:
                event_id = f"EVT-{application_id}-DECISION-{status}"

                connection.execute(
                    """
                    INSERT INTO application_events (
                        event_id,
                        application_id,
                        event_type,
                        old_status,
                        new_status,
                        event_details,
                        occurred_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO NOTHING
                    """,
                    (
                        event_id,
                        application_id,
                        "DECISION_RECORDED",
                        old_status,
                        status,
                        reason,
                        decided_at,
                    ),
                )

        breakdown = connection.execute(
            """
            SELECT decision_status, COUNT(*)
            FROM decisions
            GROUP BY decision_status
            ORDER BY decision_status
            """
        ).fetchall()

        decision_count = connection.execute(
            "SELECT COUNT(*) FROM decisions"
        ).fetchone()[0]

    print(f"Applications evaluated: {len(decisions)}")
    print(f"Total current decisions: {decision_count}")
    print("Decision breakdown:")

    for status, count in breakdown:
        print(f"  {status}: {count}")


if __name__ == "__main__":
    decide_applications()
