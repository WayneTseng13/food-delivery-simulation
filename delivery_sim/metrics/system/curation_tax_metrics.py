# delivery_sim/metrics/system/curation_tax_metrics.py
"""
Curation tax metrics (cost channel for edge-manufacture).

Tax is the delivery-leg cost of steering a curated order to R* (the cheapest
bundleable restaurant) instead of R_nearest (the cheapest overall). It is
defined ONLY for the edge_manufacture branch, which is the only branch that
chooses R* over its own R_nearest default.

Two per-order fields, stamped in order_arrival_service:

    curation_computed_tax : the tax the policy OFFERED.
        float  for every edge_manufacture recommendation (0.0 iff R*==R_nearest,
               i.e. self-cancellation -- a MEANINGFUL zero).
        None   otherwise (U orders, single_immediate, single_queued): tax is
               undefined, no choice against R_nearest was made.

    curation_realized_tax : the tax the system actually PAID.
        float  only when edge_manufacture fired AND the customer complied
               (originated at R*, so R_nearest is the valid counterfactual).
        None   otherwise -- including edge_manufacture-fired-but-rejected: a
               non-complier's origin is a random draw, so R_nearest is not its
               baseline and tax does not apply.

CRITICAL: filter on 'is not None', never coerce None to 0.0. 0.0 is a real
edge_manufacture measurement (self-cancellation); None means tax is undefined.
Conflating them would dilute the means with structural non-values.

Interpretation:
    mean_computed_tax  : average diversion offered, over fired edge_manufacture orders.
    mean_realized_tax  : average diversion paid, over complying fired orders.
    diverted_offer_rate: fraction of fired orders with computed_tax > eps
                         (offered a real diversion vs self-cancelled onto R_nearest).
                         This is the empirical handle on self-cancellation: it
                         should fall toward saturation as R_nearest increasingly
                         already holds a compatible order.
    realized_offer_rate: fraction of fired orders that were both complied-with
                         and diverting -- the share that actually cost travel.

    mean_realized / mean_computed ~ (compliance x diverted fraction): the
    compliance throttle, visible as the gap between offered and paid.
"""

_EPS = 1e-9


def calculate_all_curation_tax_metrics(analysis_data):
    """
    Calculate curation tax metrics for a replication.

    Denominator is the set of edge_manufacture recommendations (orders whose
    curation_computed_tax is not None). U / single_immediate / single_queued
    orders are excluded automatically by that filter.

    Args:
        analysis_data: AnalysisData object with cohort_orders.

    Returns:
        dict of scalar metrics. All zeros when no edge_manufacture order exists
        (e.g. Policy U runs), so callers need not branch on policy.
    """
    cohort_orders = analysis_data.cohort_orders

    # Fired edge_manufacture recommendations: tax was defined (offered).
    fired = [o for o in cohort_orders if o.curation_computed_tax is not None]
    n_fired = len(fired)

    if n_fired == 0:
        return {
            'mean_computed_tax':   0.0,
            'mean_realized_tax':   0.0,
            'diverted_offer_rate': 0.0,
            'realized_offer_rate': 0.0,
            'n_edge_manufacture':  0,
        }

    computed_values = [o.curation_computed_tax for o in fired]
    mean_computed_tax = sum(computed_values) / n_fired

    # Paid: fired AND complied (realized_tax is not None).
    paid = [o.curation_realized_tax for o in fired if o.curation_realized_tax is not None]
    # mean_realized over the complying-fired subset (its own denominator).
    mean_realized_tax = sum(paid) / len(paid) if paid else 0.0

    diverted_offers = sum(1 for v in computed_values if v > _EPS)
    diverted_offer_rate = diverted_offers / n_fired

    realized_diverting = sum(
        1 for o in fired
        if o.curation_realized_tax is not None and o.curation_realized_tax > _EPS
    )
    realized_offer_rate = realized_diverting / n_fired

    return {
        'mean_computed_tax':   mean_computed_tax,
        'mean_realized_tax':   mean_realized_tax,
        'diverted_offer_rate': diverted_offer_rate,
        'realized_offer_rate': realized_offer_rate,
        'n_edge_manufacture':  n_fired,
    }