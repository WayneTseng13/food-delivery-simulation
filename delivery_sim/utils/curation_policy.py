# delivery_sim/utils/curation_policy.py
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.route_evaluator import evaluate_partial


class UniformPolicy:
    """
    Policy U: uniform random restaurant selection.

    Baseline behavior — equivalent to the original _select_restaurant_location
    logic extracted into a policy object.
    """

    def __init__(self, restaurant_repository, restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.rng = restaurant_selection_stream

    def select(self, customer_location=None):
        """
        Select a restaurant uniformly at random.
        customer_location is accepted but ignored (interface compatibility).

        Returns:
            tuple: (Restaurant, None)
        """
        restaurants = self.restaurant_repository.find_all()
        selected = self.rng.choice(restaurants)
        self.logger.debug(f"UniformPolicy selected restaurant {selected.restaurant_id}")
        return selected, None


class ProximityCurationPolicy:
    """
    Policy X: R-D proximity curation (Savelsbergh & Ulmer, 2024).

    When idle drivers exist:
        Ranks all restaurants by their distance to the nearest idle driver.
        Returns the restaurant with the shortest minimum distance.

    When no idle drivers exist:
        R-D signal is unavailable. Falls back to uniform random selection.
    """

    def __init__(self, restaurant_repository, driver_repository,
                 restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.rng = restaurant_selection_stream

    def select(self, customer_location=None):
        """
        Select a restaurant using R-D proximity curation.
        customer_location is accepted but ignored (interface compatibility).

        Returns:
            tuple: (Restaurant, curation_result)
                   'curated'  — idle drivers existed, proximity selection applied.
                   'fallback' — no idle drivers, uniform random used instead.
        """
        idle_drivers = self.driver_repository.find_available_drivers()

        if not idle_drivers:
            restaurants = self.restaurant_repository.find_all()
            selected = self.rng.choice(restaurants)
            self.logger.debug(
                f"ProximityCuration: no idle drivers, fallback to random "
                f"-> restaurant {selected.restaurant_id}"
            )
            return selected, 'fallback'

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