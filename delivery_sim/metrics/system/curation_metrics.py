# delivery_sim/metrics/system/curation_metrics.py
"""
Curation metric for the featuring chapter.

One metric describes the realized business outcome of curation:

    featured_origin_rate
        Fraction of cohort arrivals whose order ACTUALLY ORIGINATED at the
        featured restaurant R_F (origin_restaurant_id == featured id). This is
        realized business capture -- what a sponsor pays for.

        Its VALUE lies in the contrast between two runs at matched customer
        proximity-sensitivity:
          - Policy U (no curation): ORGANIC capture -- how much of R_F's demand
            arrives with no boost at all, purely because R_F sits where it sits
            and customers weigh distance. The baseline.
          - Policy F (always feature R_F): BOOSTED capture.
        The gap origin_rate(F) - origin_rate(U) at matched conditions is the
        featuring LIFT -- the business the boost actually moved, over and above
        what proximity would have delivered on its own. Under the customer choice
        model that gap narrows as customers grow more proximity-sensitive (the
        boost must overcome a stiffer distance penalty), so featuring self-limits.

The metric only COUNTS realized origins; it is agnostic to HOW the customer's
selection resolved (recommendation-and-compliance, or unaided choice). That keeps
it valid regardless of the downstream selection mechanism.

WHAT WAS REMOVED (completing the migration off blended/tau curation):

    featured_recommendation_rate
        Retired. It measured how often R_F was recommended, which under the old
        blend(tau) varied with tau and was the frontier x-axis. With tau gone,
        'featured' mode recommends R_F on EVERY arrival (rate == 1.0) and
        'operational'/U never do (rate == 0.0), so the metric is a constant that
        merely re-encodes the policy label. A "did the featured slot fire on
        every arrival" check belongs in a test, not a per-cell CI metric.

    featured_throughput / featured_completion_rate / featured_delivered_share
        Removed. These completion-side metrics were advertised in the docstring
        and registered in metric_configurations, but the function body never
        computed them, and the featured_frontier study dropped them from its
        matrix by hand -- dead config. The captured-vs-delivered distinction they
        were meant to capture (an R_F order counted 'captured' at arrival can
        still die in backlog under saturation, overstating realized value) is
        relevant to the load-stability findings, but re-adding it is a deliberate
        build (delivered-R_F counts from cohort_completed_orders plus window
        normalization), not part of this streamline. Left out until wanted.

Branch mix (immediate/queued) is NOT here: it lives in entity_derived_metrics
(arrival_immediate_rate / arrival_queued_rate), a system-state property read at
arrival for ALL policies, not a curation property.

The featuring penalty (order.featuring_penalty) is NOT here either: it is stamped
per featured arrival by CurationPolicy as the operational externality of
featuring (c(R_F) - c(R_op)), and its whole distribution -- not a per-cell scalar
-- is summarised offline from the raw order dump.

Denominator note: featured_origin_rate is denominated on ALL cohort orders
(post-warmup arrivals). Under Policy U / operational mode with no featured id,
origin capture is not a meaningful target and the metric is reported as 0.0.
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
    Realized business capture at the featured restaurant, for a replication.

    Entry point called by the analysis pipeline (one_level pattern).

    Returns featured_origin_rate = (cohort orders originating at R_F) / (all
    cohort orders), plus its raw numerator and denominator. Meaningful only when a
    featured id is present; 0.0 otherwise (U / operational with no featured id).

    Args:
        analysis_data: AnalysisData with cohort_orders and featured_restaurant_id.

    Returns:
        dict (all keys always present; 0.0 / 0 when undefined).
    """
    cohort_orders = analysis_data.cohort_orders
    n_cohort = len(cohort_orders)
    featured_id = _featured_id(analysis_data)

    # Guard: empty cohort or no observation target -> metric undefined.
    # Origin is a fact about where every order landed, so we denominate over ALL
    # cohort orders (U's unaided picks included), never over curated orders only.
    if n_cohort == 0 or featured_id is None:
        return {
            'featured_origin_rate': 0.0,
            'featured_origins':     0,
            'total_cohort':         n_cohort,
        }

    featured_origins = sum(1 for o in cohort_orders
                           if o.origin_restaurant_id == featured_id)

    return {
        'featured_origin_rate': featured_origins / n_cohort,
        'featured_origins':     featured_origins,
        'total_cohort':         n_cohort,
    }