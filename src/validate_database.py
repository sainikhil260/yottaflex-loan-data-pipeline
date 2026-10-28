
"""Validate database integrity and loan-processing business rules."""

import sqlite3

from config import MAX_DTI_RATIO, NUM_LOAN_APPLICATIONS
from database import DATABASE_PATH


PRIMARY_KEYS = {
    "applicants": "applicant_id",
    "employment": "employment_id",
    "income_records": "income_id",
    "credit_facilities": "facility_id",
    "loan_products": "product_id",
    "loan_applications": "application_id",
    "documents": "document_id",
    "affordability_checks": "check_id",
    "decisions": "decision_id",
    "repayment_schedules": "schedule_id",
    "application_events": "event_id",
    "anomaly_labels": "anomaly_id",
}


def validate_database():
    errors = []
    warnings = []

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # 1. Check required tables.
        actual_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }

        missing_tables = set(PRIMARY_KEYS) - actual_tables

        if missing_tables:
            errors.append(
                f"Missing required tables: {sorted(missing_tables)}"
            )
        else:
            print("PASS: All required tables exist.")

        # Stop safely if required tables are missing.
        if missing_tables:
            raise SystemExit(
                "Database validation failed. Fix missing tables first."
            )

        # 2. Check foreign-key integrity.
        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            errors.append(
                f"Foreign-key violations: {foreign_key_errors[:10]}"
            )

        # 3. Check primary keys for duplicates and NULL values.
        for table, key in PRIMARY_KEYS.items():
            duplicate_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT {key}
                    FROM {table}
                    GROUP BY {key}
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]

            null_count = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {key} IS NULL"
            ).fetchone()[0]

            if duplicate_count:
                errors.append(
                    f"{table}: {duplicate_count} duplicate primary keys"
                )

            if null_count:
                errors.append(
                    f"{table}: {null_count} NULL primary keys"
                )

        # 4. Check the expected number of applications for the selected mode.
        application_count = connection.execute(
            "SELECT COUNT(*) FROM loan_applications"
        ).fetchone()[0]

        if application_count != NUM_LOAN_APPLICATIONS:
            errors.append(
                f"Expected {NUM_LOAN_APPLICATIONS} applications, "
                f"found {application_count}. A clean rebuild may be needed."
            )

        # 5. Every application must have exactly one current decision.
        decision_count_errors = connection.execute(
            """
            SELECT l.application_id, COUNT(d.decision_id)
            FROM loan_applications l
            LEFT JOIN decisions d
              ON d.application_id = l.application_id
            GROUP BY l.application_id
            HAVING COUNT(d.decision_id) != 1
            """
        ).fetchall()

        if decision_count_errors:
            errors.append(
                "Applications without exactly one decision: "
                f"{len(decision_count_errors)}"
            )

        # 6. Every application must have an affordability check.
        missing_checks = connection.execute(
            """
            SELECT COUNT(*)
            FROM loan_applications l
            LEFT JOIN affordability_checks a
              ON a.application_id = l.application_id
            WHERE a.check_id IS NULL
            """
        ).fetchone()[0]

        if missing_checks:
            errors.append(
                f"Applications without affordability checks: {missing_checks}"
            )

        # 7. Repayment schedules must belong to approved applications.
        invalid_schedules = connection.execute(
            """
            SELECT COUNT(*)
            FROM repayment_schedules r
            LEFT JOIN decisions d
              ON d.application_id = r.application_id
            WHERE d.decision_id IS NULL
               OR d.decision_status != 'APPROVED'
            """
        ).fetchone()[0]

        if invalid_schedules:
            errors.append(
                f"Schedules for non-approved loans: {invalid_schedules}"
            )

        # 8. Every approved application must have exactly term_months entries.
        incorrect_installments = connection.execute(
            """
            SELECT l.application_id
            FROM loan_applications l
            JOIN decisions d
              ON d.application_id = l.application_id
            LEFT JOIN repayment_schedules r
              ON r.application_id = l.application_id
            WHERE d.decision_status = 'APPROVED'
            GROUP BY l.application_id, l.term_months
            HAVING COUNT(r.schedule_id) != l.term_months
            """
        ).fetchall()

        if incorrect_installments:
            errors.append(
                "Approved loans with incorrect installment counts: "
                f"{len(incorrect_installments)}"
            )

        # 9. Validate applicant credit scores.
        invalid_scores = connection.execute(
            """
            SELECT COUNT(*)
            FROM applicants
            WHERE credit_score IS NULL
               OR credit_score < 300
               OR credit_score > 900
            """
        ).fetchone()[0]

        if invalid_scores:
            errors.append(
                f"Missing or out-of-range credit scores: {invalid_scores}"
            )

        # 10. Validate product limits and application values.
        invalid_applications = connection.execute(
            """
            SELECT COUNT(*)
            FROM loan_applications l
            JOIN loan_products p
              ON p.product_id = l.product_id
            WHERE l.principal < p.min_principal
               OR l.principal > p.max_principal
               OR l.term_months < p.min_term_months
               OR l.term_months > p.max_term_months
            """
        ).fetchone()[0]

        if invalid_applications:
            errors.append(
                f"Applications outside product limits: {invalid_applications}"
            )

        # 11. Validate affordability values.
        invalid_affordability = connection.execute(
            """
            SELECT COUNT(*)
            FROM affordability_checks
            WHERE monthly_income <= 0
               OR existing_monthly_debt < 0
               OR proposed_monthly_payment < 0
               OR dti_ratio < 0
               OR affordable NOT IN (0, 1)
            """
        ).fetchone()[0]

        if invalid_affordability:
            errors.append(
                f"Invalid affordability records: {invalid_affordability}"
            )

        # 12. Validate document timestamps.
        invalid_documents = connection.execute(
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

        if invalid_documents:
            errors.append(
                f"Invalid document timestamps: {invalid_documents}"
            )

        # 13. Validate anomaly ground-truth labels.
        invalid_labels = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly_labels
            WHERE ground_truth NOT IN (0, 1)
               OR issue_type NOT IN (
                   'MISSING_INCOME_PROOF',
                   'HIGH_DEBT_BURDEN',
                   'UNSTABLE_EMPLOYMENT',
                   'BORDERLINE_CREDIT_SCORE',
                   'DUPLICATE_APPLICATION'
               )
            """
        ).fetchone()[0]

        if invalid_labels:
            errors.append(
                f"Invalid anomaly labels: {invalid_labels}"
            )

        # 14. Report row counts for all tables.
        print("\nDATABASE ROW COUNTS")

        for table in PRIMARY_KEYS:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"{table}: {count}")

        high_dti_count = connection.execute(
            "SELECT COUNT(*) FROM affordability_checks WHERE dti_ratio > ?",
            (MAX_DTI_RATIO,),
        ).fetchone()[0]

        if high_dti_count:
            print(
                f"\nInformational: {high_dti_count} checks exceed "
                f"the {MAX_DTI_RATIO:.0%} DTI threshold."
            )

    print("\nVALIDATION RESULTS")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")

        raise SystemExit(1)

    print("PASS: Foreign-key integrity.")
    print("PASS: Primary-key integrity.")
    print("PASS: Exactly one decision per application.")
    print("PASS: Affordability checks exist.")
    print("PASS: Repayment schedules match approved loans.")
    print("PASS: Credit scores are in range.")
    print("PASS: Applications respect product limits.")
    print("PASS: Affordability and document data are valid.")
    print("PASS: Anomaly labels are valid.")
    print("\nDATABASE VALIDATION PASSED.")


if __name__ == "__main__":
    validate_database()
