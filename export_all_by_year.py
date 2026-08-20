"""
export_all_by_year.py
Pulls REAL year-by-year breakdowns for every section of the dashboard —
channel performance, funnel, retention, ML risk bands, and A/B test
results — all segmented by year so the React dashboard's Year filter
can be backed by genuine data instead of estimates.

Run this locally (with Postgres running):
    python export_all_by_year.py

It writes dashboard_data.json and also prints it to the terminal.
Upload dashboard_data.json back to Claude (or paste its contents) so
the dashboard can be rebuilt with real numbers throughout.
"""

import os
import json
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

output = {}


# 1. Customer growth by year + month (one row per customer)

q = """
SELECT
    EXTRACT(YEAR FROM signup_date)::int AS year,
    TO_CHAR(signup_date, 'Mon') AS month,
    EXTRACT(MONTH FROM signup_date)::int AS month_num,
    COUNT(*) AS customers
FROM customers
GROUP BY year, month, month_num
ORDER BY year, month_num;
"""
output["customer_growth"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"customer_growth: {len(output['customer_growth'])} rows")


# 2. Spend + conversions by year + month + channel (real)

q = """
SELECT
    EXTRACT(YEAR FROM spend_date)::int AS year,
    TO_CHAR(spend_date, 'Mon') AS month,
    EXTRACT(MONTH FROM spend_date)::int AS month_num,
    CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel,
    SUM(cost) AS spend,
    SUM(conversions) AS conversions
FROM marketing_spend
GROUP BY year, month, month_num, channel
ORDER BY year, month_num;
"""
output["spend_trend"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"spend_trend: {len(output['spend_trend'])} rows")


# 3. Channel performance BY SIGNUP YEAR (cohort-based breakdown)
# CAC/ROAS/LTV/LTV:CAC for customers who signed up in each year,
# measured to-date. This is the correct, honest way to segment these
# metrics by year - "how did the Year-Y signup cohort perform".

