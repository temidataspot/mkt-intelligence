-- creating customers table

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,        -- auto-incrementing unique ID for each customer
    signup_date DATE NOT NULL,             -- the date they first signed up
    acquisition_channel VARCHAR(50),       -- e.g. 'Google', 'Meta', 'Organic', 'Referral'
    country VARCHAR(50),                   -- simple geography field, useful for segmentation
    customer_type VARCHAR(20)              -- 'ecommerce', 'saas', or 'both'
);

-- creating marketing spend table

CREATE TABLE marketing_spend (
	spend_id SERIAL PRIMARY KEY,					-- unique id for each row
	spend_date DATE NOT NULL,				-- day of spend
	channel VARCHAR(50) NOT NULL,			-- marketing channel eg google ads, meta ads
	campaign_name VARCHAR(100),				-- name of ad campaign
	impressions INTEGER,					-- how many times ad was shown
	clicks INTEGER,							-- how many times ad was clicked
	cost NUMERIC(10,2),						-- money spent to 2 d.p
	conversions INTEGER						-- how many conversions the platform attribute to this campaign
);

-- creating ga4 table
CREATE TABLE ga4_events (
	event_id SERIAL PRIMARY KEY,			-- unique event id
	customer_id INTEGER REFERENCES customers(customer_id),				-- customer triggering an event
	event_date DATE NOT NULL, 				-- date of event occurence
	event_name VARCHAR(50),					-- type of ga4 event
	page_path VARCHAR(200),						-- page/url where event happened
	session_id VARCHAR(100),				-- group event into a single visit or session
	traffic_source VARCHAR(50),				-- where the event came from
	device_category VARCHAR(50)				-- device used
);

-- creating orders table
CREATE TABLE orders(
	order_id SERIAL PRIMARY KEY,
	customer_id INTEGER REFERENCES customers(customer_id),
	order_date DATE NOT NULL,
	product_name VARCHAR(50),
	quantity INTEGER,
	unit_price NUMERIC(10,2),
	total_amount NUMERIC(10,2),
	order_status VARCHAR(50)	
);

-- creating subscriptions table
CREATE TABLE subscriptions(
	subscription_id SERIAL PRIMARY KEY,
	customer_id INTEGER REFERENCES customers(customer_id),
	plan_name VARCHAR(50),
	start_date DATE NOT NULL,
	end_date DATE,
	mrr NUMERIC(10,2),
	status VARCHAR(50)
);

-- creating crm engagement table
CREATE TABLE crm_engagement(
	engagement_id SERIAL PRIMARY KEY,
	customer_id INTEGER REFERENCES customers(customer_id),
	campaign_name VARCHAR(50),
	channel VARCHAR(50),
	sent_date DATE NOT NULL,
	opened BOOLEAN,
	clicked BOOLEAN
);

-- quick sanity check: count rows and preview a sample
SELECT COUNT(*) FROM customers;

SELECT * FROM customers LIMIT 10;

-- check the distribution looks realistic (not evenly split)
SELECT country, COUNT(*) AS num_customers
FROM customers
GROUP BY country
ORDER BY num_customers DESC;

-- confirm funnel shape: counts should decrease at each stage
SELECT event_name, COUNT(*) AS event_count
FROM ga4_events
GROUP BY event_name
ORDER BY event_count DESC;



-- Wipe the orders table clean so we can reload it correctly.
-- TRUNCATE is faster than DELETE for clearing an entire table,
-- and RESTART IDENTITY resets the auto-incrementing order_id back to 1.
TRUNCATE TABLE orders RESTART IDENTITY;

SELECT * FROM orders;
SELECT * FROM subscriptions;
SELECT * FROM marketing_spend;
SELECT * FROM ga4_events;
SELECT * FROM customers;
SELECT * FROM crm_engagement;


SELECT * FROM customer_scores
ORDER BY churn_risk_score DESC NULLS LAST
LIMIT 10;



