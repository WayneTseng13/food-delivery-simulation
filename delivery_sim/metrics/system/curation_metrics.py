# delivery_sim/metrics/system/curation_metrics.py
"""
Curation metrics for the featuring / blended-curation chapter.

These describe the FEATURING DECISION and its realized business outcome. They
are computed only for featuring runs ('blended' / 'featured' modes); Policy U and
'operational' mode produce no featuring, so their curation metrics are trivially
0.0 / undefined (see per-metric notes).

Two metrics, deliberately minimal:

    featured_recommendation_rate
        Fraction of arrivals on which the featured restaurant R_F was RECOMMENDED
        (curation_result starts with 'featured_'). A property of the DECISION
        RULE only -- it is independent of customer compliance p, because
        compliance is applied AFTER the recommendation is chosen. This is the
        honest "how aggressively does this tau feature" reading, and the natural
        x-axis of the operational/business frontier.

    featured_origin_rate
        Fraction of arrivals whose order ACTUALLY ORIGINATED at R_F
        (origin_restaurant_id == featured id). This is realized business capture
        -- what a sponsor pays for -- and it DOES depend on p. It aggregates
        three channels:
          1. featured and complied      (featuring working as intended),
          2. R_F was the operational optimum anyway and got recommended,
          3. R_F picked up as a uniform-random landing after a rejection of some
             other recommendation.
        Because of channels 2 and 3 it does NOT go to zero even at tau=0.
        The GAP between featured_recommendation_rate (offered) and
        featured_origin_rate (captured) across tau is itself a finding.

WHAT IS NOT HERE (and why):
  - Branch mix (immediate/queued) moved to entity_derived_metrics
    (arrival_immediate_rate / arrival_queued_rate). It is a system-state property
    read at arrival for ALL policies, not a curation property; the curation
    policy merely happens to read the same state.
  - Penalty summaries / tau calibration are NOT per-cell scalars. The penalty
    distribution is read offline from the raw order dump (order.featuring_penalty)
    of a tau=0 'blended' run, where fire_rate(tau') = P(penalty <= tau') is the
    empirical CDF. Placing tau at penalty quantiles is a one-time exploratory
    act, not a pipeline metric.

Denominator note: in a featuring run every arrival is curated (a recommendation
is always produced), so 'curated orders' == 'cohort orders'. Both metrics are
denominated on ALL cohort orders. Orders with curation_result is None (Policy U)
are excluded from featured_recommendation_rate's numerator by construction and
contribute 0 to featured_origin_rate unless U is run with a featured id set
(which it is not).

The featured restaurant id is read from config.featured_restaurant_id via
analysis_data. If it is None (U / operational mode), featured_origin_rate is not
meaningful and is reported as 0.0.
"""


def _featured_id(analysis_data):
    """
    Featured restaurant id for this run, or None (Policy U / operational mode).

    Read from AnalysisData.featured_restaurant_id, populated from run_context at
    the simulation boundary. The metrics layer reads this named field -- never a
    config object -- so it stays decoupled from config's schema. getattr with a
    None default keeps it robust to legacy AnalysisData built without the field.
    """

    return getattr(analysis_data, 'featured_restaurant_id', None)


def calculate_all_curation_metrics(analysis_data):
    """
    Calculate featuring decision + capture metrics for a replication.

    Entry point called by the analysis pipeline (one_level pattern).

    Args:
        analysis_data: AnalysisData with cohort_orders (and, ideally, config
                       carrying featured_restaurant_id).

    Returns:
        dict:
            featured_recommendation_rate  in [0, 1]
            featured_origin_rate          in [0, 1]
            featured_recommendations      raw count (diagnostic)
            featured_origins              raw count (diagnostic)
            total_curated                 raw count (diagnostic)
    """
    cohort_orders = analysis_data.cohort_orders

    # Curated orders = a recommendation was produced (excludes Policy U, whose
    # curation_result is None). In a featuring run this equals all cohort orders.
    curated = [o for o in cohort_orders if o.curation_result is not None]
    n_curated = len(curated)

    featured_id = _featured_id(analysis_data)

    if n_curated == 0:
        # Policy U (or empty cohort): featuring metrics undefined -> 0.0.
        return {
            'featured_recommendation_rate': 0.0,
            'featured_origin_rate':         0.0,
            'featured_recommendations':     0,
            'featured_origins':             0,
            'total_curated':                0,
        }

    # (1) Recommendation rate -- decision only, p-independent.
    featured_recs = sum(
        1 for o in curated
        if o.curation_result is not None and o.curation_result.startswith('featured_')
    )

    # (2) Origin rate -- realized capture, p-dependent. Denominated on all cohort
    # orders (share of total demand), which for a featuring run equals n_curated.
    if featured_id is None:
        featured_origins = 0
    else:
        featured_origins = sum(
            1 for o in curated if o.origin_restaurant_id == featured_id
        )

    return {
        'featured_recommendation_rate': featured_recs    / n_curated,
        'featured_origin_rate':         featured_origins / n_curated,
        'featured_recommendations':     featured_recs,
        'featured_origins':             featured_origins,
        'total_curated':                n_curated,
    }