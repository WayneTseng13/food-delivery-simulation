# delivery_sim/utils/curation_policy.py
"""
Curation policy for assignment-time bundling (mechanism iii).

Curation writes one thing at order arrival: the restaurant R recommended to the
customer. If the customer complies, the order originates at R. Curation cannot
mutate anything else -- not the driver, not the pending pool, not the dispatch
decision. Under (iii) the dispatcher chooses the partner and route later, at the
moment of maximal information, so curation's job is to pre-shape only the
INVARIANT geometry the dispatcher will then exploit:

  - the order's delivery leg (R-C), fixed the instant the customer complies, and
    charged to the order through every possible dispatch outcome;
  - the order's compatibility edges (C-C-gated, R-R-manufacturable), which
    generate bundle OPTIONS at every subsequent dispatch.

Anything whose value depends on the identity or position of the driver that
eventually claims the order is NOT resolvable at arrival and is left to the
dispatcher. This is why predictive driver-targeting earns no branch: a predicted
R-D advantage is perishable (pays only if that one driver claims this order at
that one dispatch) and single-use, whereas a bundleability edge is durable
(survives across dispatches) and regenerative (self-harvests within a cluster).

State-adaptive branching (three reachable states under the greedy invariant,
NOT (D>0 AND O>0), which holds at curation time -- the arriving order is not yet
in the pool):

  edge_manufacture  D=0, a C-C-compatible pending single exists.
                    Recommend R* = argmin over the BUNDLEABLE restaurant set of
                    R-C. R* is the cheapest-delivery restaurant that also makes
                    the curated order R-R-compatible with at least one
                    C-C-compatible anchor -- i.e. the recommendation that
                    manufactures a bundle edge at the smallest certain tax.
                    (Contrast R_total = argmin pair route cost, usually the
                    anchor's own restaurant: that minimizes a CONTINGENT cost
                    that only materializes if the edge is harvested. We minimize
                    the certain cost, R-C, instead.)

  single_immediate  D>0 (=> empty pool by the invariant, so no anchors).
                    Recommend R minimizing R-D + R-C. The arriving order takes
                    the immediate-assignment path as a solo; this rule aligns
                    with the dispatcher (for a fresh single, distance score is
                    monotone in total distance; throughput and fairness are
                    constant across drivers).

  single_queued     D=0, no C-C-compatible anchor.
                    Recommend R_nearest = argmin over all restaurants of R-C.

Self-cancellation: when R_nearest already belongs to the bundleable set (common
at saturation, where the deep pool usually puts a compatible pending order at
the nearest restaurant), R* = R_nearest and tax = 0 -- edge_manufacture and
single_queued coincide. The branch does not need to be switched off at high
load; it self-cancels, which is the mechanism behind the empirically observed
decay of pair-push value toward saturation.

Scope note: this build is the MAXIMALLY AGGRESSIVE push -- no fire/skip tax
threshold. Whenever any C-C-compatible anchor exists, it steers to R* and pays
whatever tax that incurs. This is the clean upper bound on manufacturing
curation, an ablation extreme rather than a tuned policy; a mid-load backfire
(positive tax against low realization probability) is an expected and
informative outcome. The threshold that would buy edges only when cheap is left
as a documented one-knob extension (config.pair_push_tax_threshold), not built.

Ablation policies (R-D-only, R-C-only, pair-push-only) are intentionally removed
for now; they will be re-added for signal isolation once this policy is
validated under (iii).
"""

from delivery_sim.entities.states import OrderState
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.bundleability import is_bundleable
from delivery_sim.utils.logging_system import get_logger


