# delivery_sim/utils/curation_policy.py
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.route_evaluator import evaluate_partial


class ProximityCurationPolicy:
    """
    Policy X: R-D proximity curation (Savelsbergh & Ulmer, 2024).

    When idle drivers exist:
        Ranks all restaurants by their distance to the nearest idle driver.
        Returns the restaurant with the shortest minimum distance.

    When no idle drivers exist:
        R-D signal is unavailable. Policy returns None — no recommendation is
        produced. The customer behavior layer (order_arrival_service) handles
        the no-recommendation case by sampling uniformly over all restaurants.
    """

    def __init__(self, restaurant_repository, driver_repository):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository

    def select(self, customer_location=None):
        """
        Select a restaurant using R-D proximity curation.
        customer_location is accepted but ignored (interface compatibility).

        Returns:
            tuple: (Restaurant or None, curation_result)
                   (Restaurant, 'curated')  — idle drivers existed, proximity selection applied.
                   (None,       'fallback') — no idle drivers, no recommendation produced.
        """
        idle_drivers = self.driver_repository.find_available_drivers()

        if not idle_drivers:
            self.logger.debug(
                "ProximityCuration: no idle drivers, no recommendation produced"
            )
            return None, 'fallback'

        restaurants = self.restaurant_repository.find_all()
        best_restaurant = None
        best_dist = float('inf')

        for r in restaurants:
            min_dist = min(
                calculate_distance(r.location, d.location)
                for d in idle_drivers
            )
            if min_dist < best_dist:
                best_dist = min_dist
                best_restaurant = r

        self.logger.debug(
            f"ProximityCuration selected restaurant {best_restaurant.restaurant_id} "
            f"(nearest idle driver dist={best_dist:.3f}km, "
            f"idle_drivers={len(idle_drivers)})"
        )
        return best_restaurant, 'curated'


