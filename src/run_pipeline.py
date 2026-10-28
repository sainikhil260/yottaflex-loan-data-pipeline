
"""Run the YottaFlex loan data pipeline safely."""

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Respect the database selected through the environment variable.
DATABASE_PATH = Path(
    os.environ.get(
        "YOTTAFLEX_DB_PATH",
        str(PROJECT_ROOT / "data" / "yottaflex.db"),
    )
).resolve()

BACKUP_PATH = DATABASE_PATH.with_name(
    f"{DATABASE_PATH.stem}_backup{DATABASE_PATH.suffix}"
)

# Execute master data first, then applicants and their dependent records.
PIPELINE_STEPS = [
    "check_database.py",
    "master_data.py",
    "generate_master_data.py",
    "generate_applicants.py",
    "add_credit_scores.py",
    "generate_employment.py",
    "generate_income.py",
    "generate_credit.py",
    "generate_applications.py",
    "generate_documents.py",
    "generate_affordability.py",
    "generate_decisions.py",
    "sync_application_statuses.py",
    "generate_repayments.py",
    "generate_anomalies.py",
    "validate_database.py",
    "check_anomaly_integrity.py",
    "check_anomalies.py",
    "check_documents.py",
    "export_csv.py",
    "export_json.py",
    "generate_data_dictionary.py",
]


def run_script(script_name):
    """Run a pipeline script and stop if it fails."""
    script_path = SRC_DIR / script_name

    if not script_path.is_file():
        raise RuntimeError(
            f"Pipeline script not found: {script_path}"
        )

    print(f"\n{'=' * 60}", flush=True)
    print(f"Running: {script_name}", flush=True)
    print("=" * 60, flush=True)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code "
            f"{result.returncode}."
        )


def run_pipeline():
    """Run the pipeline without resetting the selected database."""
    print("YottaFlex Loan Data Pipeline")
    print(f"Project directory: {PROJECT_ROOT}")
    print(f"Selected database: {DATABASE_PATH}")
    print(f"Expected backup: {BACKUP_PATH}")

    if not DATABASE_PATH.is_file():
        print(
            f"ERROR: Selected database does not exist: "
            f"{DATABASE_PATH}"
        )
        raise SystemExit(1)

    if not BACKUP_PATH.is_file():
        print(
            f"ERROR: Database backup does not exist: "
            f"{BACKUP_PATH}"
        )
        print("Create a backup before running the pipeline.")
        raise SystemExit(1)

    print("Backup check: PASS")
    print("Safety mode: database will not be reset by this runner.")
    print("Dataset generation uses the configured random seed.")

    try:
        for script_name in PIPELINE_STEPS:
            run_script(script_name)

    except RuntimeError as error:
        print(f"\nPIPELINE FAILED: {error}")
        print("Fix the reported issue before rerunning.")
        raise SystemExit(1) from error

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("Next command:")
    print("python -m pytest tests -v")


if __name__ == "__main__":
    run_pipeline()
