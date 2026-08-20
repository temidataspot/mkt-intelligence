# ab_test_significance.py
# Purpose: run a two-proportion z-test to determine whether the
# observed difference in checkout conversion rate between variant A
# and B is statistically significant, or could be due to random chance.

import os
import psycopg2
from dotenv import load_dotenv
from statsmodels.stats.proportion import proportions_ztest

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def fetch_variant_stats():
    """Pull total_assigned and total_converted per variant from Postgres."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT variant, COUNT(*) AS total_assigned, SUM(converted::int) AS total_converted
        FROM ab_test_assignments
        GROUP BY variant
        ORDER BY variant
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def main():
    stats = fetch_variant_stats()
    variant_data = {row[0]: {"assigned": row[1], "converted": row[2]} for row in stats}

    a = variant_data["A"]
    b = variant_data["B"]

    print(f"Variant A: {a['converted']} / {a['assigned']} converted ({100*a['converted']/a['assigned']:.2f}%)")
    print(f"Variant B: {b['converted']} / {b['assigned']} converted ({100*b['converted']/b['assigned']:.2f}%)")

    # proportions_ztest compares two conversion counts against two sample sizes.
    # It returns a z-statistic (how many standard deviations apart the two
    # rates are) and a p-value (the probability of seeing a difference this
    # large, or larger, purely by random chance if there were truly no effect).
    counts = [a["converted"], b["converted"]]
    nobs = [a["assigned"], b["assigned"]]
    z_stat, p_value = proportions_ztest(counts, nobs)

    print(f"\nZ-statistic: {z_stat:.4f}")
    print(f"P-value: {p_value:.6f}")

    ALPHA = 0.05  # standard significance threshold
    if p_value < ALPHA:
        print(f"Statistically significant (p < {ALPHA}). We reject the null hypothesis —")
        print("   the conversion rate difference is unlikely to be due to random chance.")
    else:
        print(f"Not statistically significant (p >= {ALPHA}). We cannot conclude")
        print("   there's a real difference — the observed gap could be random noise.")

if __name__ == "__main__":
    main()


# Variant A: 840 / 3484 converted (24.11%)
# Variant B: 997 / 3432 converted (29.05%)

# Z-statistic: -4.6507
# P-value: 0.000003
# Statistically significant (p < 0.05). We reject the null hypothesis - 
# the conversion rate difference is unlikely to be due to random chance.