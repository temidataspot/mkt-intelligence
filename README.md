# Marketing Intelligence Project

**Built by Temi Priscilla Jokotola**


*Looker [Google Data Studio]* → [![AI](https://img.shields.io/badge/Looker%20Dashboard-250e14)](https://datastudio.google.com/reporting/e034ed39-f62b-4f19-bbaa-2bd30f7f4cb4)


Intelligence for a hybrid e-commerce + SaaS company:
building a data pipeline from scratch, writing SQL analysis from
first principles, running A/B tests, building and validating
three machine learning models, and shipping two different dashboards.

The data, the schema, the pipeline, the
analysis, the models were built end-to-end, including finding and
fixing real data-quality issues along the way (see "Lessons & fixes
along the way" below).

---

## Tech stack

- **PostgreSQL**: the warehouse
- **Python**: (pandas, psycopg2, SQLAlchemy, Faker) — data simulation and pipeline
- **SQL**: all analysis, written by hand (no ORM query builders)
- **scikit-learn**: churn prediction, purchase propensity, LTV prediction
- **statsmodels**: A/B test significance testing
- **Jupyter**: ML model development
- **Looker Studio**: BI dashboard (connected via Google Sheets)
- **React + Recharts**: a second, fully interactive dashboard

---

## Project structure

```
marketing-intelligence-project/
├── .env                          # DB credentials (not committed)
├── data_dictionary.md            # full schema reference — start here
│
├── generate_customers.py         # pipeline: builds the customers table
├── generate_marketing_spend.py   # pipeline: Google/Meta ad spend simulation
├── generate_ga4_events.py        # pipeline: GA4-style event/funnel simulation
├── generate_orders.py            # pipeline: e-commerce orders
├── generate_subscriptions.py     # pipeline: SaaS subscriptions
├── generate_crm_engagement.py    # pipeline: Braze-style CRM touches
├── generate_ab_test.py           # pipeline: checkout redesign experiment
│
├── ab_test_significance.py       # two-proportion z-test on the A/B results
│
├── churn_model.ipynb             # ML: churn prediction (Random Forest)
├── purchase_propensity_model.ipynb  # ML: purchase propensity (Logistic Regression)
├── ltv_prediction_model.ipynb    # ML: LTV prediction (Random Forest, log-transformed target)
├── *_model.pkl / *_model_features.pkl  # saved trained models
│
├── batch_score_customers.py      # loads models, scores all customers, writes to Postgres
│
├── export_dashboard_data.py      # exports summary CSVs for Looker Studio
├── export_all_by_year.py         # exports year-segmented JSON for the React dashboard
├── dashboard_exports/            # CSVs feeding Looker Studio
├── MarketingDashboard.jsx        # standalone React dashboard (real data embedded)
│
└── test_connection.py            # first script — verifies Postgres connectivity
```

---

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install psycopg2-binary pandas faker python-dotenv sqlalchemy scikit-learn statsmodels seaborn matplotlib jupyter ipykernel
   ```
3. Create a Postgres database (`marketing_intel_db`) and a `.env` file:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=marketing_intel_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   ```
4. Confirm the connection:
   ```bash
   python test_connection.py
   ```

---

## Running the pipeline

Run the schema SQL (see `data_dictionary.md` for the full `CREATE TABLE`
statements), then generate data **in this order** — later scripts
depend on earlier ones:

```bash
python generate_customers.py         # 20,000 customers
python generate_marketing_spend.py   # 5,840 rows
python generate_ga4_events.py        # ~183,000 events (realistic funnel + retention)
python generate_orders.py            # derived from GA4 purchase events
python generate_subscriptions.py     # 8,940 rows
python generate_crm_engagement.py    # ~180,000 rows
python generate_ab_test.py           # checkout redesign experiment
```

Every script includes a duplicate-load safety check — re-running one
against an already-populated table aborts instead of creating
duplicates.

---

## Business metrics (SQL)

All written by hand, progressing from basics through window functions
and multi-CTE composition:

- **CAC / ROAS** by channel
- **Funnel conversion** (page_view → purchase, stage-by-stage drop-off via `LAG()`)
- **Retention** (month-over-month, via a self-join)
- **LTV** (e-commerce + SaaS combined) and **LTV:CAC ratio** by channel

Headline finding: Meta outperforms Google on both cost-efficiency and
return (CAC $12.72 vs $20.43; LTV:CAC 16.3x vs 10.8x), though the
picture shifts by signup cohort — see `MarketingDashboard.jsx`'s
cohort-level breakdown.

---

## A/B testing

A simulated checkout redesign experiment with a known, deliberately
built-in conversion lift (Control 25% vs. Treatment 29%), used to
validate that the statistical method correctly detects a real effect
before trusting it on anything else. Result: p = 0.000003 —
statistically significant, correctly recovered the built-in lift.

---

## Machine learning

Three models, each built with the same discipline: careful problem
definition (avoiding data leakage), feature engineering in SQL,
imbalance handling where needed, and — critically — **validating**
feature importance with permutation importance rather than trusting
raw coefficients at face value.

| Model | Type | Key validated finding |
|---|---|---|
| Churn prediction | Random Forest classifier | Tenure is the only strong driver — risk is high through ~month 11, then drops sharply by month 17 |
| Purchase propensity | Logistic Regression | Browsing intent (`view_item` events) overwhelmingly dominates every other signal |
| LTV prediction | Random Forest regressor (log target) | R² ≈ 0.24 — useful for ranking, not precise forecasting; systematically under-predicts top-value customers |

`batch_score_customers.py` loads all three saved models and writes
live churn risk, purchase propensity, and predicted LTV scores back
into a `customer_scores` table — the pattern a real production system
would use (batch scoring on a schedule, not training on demand).

---

## Dashboards

Two, deliberately different:

- **Looker Studio** — a single, dense, BI-style report (fed by
  `dashboard_exports/*.csv` via Google Sheets), demonstrating the tool
  named in the target job description.
- **`MarketingDashboard.jsx`** — a standalone, fully interactive React
  dashboard with a genuine Year filter, built on real Postgres exports
  (via `export_all_by_year.py`), including honest empty-states where
  data genuinely doesn't exist for a given year (e.g. the A/B test only
  ran in 2026) rather than faking it.

---

## Lessons & fixes along the way

Worth keeping because they're a real part of the story:

- **ROAS came out unrealistically low (~0.1x)** on the first pass —
  root-caused to `marketing_spend` and `orders` being generated
  independently with mismatched scale. Fixed by rebalancing both
  generators, not by fudging the output.
- **Retention came out unrealistically low (~15-20%)** — root-caused
  to GA4 session dates being scattered uniformly at random per
  customer, with no month-to-month "stickiness." Fixed by rewriting
  the event generator to use a proper month-by-month activity
  simulation with decay and reactivation probability.
- **A churn-model feature (`active_days`) looked backwards** (more
  activity → *more* predicted churn) — investigated with feature
  engineering, Random Forest, partial dependence plots, and finally
  permutation importance, which revealed the raw feature was a
  disguised tenure proxy, not a real signal.
