# Data Dictionary — Marketing Intelligence Project

**Database:** `marketing_intel_db` (PostgreSQL)
**Business model simulated:** hybrid e-commerce + SaaS company
**Scale:** ~389,000 rows across 7 tables

This document describes every table and column in the database: what it represents, its data type, the values it can take, and how it relates to other tables.

---

## 1. `customers`

The core table — one row per person who becomes a customer. Nearly every other table references this one via `customer_id`.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `customer_id` | `SERIAL` (PK) | Unique identifier for the customer | Auto-incrementing integer |
| `signup_date` | `DATE` | Date the customer first signed up | Spread over the last ~2 years |
| `acquisition_channel` | `VARCHAR(50)` | How the customer was acquired | `Google`, `Meta`, `Organic`, `Referral`, `Direct`, `Email` — weighted distribution (Google/Meta most common) |
| `country` | `VARCHAR(50)` | Customer's country | `United States`, `United Kingdom`, `Nigeria`, `Canada`, `Germany`, `India` — weighted (US most common) |
| `customer_type` | `VARCHAR(20)` | Which side(s) of the business this customer belongs to | `ecommerce`, `saas`, `both` |

**Row count:** 20,000

---

## 2. `marketing_spend`

Simulates daily ad performance data, as if pulled from the Google Ads and Meta Ads Insights APIs. One row per campaign, per day. **Not** linked to `customers` — ad platforms report at the campaign level, not the individual level.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `spend_id` | `SERIAL` (PK) | Unique identifier for the row | Auto-incrementing integer |
| `spend_date` | `DATE` | The day this spend/performance data covers | Daily granularity, ~2 years of history |
| `channel` | `VARCHAR(50)` | Ad platform | `Google Ads`, `Meta Ads` |
| `campaign_name` | `VARCHAR(100)` | Name of the ad campaign | e.g. `Search - Brand`, `Feed - Retargeting` — 4 campaigns per channel |
| `impressions` | `INTEGER` | Number of times the ad was shown that day | |
| `clicks` | `INTEGER` | Number of clicks that day | Derived from impressions × a realistic CTR (1–5%) |
| `cost` | `NUMERIC(10,2)` | Amount spent that day, in currency units | Derived from clicks × a channel-specific CPC range |
| `conversions` | `INTEGER` | Conversions attributed to the campaign that day | Derived from clicks × a realistic conversion rate (2–8%) |

**Note:** `channel` values (`Google Ads`/`Meta Ads`) differ from `customers.acquisition_channel` (`Google`/`Meta`) — queries joining the two must standardize naming (see `CASE WHEN` pattern used throughout the analysis).

**Row count:** 5,840 (730 days × 2 channels × 4 campaigns)

---

## 3. `ga4_events`

Simulates a GA4 event export — one row per event within a customer's browsing session. Session dates follow a month-by-month activity model (not pure random) so that realistic retention patterns emerge.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `event_id` | `SERIAL` (PK) | Unique identifier for the event | Auto-incrementing integer |
| `customer_id` | `INTEGER` (FK → `customers`) | Which customer triggered the event | Nullable — not used in practice here, but supports anonymous browsing conceptually |
| `event_date` | `DATE` | Date the event occurred | |
| `event_name` | `VARCHAR(50)` | Type of GA4 event | `page_view`, `view_item`, `add_to_cart`, `begin_checkout`, `purchase` — ordered funnel stages |
| `page_path` | `VARCHAR(200)` | URL/page where the event happened | e.g. `/pricing`, `/checkout`, `/product/123` |
| `session_id` | `VARCHAR(100)` | Groups events into a single visit | UUID, unique per session |
| `traffic_source` | `VARCHAR(50)` | Where the session's traffic came from | Mirrors the customer's `acquisition_channel`, lowercased (`google`, `meta`, `organic`, `referral`, `direct`, `email`) |
| `device_category` | `VARCHAR(50)` | Device used for the session | `desktop`, `mobile`, `tablet` (mobile/desktop ~45% each, tablet ~10%) |

**Funnel logic:** each session walks through the funnel stages in order, with a real drop-off probability at each stage (page_view 100% → view_item 55% → add_to_cart 30% → begin_checkout 55% → purchase 65%), so purchase events are naturally rare relative to page views.

**Row count:** 183,360

---

## 4. `orders`

