
"""Export every database table to a verified JSON file."""

import json
import sqlite3
from pathlib import Path

from database import DATABASE_PATH


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "data" / "full_json"


def export_json():
    """Export all tables and verify JSON structure and record counts."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

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

        for row in tables:
            table_name = row["name"]

            records = connection.execute(
                f'SELECT * FROM "{table_name}" ORDER BY 1'
            ).fetchall()

            data = [dict(record) for record in records]
            output_path = EXPORT_DIR / f"{table_name}.json"

            with output_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as json_file:
                json.dump(
                    data,
                    json_file,
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                json_file.write("\n")

            # Reopen the file and verify the exported records.
            with output_path.open("r", encoding="utf-8") as json_file:
                exported_data = json.load(json_file)

            if not isinstance(exported_data, list):
                export_errors.append(
                    f"{table_name}: JSON root must be a list."
                )
            elif len(exported_data) != len(data):
                export_errors.append(
                    f"{table_name}: expected {len(data)} records, "
                    f"found {len(exported_data)}."
                )
            elif exported_data != data:
                export_errors.append(
                    f"{table_name}: exported content does not match "
                    "the database."
                )

            total_rows += len(exported_data)

            print(
                f"{table_name}: {len(exported_data)} records "
                "exported and verified"
            )

        print(f"\nJSON folder: {EXPORT_DIR}")
        print(f"Total JSON records exported: {total_rows}")

        if export_errors:
            for error in export_errors:
                print(f"FAIL: {error}")

            raise RuntimeError("JSON export verification failed.")

        print("JSON export verification: PASS")


if __name__ == "__main__":
    export_json()
