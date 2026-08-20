# generate_subscriptions.py
# Purpose: generate subscription records for customers whose type is
# 'saas' or 'both', keeping this consistent with the customers table.

import os
import random
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

PLANS = {
    "Basic": 15.00,
    "Pro": 45.00,
    "Enterprise": 150.00
}
PLAN_WEIGHTS = [0.55, 0.35, 0.10]  # most customers are on cheaper plans

# Of all SaaS subscribers, how many are still active vs. churned
STATUS_WEIGHTS = {"active": 0.70, "cancelled": 0.25, "paused": 0.05}

def fetch_saas_customers():
    """Get customers eligible for a subscription: type saas or both."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, signup_date FROM customers
        WHERE customer_type IN ('saas', 'both')
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def generate_subscription(customer_id, signup_date):
    plan_name = random.choices(list(PLANS.keys()), weights=PLAN_WEIGHTS)[0]
    mrr = PLANS[plan_name]

    # Subscription starts a few days after signup (a realistic small lag)
    start_date = signup_date + timedelta(days=random.randint(0, 14))

    status = random.choices(list(STATUS_WEIGHTS.keys()), weights=list(STATUS_WEIGHTS.values()))[0]

    # Only cancelled/paused subscriptions get an end_date; active ones are ongoing (None)
    end_date = None
    if status in ("cancelled", "paused"):
        days_active = random.randint(30, 500)
        end_date = start_date + timedelta(days=days_active)
        # Cap end_date at today, so we don't get subscriptions "ending" in the future
        if end_date > date.today():
            end_date = date.today()

    return (customer_id, plan_name, start_date, end_date, mrr, status)

def main():
    saas_customers = fetch_saas_customers()
    print(f"Found {len(saas_customers)} SaaS-eligible customers.")

    conn = get_connection()
    cur = conn.cursor()

    subscriptions_data = [generate_subscription(cid, sdate) for cid, sdate in saas_customers]

    execute_values(cur, """
        INSERT INTO subscriptions (customer_id, plan_name, start_date, end_date, mrr, status)
        VALUES %s
    """, subscriptions_data)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(subscriptions_data)} subscriptions.")

if __name__ == "__main__":
    main()