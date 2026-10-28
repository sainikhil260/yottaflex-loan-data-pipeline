
"""Configuration for the YottaFlex loan data pipeline."""

RANDOM_SEED = 20261022
DATASET_MODE = "full"  # Change to "full" for the full dataset.

# Starter dataset.
STARTER_NUM_APPLICANTS = 100
STARTER_NUM_LOAN_APPLICATIONS = 60

# Full challenge dataset.
FULL_NUM_APPLICANTS = 10_000
FULL_NUM_LOAN_APPLICATIONS = 6_000

# Select active dataset sizes.
if DATASET_MODE == "starter":
    NUM_APPLICANTS = STARTER_NUM_APPLICANTS
    NUM_LOAN_APPLICATIONS = STARTER_NUM_LOAN_APPLICATIONS
elif DATASET_MODE == "full":
    NUM_APPLICANTS = FULL_NUM_APPLICANTS
    NUM_LOAN_APPLICATIONS = FULL_NUM_LOAN_APPLICATIONS
else:
    raise ValueError(
        "DATASET_MODE must be either 'starter' or 'full'."
    )

NUM_LOAN_PRODUCTS = 4
CURRENCY = "INR"
MAX_DTI_RATIO = 0.40

MIN_BORDERLINE_SCORE = 650
MAX_BORDERLINE_SCORE = 680
