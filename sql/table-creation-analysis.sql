-- SECTION 1: SCHEMA — TABLE CREATION

-- customers table
-- One row per person who becomes a customer.
-- This is our "core" table — almost everything else references it.
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,        -- auto-incrementing unique ID
    signup_date DATE NOT NULL,             -- date they first signed up
    acquisition_channel VARCHAR(50),       -- e.g. 'Google', 'Meta', 'Organic', 'Referral'
    country VARCHAR(50),                   -- simple geography field for segmentation
    customer_type VARCHAR(20)              -- 'ecommerce', 'saas', or 'both'
);

select * from customers

-- marketing_spend table
-- One row per day, per channel, per campaign.
-- Simulates data normally pulled from Google Ads / Meta Ads Insights APIs.
CREATE TABLE marketing_spend (
    spend_id SERIAL PRIMARY KEY,
    spend_date DATE NOT NULL,
    channel VARCHAR(50) NOT NULL,          -- 'Google Ads' or 'Meta Ads'
    campaign_name VARCHAR(100),
    impressions INTEGER,
    clicks INTEGER,
    cost NUMERIC(10,2),                    -- NUMERIC is the correct type for money
    conversions INTEGER
    -- Note: no customer_id FK here on purpose — ad platforms report at
    -- the campaign level, not the individual customer level. This
    -- table lives at a different "grain" than customers.
);
select * from marketing_spend

-- ga4_events table
-- One row per event in a customer's browsing session.
-- Simulates a real GA4 event export.
CREATE TABLE ga4_events (
    event_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),  -- nullable: anonymous browsing exists
    event_date DATE NOT NULL,
    event_name VARCHAR(50),                -- 'page_view','view_item','add_to_cart','begin_checkout','purchase'
    page_path VARCHAR(200),
    session_id VARCHAR(100),
    traffic_source VARCHAR(50),
    device_category VARCHAR(50)
);

-- orders table — the e-commerce side
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    product_name VARCHAR(50),
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    total_amount NUMERIC(10,2),
    order_status VARCHAR(50)               -- 'completed','refunded','cancelled'
);

-- subscriptions table — the SaaS side
CREATE TABLE subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    plan_name VARCHAR(50),                 -- 'Basic','Pro','Enterprise'
    start_date DATE NOT NULL,
    end_date DATE,                         -- nullable: still-active subscribers have no end date
    mrr NUMERIC(10,2),                     -- Monthly Recurring Revenue
    status VARCHAR(50)                     -- 'active','cancelled','paused'
);

-- crm_engagement table — Braze-style email/push/SMS campaign touches
CREATE TABLE crm_engagement (
    engagement_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    campaign_name VARCHAR(50),
    channel VARCHAR(50),                   -- 'email','push','sms'
    sent_date DATE NOT NULL,
    opened BOOLEAN,
    clicked BOOLEAN
);


-- SECTION 2

-- 2.1 — SELECT / WHERE / ORDER BY / LIMIT
-- 10 most recent completed orders.
SELECT customer_id, order_date, product_name, total_amount
FROM orders
WHERE order_status = 'completed'
ORDER BY order_date DESC
LIMIT 10;

-- 2.2 — Filtering with AND, ascending order
-- Purchase events made on mobile, oldest first.
SELECT *
FROM ga4_events
WHERE event_name = 'purchase' AND device_category = 'mobile'
ORDER BY event_date ASC
LIMIT 15;


-- SECTION 3:


-- 3.1 — Total cost and conversions per channel
SELECT channel, SUM(cost) AS total_cost, SUM(conversions) AS total_conversions
FROM marketing_spend
GROUP BY channel
ORDER BY total_cost DESC;

-- 3.2 — Products ordered more than 500 times, with average order value
-- Note: HAVING can't reference a SELECT alias (it runs before SELECT),
-- so we repeat the aggregate function itself.
SELECT product_name, COUNT(*) AS order_count, AVG(total_amount) AS avg_total_amt
FROM orders
GROUP BY product_name
HAVING COUNT(*) > 500;


-- =====================================================================
-- SECTION 4: JOINS
-- =====================================================================

-- 4.1 — INNER JOIN: customer country + order details for completed orders
-- Table aliases (c, o) make repeated references shorter and unambiguous.
SELECT c.customer_id, c.country, o.order_date, o.total_amount
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'completed';

-- 4.2 — JOIN + aggregation: revenue and distinct customers per country
SELECT COUNT(DISTINCT c.customer_id) AS distinct_customers, c.country,
       SUM(o.total_amount) AS total_revenue
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'completed'
GROUP BY c.country
ORDER BY total_revenue DESC;

