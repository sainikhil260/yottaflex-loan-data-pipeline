
"""Export every database table to an individual CSV file."""

import csv
import sqlite3
from pathlib import Path

from database import DATABASE_PATH


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "data" / "full_exports"


def export_tables():
    """Export all database tables and verify exported row counts."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

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

        total_rows = 0
        export_errors = []

        for (table_name,) in tables:
            cursor = connection.execute(
                f'SELECT * FROM "{table_name}" ORDER BY 1'
            )

            column_names = [
                description[0]
                for description in cursor.description
            ]
            rows = cursor.fetchall()

            output_path = EXPORT_DIR / f"{table_name}.csv"

            with output_path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                writer.writerow(column_names)
                writer.writerows(rows)

            # Read the CSV back to verify its structure and row count.
            with output_path.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as csv_file:
                reader = csv.reader(csv_file)
                exported_headers = next(reader, None)
                exported_rows = sum(1 for _ in reader)

            if exported_headers != column_names:
                export_errors.append(
                    f"{table_name}: CSV headers do not match."
                )

            if exported_rows != len(rows):
                export_errors.append(
                    f"{table_name}: expected {len(rows)} rows, "
                    f"exported {exported_rows}."
                )

            total_rows += exported_rows

            print(
                f"{table_name}: {exported_rows} rows exported "
                f"and verified"
            )

        print(f"\nExport folder: {EXPORT_DIR}")
        print(f"Total data rows exported: {total_rows}")

        if export_errors:
            for error in export_errors:
                print(f"FAIL: {error}")

            raise RuntimeError("CSV export verification failed.")

        print("CSV export verification: PASS")


if __name__ == "__main__":
    export_tables()
