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

The featured restaurant id. If it is None (U / operational mode), featured_origin_rate is not
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
    Calculate featuring decision + business-outcome metrics for a replication.
 
    Entry point called by the analysis pipeline (one_level pattern).
 
    Arrival-side (the PROMISE -- demand routed to R_F):
        featured_recommendation_rate  offered;   p-independent
        featured_origin_rate          captured;  p-dependent
 
    Completion-side (the DELIVERY -- demand actually served from R_F):
        featured_throughput           delivered R_F orders per unit time
        featured_completion_rate      delivered R_F orders / arrived R_F orders
        featured_delivered_share      delivered R_F orders / all delivered orders
 
    Why the completion side matters: featured_origin_rate counts arrivals, so an
    R_F order that sits in backlog forever and never delivers still counts as
    'captured'. Under saturation that overstates realized business value. The
    completion-side metrics are what survive the cliff; their divergence from
    origin_rate as tau rises LOCATES the cliff from the business side.
 
    Args:
        analysis_data: AnalysisData with cohort_orders, cohort_completed_orders,
                       featured_restaurant_id, analysis_window_length.
 
    Returns:
        dict (all keys always present; 0.0 when undefined, e.g. U / operational).
    """
    cohort_orders = analysis_data.cohort_orders
    curated = [o for o in cohort_orders if o.curation_result is not None]
    n_curated = len(curated)
 
    featured_id = _featured_id(analysis_data)
 
    # Empty / Policy U: every featuring metric undefined -> 0.0.
    if n_curated == 0:
        return {
            'featured_recommendation_rate': 0.0,
            'featured_origin_rate':         0.0,
            'featured_throughput':          0.0,
            'featured_completion_rate':     0.0,
            'featured_delivered_share':     0.0,
            'featured_recommendations':     0,
            'featured_origins':             0,
            'featured_delivered':           0,
            'total_curated':                0,
        }
 
    # ----- arrival-side (existing) -----
    featured_recs = sum(
        1 for o in curated
        if o.curation_result is not None and o.curation_result.startswith('featured_')
    )
 
    if featured_id is None:
        featured_origins = 0
    else:
        featured_origins = sum(1 for o in cohort_orders
                           if o.origin_restaurant_id == featured_id)
 
    # ----- completion-side (new) -----
    # cohort_completed_orders: delivered orders that ARRIVED in the analysis
    # window (same cohort filter used by system completion/throughput).
    completed = analysis_data.cohort_completed_orders
    n_completed = len(completed)
 
    if featured_id is None:
        featured_delivered = 0
    else:
        featured_delivered = sum(
            1 for o in completed if o.origin_restaurant_id == featured_id
        )
 
    # Throughput: delivered R_F orders per unit time. Same window as
    # system_throughput, so directly comparable (featured_throughput <=
    # system_throughput always). None window -> 0.0 (matches system_throughput).
    window = getattr(analysis_data, 'analysis_window_length', None)
    if window is not None and window > 0:
        featured_throughput = featured_delivered / window
    else:
        featured_throughput = 0.0
 
    # Completion rate SPECIFIC to R_F: of orders that originated at R_F, what
    # fraction delivered. Isolates whether R_F itself is starved, separate from
    # system-wide completion. If system completion is 0.85 but this is 0.60 at
    # high tau, featuring is cannibalizing its own sponsor.
    if featured_origins > 0:
        featured_completion_rate = featured_delivered / featured_origins
    else:
        featured_completion_rate = 0.0   # no R_F origins -> undefined -> 0.0
 
    # R_F's share of all delivered orders (business share of realized throughput).
    if n_completed > 0:
        featured_delivered_share = featured_delivered / n_completed
    else:
        featured_delivered_share = 0.0
 
    return {
        # arrival-side (promise)
        'featured_recommendation_rate': featured_recs    / n_curated,
        'featured_origin_rate':         featured_origins / n_curated,
        # completion-side (delivery)
        'featured_throughput':          featured_throughput,
        'featured_completion_rate':     featured_completion_rate,
        'featured_delivered_share':     featured_delivered_share,
        # raw counts (diagnostics)
        'featured_recommendations':     featured_recs,
        'featured_origins':             featured_origins,
        'featured_delivered':           featured_delivered,
        'total_curated':                n_curated,
    }