-- 4.3 — LEFT JOIN: every customer's total spend, including customers
-- with ZERO completed orders (they show NULL/0 instead of disappearing).
-- Key detail: the 'completed' filter lives in the ON clause, not WHERE —
-- putting it in WHERE would silently turn this back into an INNER JOIN
-- by filtering out the very NULL rows we want to keep.
SELECT c.customer_id, c.country, SUM(o.total_amount) AS total_spend
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
GROUP BY c.customer_id, c.country;


-- SECTION 5: SUBQUERIES & CTEs

-- 5.1 — Subquery version: Nigerian customers with at least one completed order
SELECT customer_id, country
FROM customers
WHERE country = 'Nigeria'
AND customer_id IN (
    SELECT customer_id
    FROM orders
    WHERE order_status = 'completed'
);

-- 5.2 — Same logic as a CTE (more readable, same result)
WITH completed_order_customers AS (
    SELECT customer_id
    FROM orders
    WHERE order_status = 'completed'
)
SELECT c.customer_id, c.country
FROM customers c
WHERE c.country = 'Nigeria'
AND c.customer_id IN (SELECT customer_id FROM completed_order_customers);

-- 5.3 — Two-stage CTE: average total spend per customer, by channel
-- Stage 1 collapses to one row per customer (their total spend).
-- Stage 2 collapses those customer-level rows down to one row per channel.
WITH customer_spend AS (
    SELECT c.customer_id, c.acquisition_channel, SUM(o.total_amount) AS total_spend
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed'
    GROUP BY c.customer_id, c.acquisition_channel
)
SELECT acquisition_channel, AVG(total_spend) AS avg_spend_per_customer
FROM customer_spend
GROUP BY acquisition_channel
ORDER BY avg_spend_per_customer DESC;



-- SECTION 6: WINDOW FUNCTIONS


-- 6.1 — RANK(): rank customers within each country by completed-order spend
WITH customer_spend AS (
    SELECT c.customer_id, c.country, SUM(o.total_amount) AS total_spend
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed'
    GROUP BY c.customer_id, c.country
)
SELECT customer_id, country, total_spend,
    RANK() OVER (PARTITION BY country ORDER BY total_spend DESC) AS spend_rank
FROM customer_spend;

-- 6.2 — Running total: cumulative spend per channel over time
SELECT spend_date, channel, cost,
    SUM(cost) OVER (PARTITION BY channel ORDER BY spend_date) AS running_total_cost
FROM marketing_spend
ORDER BY channel, spend_date;



-- SECTION 7: BUSINESS METRICS

-- 7.1 — CAC (Customer Acquisition Cost) by channel
-- marketing_spend uses 'Google Ads'/'Meta Ads'; customers uses
-- 'Google'/'Meta' — CASE WHEN standardizes the naming so we can join.
WITH spend_by_channel AS (
    SELECT
        CASE
            WHEN channel = 'Google Ads' THEN 'Google'
            WHEN channel = 'Meta Ads' THEN 'Meta'
        END AS channel_clean,
        SUM(cost) AS total_spend
    FROM marketing_spend
    GROUP BY channel_clean
),
customers_by_channel AS (
    SELECT acquisition_channel, COUNT(*) AS new_customers
    FROM customers
    WHERE acquisition_channel IN ('Google', 'Meta')
    GROUP BY acquisition_channel
)
SELECT s.channel_clean, s.total_spend, c.new_customers,
    ROUND(s.total_spend / c.new_customers, 2) AS cac
FROM spend_by_channel s
INNER JOIN customers_by_channel c ON s.channel_clean = c.acquisition_channel
ORDER BY cac;

-- 7.2 — ROAS (Return on Ad Spend) by channel
WITH spend_by_channel AS (
    SELECT
        CASE
            WHEN channel = 'Google Ads' THEN 'Google'
            WHEN channel = 'Meta Ads' THEN 'Meta'
        END AS channel_clean,
        SUM(cost) AS total_spend
    FROM marketing_spend
    GROUP BY channel_clean
),
revenue_by_channel AS (
    SELECT c.acquisition_channel, SUM(o.total_amount) AS total_revenue
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'completed' AND c.acquisition_channel IN ('Google', 'Meta')
    GROUP BY c.acquisition_channel
)
SELECT s.channel_clean, s.total_spend, r.total_revenue,
    ROUND(r.total_revenue / s.total_spend, 2) AS roas
FROM spend_by_channel s
INNER JOIN revenue_by_channel r ON s.channel_clean = r.acquisition_channel
ORDER BY roas DESC;

