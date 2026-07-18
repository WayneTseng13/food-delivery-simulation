# delivery_sim/utils/bundleability.py
"""
Bundleability check for two orders.

Single source of truth for the pairing eligibility geometry: two orders may be
bundled into one delivery only if their restaurants are within delta_r of each
other AND their customers are within delta_c of each other.

This was previously a private method inside PairingService. Under assignment-time
bundling (mechanism iii) PairingService no longer exists, and two independent
consumers need this same check:

  - AssignmentService: enumerates bundle options at dispatch, filtering candidate
    order pairs by bundleability before scoring.
  - Curation policy: pre-checks C-C compatibility at arrival to decide whether a
    consolidation recommendation can manufacture a bundling opportunity.

Keeping the check in one stateless function guarantees both call sites apply
identical thresholds and identical distance functions. Inlining it in either
place is how delta_r or delta_c silently diverge between the two code paths.

Domain-light by design: takes Order objects (their .restaurant_location and
.customer_location) and the two thresholds as plain arguments. No config object,
no services, no repositories, no env.
"""

from delivery_sim.utils.location_utils import calculate_distance


def is_bundleable(order_a, order_b, restaurant_threshold, customer_threshold):
    """
    Determine whether two orders satisfy the proximity constraints for bundling.

    Both constraints must hold:
      - restaurant-to-restaurant distance <= restaurant_threshold (delta_r)
      - customer-to-customer distance     <= customer_threshold   (delta_c)

    The restaurant constraint is checked first and short-circuits, since a
    restaurant miss is the more common rejection and avoids the second distance
    computation.

    Args:
        order_a: An Order with restaurant_location and customer_location
        order_b: An Order with restaurant_location and customer_location
        restaurant_threshold: Maximum allowed R-R distance (delta_r), in km
        customer_threshold: Maximum allowed C-C distance (delta_c), in km

    Returns:
        bool: True if the two orders may be bundled, False otherwise
    """
    restaurant_distance = calculate_distance(
        order_a.restaurant_location, order_b.restaurant_location)
    if restaurant_distance > restaurant_threshold:
        return False

    customer_distance = calculate_distance(
        order_a.customer_location, order_b.customer_location)
    if customer_distance > customer_threshold:
        return False

    return True