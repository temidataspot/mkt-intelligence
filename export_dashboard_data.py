# export_dashboard_data.py
# Purpose: run key analysis queries and export each as a clean CSV,
# ready to feed into Looker Studio (via Google Sheets).

import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Create a folder to keep all exports organized
os.makedirs('dashboard_exports', exist_ok=True)


#  1. Channel performance: CAC, ROAS, LTV, LTV:CAC 
channel_performance_query = """
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
    SELECT acquisition_channel, AVG(total_ltv) AS avg_ltv
    FROM customer_ltv WHERE acquisition_channel IN ('Google', 'Meta') GROUP BY acquisition_channel
),
spend_by_channel AS (
    SELECT CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel_clean,
        SUM(cost) AS total_spend
    FROM marketing_spend GROUP BY channel_clean
),
customers_by_channel AS (
    SELECT acquisition_channel, COUNT(*) AS new_customers
    FROM customers WHERE acquisition_channel IN ('Google', 'Meta') GROUP BY acquisition_channel
),
revenue_by_channel AS (
    SELECT c.acquisition_channel, SUM(o.total_amount) AS total_revenue
    FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed' AND c.acquisition_channel IN ('Google', 'Meta')
    GROUP BY c.acquisition_channel
)
SELECT 
    s.channel_clean AS channel,
    s.total_spend,
    c.new_customers,
    ROUND(s.total_spend / c.new_customers, 2) AS cac,
    r.total_revenue,
    ROUND(r.total_revenue / s.total_spend, 2) AS roas,
    ROUND(l.avg_ltv, 2) AS avg_ltv,
    ROUND(l.avg_ltv / (s.total_spend / c.new_customers), 2) AS ltv_to_cac_ratio
FROM spend_by_channel s
INNER JOIN customers_by_channel c ON s.channel_clean = c.acquisition_channel
INNER JOIN revenue_by_channel r ON s.channel_clean = r.acquisition_channel
INNER JOIN ltv_by_channel l ON s.channel_clean = l.acquisition_channel;
"""
channel_performance = pd.read_sql(channel_performance_query, engine)
channel_performance.to_csv('dashboard_exports/channel_performance.csv', index=False)
print(f"channel_performance.csv ({len(channel_performance)} rows)")

#  2. Funnel conversion: stage counts and % of previous stage 
funnel_query = """
WITH funnel_counts AS (
    SELECT event_name, COUNT(*) AS event_count
    FROM ga4_events GROUP BY event_name
),
funnel_ordered AS (
    SELECT event_name, event_count,
        CASE event_name
            WHEN 'page_view' THEN 1 WHEN 'view_item' THEN 2
            WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4
            WHEN 'purchase' THEN 5
        END AS stage_order
    FROM funnel_counts
)
SELECT event_name, event_count,
    ROUND(100.0 * event_count / FIRST_VALUE(event_count) OVER (ORDER BY stage_order), 1) AS pct_of_total,
    ROUND(100.0 * event_count / LAG(event_count) OVER (ORDER BY stage_order), 1) AS pct_of_previous_stage
FROM funnel_ordered
ORDER BY stage_order;
"""
funnel_conversion = pd.read_sql(funnel_query, engine)
funnel_conversion.to_csv('dashboard_exports/funnel_conversion.csv', index=False)
print(f"funnel_conversion.csv ({len(funnel_conversion)} rows)")


#  3. Retention curve: month-over-month retention rate 
retention_query = """
WITH monthly_activity AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', event_date) AS activity_month
    FROM ga4_events
)
SELECT 
    TO_CHAR(a.activity_month, 'YYYY-MM') AS activity_month,
    COUNT(DISTINCT a.customer_id) AS active_customers,
    COUNT(DISTINCT b.customer_id) AS retained_next_month,
    ROUND(100.0 * COUNT(DISTINCT b.customer_id) / COUNT(DISTINCT a.customer_id), 1) AS retention_rate_pct
FROM monthly_activity a
LEFT JOIN monthly_activity b 
    ON a.customer_id = b.customer_id 
    AND b.activity_month = a.activity_month + INTERVAL '1 month'
GROUP BY a.activity_month
ORDER BY a.activity_month;
"""
retention_curve = pd.read_sql(retention_query, engine)
retention_curve.to_csv('dashboard_exports/retention_curve.csv', index=False)
print(f"retention_curve.csv ({len(retention_curve)} rows)")


#  4. ML risk bands: customers grouped into risk/propensity tiers 
ml_bands_query = """
SELECT
    CASE 
        WHEN churn_risk_score >= 0.5 THEN 'High Risk'
        WHEN churn_risk_score >= 0.3 THEN 'Medium Risk'
        WHEN churn_risk_score IS NOT NULL THEN 'Low Risk'
        ELSE 'N/A (not subscriber)'
    END AS churn_risk_band,
    CASE 
        WHEN purchase_propensity_score >= 0.5 THEN 'High Propensity'
        WHEN purchase_propensity_score >= 0.3 THEN 'Medium Propensity'
        ELSE 'Low Propensity'
    END AS propensity_band,
    COUNT(*) AS customer_count,
    ROUND(AVG(predicted_ltv), 2) AS avg_predicted_ltv
FROM customer_scores
GROUP BY churn_risk_band, propensity_band
ORDER BY churn_risk_band, propensity_band;
"""
ml_risk_bands = pd.read_sql(ml_bands_query, engine)
ml_risk_bands.to_csv('dashboard_exports/ml_risk_bands.csv', index=False)
print(f"ml_risk_bands.csv ({len(ml_risk_bands)} rows)")


#  5. A/B test results: conversion rate by variant 
ab_test_query = """
SELECT variant,
    COUNT(*) AS total_assigned,
    SUM(converted::int) AS total_converted,
    ROUND(100.0 * SUM(converted::int) / COUNT(*), 2) AS conversion_rate_pct
FROM ab_test_assignments
GROUP BY variant
ORDER BY variant;
"""
ab_test_results = pd.read_sql(ab_test_query, engine)
ab_test_results.to_csv('dashboard_exports/ab_test_results.csv', index=False)
print(f"ab_test_results.csv ({len(ab_test_results)} rows)")

print("\nAll exports complete!")

#  6. Daily spend trend (time series, for trend charts) 
spend_trend_query = """
SELECT 
    TO_CHAR(DATE_TRUNC('month', spend_date), 'YYYY-MM') AS year_month,
    DATE_TRUNC('month', spend_date) AS month_sort,
    CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel_clean,
    SUM(cost) AS daily_cost,
    SUM(clicks) AS daily_clicks,
    SUM(impressions) AS daily_impressions,
    SUM(conversions) AS daily_conversions
FROM marketing_spend
GROUP BY year_month, month_sort, channel_clean
ORDER BY month_sort;
"""
spend_trend = pd.read_sql(spend_trend_query, engine)
spend_trend.to_csv('dashboard_exports/spend_trend.csv', index=False)
print(f"spend_trend.csv ({len(spend_trend)} rows)")


#  7. Customer breakdown by channel and country 
customer_breakdown_query = """
SELECT acquisition_channel, country, customer_type, COUNT(*) AS customer_count
FROM customers
GROUP BY acquisition_channel, country, customer_type
ORDER BY customer_count DESC;
"""
customer_breakdown = pd.read_sql(customer_breakdown_query, engine)
customer_breakdown.to_csv('dashboard_exports/customer_breakdown.csv', index=False)
print(f"customer_breakdown.csv ({len(customer_breakdown)} rows)")