class StateAdaptiveCurationPolicy:
    """
    Policy X': state-adaptive curation.

    Extends curation into high-load regimes where Policy X's R-D signal
    vanishes by branching on observable system state at arrival time.

    Three reachable operating states:

      pair_queued      D=0, pair-eligible anchor exists.
                       Pick (R_N, anchor) jointly via evaluate_partial,
                       minimising expected pair route cost.

      single_immediate D>0, no pair-eligible anchors.
                       (No anchors implied by assignment invariant when D>0.)
                       Pick R_N minimising R-D + R-C.

      single_queued    D=0, no pair-eligible anchors.
                       Pick R_N minimising R-C alone.

    A fourth state (pair_immediate: D>0 AND pair-eligible anchors) is
    structurally unreachable under the current event-driven greedy assignment
    because the system never has both idle drivers and pending entities
    simultaneously. An assertion guards against future violations.

    curation_result labels: 'pair_queued', 'single_immediate', 'single_queued'.
    There is no 'fallback' label — even the weakest branch (single_queued)
    applies R-C signal, which has no analogue in Policy U.
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
                   curation_result is one of 'pair_queued', 'single_immediate',
                   'single_queued'.
        """
        idle_drivers = self.driver_repository.find_available_drivers()
        restaurants = self.restaurant_repository.find_all()

        if self.config.pairing_enabled:
            best_pair = self._find_best_pair(customer_location, restaurants)

            if best_pair is not None:
                # pair_immediate (D>0 AND pair-eligible anchor) is unreachable
                # under the current assignment architecture.
                assert not idle_drivers, (
                    "pair_immediate state reached: idle drivers and pair-eligible "
                    "anchors coexist. This violates the assignment invariant "
                    "(NOT D>0 AND O>0) and signals a change in assignment architecture."
                )
                selected = best_pair['restaurant']
                self.logger.debug(
                    f"StateAdaptive [pair_queued]: selected restaurant "
                    f"{selected.restaurant_id} "
                    f"(pair route_cost={best_pair['route_cost']:.3f}km)"
                )
                return selected, 'pair_queued'

        if idle_drivers:
            selected = self._select_single_immediate(
                customer_location, restaurants, idle_drivers
            )
            self.logger.debug(
                f"StateAdaptive [single_immediate]: selected restaurant "
                f"{selected.restaurant_id}"
            )
            return selected, 'single_immediate'

        selected = self._select_single_queued(customer_location, restaurants)
        self.logger.debug(
            f"StateAdaptive [single_queued]: selected restaurant "
            f"{selected.restaurant_id}"
        )
        return selected, 'single_queued'

    def _find_best_pair(self, customer_location, restaurants):
        """
        Search for the best (R_N, anchor) combination in pair_queued state.

        Checks R-R and C-C proximity constraints before scoring. Uses
        evaluate_partial to mirror the computation pairing service will later
        perform — alignment by shared computation ensures curation's intended
        pair is the pair that actually forms.

        Returns a dict with 'restaurant', 'anchor', 'route_cost', or None if
        no valid (R_N, anchor) combination exists.
        """
        # Only unpaired singleton orders can serve as anchors.
        # The pair is None guard is a safety net in case find_unassigned_orders
        # includes orders already in a pair (e.g. PAIRED but not yet ASSIGNED).
        pending = [
            o for o in self.order_repository.find_unassigned_orders()
            if o.pair is None
        ]
        if not pending:
            return None

        best = None
        best_cost = float('inf')

        for r_n in restaurants:
            for anchor in pending:
                # C-C proximity check (customer_location is already known)
                if calculate_distance(customer_location, anchor.customer_location) \
                        > self.config.customers_proximity_threshold:
                    continue
                # R-R proximity check
                if calculate_distance(r_n.location, anchor.restaurant_location) \
                        > self.config.restaurants_proximity_threshold:
                    continue
                # Score this (R_N, anchor) pair
                result = evaluate_partial(
                    r_n.location, customer_location,
                    anchor.restaurant_location, anchor.customer_location,
                )
                if result['route_cost'] < best_cost:
                    best_cost = result['route_cost']
                    best = {
                        'restaurant': r_n,
                        'anchor': anchor,
                        'route_cost': best_cost,
                    }

        return best

    def _select_single_immediate(self, customer_location, restaurants, idle_drivers):
        """
        Select R_N minimising R-D + R-C in single_immediate state.

        R-D: distance from nearest idle driver to R_N.
        R-C: distance from R_N to customer.
        Both signals are actionable when idle drivers are present.
        """
        best = None
        best_score = float('inf')

        for r in restaurants:
            r_c = calculate_distance(r.location, customer_location)
            r_d = min(
                calculate_distance(r.location, d.location) for d in idle_drivers
            )
            if r_d + r_c < best_score:
                best_score = r_d + r_c
                best = r

        return best

    def _select_single_queued(self, customer_location, restaurants):
        """
        Select R_N minimising R-C in single_queued state.

        No idle drivers means R-D is uninformative. R-C is the only available
        signal: a shorter restaurant-to-customer leg benefits delivery time
        regardless of which driver eventually picks up the order.
        """
        best = None
        best_score = float('inf')

        for r in restaurants:
            r_c = calculate_distance(r.location, customer_location)
            if r_c < best_score:
                best_score = r_c
                best = r

        return best


class StateAdaptiveNoPairPushCurationPolicy(StateAdaptiveCurationPolicy):
    """
    Policy X'': state-adaptive curation without active pair-formation push.

    Same state-adaptive structure as X' (driver-availability branching with R-C
    signal in both states), but the pair_queued branch is removed. When no
    idle drivers exist, X'' selects R_N minimising R-C alone — it does NOT
    inspect the pending queue for pair-eligible anchors.

    Reachable operating states:

      single_immediate D>0, no pair-eligible anchors (by assignment invariant).
                       Pick R_N minimising R-D + R-C.
                       Identical to X' single_immediate branch.

      single_queued    D=0.
                       Pick R_N minimising R-C alone.
                       Identical to X' single_queued branch.

    Purpose in the policy hierarchy:
      X    (proximity)                  uses R-D only
      X''  (state_adaptive_no_pair_push) adds R-C signal, no pair construction
      X'   (state_adaptive)              adds active pair-formation push

    X vs X''  isolates the contribution of the R-C signal and the
              state-adaptive structure that uses it.
    X' vs X'' isolates the contribution of the active pair-formation push.
              Note: zero under pairing OFF by construction (X' gates the
              pair_queued branch on config.pairing_enabled), nonzero under
              pairing ON.

    curation_result labels: 'single_immediate', 'single_queued'.
    The label 'pair_queued' never appears under X''.
    """

    def select(self, customer_location=None):
        """
        Select a restaurant based on current system state, without considering
        pair construction. Inherits all helper methods from
        StateAdaptiveCurationPolicy.
        """
        idle_drivers = self.driver_repository.find_available_drivers()
        restaurants = self.restaurant_repository.find_all()

        if idle_drivers:
            selected = self._select_single_immediate(
                customer_location, restaurants, idle_drivers
            )
            self.logger.debug(
                f"StateAdaptiveNoPairPush [single_immediate]: selected restaurant "
                f"{selected.restaurant_id}"
            )
            return selected, 'single_immediate'

        selected = self._select_single_queued(customer_location, restaurants)
        self.logger.debug(
            f"StateAdaptiveNoPairPush [single_queued]: selected restaurant "
            f"{selected.restaurant_id}"
        )
        return selected, 'single_queued'    


