
"""Insert the four master loan products into SQLite."""

import sqlite3
from database import DATABASE_PATH


LOAN_PRODUCTS = [
    {
        "product_id": "PROD-001",
        "product_name": "Personal Loan",
        "min_principal": 10000,
        "max_principal": 500000,
        "annual_interest_rate": 0.18,
        "min_term_months": 6,
        "max_term_months": 60,
    },
    {
        "product_id": "PROD-002",
        "product_name": "Education Loan",
        "min_principal": 25000,
        "max_principal": 1500000,
        "annual_interest_rate": 0.10,
        "min_term_months": 12,
        "max_term_months": 120,
    },
    {
        "product_id": "PROD-003",
        "product_name": "Home Improvement Loan",
        "min_principal": 50000,
        "max_principal": 1000000,
        "annual_interest_rate": 0.12,
        "min_term_months": 12,
        "max_term_months": 84,
    },
    {
        "product_id": "PROD-004",
        "product_name": "Small Business Loan",
        "min_principal": 50000,
        "max_principal": 2000000,
        "annual_interest_rate": 0.16,
        "min_term_months": 6,
        "max_term_months": 60,
    },
]


def insert_loan_products():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executemany(
            """
            INSERT INTO loan_products (
                product_id,
                product_name,
                min_principal,
                max_principal,
                annual_interest_rate,
                min_term_months,
                max_term_months
            )
            VALUES (
                :product_id,
                :product_name,
                :min_principal,
                :max_principal,
                :annual_interest_rate,
                :min_term_months,
                :max_term_months
            )
            ON CONFLICT(product_id) DO NOTHING
            """,
            LOAN_PRODUCTS,
        )

    print(f"Loan products loaded: {len(LOAN_PRODUCTS)}")


if __name__ == "__main__":
    insert_loan_products()
