-- purchase_propensity_features.sql
-- Purpose: predict whether a customer will make a purchase, using
-- only signals that exist independently of the purchase funnel itself
-- (no add_to_cart/begin_checkout — those are too close to the outcome).

SELECT
    c.customer_id,
    c.acquisition_channel,
    c.country,
    c.customer_type,

    -- Account age: how long they've been a customer
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.signup_date)) * 12 +
    EXTRACT(MONTH FROM AGE(CURRENT_DATE, c.signup_date)) AS account_age_months,

    -- Top-of-funnel browsing only — page_view and view_item,
    -- deliberately excluding add_to_cart/begin_checkout (too close to outcome)
    COALESCE(browse.page_views, 0) AS page_views,
    COALESCE(browse.view_item_events, 0) AS view_item_events,
    COALESCE(browse.distinct_sessions, 0) AS distinct_sessions,

    -- Most common device across their sessions (a simple behavioral signal)
    COALESCE(browse.mobile_session_pct, 0) AS mobile_session_pct,

    -- CRM engagement — independent of the purchase funnel
    COALESCE(crm.total_sent, 0) AS crm_emails_sent,
    COALESCE(crm.total_opened, 0) AS crm_emails_opened,
    COALESCE(crm.total_clicked, 0) AS crm_emails_clicked,

    -- TARGET VARIABLE
    CASE WHEN o.customer_id IS NOT NULL THEN 1 ELSE 0 END AS purchased

FROM customers c

-- Browsing behavior: only page_view and view_item events
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
) crm ON c.customer_id = crm.customer_id

-- Just need to know IF they purchased, one row per customer regardless
-- of how many orders — DISTINCT customer_id from completed orders
LEFT JOIN (
    SELECT DISTINCT customer_id FROM orders WHERE order_status = 'completed'
) o ON c.customer_id = o.customer_id;


-- customer_scores table
-- Stores the latest ML-generated scores for every customer.
-- A real production system would refresh this table on a schedule
-- (e.g. nightly), and dashboards/CRM tools would read from it directly.

CREATE TABLE customer_scores (
    customer_id INTEGER PRIMARY KEY REFERENCES customers(customer_id),
    churn_risk_score NUMERIC(5,4),        -- probability of churning, 0 to 1
    purchase_propensity_score NUMERIC(5,4), -- probability of purchasing, 0 to 1
    predicted_ltv NUMERIC(10,2),           -- predicted lifetime value in dollars
    scored_at TIMESTAMP NOT NULL           -- when this score was generated
);