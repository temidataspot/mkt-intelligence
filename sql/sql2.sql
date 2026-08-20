-- churn_features.sql
-- Purpose: build one row per active/cancelled SaaS subscriber, with
-- churn-predictive features. This becomes our ML training dataset.

SELECT 
    s.customer_id,
    s.plan_name,
    
    -- Tenure: how many months they've been subscribed (up to today if
    -- still active, or up to end_date if cancelled — this is fine to use,
    -- it's just "how long were/have they been a subscriber," not leakage).
    EXTRACT(YEAR FROM AGE(COALESCE(s.end_date, CURRENT_DATE), s.start_date)) * 12 +
    EXTRACT(MONTH FROM AGE(COALESCE(s.end_date, CURRENT_DATE), s.start_date)) AS tenure_months,
    
    s.mrr,
    
    -- GA4 engagement: total events and distinct active days, ever
    COALESCE(ga.total_events, 0) AS total_events,
    COALESCE(ga.active_days, 0) AS active_days,
    
    -- CRM engagement: how many emails opened / clicked, ever
    COALESCE(crm.total_sent, 0) AS crm_emails_sent,
    COALESCE(crm.total_opened, 0) AS crm_emails_opened,
    COALESCE(crm.total_clicked, 0) AS crm_emails_clicked,
    
    -- Cross-buying: does this SaaS customer also buy physical products?
    CASE WHEN c.customer_type = 'both' THEN 1 ELSE 0 END AS also_ecommerce,
    
    -- TARGET VARIABLE: what we're trying to predict
    CASE WHEN s.status = 'cancelled' THEN 1 ELSE 0 END AS churned

FROM subscriptions s
INNER JOIN customers c ON s.customer_id = c.customer_id

-- Aggregate GA4 activity per customer (subquery-as-table, aliased as "ga")
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS total_events, COUNT(DISTINCT event_date) AS active_days
    FROM ga4_events
    GROUP BY customer_id
) ga ON c.customer_id = ga.customer_id

-- Aggregate CRM engagement per customer (aliased as "crm")
LEFT JOIN (
    SELECT customer_id, 
        COUNT(*) AS total_sent,
        SUM(opened::int) AS total_opened,
        SUM(clicked::int) AS total_clicked
    FROM crm_engagement
    GROUP BY customer_id
) crm ON c.customer_id = crm.customer_id

WHERE s.status IN ('active', 'cancelled');  -- exclude 'paused' — keep it clean binary