
"""Calculate reproducible affordability metrics for loan applications."""

import sqlite3
from datetime import datetime

from config import MAX_DTI_RATIO
from database import DATABASE_PATH


CHECKED_AT = "2026-10-22T12:00:00"


def calculate_monthly_payment(principal, annual_rate, term_months):
    """Calculate the fixed monthly payment using the EMI formula."""
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")

    if term_months <= 0:
        raise ValueError("Term must be greater than zero.")

    if annual_rate < 0:
        raise ValueError("Annual interest rate cannot be negative.")

    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        return principal / term_months

    factor = (1 + monthly_rate) ** term_months

    return principal * monthly_rate * factor / (factor - 1)


def generate_affordability_checks():
    """Calculate affordability for each application from source records."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        applications = connection.execute(
            """
            SELECT
                l.application_id,
                l.principal,
                l.term_months,
                p.annual_interest_rate,
                i.monthly_income,
                COALESCE(
                    (
                        SELECT SUM(c.monthly_payment)
                        FROM credit_facilities c
                        WHERE c.applicant_id = l.applicant_id
                          AND c.credit_status = 'ACTIVE'
                    ),
                    0
                ) AS existing_debt
            FROM loan_applications l
            JOIN loan_products p
              ON p.product_id = l.product_id
            JOIN income_records i
              ON i.applicant_id = l.applicant_id
             AND i.effective_from <= DATE(l.applied_at)
             AND (
                 i.effective_to IS NULL
                 OR i.effective_to >= DATE(l.applied_at)
             )
            ORDER BY l.application_id
            """
        ).fetchall()

        records = []

        for (
            application_id,
            principal,
            term_months,
            annual_rate,
            monthly_income,
            existing_debt,
        ) in applications:
            if monthly_income is None or monthly_income <= 0:
                raise ValueError(
                    f"Missing or invalid monthly income for {application_id}."
                )

            if existing_debt is None:
                existing_debt = 0

            monthly_payment = calculate_monthly_payment(
                principal,
                annual_rate,
                term_months,
            )

            total_monthly_debt = existing_debt + monthly_payment
            dti_ratio = total_monthly_debt / monthly_income
            affordable = int(dti_ratio <= MAX_DTI_RATIO)

            records.append(
                (
                    f"CHK-{application_id}",
                    application_id,
                    monthly_income,
                    existing_debt,
                    round(monthly_payment, 2),
                    round(dti_ratio, 4),
                    affordable,
                    CHECKED_AT,
                )
            )

        connection.executemany(
            """
            INSERT INTO affordability_checks (
                check_id,
                application_id,
                monthly_income,
                existing_monthly_debt,
                proposed_monthly_payment,
                dti_ratio,
                affordable,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(check_id) DO UPDATE SET
                application_id = excluded.application_id,
                monthly_income = excluded.monthly_income,
                existing_monthly_debt = excluded.existing_monthly_debt,
                proposed_monthly_payment = excluded.proposed_monthly_payment,
                dti_ratio = excluded.dti_ratio,
                affordable = excluded.affordable,
                checked_at = excluded.checked_at
            """,
            records,
        )

        total = connection.execute(
            "SELECT COUNT(*) FROM affordability_checks"
        ).fetchone()[0]

        affordable_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM affordability_checks
            WHERE affordable = 1
            """
        ).fetchone()[0]

        high_dti_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM affordability_checks
            WHERE dti_ratio > ?
            """,
            (MAX_DTI_RATIO,),
        ).fetchone()[0]

        missing_checks = connection.execute(
            """
            SELECT COUNT(*)
            FROM loan_applications l
            LEFT JOIN affordability_checks a
              ON a.application_id = l.application_id
            WHERE a.application_id IS NULL
            """
        ).fetchone()[0]

    print(f"Affordability checks generated: {len(records)}")
    print(f"Total checks in database: {total}")
    print(f"Affordable checks: {affordable_count}")
    print(f"Checks above {MAX_DTI_RATIO:.0%} DTI: {high_dti_count}")
    print(f"Applications without a check: {missing_checks}")

    if missing_checks:
        raise RuntimeError(
            "Some applications do not have an affordability check. "
            "Check whether their source income records exist."
        )


if __name__ == "__main__":
    generate_affordability_checks()
