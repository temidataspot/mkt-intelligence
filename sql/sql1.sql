-- top 10 most recent orders that were completed (not refunded/cancelled), 
-- including customer_id, order_date, product_name, and total_amount — most recent first.
SELECT * from orders

select customer_id, order_date, product_name, total_amount
from orders
where order_status = 'completed'
order by order_date desc
limit 10;

-- all GA4 events where the event was 'purchase' AND the device_category was 'mobile', 
-- ordered by event_date ascending (oldest first), limited to 15 rows.
select * from ga4_events

select * from ga4_events
where event_name = 'purchase' AND device_category = 'mobile'
order by event_date asc
limit 15;

-- For each channel in marketing_spend, get total cost and total conversions, 
-- ordered by total cost descending
select * from marketing_spend

select channel, sum(cost) AS total_cost, sum(conversions) AS total_conversions
from marketing_spend
group by channel
order by total_cost desc;

-- Show each product_name from orders, along with how many times it was ordered  
-- and its average total_amount, but only include products that were ordered more than 500 times

select * from orders

select product_name, count(*) AS order_count, avg(total_amount) AS avg_total_amt
from orders
group by product_name
having count(*) > 500;


-- Show customer_id, country, order_date, and total_amount for every completed order
-- pulling country from customers and the order details from orders

select c.customer_id, c.country, o.order_date, o.total_amount
from customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
where o.order_status = 'completed';

-- For each country, show the total revenue (SUM(total_amount)) from completed orders 
-- and the number of distinct customers who ordered, ordered by total revenue descending.
select count(distinct(c.customer_id)) AS distinct_customers, c.country, sum(o.total_amount) AS total_revenue
from customers c
inner join orders o ON c.customer_id = o.customer_id
where o.order_status = 'completed'
group by country
order by total_revenue desc;

select * from orders
select * from customers

-- Show every customer's customer_id and country, plus their total spend (SUM(total_amount)) 
-- from completed orders — including customers who have never placed an order 
-- (their total should show as 0 or NULL, not disappear from the results)

SELECT c.customer_id, c.country, SUM(o.total_amount) AS total_spend
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
GROUP BY c.customer_id, c.country;

-- Find all customers whose country is 'Nigeria' AND who have made at least one completed order. 
-- Just return customer_id and country
SELECT customer_id, country
FROM customers
WHERE country = 'Nigeria'
AND customer_id IN (
    SELECT customer_id
    FROM orders
    WHERE order_status = 'completed'
);

-- same task above with CTE
WITH completed_order_customers AS (
    SELECT customer_id
    FROM orders
    WHERE order_status = 'completed'
)
SELECT c.customer_id, c.country
FROM customers c
WHERE c.country = 'Nigeria'
AND c.customer_id IN (SELECT customer_id FROM completed_order_customers);

-- For each acquisition channel, calculate the average total spend per customer
-- (only counting customers who made at least one completed order)
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

-- Rank customers within each country by their total completed-order spend, highest spender first. 
-- Show customer_id, country, total_spend, and their rank

WITH customer_spend AS(
	SELECT c.customer_id, c.country, sum(o.total_amount) AS total_spend
	FROM customers c
	INNER JOIN orders o ON c.customer_id = o.customer_id
	WHERE o.order_status = 'completed'
	GROUP BY c.customer_id, c.country
)
SELECT customer_id, country, total_spend,
	RANK() OVER(PARTITION BY country ORDER BY total_spend DESC) AS spend_rank
FROM customer_spend;

-- For marketing_spend, show each day's cost per channel, plus a running 
-- (cumulative) total of cost per channel over time, ordered by date.
SELECT spend_date, channel, cost,
	SUM(cost) OVER (PARTITION BY channel ORDER BY spend_date) AS total_running_cost
FROM marketing_spend
ORDER BY channel, spend_date;

select * from marketing_spend
select * from customers

-- CAC - customer acquisition cost
-- CAC = total spend on a channel ÷ number of new customers acquired through that channel
-- marketing_spend.channel uses values like 'Google Ads' / 'Meta Ads'
-- customers.acquisition_channel uses 'Google' / 'Meta', these don't match exactly.
-- using CASE statement to resolve
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

-- ROAS - Return on Ad Spend
-- ROAS = revenue generated ÷ ad spend, usually expressed as a multiple 
-- (e.g. "3.5x" means $3.50 earned per $1 spent). Unlike CAC (cost per person), ROAS ties spend to actual revenue, not just customer count.
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


TRUNCATE TABLE marketing_spend RESTART IDENTITY;
TRUNCATE TABLE orders RESTART IDENTITY;


-- =====================================================================
-- CAC (Customer Acquisition Cost) by channel, recalculated after
-- rebalancing marketing_spend generation to more realistic levels.
-- =====================================================================
WITH spend_by_channel AS (
    -- Total ad spend per channel, standardizing naming
    -- ('Google Ads' -> 'Google', 'Meta Ads' -> 'Meta') so it can be
    -- joined against customers.acquisition_channel later.
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
    -- Count of new customers acquired per channel
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


-- =====================================================================
-- ROAS (Return on Ad Spend) by channel, recalculated after rebalancing
-- both marketing_spend (lower cost) and orders (higher order values).
-- =====================================================================
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
    -- Total revenue from completed orders, per acquisition channel
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

-- LAG 
WITH funnel_counts AS (
    -- Count how many events happened at each funnel stage
    SELECT event_name, COUNT(*) AS event_count
    FROM ga4_events
    GROUP BY event_name
),
funnel_ordered AS (
    -- Manually assign each stage its correct funnel order,
    -- since alphabetical/default ordering wouldn't reflect the real sequence
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


-- retention
-- get each customer's active months
WITH monthly_activity AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', event_date) AS activity_month
    FROM ga4_events
)
SELECT * FROM monthly_activity
ORDER BY customer_id, activity_month
LIMIT 20;


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

TRUNCATE TABLE orders RESTART IDENTITY;
TRUNCATE TABLE ga4_events RESTART IDENTITY;





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

WITH ecommerce_revenue AS (
    -- Total completed-order revenue per customer
    SELECT customer_id, SUM(total_amount) AS ecommerce_ltv
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
),
saas_revenue AS (
    -- Total subscription revenue per customer:
    -- mrr * number of months active (use end_date if churned, else today)
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
    -- Combine both revenue types per customer, tagged with their channel
    SELECT c.customer_id, c.acquisition_channel,
        COALESCE(e.ecommerce_ltv, 0) + COALESCE(s.saas_ltv, 0) AS total_ltv
    FROM customers c
    LEFT JOIN ecommerce_revenue e ON c.customer_id = e.customer_id
    LEFT JOIN saas_revenue s ON c.customer_id = s.customer_id
),
ltv_by_channel AS (
    -- Average LTV per channel
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

-- A/B Testing

CREATE TABLE ab_test_assignments (
	assignment_id SERIAL PRIMARY KEY,
	customer_id INTEGER REFERENCES customers(customer_id),
	experiment_name VARCHAR(50),
	variant VARCHAR(10),
	assigned_date DATE NOT NULL,
	converted BOOLEAN
);

select * from ab_test_assignments
-- For each variant in ab_test_assignments, show the total number assigned, 
-- the number converted, and the conversion rate as a percentage.
select variant, 
	count(*) AS total_assigned, 
	sum(converted::int) AS total_converted,
	round(100.0 * sum(converted::int)/count(*), 2) AS conversion_rate_pct
from ab_test_assignments
group by variant
order by variant;
where converted ='true'







