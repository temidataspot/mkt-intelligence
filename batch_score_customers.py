# batch_score_customers.py
# Purpose: load the three trained models, score every current customer,
# and write the results into the customer_scores table. This is the
# script that would run on a schedule (e.g. nightly) in production.

import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("Loading saved models...")
churn_model = joblib.load('churn_model.pkl')
churn_model_features = joblib.load('churn_model_features.pkl')

purchase_model = joblib.load('purchase_model.pkl')
purchase_model_features = joblib.load('purchase_model_features.pkl')

ltv_model = joblib.load('ltv_model.pkl')
ltv_model_features = joblib.load('ltv_model_features.pkl')

print("Models loaded.")

def align_features(data, expected_columns):
    """
    Ensures a DataFrame has exactly the columns a model expects, in the
    right order — adding any missing one-hot columns as 0 (e.g. if
    today's data happens to have no 'India' customers, that column
    might not get created by get_dummies, but the model still expects it).
    """
    for col in expected_columns:
        if col not in data.columns:
            data[col] = 0
    return data[expected_columns]

#  Score churn risk (only for active subscribers) 
print("Scoring churn risk...")
churn_query = """
    SELECT 
        s.customer_id, s.plan_name,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.start_date)) * 12 +
        EXTRACT(MONTH FROM AGE(CURRENT_DATE, s.start_date)) AS tenure_months,
        s.mrr,
        COALESCE(ga.total_events, 0) AS total_events,
        COALESCE(ga.active_days, 0) AS active_days,
        COALESCE(crm.total_sent, 0) AS crm_emails_sent,
        COALESCE(crm.total_opened, 0) AS crm_emails_opened,
        COALESCE(crm.total_clicked, 0) AS crm_emails_clicked,
        CASE WHEN c.customer_type = 'both' THEN 1 ELSE 0 END AS also_ecommerce
    FROM subscriptions s
    INNER JOIN customers c ON s.customer_id = c.customer_id
    LEFT JOIN (SELECT customer_id, COUNT(*) AS total_events, COUNT(DISTINCT event_date) AS active_days
        FROM ga4_events GROUP BY customer_id) ga ON c.customer_id = ga.customer_id
    LEFT JOIN (SELECT customer_id, COUNT(*) AS total_sent, SUM(opened::int) AS total_opened, SUM(clicked::int) AS total_clicked
        FROM crm_engagement GROUP BY customer_id) crm ON c.customer_id = crm.customer_id
    WHERE s.status = 'active';
"""
churn_data = pd.read_sql(churn_query, engine)
churn_ids = churn_data['customer_id']
churn_data_encoded = pd.get_dummies(churn_data, columns=['plan_name'], drop_first=True)
churn_data_aligned = align_features(churn_data_encoded, churn_model_features)
churn_scores = churn_model.predict_proba(churn_data_aligned)[:, 1]  # probability of class 1 (churned)

print(f"Scored {len(churn_ids)} active subscribers for churn risk.")

#  Score purchase propensity (all customers) 
print("Scoring purchase propensity...")
propensity_query = """
    SELECT
        c.customer_id, c.acquisition_channel, c.country, c.customer_type,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.signup_date)) * 12 +
        EXTRACT(MONTH FROM AGE(CURRENT_DATE, c.signup_date)) AS account_age_months,
        COALESCE(browse.page_views, 0) AS page_views,
        COALESCE(browse.view_item_events, 0) AS view_item_events,
        COALESCE(browse.distinct_sessions, 0) AS distinct_sessions,
        COALESCE(browse.mobile_session_pct, 0) AS mobile_session_pct,
        COALESCE(crm.total_sent, 0) AS crm_emails_sent,
        COALESCE(crm.total_opened, 0) AS crm_emails_opened,
        COALESCE(crm.total_clicked, 0) AS crm_emails_clicked
    FROM customers c
    LEFT JOIN (
        SELECT customer_id,
            COUNT(*) FILTER (WHERE event_name = 'page_view') AS page_views,
            COUNT(*) FILTER (WHERE event_name = 'view_item') AS view_item_events,
            COUNT(DISTINCT session_id) AS distinct_sessions,
            ROUND(100.0 * COUNT(*) FILTER (WHERE device_category = 'mobile') / COUNT(*), 1) AS mobile_session_pct
        FROM ga4_events WHERE event_name IN ('page_view', 'view_item') GROUP BY customer_id
    ) browse ON c.customer_id = browse.customer_id
    LEFT JOIN (SELECT customer_id, COUNT(*) AS total_sent, SUM(opened::int) AS total_opened, SUM(clicked::int) AS total_clicked
        FROM crm_engagement GROUP BY customer_id) crm ON c.customer_id = crm.customer_id;
"""
propensity_data = pd.read_sql(propensity_query, engine)
propensity_ids = propensity_data['customer_id']
propensity_data_encoded = pd.get_dummies(propensity_data, columns=['acquisition_channel', 'country', 'customer_type'], drop_first=True)
propensity_data_aligned = align_features(propensity_data_encoded, purchase_model_features)
propensity_scores = purchase_model.predict_proba(propensity_data_aligned)[:, 1]

print(f"Scored {len(propensity_ids)} customers for purchase propensity.")


# --- Score predicted LTV (all customers) ---
print("Scoring predicted LTV...")
ltv_data = propensity_data.copy()  # same feature set as propensity, reused
ltv_ids = ltv_data['customer_id']
ltv_data_encoded = pd.get_dummies(ltv_data, columns=['acquisition_channel', 'country', 'customer_type'], drop_first=True)
ltv_data_aligned = align_features(ltv_data_encoded, ltv_model_features)
ltv_log_predictions = ltv_model.predict(ltv_data_aligned)
ltv_predictions = np.expm1(ltv_log_predictions)  # convert back from log scale to dollars

print(f"Scored {len(ltv_ids)} customers for predicted LTV.")

# --- Combine all scores into one table and write to Postgres ---
print("Combining scores...")

churn_scores_df = pd.DataFrame({'customer_id': churn_ids, 'churn_risk_score': churn_scores})
propensity_scores_df = pd.DataFrame({'customer_id': propensity_ids, 'purchase_propensity_score': propensity_scores})
ltv_scores_df = pd.DataFrame({'customer_id': ltv_ids, 'predicted_ltv': ltv_predictions})

# Merge all three on customer_id. Use outer joins since not every
# customer has a churn score (only active subscribers do) — customers
# without one will simply show NULL for that column, which is correct.
combined_scores = propensity_scores_df.merge(ltv_scores_df, on='customer_id', how='outer')
combined_scores = combined_scores.merge(churn_scores_df, on='customer_id', how='outer')
combined_scores['scored_at'] = datetime.now()

# Reorder columns to match the table structure
combined_scores = combined_scores[['customer_id', 'churn_risk_score', 'purchase_propensity_score', 'predicted_ltv', 'scored_at']]

print(f"Combined into {len(combined_scores)} total scored customers.")

# Clear any previous scores before inserting fresh ones — this script
# represents a full daily/nightly refresh, not an incremental append.
with engine.connect() as connection:
    connection.execute(text("TRUNCATE TABLE customer_scores"))
    connection.commit()

combined_scores.to_sql('customer_scores', engine, if_exists='append', index=False)

print(f"Wrote {len(combined_scores)} rows to customer_scores.")

# Scored 6225 active subscribers for churn risk.
# Scored 20000 customers for purchase propensity.
# Scored 20000 customers for predicted LTV.
# Combined into 20000 total scored customers.
