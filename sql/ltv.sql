-- ltv_prediction_features.sql
-- Purpose: predict a customer's total lifetime value from early,
-- independent signals — same leakage discipline as before.

WITH ecommerce_revenue AS (
    SELECT customer_id, SUM(total_amount) AS ecommerce_ltv
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
),
saas_revenue AS (
    SELECT customer_id,
        SUM(mrr * GREATEST(
            EXTRACT(YEAR FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)) * 12 +
            EXTRACT(MONTH FROM AGE(COALESCE(end_date, CURRENT_DATE), start_date)),
        1)) AS saas_ltv
    FROM subscriptions
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.acquisition_channel,
    c.country,
    c.customer_type,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.signup_date)) * 12 +
    EXTRACT(MONTH FROM AGE(CURRENT_DATE, c.signup_date)) AS account_age_months,
    COALESCE(browse.page_views, 0) AS page_views,
    COALESCE(browse.view_item_events, 0) AS view_item_events,
    COALESCE(browse.distinct_sessions, 0) AS distinct_sessions,
    COALESCE(browse.mobile_session_pct, 0) AS mobile_session_pct,
    COALESCE(crm.total_sent, 0) AS crm_emails_sent,
    COALESCE(crm.total_opened, 0) AS crm_emails_opened,
    COALESCE(crm.total_clicked, 0) AS crm_emails_clicked,

    -- TARGET VARIABLE: total lifetime value
    COALESCE(e.ecommerce_ltv, 0) + COALESCE(s.saas_ltv, 0) AS total_ltv

FROM customers c
LEFT JOIN ecommerce_revenue e ON c.customer_id = e.customer_id
LEFT JOIN saas_revenue s ON c.customer_id = s.customer_id
LEFT JOIN (
    SELECT customer_id,
        COUNT(*) FILTER (WHERE event_name = 'page_view') AS page_views,
        COUNT(*) FILTER (WHERE event_name = 'view_item') AS view_item_events,
        COUNT(DISTINCT session_id) AS distinct_sessions,
        ROUND(100.0 * COUNT(*) FILTER (WHERE device_category = 'mobile') / COUNT(*), 1) AS mobile_session_pct
    FROM ga4_events
    WHERE event_name IN ('page_view', 'view_item')
    GROUP BY customer_id
) browse ON c.customer_id = browse.customer_id
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS total_sent,
        SUM(opened::int) AS total_opened, SUM(clicked::int) AS total_clicked
    FROM crm_engagement
    GROUP BY customer_id
) crm ON c.customer_id = crm.customer_id;