# generate_customers.py
# Purpose: generate realistic fake customer records and insert them into
# the "customers" table in Postgres.

import os
import random # Python's built-in module for making random choice
from datetime import date, timedelta
import psycopg2
from dotenv import load_dotenv
from faker import Faker

# Load DB credentials from .env 
load_dotenv()

# Faker gives us realistic fake data generators (names, dates, etc.)
fake = Faker()

# How many
NUM_CUSTOMERS = 20000

# Countries with realistic weights (not evenly distributed).
# 45% of customers are from the US, 15% from the UK, etc.
COUNTRIES = ["United States", "United Kingdom", "Nigeria", "Canada", "Germany", "India"]
COUNTRY_WEIGHTS = [0.45, 0.15, 0.12, 0.10, 0.10, 0.08]  # sum to 1.0

ACQUISITION_CHANNELS = ["Google", "Meta", "Organic", "Referral", "Direct", "Email"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.10, 0.10, 0.05]  # Google/Meta dominate, realistic for paid-heavy ecommerce

CUSTOMER_TYPES = ["ecommerce", "saas", "both"]
TYPE_WEIGHTS = [0.55, 0.30, 0.15]  # most customers are one or the other, fewer do both

def generate_customer():
    days_ago = random.randint(0, 730)
    signup_date = date.today() - timedelta(days=days_ago)

    # random.choices() (note the 's') supports weights — pick 1 item, [0] unpacks it from the list it returns
    acquisition_channel = random.choices(ACQUISITION_CHANNELS, weights=CHANNEL_WEIGHTS)[0]
    country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
    customer_type = random.choices(CUSTOMER_TYPES, weights=TYPE_WEIGHTS)[0]

    return (signup_date, acquisition_channel, country, customer_type)

def main():
    """
    Generates NUM_CUSTOMERS fake customer records and bulk-inserts
    them into the Postgres "customers" table.
    """
    # Step 1: generate all the fake records in memory first
    print(f"Generating {NUM_CUSTOMERS} fake customers...")
    customers_data = [generate_customer() for _ in range(NUM_CUSTOMERS)]

    # Step 2: connect to Postgres using the .env credentials 
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cursor = connection.cursor()

    # Step 3: bulk insert using execute_values, which is much faster
    # than looping and running one INSERT per row.
    from psycopg2.extras import execute_values

    insert_query = """
        INSERT INTO customers (signup_date, acquisition_channel, country, customer_type)
        VALUES %s
    """
    execute_values(cursor, insert_query, customers_data)

    # Step 4: commit the transaction (actually save the changes) and clean up
    connection.commit()
    cursor.close()
    connection.close()

    print(f"Inserted {NUM_CUSTOMERS} customers into the database.")

# This is a standard Python pattern: only run main() if this file is
# executed directly (not if it's imported elsewhere later).
if __name__ == "__main__":
    main()
