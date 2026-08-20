# generate_orders.py
# Purpose: generate order records based on customers who actually
# completed a "purchase" event in ga4_events — keeps data consistent
# across tables instead of inventing orders out of thin air.

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

PRODUCTS = {
    "Starter Kit": (39.99, 79.99),
    "Pro Bundle": (89.99, 149.99),
    "Premium Set": (199.99, 349.99),
    "Accessory Pack": (19.99, 49.99),
    "Gift Card": (50.00, 200.00)
}

# Order status weights - most orders complete normally, some refund/cancel
STATUSES = ["completed", "refunded", "cancelled"]
STATUS_WEIGHTS = [0.88, 0.08, 0.04]

def fetch_purchase_events():
    """Get every purchase event: (customer_id, event_date)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id, event_date FROM ga4_events WHERE event_name = 'purchase'")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def generate_order(customer_id, order_date):
    product_name = random.choice(list(PRODUCTS.keys()))
    min_price, max_price = PRODUCTS[product_name]
    unit_price = round(random.uniform(min_price, max_price), 2)
    quantity = random.choices([1, 2, 3, 4], weights=[0.65, 0.20, 0.10, 0.05])[0]
    total_amount = round(unit_price * quantity, 2)
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

    return (customer_id, order_date, product_name, quantity, unit_price, total_amount, status)

def main():
    purchase_events = fetch_purchase_events()
    print(f"Found {len(purchase_events)} purchase events. Generating orders...")

    orders_data = [generate_order(cust_id, event_date) for cust_id, event_date in purchase_events]

    conn = get_connection()
    cur = conn.cursor()
    execute_values(cur, """
        INSERT INTO orders
        (customer_id, order_date, product_name, quantity, unit_price, total_amount, order_status)
        VALUES %s
    """, orders_data)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(orders_data)} orders.")

if __name__ == "__main__":
    main()