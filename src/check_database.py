
"""Verify the YottaFlex database schema and foreign-key integrity."""

import sqlite3

from database import DATABASE_PATH, initialize_database


REQUIRED_TABLES = {
    "applicants",
    "employment",
    "income_records",
    "credit_facilities",
    "loan_products",
    "loan_applications",
    "documents",
    "affordability_checks",
    "decisions",
    "repayment_schedules",
    "application_events",
    "anomaly_labels",
}


def check_tables():
    # Create missing tables without deleting existing records.
    initialize_database()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        rows = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        actual_tables = {row[0] for row in rows}

        print("Tables found in the database:")
        for table_name in sorted(actual_tables):
            print(f"- {table_name}")

        missing_tables = REQUIRED_TABLES - actual_tables

        print(f"\nTotal tables: {len(actual_tables)}")

        if missing_tables:
            raise RuntimeError(
                f"Missing required tables: {sorted(missing_tables)}"
            )

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise RuntimeError(
                f"Foreign-key violations found: {foreign_key_errors[:10]}"
            )

        print("Required tables: PASS")
        print("Foreign-key integrity: PASS")


if __name__ == "__main__":
    check_tables()
