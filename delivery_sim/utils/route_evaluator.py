# delivery_sim/utils/route_evaluator.py
"""
Shared route evaluation utility for paired deliveries.

Single source of truth for 6-sequence enumeration. Under assignment-time
bundling (mechanism iii), routes are only ever evaluated with the driver known,
at dispatch. The partner and sequence are chosen together against full
information, so there is no arrival-time / driver-absent route evaluation.

The previous `evaluate_partial` (best route by route_cost, no driver) has been
removed: its two consumers were PairingService (deleted under iii) and the
old state-adaptive curation policy's pair_queued branch, which predicted the
pair's route at arrival. Under (iii) curation no longer predicts the pair route
-- it manufactures a compatibility edge and lets the dispatcher choose the
partner and sequence later -- so it needs only distance checks (bundleability),
not route evaluation. Nothing calls `evaluate_partial` anymore.

Module design:
- Domain-light: accepts raw location lists, not Order/Driver objects.
- Dict returns: readable and field-order-resilient.
- VALID_SEQUENCES exposed as a module constant for inspection.
"""

from delivery_sim.utils.location_utils import calculate_distance


# Index mapping: [r_1, r_2, c_1, c_2]
# Each tuple is a valid pick-up-before-delivery permutation for both orders.
VALID_SEQUENCES = [
    (0, 1, 2, 3),  # R_1, R_2, C_1, C_2  -- batched
    (0, 1, 3, 2),  # R_1, R_2, C_2, C_1  -- batched
    (1, 0, 2, 3),  # R_2, R_1, C_1, C_2  -- batched
    (1, 0, 3, 2),  # R_2, R_1, C_2, C_1  -- batched
    (0, 2, 1, 3),  # R_1, C_1, R_2, C_2  -- interleaved
    (1, 3, 0, 2),  # R_2, C_2, R_1, C_1  -- interleaved
]


def _deduplicate_consecutive(stops):
    """
    Collapse consecutive duplicate locations into one stop.

    Handles same-restaurant pairs where the raw 4-stop sequence contains
    [R, R, C_1, C_2]. The duplicate R is removed so delivery_service does not
    attempt a second restaurant visit where both orders are already PICKED_UP.

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


def evaluate_complete(r_1, c_1, r_2, c_2, drivers):
    """
    Select the best (route, driver) pair by minimum total_cost = R-D + route_cost.

    The first stop of each route's executable stop list is used as the pickup
    target for computing R-D distance, so driver position influences both which
    sequence is chosen and which driver wins.

    Under mechanism (iii) this is the only route evaluation in the system, and it
    is always called with the driver known:
      - AssignmentService._score_driver_option (bundle branch): scores a bundle
        option against the freeing driver, passing [driver].
      - The returned 'stops' and 'route_cost' are carried onto the DeliveryUnit
        for the winning option, so the sequence is computed once.

    Args:
        r_1, c_1, r_2, c_2: Location lists as in enumerate_routes.
        drivers: List of Driver objects (typically one under iii).

    Returns:
        Best route dict augmented with driver and cost breakdown:
            'indices', 'stops', 'route_cost', 'driver', 'r_d', 'total_cost'
        or None if drivers is empty.
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