
"""Generate reproducible repayment schedules for approved applications."""

import sqlite3
from datetime import date

from database import DATABASE_PATH


def calculate_emi(principal, annual_rate, term_months):
    """Calculate the fixed monthly installment."""
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


def add_months(start_date, months):
    """Add calendar months and clamp to the destination month's last day."""
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    last_day = (next_month - date.resolution).day
    day = min(start_date.day, last_day)

    return date(year, month, day)


def generate_repayments():
    """Rebuild repayment schedules for currently approved loans."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        loans = connection.execute(
            """
            SELECT
                l.application_id,
                l.principal,
                l.term_months,
                l.applied_at,
                p.annual_interest_rate
            FROM loan_applications l
            JOIN loan_products p
              ON p.product_id = l.product_id
            JOIN decisions d
              ON d.application_id = l.application_id
            WHERE d.decision_status = 'APPROVED'
            ORDER BY l.application_id
            """
        ).fetchall()

        schedules = []

        for application_id, principal, term, applied_at, annual_rate in loans:
            emi = calculate_emi(principal, annual_rate, term)
            monthly_rate = annual_rate / 12
            remaining = float(principal)
            application_date = date.fromisoformat(applied_at[:10])

            for installment in range(1, term + 1):
                interest = remaining * monthly_rate

                if installment == term:
                    principal_component = remaining
                    total_payment = principal_component + interest
                else:
                    principal_component = emi - interest
                    total_payment = emi

                principal_component = min(
                    max(principal_component, 0.0),
                    remaining,
                )
                remaining = max(0.0, remaining - principal_component)

                schedules.append(
                    (
                        f"RS-{application_id}-{installment:03d}",
                        application_id,
                        installment,
                        add_months(application_date, installment).isoformat(),
                        round(principal_component, 2),
                        round(interest, 2),
                        round(total_payment, 2),
                        round(remaining, 2),
                    )
                )

        # Rebuild schedules atomically so stale installments cannot remain.
        # If any operation fails, SQLite rolls the transaction back.
        connection.execute("BEGIN")

        approved_ids = [loan[0] for loan in loans]

        if approved_ids:
            placeholders = ",".join("?" for _ in approved_ids)
            connection.execute(
                f"""
                DELETE FROM repayment_schedules
                WHERE application_id IN ({placeholders})
                """,
                approved_ids,
            )

        # Remove schedules for loans that are no longer approved.
        connection.execute(
            """
            DELETE FROM repayment_schedules
            WHERE application_id NOT IN (
                SELECT application_id
                FROM decisions
                WHERE decision_status = 'APPROVED'
            )
            """
        )

        if schedules:
            connection.executemany(
                """
                INSERT INTO repayment_schedules (
                    schedule_id,
                    application_id,
                    installment_number,
                    due_date,
                    principal_component,
                    interest_component,
                    total_payment,
                    remaining_balance
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                schedules,
            )

        total = connection.execute(
            "SELECT COUNT(*) FROM repayment_schedules"
        ).fetchone()[0]

        approved_count = len(loans)

        loans_with_wrong_installment_count = connection.execute(
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

        nonzero_final_balances = connection.execute(
            """
            SELECT r.application_id, r.remaining_balance
            FROM repayment_schedules r
            JOIN (
                SELECT application_id,
                       MAX(installment_number) AS last_installment
                FROM repayment_schedules
                GROUP BY application_id
            ) final
              ON final.application_id = r.application_id
             AND final.last_installment = r.installment_number
            WHERE ABS(r.remaining_balance) > 0.01
            """
        ).fetchall()

        if loans_with_wrong_installment_count or nonzero_final_balances:
            raise RuntimeError("Repayment schedule validation failed.")

        connection.commit()

    print(f"Approved loans: {approved_count}")
    print(f"Repayment installments generated: {len(schedules)}")
    print(f"Total installments in database: {total}")
    print(
        "Loans with incorrect installment counts: "
        f"{len(loans_with_wrong_installment_count)}"
    )
    print(f"Loans with nonzero final balances: {len(nonzero_final_balances)}")
    print("Repayment schedule validation PASSED.")


if __name__ == "__main__":
    generate_repayments()
