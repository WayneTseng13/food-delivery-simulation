# delivery_sim/metrics/system/curation_metrics.py
"""
Curation operating envelope metrics.

Metrics are derived from order.curation_result, which is stamped at arrival
time. Warmup filtering is inherited automatically from cohort_orders
(orders with arrival_time >= warmup_period).

Policy label mapping (mechanism iii):
    Policy U  — curation_result is None for every order. No curation attempted.
    Policy X' — curation_result is 'edge_manufacture', 'single_immediate',
                or 'single_queued'.

    (The 'edge_manufacture' label replaces the mechanism-(ii) 'pair_queued'
    label. Under (ii) the branch predicted a pair's route; under (iii) it
    manufactures a compatibility edge and lets the dispatcher choose the
    partner later. The state that triggers the branch is the same -- no idle
    driver, a C-C-compatible pending anchor exists -- but the action and its
    semantics differ, so the label was renamed to prevent conflating (ii)
    pair_queued rates with (iii) edge_manufacture rates.)

    The mechanism-(ii) Policy X labels 'curated' / 'fallback' are no longer
    produced -- Policy X (R-D-only proximity) was removed in the (iii) curation
    redesign. curation_fallback_rate is retained (computed, always 0.0 for the
    surviving policies) only so downstream code that still reads the key does
    not KeyError during the transition; drop it once no caller references it.

All rate metrics are computed from the same pass over cohort_orders. Rates for
labels not present in a given run naturally come out as 0.0, so callers do not
need to branch on which policy was active.

    Policy U  -> all rates = 0.0
    Policy X' -> branch rates meaningful; fallback_rate = 0.0
"""


def calculate_all_curation_metrics(analysis_data):
    """
    Calculate curation operating envelope metrics for a replication.

    Entry point called by the analysis pipeline (one_level pattern).

    Args:
        analysis_data: AnalysisData object with cohort_orders population.

    Returns:
        dict: Scalar metrics keyed by metric name. All values are floats
              in [0, 1] representing fractions of post-warmup arrivals for
              which curation was attempted.
    """
    cohort_orders = analysis_data.cohort_orders

    # Orders where any curation was attempted (excludes Policy U orders, whose
    # curation_result is None).
    attempted = [o for o in cohort_orders if o.curation_result is not None]
    n = len(attempted)

    if n == 0:
        return {
            'curation_edge_manufacture_rate': 0.0,
            'curation_single_immediate_rate': 0.0,
            'curation_single_queued_rate':    0.0,
            'curation_fallback_rate':         0.0,
        }

    edge_manufacture_count = sum(1 for o in attempted if o.curation_result == 'edge_manufacture')
    single_immediate_count = sum(1 for o in attempted if o.curation_result == 'single_immediate')
    single_queued_count    = sum(1 for o in attempted if o.curation_result == 'single_queued')
    fallback_count         = sum(1 for o in attempted if o.curation_result == 'fallback')

    return {
        'curation_edge_manufacture_rate': edge_manufacture_count / n,
        'curation_single_immediate_rate': single_immediate_count / n,
        'curation_single_queued_rate':    single_queued_count    / n,
        'curation_fallback_rate':         fallback_count         / n,
    }