# generate_marketing_spend.py
# Purpose: simulate daily marketing spend data per channel/campaign,
# mimicking exports from Google Ads and Meta Ads Insights APIs.

import os
import random
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# I'll generate one row per campaign, per day, over this many past days
NUM_DAYS = 730  # 2 years, matching the customers' signup range

CHANNELS = ["Google Ads", "Meta Ads"]

CAMPAIGNS = {
    "Google Ads": ["Search - Brand", "Search - Generic", "Shopping - Ecommerce", "Display - Retargeting"],
    "Meta Ads": ["Feed - Prospecting", "Feed - Retargeting", "Stories - Awareness", "Reels - Conversion"]
}

# Realistic cost-per-click ranges by channel (in currency units)
CPC_RANGE = {
    "Google Ads": (0.30, 1.50),
    "Meta Ads": (0.15, 0.80)
}

def generate_spend_row(spend_date, channel, campaign_name):
    """
    Builds one realistic row of daily ad performance data,
    following a natural funnel: impressions -> clicks -> conversions.
    Returns a tuple matching marketing_spend's column order:
    (spend_date, channel, campaign_name, impressions, clicks, cost, conversions)
    """
    # Impressions: how many times the ad was shown that day.
    # Randomized within a realistic daily range.
    impressions = random.randint(100, 3000)

    # Click-through rate (CTR): what % of impressions turn into clicks.
    # Real CTRs are usually low — typically 1% to 5%.
    ctr = random.uniform(0.01, 0.05)
    clicks = int(impressions * ctr)

    # Cost-per-click: pick a random value within this channel's realistic range
    min_cpc, max_cpc = CPC_RANGE[channel]
    cpc = random.uniform(min_cpc, max_cpc)
    cost = round(clicks * cpc, 2)

    # Conversion rate: what % of clicks actually convert.
    # Realistic range is roughly 2% to 8%.
    conversion_rate = random.uniform(0.02, 0.08)
    conversions = int(clicks * conversion_rate)

    return (spend_date, channel, campaign_name, impressions, clicks, cost, conversions)

def main():
    """
    Generates daily spend rows for every campaign, across every channel,
    for the past NUM_DAYS days, and bulk-inserts them into marketing_spend.
    """
    spend_data = []

    # Loop over every day in the date range
    for days_ago in range(NUM_DAYS):
        spend_date = date.today() - timedelta(days=days_ago)

        # For each day, loop over every channel
        for channel in CHANNELS:
            # And for each channel, loop over its campaigns
            for campaign_name in CAMPAIGNS[channel]:
                row = generate_spend_row(spend_date, channel, campaign_name)
                spend_data.append(row)

    print(f"Generated {len(spend_data)} rows of marketing spend data.")
    print("Connecting to database...")

    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cursor = connection.cursor()

    insert_query = """
        INSERT INTO marketing_spend
        (spend_date, channel, campaign_name, impressions, clicks, cost, conversions)
        VALUES %s
    """
    execute_values(cursor, insert_query, spend_data)

    connection.commit()
    cursor.close()
    connection.close()

    print(f"Inserted {len(spend_data)} rows into marketing_spend.")

if __name__ == "__main__":
    main()