q = """
WITH ecommerce_revenue AS (
    SELECT customer_id, SUM(total_amount) AS ecommerce_ltv
    FROM orders WHERE order_status = 'completed' GROUP BY customer_id
),
saas_revenue AS (
    SELECT customer_id,
        SUM(mrr * GREATEST(
            EXTRACT(YEAR FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)) * 12 +
            EXTRACT(MONTH FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)), 1)) AS saas_ltv
    FROM subscriptions GROUP BY customer_id
),
customer_ltv AS (
    SELECT c.customer_id, c.acquisition_channel,
        EXTRACT(YEAR FROM c.signup_date)::int AS signup_year,
        COALESCE(e.ecommerce_ltv, 0) + COALESCE(s.saas_ltv, 0) AS total_ltv
    FROM customers c
    LEFT JOIN ecommerce_revenue e ON c.customer_id = e.customer_id
    LEFT JOIN saas_revenue s ON c.customer_id = s.customer_id
    WHERE c.acquisition_channel IN ('Google', 'Meta')
),
ltv_by_year_channel AS (
    SELECT signup_year, acquisition_channel AS channel, AVG(total_ltv) AS avg_ltv, COUNT(*) AS new_customers
    FROM customer_ltv GROUP BY signup_year, acquisition_channel
),
spend_by_year_channel AS (
    SELECT EXTRACT(YEAR FROM spend_date)::int AS signup_year,
        CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel,
        SUM(cost) AS total_spend
    FROM marketing_spend GROUP BY signup_year, channel
),
revenue_by_year_channel AS (
    SELECT EXTRACT(YEAR FROM c.signup_date)::int AS signup_year,
        c.acquisition_channel AS channel, SUM(o.total_amount) AS total_revenue
    FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed' AND c.acquisition_channel IN ('Google', 'Meta')
    GROUP BY signup_year, c.acquisition_channel
)
SELECT
    l.signup_year AS year, l.channel,
    l.new_customers,
    ROUND(l.avg_ltv, 2) AS avg_ltv,
    s.total_spend,
    ROUND(s.total_spend / NULLIF(l.new_customers, 0), 2) AS cac,
    r.total_revenue,
    ROUND(r.total_revenue / NULLIF(s.total_spend, 0), 2) AS roas,
    ROUND(l.avg_ltv / NULLIF(s.total_spend / NULLIF(l.new_customers, 0), 0), 2) AS ltv_to_cac_ratio
FROM ltv_by_year_channel l
LEFT JOIN spend_by_year_channel s ON l.signup_year = s.signup_year AND l.channel = s.channel
LEFT JOIN revenue_by_year_channel r ON l.signup_year = r.signup_year AND l.channel = r.channel
ORDER BY l.signup_year, l.channel;
"""
output["channel_performance_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"channel_performance_by_year: {len(output['channel_performance_by_year'])} rows")

# All-time version too, for the "All years" filter option
q_alltime = """
WITH ecommerce_revenue AS (
    SELECT customer_id, SUM(total_amount) AS ecommerce_ltv
    FROM orders WHERE order_status = 'completed' GROUP BY customer_id
),
saas_revenue AS (
    SELECT customer_id,
        SUM(mrr * GREATEST(
            EXTRACT(YEAR FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)) * 12 +
            EXTRACT(MONTH FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)), 1)) AS saas_ltv
    FROM subscriptions GROUP BY customer_id
),
customer_ltv AS (
    SELECT c.customer_id, c.acquisition_channel,
        COALESCE(e.ecommerce_ltv, 0) + COALESCE(s.saas_ltv, 0) AS total_ltv
    FROM customers c
    LEFT JOIN ecommerce_revenue e ON c.customer_id = e.customer_id
    LEFT JOIN saas_revenue s ON c.customer_id = s.customer_id
),
ltv_by_channel AS (
    SELECT acquisition_channel AS channel, AVG(total_ltv) AS avg_ltv
    FROM customer_ltv WHERE acquisition_channel IN ('Google', 'Meta') GROUP BY acquisition_channel
),
spend_by_channel AS (
    SELECT CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel,
        SUM(cost) AS total_spend
    FROM marketing_spend GROUP BY channel
),
customers_by_channel AS (
    SELECT acquisition_channel AS channel, COUNT(*) AS new_customers
    FROM customers WHERE acquisition_channel IN ('Google', 'Meta') GROUP BY acquisition_channel
),
revenue_by_channel AS (
    SELECT c.acquisition_channel AS channel, SUM(o.total_amount) AS total_revenue
    FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed' AND c.acquisition_channel IN ('Google', 'Meta')
    GROUP BY c.acquisition_channel
)
SELECT
    s.channel, s.total_spend, c.new_customers,
    ROUND(s.total_spend / c.new_customers, 2) AS cac,
    r.total_revenue,
    ROUND(r.total_revenue / s.total_spend, 2) AS roas,
    ROUND(l.avg_ltv, 2) AS avg_ltv,
    ROUND(l.avg_ltv / (s.total_spend / c.new_customers), 2) AS ltv_to_cac_ratio
FROM spend_by_channel s
INNER JOIN customers_by_channel c ON s.channel = c.channel
INNER JOIN revenue_by_channel r ON s.channel = r.channel
INNER JOIN ltv_by_channel l ON s.channel = l.channel;
"""
output["channel_performance_all_time"] = pd.read_sql(q_alltime, engine).to_dict(orient="records")
print(f"channel_performance_all_time: {len(output['channel_performance_all_time'])} rows")


# 4. Funnel BY YEAR (based on when the event happened)

q = """
WITH funnel_counts AS (
    SELECT EXTRACT(YEAR FROM event_date)::int AS year, event_name, COUNT(*) AS event_count
    FROM ga4_events GROUP BY year, event_name
)
SELECT year, event_name, event_count,
    CASE event_name
        WHEN 'page_view' THEN 1 WHEN 'view_item' THEN 2
        WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4
        WHEN 'purchase' THEN 5 END AS stage_order
FROM funnel_counts ORDER BY year, stage_order;
"""
output["funnel_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"funnel_by_year: {len(output['funnel_by_year'])} rows")

q_alltime = """
WITH funnel_counts AS (
    SELECT event_name, COUNT(*) AS event_count FROM ga4_events GROUP BY event_name
)
SELECT event_name, event_count,
    CASE event_name
        WHEN 'page_view' THEN 1 WHEN 'view_item' THEN 2
        WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4
        WHEN 'purchase' THEN 5 END AS stage_order
FROM funnel_counts ORDER BY stage_order;
"""
output["funnel_all_time"] = pd.read_sql(q_alltime, engine).to_dict(orient="records")
print(f"funnel_all_time: {len(output['funnel_all_time'])} rows")


# 5. Retention - already monthly, extract year for filtering (real)

q = """
WITH monthly_activity AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', event_date) AS activity_month
    FROM ga4_events
)
SELECT
    EXTRACT(YEAR FROM a.activity_month)::int AS year,
    TO_CHAR(a.activity_month, 'Mon') AS month,
    EXTRACT(MONTH FROM a.activity_month)::int AS month_num,
    COUNT(DISTINCT a.customer_id) AS active_customers,
    COUNT(DISTINCT b.customer_id) AS retained_next_month,
    ROUND(100.0 * COUNT(DISTINCT b.customer_id) / COUNT(DISTINCT a.customer_id), 1) AS retention_rate_pct
FROM monthly_activity a
LEFT JOIN monthly_activity b
    ON a.customer_id = b.customer_id
    AND b.activity_month = a.activity_month + INTERVAL '1 month'
GROUP BY year, month, month_num ORDER BY year, month_num;
"""
output["retention_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"retention_by_year: {len(output['retention_by_year'])} rows")


# 6. ML risk/propensity bands BY SIGNUP YEAR

q = """
SELECT
    EXTRACT(YEAR FROM c.signup_date)::int AS year,
    CASE
        WHEN cs.churn_risk_score >= 0.5 THEN 'High Risk'
        WHEN cs.churn_risk_score >= 0.3 THEN 'Medium Risk'
        WHEN cs.churn_risk_score IS NOT NULL THEN 'Low Risk'
        ELSE NULL
    END AS churn_risk_band,
    COUNT(*) AS customer_count,
    ROUND(AVG(cs.predicted_ltv), 2) AS avg_predicted_ltv
FROM customers c
INNER JOIN customer_scores cs ON c.customer_id = cs.customer_id
WHERE cs.churn_risk_score IS NOT NULL
GROUP BY year, churn_risk_band
ORDER BY year, churn_risk_band;
"""
output["churn_risk_bands_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"churn_risk_bands_by_year: {len(output['churn_risk_bands_by_year'])} rows")

q = """
SELECT
    EXTRACT(YEAR FROM c.signup_date)::int AS year,
    CASE
        WHEN cs.purchase_propensity_score >= 0.5 THEN 'High'
        WHEN cs.purchase_propensity_score >= 0.3 THEN 'Medium'
        ELSE 'Low'
    END AS propensity_band,
    COUNT(*) AS customer_count
FROM customers c
INNER JOIN customer_scores cs ON c.customer_id = cs.customer_id
GROUP BY year, propensity_band
ORDER BY year, propensity_band;
"""
output["propensity_bands_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"propensity_bands_by_year: {len(output['propensity_bands_by_year'])} rows")


# 7. A/B test results BY YEAR (based on assigned_date)

q = """
SELECT
    EXTRACT(YEAR FROM assigned_date)::int AS year,
    variant, COUNT(*) AS total_assigned,
    SUM(converted::int) AS total_converted,
    ROUND(100.0 * SUM(converted::int) / COUNT(*), 2) AS conversion_rate_pct
FROM ab_test_assignments GROUP BY year, variant ORDER BY year, variant;
"""
output["ab_test_by_year"] = pd.read_sql(q, engine).to_dict(orient="records")
print(f"ab_test_by_year: {len(output['ab_test_by_year'])} rows")

q_alltime = """
SELECT variant, COUNT(*) AS total_assigned,
    SUM(converted::int) AS total_converted,
    ROUND(100.0 * SUM(converted::int) / COUNT(*), 2) AS conversion_rate_pct
FROM ab_test_assignments GROUP BY variant ORDER BY variant;
"""
output["ab_test_all_time"] = pd.read_sql(q_alltime, engine).to_dict(orient="records")
print(f"ab_test_all_time: {len(output['ab_test_all_time'])} rows")


# Save
with open("dashboard_data.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print("\n🎉 Saved dashboard_data.json")
print("   Upload this file back to Claude (or paste its contents) so the")
print("   React dashboard can be rebuilt with 100% real, year-accurate data.")
