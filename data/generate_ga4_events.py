# generate_ga4_events.py
# Purpose: simulate realistic GA4 event data — sessions with logical
# event sequences (view -> cart -> checkout -> purchase), not random noise.

import os
import random
import uuid
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Reusable connection helper"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# Map each customer's acquisition_channel to a realistic GA4 traffic_source value
CHANNEL_TO_TRAFFIC_SOURCE = {
    "Google": "google", "Meta": "meta", "Organic": "organic",
    "Referral": "referral", "Direct": "direct", "Email": "email"
}

DEVICE_CATEGORIES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.45, 0.45, 0.10]  # mobile/desktop split roughly evenly, tablet rare

PAGES = ["/", "/products", "/pricing", "/product/123", "/cart", "/checkout", "/signup", "/blog/marketing-tips"]

# The funnel: each stage has a probability of the customer proceeding
# to the next stage, given they reached the current one. This is the
# key realism trick — most people drop off, fewer make it to purchase.
FUNNEL_STAGES = [
    ("page_view", 1.00),      # everyone in a session at least views a page
    ("view_item", 0.55),      # 55% go on to view a product
    ("add_to_cart", 0.30),    # of those, 30% add to cart
    ("begin_checkout", 0.55), # of those, 55% start checkout
    ("purchase", 0.65),       # of those, 65% complete purchase
]

def fetch_customers():
    """Pull (customer_id, acquisition_channel, signup_date) for every customer."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id, acquisition_channel, signup_date FROM customers")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def generate_session_events(customer_id, traffic_source, session_date):
    """
    Simulates one browsing session for a customer, walking the funnel
    stage by stage. Returns a list of event tuples for this session.
    """
    session_id = str(uuid.uuid4())  # unique random ID per session
    device = random.choices(DEVICE_CATEGORIES, weights=DEVICE_WEIGHTS)[0]

    events = []
    for event_name, probability in FUNNEL_STAGES:
        # Roll the dice: does the customer proceed to this stage?
        if random.random() > probability:
            break  # they dropped off — session ends here, no further events

        page_path = random.choice(PAGES)
        events.append((
            customer_id, session_date, event_name, page_path,
            session_id, traffic_source, device
        ))

    return events

def main():
    customers = fetch_customers()
    print(f"Fetched {len(customers)} customers. Generating sessions...")

    all_events = []
    for customer_id, acquisition_channel, signup_date in customers:
        traffic_source = CHANNEL_TO_TRAFFIC_SOURCE.get(acquisition_channel, "direct")

        # --- Month-by-month activity simulation (creates realistic retention) ---
        months_since_signup = max((date.today().year - signup_date.year) * 12 +
                                   (date.today().month - signup_date.month), 1)

        was_active_last_month = True  # everyone is "active" the month they sign up
        base_retention_chance = 0.55  # chance of returning next month if active last month
        churn_decay = 0.03            # retention chance shrinks slightly each month (natural decay)

        for month_offset in range(months_since_signup):
            month_start = signup_date + timedelta(days=30 * month_offset)

            if month_offset == 0:
                is_active_this_month = True  # signup month always has activity
            elif was_active_last_month:
                # Returning customers have a decaying chance to stay active
                chance = max(base_retention_chance - churn_decay * month_offset, 0.05)
                is_active_this_month = random.random() < chance
            else:
                # Customers who already churned have a small chance of reactivating
                is_active_this_month = random.random() < 0.05

            if is_active_this_month:
                # 1-3 sessions within this month if active
                num_sessions_this_month = random.randint(1, 3)
                for _ in range(num_sessions_this_month):
                    day_offset = random.randint(0, 29)
                    session_date = month_start + timedelta(days=day_offset)
                    if session_date > date.today():
                        session_date = date.today()
                    all_events.extend(generate_session_events(customer_id, traffic_source, session_date))

            was_active_last_month = is_active_this_month

    print(f"Generated {len(all_events)} total events. Inserting...")

    conn = get_connection()
    cur = conn.cursor()
    execute_values(cur, """
        INSERT INTO ga4_events
        (customer_id, event_date, event_name, page_path, session_id, traffic_source, device_category)
        VALUES %s
    """, all_events)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(all_events)} GA4 events.")

if __name__ == "__main__":
    main()