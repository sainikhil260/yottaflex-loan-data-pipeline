
"""Synchronize application statuses with recorded decisions."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from database import DATABASE_PATH


def sync_application_statuses():
    database_path = Path(DATABASE_PATH)

    # Create a timestamped backup before modifying the database.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = database_path.with_name(
        f"{database_path.stem}_before_status_sync_{timestamp}"
        f"{database_path.suffix}"
    )
    shutil.copy2(database_path, backup_path)
    print(f"Backup created: {backup_path}")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        mismatches = connection.execute(
            """
            SELECT COUNT(*)
            FROM loan_applications AS la
            JOIN decisions AS d
              ON d.application_id = la.application_id
            WHERE la.application_status != d.decision_status
            """
        ).fetchone()[0]

        connection.execute(
            """
            UPDATE loan_applications
            SET application_status = (
                SELECT d.decision_status
                FROM decisions AS d
                WHERE d.application_id =
                      loan_applications.application_id
            )
            WHERE EXISTS (
                SELECT 1
                FROM decisions AS d
                WHERE d.application_id =
                      loan_applications.application_id
            )
            """
        )

        remaining = connection.execute(
            """
            SELECT COUNT(*)
            FROM loan_applications AS la
            JOIN decisions AS d
              ON d.application_id = la.application_id
            WHERE la.application_status != d.decision_status
            """
        ).fetchone()[0]

        if remaining != 0:
            raise RuntimeError(
                f"Status synchronization failed: {remaining} mismatches remain."
            )

    print(f"Status mismatches before repair: {mismatches}")
    print("Status mismatches after repair: 0")
    print("Application status synchronization PASSED.")


if __name__ == "__main__":
    sync_application_statuses()