-- 7.3 — Funnel conversion rate, stage over stage
-- LAG() looks at the previous row's value within the ordered sequence.
-- Multiplying by 100.0 (not 100) forces decimal math instead of
-- truncating integer division.
WITH funnel_counts AS (
    SELECT event_name, COUNT(*) AS event_count
    FROM ga4_events
    GROUP BY event_name
),
funnel_ordered AS (
    SELECT event_name, event_count,
        CASE event_name
            WHEN 'page_view' THEN 1
            WHEN 'view_item' THEN 2
            WHEN 'add_to_cart' THEN 3
            WHEN 'begin_checkout' THEN 4
            WHEN 'purchase' THEN 5
        END AS stage_order
    FROM funnel_counts
)
SELECT event_name, event_count,
    LAG(event_count) OVER (ORDER BY stage_order) AS previous_stage_count,
    ROUND(100.0 * event_count / LAG(event_count) OVER (ORDER BY stage_order), 1) AS pct_of_previous_stage
FROM funnel_ordered
ORDER BY stage_order;

-- 7.4 — Retention: month-over-month active customer retention
-- DATE_TRUNC rounds each event date down to the 1st of its month.
-- A self-join (table joined to itself) checks whether the same
-- customer was also active exactly one month later.
WITH monthly_activity AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', event_date) AS activity_month
    FROM ga4_events
)
SELECT
    a.activity_month,
    COUNT(DISTINCT a.customer_id) AS active_customers,
    COUNT(DISTINCT b.customer_id) AS retained_next_month,
    ROUND(100.0 * COUNT(DISTINCT b.customer_id) / COUNT(DISTINCT a.customer_id), 1) AS retention_rate_pct
FROM monthly_activity a
LEFT JOIN monthly_activity b
    ON a.customer_id = b.customer_id
    AND b.activity_month = a.activity_month + INTERVAL '1 month'
GROUP BY a.activity_month
ORDER BY a.activity_month;

-- 7.5 — LTV (Lifetime Value): combines ecommerce orders + SaaS subscriptions
-- COALESCE(value, 0) turns NULLs (from LEFT JOINs where a customer has
-- no orders or no subscription) into 0 so the totals don't break.
-- AGE() + EXTRACT() convert a subscription's start/end dates into a
-- total number of months active, so MRR can be multiplied out properly.
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
SELECT c.customer_id, c.acquisition_channel,
    COALESCE(e.ecommerce_ltv, 0) AS ecommerce_ltv,
    COALESCE(s.saas_ltv, 0) AS saas_ltv,
    COALESCE(e.ecommerce_ltv, 0) + COALESCE(s.saas_ltv, 0) AS total_ltv
FROM customers c
LEFT JOIN ecommerce_revenue e ON c.customer_id = e.customer_id
LEFT JOIN saas_revenue s ON c.customer_id = s.customer_id
ORDER BY total_ltv DESC
LIMIT 20;

-- 7.6 — LTV : CAC ratio by channel — the headline metric.
-- Chains 5 CTEs together: LTV per customer -> avg LTV per channel,
-- and spend/customers -> CAC per channel, then joins the two results.
-- Rule of thumb: 3:1 or higher is considered healthy.
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
    FROM customer_ltv
    WHERE acquisition_channel IN ('Google', 'Meta')
    GROUP BY acquisition_channel
),
spend_by_channel AS (
    SELECT
        CASE WHEN channel = 'Google Ads' THEN 'Google' WHEN channel = 'Meta Ads' THEN 'Meta' END AS channel_clean,
        SUM(cost) AS total_spend
    FROM marketing_spend
    GROUP BY channel_clean
),
customers_by_channel AS (
    SELECT acquisition_channel, COUNT(*) AS new_customers
    FROM customers
    WHERE acquisition_channel IN ('Google', 'Meta')
    GROUP BY acquisition_channel
),
cac_by_channel AS (
    SELECT s.channel_clean AS acquisition_channel,
        ROUND(s.total_spend / c.new_customers, 2) AS cac
    FROM spend_by_channel s
    INNER JOIN customers_by_channel c ON s.channel_clean = c.acquisition_channel
)
SELECT l.acquisition_channel, ROUND(l.avg_ltv, 2) AS avg_ltv, c.cac,
    ROUND(l.avg_ltv / c.cac, 2) AS ltv_to_cac_ratio
FROM ltv_by_channel l
INNER JOIN cac_by_channel c ON l.acquisition_channel = c.acquisition_channel
ORDER BY ltv_to_cac_ratio DESC;