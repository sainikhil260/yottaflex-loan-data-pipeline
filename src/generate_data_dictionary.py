
"""Generate a detailed data dictionary from the SQLite schema."""

import csv
import sqlite3
from pathlib import Path

from database import DATABASE_PATH


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "full_exports" / "data_dictionary.csv"
)


def get_allowed_values(column_name):
    """Return documented allowed values for known categorical columns."""
    allowed_values = {
        "employment_type": "FULL_TIME, CONTRACT, PART_TIME",
        "employment_status": "ACTIVE, UNSTABLE",
        "income_source": "SALARY, BUSINESS, CONTRACT",
        "verification_status": "VERIFIED, UNVERIFIED",
        "facility_type": "PERSONAL_LOAN, CAR_LOAN, CREDIT_CARD",
        "credit_status": "ACTIVE",
        "document_type": "IDENTITY_PROOF, INCOME_PROOF, BANK_STATEMENT",
        "document_status": "SUBMITTED, VERIFIED, REJECTED, MISSING",
        "decision_status": "APPROVED, REJECTED, MANUAL_REVIEW",
        "reviewer_type": "RULE_ENGINE",
        "issue_type": (
            "MISSING_INCOME_PROOF, HIGH_DEBT_BURDEN, "
            "UNSTABLE_EMPLOYMENT, BORDERLINE_CREDIT_SCORE, "
            "DUPLICATE_APPLICATION"
        ),
        "affordable": "0 = No, 1 = Yes",
        "ground_truth": "0 = Not an anomaly, 1 = Anomaly",
    }

    return allowed_values.get(column_name, "")


def get_units(column_name):
    """Return units for commonly used numeric fields."""
    if column_name in {
        "principal",
        "min_principal",
        "max_principal",
        "monthly_income",
        "monthly_payment",
        "existing_monthly_debt",
        "proposed_monthly_payment",
        "outstanding_balance",
        "principal_component",
        "interest_component",
        "total_payment",
        "remaining_balance",
    }:
        return "INR"

    if column_name in {"annual_interest_rate", "dti_ratio"}:
        return "Decimal ratio; e.g. 0.18 = 18%"

    if column_name in {
        "term_months",
        "min_term_months",
        "max_term_months",
        "installment_number",
    }:
        return "Months or installment count, as applicable"

    if column_name == "credit_score":
        return "Synthetic credit-score points; range 300–900"

    return ""


def get_validation_notes(table_name, column_name, primary_key, foreign_key):
    """Describe constraints and important business rules."""
    notes = []

    if primary_key:
        notes.append("Primary key; unique and non-null")

    if foreign_key:
        notes.append(
            f"Foreign key references "
            f"{foreign_key[0]}.{foreign_key[1]}"
        )

    if column_name == "credit_score":
        notes.append("Integer between 300 and 900")

    if column_name == "dti_ratio":
        notes.append("Non-negative ratio; compare with configured DTI threshold")

    if column_name == "monthly_income":
        notes.append("Must be greater than zero for affordability checks")

    if column_name in {"principal", "min_principal", "max_principal"}:
        notes.append("Validate against the selected loan product's limits")

    if column_name in {"term_months", "min_term_months", "max_term_months"}:
        notes.append("Validate against the selected loan product's term limits")

    if column_name in {"start_date", "end_date", "effective_from", "effective_to"}:
        notes.append("Validate date format and effective-date ordering")

    if column_name in {"applied_at", "created_at", "checked_at", "decided_at",
                       "submitted_at", "verified_at", "occurred_at", "due_date"}:
        notes.append("Validate timestamp format and chronological consistency")

    allowed = get_allowed_values(column_name)
    if allowed:
        notes.append(f"Allowed values: {allowed}")

    if column_name == "dti_ratio":
        notes.append("High debt burden when above configured threshold")

    if table_name == "anomaly_labels" and column_name == "ground_truth":
        notes.append("Ground-truth target; exclude from predictive input features")

    return "; ".join(notes) or "Validate against applicable business rules"


def generate_dictionary():
    """Generate the data dictionary and verify the output."""
    dictionary_rows = []

    with sqlite3.connect(DATABASE_PATH) as connection:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table_name,) in tables:
            columns = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            foreign_keys = connection.execute(
                f'PRAGMA foreign_key_list("{table_name}")'
            ).fetchall()

            foreign_key_map = {
                row[3]: (row[2], row[4])
                for row in foreign_keys
            }

            for column in columns:
                (
                    cid,
                    column_name,
                    data_type,
                    not_null,
                    default,
                    primary_key,
                ) = column

                foreign_key = foreign_key_map.get(column_name)

                # SQLite primary keys are inherently required.
                required = bool(not_null or primary_key)

                unique_count = connection.execute(
                    f'PRAGMA index_list("{table_name}")'
                ).fetchall()

                unique_indexes = [
                    index[1]
                    for index in unique_count
                    if index[2]
                ]

                is_unique = bool(primary_key)

                for index_name in unique_indexes:
                    indexed_columns = connection.execute(
                        f'PRAGMA index_info("{index_name}")'
                    ).fetchall()

                    if any(
                        indexed_column[2] == column_name
                        for indexed_column in indexed_columns
                    ):
                        is_unique = True

                dictionary_rows.append(
                    [
                        table_name,
                        column_name,
                        data_type or "Not declared",
                        "Yes" if required else "No",
                        "Yes" if primary_key else "No",
                        "Yes" if is_unique else "No",
                        "Yes" if foreign_key else "No",
                        (
                            f"{foreign_key[0]}.{foreign_key[1]}"
                            if foreign_key
                            else ""
                        ),
                        get_units(column_name),
                        get_allowed_values(column_name),
                        default,
                        get_validation_notes(
                            table_name,
                            column_name,
                            primary_key,
                            foreign_key,
                        ),
                    ]
                )

    headers = [
        "table_name",
        "column_name",
        "data_type",
        "required",
        "primary_key",
        "unique",
        "foreign_key",
        "references",
        "units",
        "allowed_values",
        "default_value",
        "validation_notes",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(dictionary_rows)

    # Verify the generated file can be read and has the expected columns.
    with OUTPUT_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.reader(csv_file)
        exported_headers = next(reader, None)
        exported_rows = sum(1 for _ in reader)

    if exported_headers != headers:
        raise RuntimeError("Data dictionary header verification failed.")

    if exported_rows != len(dictionary_rows):
        raise RuntimeError("Data dictionary row-count verification failed.")

    print(f"Data dictionary created: {OUTPUT_PATH}")
    print(f"Tables documented: {len(tables)}")
    print(f"Columns documented: {len(dictionary_rows)}")
    print("Data dictionary verification: PASS")


if __name__ == "__main__":
    generate_dictionary()
