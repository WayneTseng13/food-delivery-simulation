# delivery_sim/utils/route_evaluator.py
"""
Shared route evaluation utility for paired deliveries.

Single source of truth for all 6-sequence enumeration logic. Pairing,
assignment, and curation all call these functions instead of inlining
their own distance/sequence calculations. Alignment-by-construction
is achieved because all three stages share the same scoring functions
on the same information.

Module design:
- Domain-light: accepts raw location lists, not Order/Driver objects.
- Dict returns: readable and field-order-resilient.
- VALID_SEQUENCES exposed as module constant for inspection.
"""

from delivery_sim.utils.location_utils import calculate_distance


# Index mapping: [r_1, r_2, c_1, c_2]
# Each tuple is a valid pick-up-before-delivery permutation for both orders.
VALID_SEQUENCES = [
    (0, 1, 2, 3),  # R_1, R_2, C_1, C_2  — batched
    (0, 1, 3, 2),  # R_1, R_2, C_2, C_1  — batched
    (1, 0, 2, 3),  # R_2, R_1, C_1, C_2  — batched
    (1, 0, 3, 2),  # R_2, R_1, C_2, C_1  — batched
    (0, 2, 1, 3),  # R_1, C_1, R_2, C_2  — interleaved
    (1, 3, 0, 2),  # R_2, C_2, R_1, C_1  — interleaved
]


def _deduplicate_consecutive(stops):
    """
    Collapse consecutive duplicate locations into one stop.

    Handles same-restaurant pairs where the raw 4-stop sequence contains
    [R, R, C_1, C_2]. The duplicate R is removed so delivery_service
    does not attempt a second restaurant visit where both orders are
    already PICKED_UP.

    The 'indices' field in the returned route dict is unchanged (4 elements)
    for diagnostic purposes. Only 'stops' is deduplicated.
    """
    if not stops:
        return stops
    result = [stops[0]]
    for stop in stops[1:]:
        if stop != result[-1]:
            result.append(stop)
    return result


def enumerate_routes(r_1, c_1, r_2, c_2):
    """
    Enumerate all 6 valid delivery routes for a 2-order pair.

    Args:
        r_1: Restaurant location for order 1 (list [x, y])
        c_1: Customer location for order 1 (list [x, y])
        r_2: Restaurant location for order 2 (list [x, y])
        c_2: Customer location for order 2 (list [x, y])

    Returns:
        list of dicts, one per valid sequence:
            'indices'   : tuple of 4 ints (index into [r_1, r_2, c_1, c_2])
            'stops'     : list of locations in executable visit order
                          (consecutive duplicates removed for same-restaurant pairs)
            'route_cost': total travel distance along the stop sequence (float)
    """
    stops_by_index = [r_1, r_2, c_1, c_2]
    routes = []
    for indices in VALID_SEQUENCES:
        raw_stops = [stops_by_index[i] for i in indices]
        route_cost = sum(
            calculate_distance(raw_stops[i], raw_stops[i + 1])
            for i in range(len(raw_stops) - 1)
        )
        executable_stops = _deduplicate_consecutive(raw_stops)
        routes.append({
            'indices': indices,
            'stops': executable_stops,
            'route_cost': route_cost,
        })
    return routes


def evaluate_partial(r_1, c_1, r_2, c_2):
    """
    Select the best route by minimum route_cost, without driver position.

    Used by:
    - PairingService: to pick pair identity and store partial-info hint.
    - StateAdaptiveCurationPolicy (pair_queued branch): to score (R_N, anchor)
      pairs when no idle drivers are present.

    Args:
        r_1, c_1, r_2, c_2: Location lists as in enumerate_routes.

    Returns:
        Single route dict (best by route_cost):
            'indices', 'stops', 'route_cost'
    """
    routes = enumerate_routes(r_1, c_1, r_2, c_2)
    return min(routes, key=lambda r: r['route_cost'])


def evaluate_complete(r_1, c_1, r_2, c_2, drivers):
    """
    Select the best (route, driver) pair by minimum total_cost = R-D + route_cost.

    The first stop of each route's executable stop list is used as the
    pickup target for computing R-D distance. This means driver position
    influences both which sequence is chosen and which driver wins.

    Used by:
    - PriorityScorer._calculate_total_distance (pair branch): to score a
      specific driver against the pair.
    - AssignmentService._create_assignment: to finalize the binding sequence
      after the winning driver is known.
    - StateAdaptiveCurationPolicy (single_immediate branch): to predict which
      restaurant minimizes R-D + R-C.

    Args:
        r_1, c_1, r_2, c_2: Location lists as in enumerate_routes.
        drivers: List of Driver objects with a .location attribute.
                 Pass a single-element list when evaluating one driver.

    Returns:
        dict or None (None only if drivers is empty):
            'indices'    : tuple — winning sequence index pattern
            'stops'      : list  — executable stop locations
            'driver'     : Driver object that won
            'route_cost' : float — sum of inter-stop distances
            'r_d'        : float — distance from winning driver to first stop
            'total_cost' : float — r_d + route_cost
    """
    if not drivers:
        return None

    routes = enumerate_routes(r_1, c_1, r_2, c_2)
    best = None

    for route in routes:
        first_pickup = route['stops'][0]
        for driver in drivers:
            r_d = calculate_distance(driver.location, first_pickup)
            total = r_d + route['route_cost']
            if best is None or total < best['total_cost']:
                best = {
                    'indices': route['indices'],
                    'stops': route['stops'],
                    'driver': driver,
                    'route_cost': route['route_cost'],
                    'r_d': r_d,
                    'total_cost': total,
                }

    return best