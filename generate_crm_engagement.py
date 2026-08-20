# generate_crm_engagement.py
# Purpose: simulate CRM/email campaign touches per customer,
# with realistic open/click funnel rates (Braze-style).

import os
import random
from datetime import timedelta
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

CAMPAIGNS = ["Welcome Series", "Cart Abandonment", "Weekly Newsletter", "Win-Back", "Product Announcement"]
CHANNELS = ["email", "push", "sms"]
CHANNEL_WEIGHTS = [0.70, 0.25, 0.05]  # email dominates, realistic for most CRM programs

# Realistic open/click rates — most sends aren't opened, fewer are clicked
OPEN_RATE = 0.35
CLICK_RATE_GIVEN_OPEN = 0.20  # of those who open, 20% click

def fetch_customers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id, signup_date FROM customers")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def generate_engagement(customer_id, signup_date):
    campaign_name = random.choice(CAMPAIGNS)
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0]
    sent_date = signup_date + timedelta(days=random.randint(0, 400))

    opened = random.random() < OPEN_RATE
    clicked = opened and (random.random() < CLICK_RATE_GIVEN_OPEN)  # can't click without opening

    return (customer_id, campaign_name, channel, sent_date, opened, clicked)

def main():
    customers = fetch_customers()
    print(f"Fetched {len(customers)} customers.")

    conn = get_connection()
    cur = conn.cursor()

    # Each customer gets 3–15 CRM touches over their lifetime
    engagement_data = []
    for customer_id, signup_date in customers:
        num_touches = random.randint(3, 15)
        for _ in range(num_touches):
            engagement_data.append(generate_engagement(customer_id, signup_date))

    execute_values(cur, """
        INSERT INTO crm_engagement (customer_id, campaign_name, channel, sent_date, opened, clicked)
        VALUES %s
    """, engagement_data)
    conn.commit()
    cur.close(); conn.close()
    print(f"Inserted {len(engagement_data)} CRM engagement rows.")

if __name__ == "__main__":
    main()