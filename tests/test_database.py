
import sqlite3
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "yottaflex.db"


@pytest.fixture
def connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


def test_database_exists():
    assert DATABASE_PATH.exists()


def test_required_tables_exist(connection):
    tables = {
        row[0]
        for row in connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """).fetchall()
    }

    required_tables = {
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

    assert required_tables.issubset(tables)


def test_primary_keys_are_unique(connection):
    tables = [
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
    ]

    for table in tables:
        primary_key_columns = [
            row[1]
            for row in connection.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()
            if row[5] > 0
        ]

        assert primary_key_columns, f"{table} has no primary key"

        key = ", ".join(f'"{column}"' for column in primary_key_columns)

        duplicates = connection.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT {key}
                FROM "{table}"
                GROUP BY {key}
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        assert duplicates == 0, f"Duplicate primary keys in {table}"


def test_foreign_keys_are_valid(connection):
    violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    assert violations == []


def test_every_application_has_a_decision(connection):
    missing = connection.execute("""
        SELECT COUNT(*)
        FROM loan_applications la
        LEFT JOIN decisions d
            ON la.application_id = d.application_id
        WHERE d.application_id IS NULL
    """).fetchone()[0]

    assert missing == 0


def test_repayment_schedules_only_for_approved_loans(connection):
    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM repayment_schedules rs
        JOIN loan_applications la
            ON rs.application_id = la.application_id
        WHERE la.application_status != 'APPROVED'
    """).fetchone()[0]

    assert invalid == 0


def test_credit_scores_are_in_range(connection):
    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM credit_facilities
        WHERE credit_score IS NULL
           OR credit_score < 300
           OR credit_score > 900
    """).fetchone()[0]

    assert invalid == 0


def test_anomaly_labels_use_valid_ground_truth(connection):
    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM anomaly_labels
        WHERE ground_truth NOT IN (0, 1)
    """).fetchone()[0]

    assert invalid == 0
