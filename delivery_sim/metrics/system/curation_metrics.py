# delivery_sim/metrics/system/curation_metrics.py
"""
Curation operating envelope metrics.

Metrics are derived from order.curation_result, which is stamped at arrival
time. Warmup filtering is inherited automatically from cohort_orders
(orders with arrival_time >= warmup_period).

Policy label mapping:
    Policy U  — curation_result is None for every order. No curation attempted.
    Policy X  — curation_result is 'curated' or 'fallback'.
    Policy X' — curation_result is 'pair_queued', 'single_immediate',
                or 'single_queued'.

All four rate metrics are computed from the same pass over cohort_orders.
Rates for labels not present in a given run naturally come out as 0.0,
so callers do not need to branch on which policy was active.

    Policy U  → all four rates = 0.0
    Policy X  → fallback_rate meaningful; branch rates = 0.0
    Policy X' → branch rates meaningful; fallback_rate = 0.0
"""


def calculate_all_curation_metrics(analysis_data):
    """
    Calculate curation operating envelope metrics for a replication.

    Entry point called by the analysis pipeline (one_level pattern).

    Args:
        analysis_data: AnalysisData object with cohort_orders population.

    Returns:
        dict: Scalar metrics keyed by metric name. All values are floats
              in [0, 1] representing fractions of post-warmup arrivals.
    """
    cohort_orders = analysis_data.cohort_orders

    # Orders where any curation was attempted (excludes Policy U orders).
    attempted = [o for o in cohort_orders if o.curation_result is not None]
    n = len(attempted)

    if n == 0:
        return {
            'curation_fallback_rate':        0.0,
            'curation_pair_queued_rate':      0.0,
            'curation_single_immediate_rate': 0.0,
            'curation_single_queued_rate':    0.0,
        }

    fallback_count        = sum(1 for o in attempted if o.curation_result == 'fallback')
    pair_queued_count     = sum(1 for o in attempted if o.curation_result == 'pair_queued')
    single_immediate_count = sum(1 for o in attempted if o.curation_result == 'single_immediate')
    single_queued_count   = sum(1 for o in attempted if o.curation_result == 'single_queued')

    return {
        'curation_fallback_rate':        fallback_count        / n,
        'curation_pair_queued_rate':      pair_queued_count     / n,
        'curation_single_immediate_rate': single_immediate_count / n,
        'curation_single_queued_rate':    single_queued_count   / n,
    }