class ProximityWithPairPushCurationPolicy(StateAdaptiveCurationPolicy):
    """
    Policy X''': R-D proximity curation with active pair-formation push.

    Isolates the contribution of the active pair-formation push branch when
    the R-C signal is NOT used as an explicit selection criterion in the
    single-order branches. Complements the X vs X'' comparison (which isolates
    R-C without pair-push) to complete the signal-contribution decomposition.

    Three reachable operating states:

      pair_queued      D=0, pair-eligible anchor exists.
                       Pick (R_N, anchor) jointly via evaluate_partial.
                       Same as X' pair_queued branch.

      curated          D>0.
                       Pick R_N minimising R-D alone.
                       Same as X's D>0 branch. Does NOT use R-C.

      fallback         D=0, no pair-eligible anchor.
                       Return None. Service layer samples uniformly.
                       Same as X's fallback behavior. Does NOT use R-C.

    Signal decomposition context:
      X    (proximity)                   uses R-D
      X''  (state_adaptive_no_pair_push) uses R-D + R-C
      X''' (proximity_with_pair_push)    uses R-D + active_pair_push
      X'   (state_adaptive)              uses R-D + R-C + active_pair_push

    Caveat — the "no R-C" framing:
      The pair_queued branch inherits evaluate_partial from X', which uses
      the arriving customer's location as a stop in route-cost enumeration.
      R-C-like geometric information is therefore present in the pair_queued
      branch's scoring. What X''' removes is R-C as an EXPLICIT selection
      criterion in the single-order branches, not R-C-like information from
      route optimization inside the pair mechanism. A stricter decoupling
      would require a different pair-selection score (e.g., R-R only) but
      would change the pair-push mechanism substantively.

    curation_result labels: 'pair_queued', 'curated', 'fallback'.
      Note: 'curated' and 'fallback' are shared with ProximityCurationPolicy
      (X). Analysis code that groups by curation_result will pool X and X'''
      results for those two labels — usually fine, since the branch semantics
      are identical, but worth remembering when interpreting diagnostics.
    """

    def select(self, customer_location=None):
        idle_drivers = self.driver_repository.find_available_drivers()
        restaurants = self.restaurant_repository.find_all()

        # Branch A: pair_queued (D=0 with pair-eligible anchor).
        # Checked first so that when pairing is enabled and an anchor exists,
        # the active push takes precedence over the D=0 fallback.
        if self.config.pairing_enabled:
            best_pair = self._find_best_pair(customer_location, restaurants)
            if best_pair is not None:
                assert not idle_drivers, (
                    "pair_immediate state reached: idle drivers and "
                    "pair-eligible anchors coexist. This violates the "
                    "assignment invariant (NOT D>0 AND O>0)."
                )
                selected = best_pair['restaurant']
                self.logger.debug(
                    f"ProximityWithPairPush [pair_queued]: selected restaurant "
                    f"{selected.restaurant_id} "
                    f"(pair route_cost={best_pair['route_cost']:.3f}km)"
                )
                return selected, 'pair_queued'

        # Branch B: curated (D>0). Min R-D only, matching Policy X.
        if idle_drivers:
            best_restaurant = None
            best_dist = float('inf')
            for r in restaurants:
                min_dist = min(
                    calculate_distance(r.location, d.location)
                    for d in idle_drivers
                )
                if min_dist < best_dist:
                    best_dist = min_dist
                    best_restaurant = r
            self.logger.debug(
                f"ProximityWithPairPush [curated]: selected restaurant "
                f"{best_restaurant.restaurant_id} "
                f"(nearest idle driver dist={best_dist:.3f}km)"
            )
            return best_restaurant, 'curated'

        # Branch C: fallback (D=0, no pair-eligible anchor). No signal available.
        # Return None so order_arrival_service samples uniformly.
        self.logger.debug(
            "ProximityWithPairPush [fallback]: no signal available "
            "(D=0 and no pair-eligible anchor)"
        )
        return None, 'fallback'    