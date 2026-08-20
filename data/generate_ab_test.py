# generate_ab_test.py
# Purpose: simulate a checkout redesign A/B test — randomly assign
# customers to variant A (control) or B (treatment), then simulate
# whether they converted, with a real, known lift built into variant B.

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

EXPERIMENT_NAME = "checkout_redesign"

# The TRUE conversion rates I'm building into the simulation.
# In real life we'd never know these in advance so I'll set them here
# on purpose so I can later verify my statistical test correctly
# detects the real effect.
CONVERSION_RATE_A = 0.25   # control: 25% of assigned customers convert
CONVERSION_RATE_B = 0.29   # treatment: 29% — a real, modest lift

def fetch_eligible_customers():
    """
    Anyone who has reached 'begin_checkout' at least once is eligible
    for this experiment — they're the realistic population you'd test
    a checkout redesign on.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT customer_id FROM ga4_events
        WHERE event_name = 'begin_checkout' AND customer_id IS NOT NULL
    """)
    rows = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def main():
    customer_ids = fetch_eligible_customers()
    print(f"Found {len(customer_ids)} eligible customers.")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM ab_test_assignments")
    if cur.fetchone()[0] > 0: # type: ignore
        print("⚠️ ab_test_assignments already has data. Aborting to prevent duplicates.")
        cur.close(); conn.close(); return

    assignments = []
    for customer_id in customer_ids:
        # Coin flip: 50/50 random assignment to A or B — the core
        # principle of a real randomized controlled experiment.
        variant = random.choice(['A', 'B'])

        # Use the TRUE conversion rate for whichever variant they landed in
        true_rate = CONVERSION_RATE_A if variant == 'A' else CONVERSION_RATE_B
        converted = random.random() < true_rate

        assigned_date = date.today() - timedelta(days=random.randint(0, 60))
        assignments.append((customer_id, EXPERIMENT_NAME, variant, assigned_date, converted))

    execute_values(cur, """
        INSERT INTO ab_test_assignments (customer_id, experiment_name, variant, assigned_date, converted)
        VALUES %s
    """, assignments)
    conn.commit()
    cur.close(); conn.close()
    print(f"Inserted {len(assignments)} A/B test assignments.")

if __name__ == "__main__":
    main()