The e-commerce side of the business — one row per order. Generated from customers who reached a `purchase` event in `ga4_events`, so order volume is internally consistent with GA4 activity.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `order_id` | `SERIAL` (PK) | Unique identifier for the order | Auto-incrementing integer |
| `customer_id` | `INTEGER` (FK → `customers`) | Who placed the order | |
| `order_date` | `DATE` | Date the order was placed | Matches the corresponding GA4 purchase event date |
| `product_name` | `VARCHAR(50)` | Product purchased | `Starter Kit`, `Pro Bundle`, `Premium Set`, `Accessory Pack`, `Gift Card` |
| `quantity` | `INTEGER` | Units ordered | 1–4, weighted toward 1 |
| `unit_price` | `NUMERIC(10,2)` | Price per unit | Varies by product, realistic ranges |
| `total_amount` | `NUMERIC(10,2)` | `unit_price × quantity` | |
| `order_status` | `VARCHAR(50)` | Order outcome | `completed` (88%), `refunded` (8%), `cancelled` (4%) |

**Row count:** 5,857

---

## 5. `subscriptions`

The SaaS side of the business — one row per subscription. Generated only for customers whose `customer_type` is `saas` or `both`.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `subscription_id` | `SERIAL` (PK) | Unique identifier for the subscription | Auto-incrementing integer |
| `customer_id` | `INTEGER` (FK → `customers`) | Who holds the subscription | |
| `plan_name` | `VARCHAR(50)` | Subscription tier | `Basic` ($15/mo, 55%), `Pro` ($45/mo, 35%), `Enterprise` ($150/mo, 10%) |
| `start_date` | `DATE` | Subscription start date | Shortly after `customers.signup_date` |
| `end_date` | `DATE`, nullable | Subscription end date | `NULL` if still active |
| `mrr` | `NUMERIC(10,2)` | Monthly Recurring Revenue for this subscription | Fixed per plan (see `plan_name`) |
| `status` | `VARCHAR(50)` | Current subscription status | `active` (70%), `cancelled` (25%), `paused` (5%) |

**Row count:** 8,940

---

## 6. `crm_engagement`

Simulates Braze-style email/push/SMS campaign touches — one row per message sent to a customer.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `engagement_id` | `SERIAL` (PK) | Unique identifier for the row | Auto-incrementing integer |
| `customer_id` | `INTEGER` (FK → `customers`) | Who the message was sent to | |
| `campaign_name` | `VARCHAR(50)` | Name of the CRM campaign | `Welcome Series`, `Cart Abandonment`, `Weekly Newsletter`, `Win-Back`, `Product Announcement` |
| `channel` | `VARCHAR(50)` | Delivery channel | `email` (70%), `push` (25%), `sms` (5%) |
| `sent_date` | `DATE` | Date the message was sent | |
| `opened` | `BOOLEAN` | Whether the customer opened it | ~35% open rate |
| `clicked` | `BOOLEAN` | Whether the customer clicked it | Only possible if `opened = true`; ~20% of opens click |

**Row count:** 180,182

---

## 7. `ab_test_assignments`

Simulates a randomized checkout-redesign A/B test. One row per customer assigned to the experiment.

| Column | Type | Description | Values / Notes |
|---|---|---|---|
| `assignment_id` | `SERIAL` (PK) | Unique identifier for the row | Auto-incrementing integer |
| `customer_id` | `INTEGER` (FK → `customers`) | Which customer was assigned | Only customers who reached `begin_checkout` at least once are eligible |
| `experiment_name` | `VARCHAR(50)` | Name of the experiment | `checkout_redesign` |
| `variant` | `VARCHAR(10)` | Which version the customer saw | `A` (control), `B` (treatment) — random 50/50 split |
| `assigned_date` | `DATE` | Date the customer entered the experiment | |
| `converted` | `BOOLEAN` | Whether the customer completed checkout | True conversion rates built into the simulation: A = 25%, B = 29% |

**Row count:** 6,916

---

## Entity relationships

```
customers (1) ──< ga4_events (many)
customers (1) ──< orders (many)
customers (1) ──< subscriptions (many)
customers (1) ──< crm_engagement (many)
customers (1) ──< ab_test_assignments (many)

marketing_spend  — standalone, not linked to customers (campaign-level grain, not individual-level)
```

## Known data-quality notes (for transparency)

- **`marketing_spend.channel`** uses `'Google Ads'`/`'Meta Ads'`; **`customers.acquisition_channel`** uses `'Google'`/`'Meta'`. Any query joining the two must standardize naming (a `CASE WHEN` mapping is used throughout the project's SQL).
- **`marketing_spend` and `orders` pricing/cost** were rebalanced once during the project after an initial pass produced an unrealistically low ROAS (~0.1x); current values were tuned to produce a believable, profitable ROAS (2–4x range).
- **`ga4_events` session timing** was rebuilt once: the original version scattered session dates uniformly at random across each customer's lifetime, producing unrealistically low month-over-month retention (~15–20%). The current version uses a month-by-month activity simulation with stickiness decay and reactivation probability, producing a realistic ~52–61% steady-state retention rate.
- **`orders`** was regenerated to stay consistent whenever `ga4_events`' purchase events changed, since order volume is derived from GA4 purchase events rather than generated independently.