class StateAdaptiveCurationPolicy:
    """
    State-adaptive curation for assignment-time bundling (mechanism iii).

    curation_result labels: 'edge_manufacture', 'single_immediate', 'single_queued'.
    There is no 'fallback' label -- even the weakest branch (single_queued)
    applies the R-C signal, which has no analogue in uniform selection.
    """

    def __init__(self, restaurant_repository, driver_repository,
                 order_repository, config):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.order_repository = order_repository
        self.config = config

    def select(self, customer_location=None):
        """
        Select a restaurant based on current system state.

        Args:
            customer_location: The incoming order's customer location.
                               Must be generated before calling select().

        Returns:
            tuple: (Restaurant, curation_result)
                   curation_result is one of 'edge_manufacture',
                   'single_immediate', 'single_queued'.
        """
        idle_drivers = self.driver_repository.find_available_drivers()
        restaurants = self.restaurant_repository.find_all()

        # Branch 1: edge_manufacture. Requires pairing enabled (structural gate)
        # and at least one C-C-compatible pending single. By the greedy invariant
        # this state implies D = 0.
        if self.config.pairing_enabled:
            r_star = self._find_edge_manufacture_restaurant(customer_location, restaurants)
            if r_star is not None:
                # Guard the invariant: anchors present => no idle drivers. If this
                # fires, the assignment architecture has changed (e.g. mechanism iv
                # batching) and this branch's assumptions need revisiting.
                assert not idle_drivers, (
                    "Greedy invariant violated at curation time: idle drivers and "
                    "C-C-compatible pending anchors coexist (NOT D>0 AND O>0)."
                )
                return r_star, 'edge_manufacture'

        # Branch 2: single_immediate. Idle drivers exist.
        if idle_drivers:
            selected = self._select_single_immediate(
                customer_location, restaurants, idle_drivers)
            self.logger.debug(
                f"StateAdaptive [single_immediate]: restaurant {selected.restaurant_id}")
            return selected, 'single_immediate'

        # Branch 3: single_queued. No driver, no anchor.
        selected = self._select_single_queued(customer_location, restaurants)
        self.logger.debug(
            f"StateAdaptive [single_queued]: restaurant {selected.restaurant_id}")
        return selected, 'single_queued'

    def _find_edge_manufacture_restaurant(self, customer_location, restaurants):
        """
        Return R*, the recommendation that manufactures a bundle edge at the
        smallest certain tax, or None if no edge can be manufactured.

        Steps:
          1. C-C gate. Anchors = pending CREATED singles whose customer is within
             delta_c of the arriving customer. Read from the SAME pending set the
             dispatcher enumerates (OrderState.CREATED), so curation's anchor set
             matches the dispatcher's solo-option set exactly.
          2. If no anchors, return None (no edge to manufacture).
          3. Bundleable restaurant set. A restaurant R qualifies if placing the
             curated order at R would make it R-R-compatible with at least one
             C-C anchor -- i.e. is_bundleable(curated-at-R, anchor). Each anchor's
             own restaurant always qualifies (R-R = 0), so the set is non-empty
             whenever anchors exist.
          4. R* = argmin over the bundleable set of R-C. This minimizes the
             certain delivery-leg cost, hence the tax against R_nearest.

        The chosen anchor's identity is deliberately NOT returned: under (iii) the
        dispatcher selects the actual partner later. Curation only establishes
        that a compatible edge exists at R*.
        """
        delta_c = self.config.customers_proximity_threshold
        delta_r = self.config.restaurants_proximity_threshold

        pending = self.order_repository.find_by_state(OrderState.CREATED)
        anchors = [
            o for o in pending
            if calculate_distance(customer_location, o.customer_location) <= delta_c
        ]

        if not anchors:
            return None

        # R* over the bundleable set. is_bundleable checks R-R and C-C; C-C is
        # already satisfied for every anchor here, so this resolves to the R-R
        # feasibility of placing the curated order at candidate restaurant r.
        best_restaurant = None
        best_r_c = float('inf')
        for r in restaurants:
            compatible = any(
                calculate_distance(r.location, a.restaurant_location) <= delta_r
                for a in anchors
            )
            if not compatible:
                continue
            r_c = calculate_distance(r.location, customer_location)
            if r_c < best_r_c:
                best_r_c = r_c
                best_restaurant = r

        if best_restaurant is None:
            # Should be unreachable (an anchor's own restaurant always qualifies),
            # but guard defensively rather than return a non-bundleable R.
            return None

        # Tax diagnostic (not used for any decision): how far R* sits from the
        # unconstrained nearest restaurant. tax == 0 means R* == R_nearest and the
        # branch has coincided with single_queued (self-cancellation).
        r_nearest_r_c = min(
            calculate_distance(r.location, customer_location) for r in restaurants)
        tax = best_r_c - r_nearest_r_c
        self.logger.debug(
            f"StateAdaptive [edge_manufacture]: restaurant {best_restaurant.restaurant_id} "
            f"(R-C={best_r_c:.3f}km, tax={tax:.3f}km, anchors={len(anchors)})")

        return best_restaurant

    def _select_single_immediate(self, customer_location, restaurants, idle_drivers):
        """
        Select R minimizing R-D + R-C in the single_immediate state.

        R-D is the distance from R to the nearest idle driver; R-C is the
        delivery leg. Their sum is the full travel distance of the immediate solo
        delivery, which is what the dispatcher's distance score minimizes for a
        fresh single. Curation and dispatcher therefore agree on the winner.
        """
        best = None
        best_score = float('inf')
        for r in restaurants:
            r_c = calculate_distance(r.location, customer_location)
            r_d = min(calculate_distance(r.location, d.location) for d in idle_drivers)
            if r_d + r_c < best_score:
                best_score = r_d + r_c
                best = r
        return best

    def _select_single_queued(self, customer_location, restaurants):
        """
        Select R_nearest minimizing R-C in the single_queued state.

        No idle drivers means R-D is uninformative. R-C is the only available
        signal: a shorter restaurant-to-customer leg benefits delivery time
        regardless of which driver eventually claims the order.
        """
        best = None
        best_score = float('inf')
        for r in restaurants:
            r_c = calculate_distance(r.location, customer_location)
            if r_c < best_score:
                best_score = r_c
                best = r
        return best