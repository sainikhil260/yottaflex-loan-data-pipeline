# YottaFlex Loan Processing Data Pipeline

A reproducible synthetic data pipeline for a loan-processing workflow. The project generates relational loan data, simulates affordability checks and loan decisions, identifies labeled anomalies, validates data integrity, and exports datasets to CSV and JSON.

## Project Objectives

- Generate deterministic synthetic loan-processing data using a fixed random seed.
- Model applicants, employment, income, credit facilities, loan products, applications, documents, affordability checks, decisions, and repayments.
- Represent missing income proof, high debt burden, unstable employment, borderline credit scores, and duplicate applications.
- Validate primary keys, foreign keys, business rules, dates, and repayment schedules.
- Export generated data for analysis and downstream experimentation.

## Technology Stack

- Python
- SQLite
- Pandas
- Pytest
- CSV and JSON

## Data Model

The database contains these tables:

| Table | Purpose |
|---|---|
| `applicants` | Applicant master records |
| `employment` | Employment details |
| `income_records` | Applicant income records |
| `credit_facilities` | Existing credit obligations |
| `loan_products` | Loan product terms and limits |
| `loan_applications` | Loan application details |
| `documents` | Application document records and statuses |
| `affordability_checks` | Income, debt, repayment, and affordability metrics |
| `decisions` | Application decision records |
| `repayment_schedules` | Repayment installments for approved loans |
| `application_events` | Application event history |
| `anomaly_labels` | Synthetic anomaly types and ground-truth labels |

## Requirements

- Python 3.13 or a compatible Python version
- Windows, macOS, or Linux
- A terminal or PowerShell

## Setup on Windows PowerShell

Clone or download the repository, then navigate to its root folder.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configure the Dataset

Open `src/config.py`.

The current configuration uses:

- Random seed: `20261022`
- Dataset mode: `starter`
- Starter dataset: 100 applicants and 60 loan applications
- Full dataset: 10,000 applicants and 6,000 loan applications
- Loan products: 4

To generate the full dataset, change `DATASET_MODE` from `"starter"` to `"full"`.

## Run the Pipeline

From the project root, with the virtual environment activated, run:

```powershell
python src/run_pipeline.py
```

The pipeline generates and validates the database records before exporting datasets.

**Important:** Back up your database before changing dataset modes or regenerating data. Review the pipeline configuration and scripts before running it against an existing database.

## Run Tests

Execute the test suite:

```powershell
python -m pytest tests -v
```

Compile a Python module to check for syntax errors:

```powershell
python -m py_compile src/check_documents.py
```

## Output Files

Generated outputs are stored under the `data` directory.

- `data/yottaflex.db` — SQLite database
- `data/exports/` — CSV exports
- `data/json/` — JSON exports

The `.gitignore` excludes local database files, the virtual environment, Python caches, and `.env` files from Git.

## Data Quality and Validation

The pipeline includes validation scripts for database integrity, application decisions, repayment schedules, anomaly labels, and document records.

Checks include:

- Primary-key uniqueness and foreign-key integrity
- Valid credit-score ranges
- Application decision coverage
- Repayment schedules for approved applications
- Valid document types, statuses, and timestamps
- Valid anomaly types and ground-truth labels

## Synthetic Data and Responsible Use

All records are intended for development, testing, and demonstration. They are synthetic and should not be treated as real customer information, actual credit assessments, or production lending decisions.

Ground-truth anomaly labels should be kept separate from model input features when building or evaluating machine-learning models.

## Limitations

This project is a demonstration pipeline, not a production lending platform. Production use would require additional security, access controls, audit requirements, privacy safeguards, monitoring, and independent validation of lending rules.

## License

Add an appropriate license before distributing or publishing this repository.
