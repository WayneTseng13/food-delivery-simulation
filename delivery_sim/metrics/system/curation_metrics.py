# delivery_sim/metrics/system/curation_metrics.py
"""
Curation operating envelope metrics.

Calculates the R-D curation fallback rate from order curation_result
attributes. Because curation_result is stamped on each order at arrival
time, warmup filtering is inherited automatically from cohort_orders
(orders with arrival_time >= warmup_period).

Fallback rate: fraction of curation attempts where no idle drivers existed,
forcing the platform to abandon proximity selection and fall back to uniform
random restaurant selection.

Note on Policy U runs:
    When UniformPolicy is active, every order has curation_result = None.
    No curation was attempted, so fallback rate is returned as 0.0.
    The study script can distinguish this case from context (policy condition).
"""


def calculate_curation_fallback_rate(analysis_data):
    """
    Calculate the R-D curation fallback rate for a replication.

    Uses cohort_orders (all post-warmup arrivals) rather than
    cohort_completed_orders because the curation result is determined
    at arrival time and is independent of whether the order was
    eventually completed.

    Args:
        analysis_data: AnalysisData object with cohort_orders population

    Returns:
        dict: Contains fallback_rate, attempted_count, and fallback_count
    """
    cohort_orders = analysis_data.cohort_orders

    attempted = [o for o in cohort_orders if o.curation_result is not None]

    if not attempted:
        return {
            'curation_fallback_rate': 0.0,
            'curation_attempted_count': 0,
            'curation_fallback_count': 0
        }

    fallback_count = sum(1 for o in attempted if o.curation_result == 'fallback')

    return {
        'curation_fallback_rate': fallback_count / len(attempted),
        'curation_attempted_count': len(attempted),
        'curation_fallback_count': fallback_count
    }


def calculate_all_curation_metrics(analysis_data):
    """
    Calculate all curation operating envelope metrics for a replication.

    Entry point called by the analysis pipeline (one_level pattern).

    Args:
        analysis_data: AnalysisData object

    Returns:
        dict: Scalar metrics keyed by metric name
    """
    fallback_result = calculate_curation_fallback_rate(analysis_data)

    return {
        'curation_fallback_rate': fallback_result['curation_fallback_rate']
    }