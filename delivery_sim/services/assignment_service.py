# delivery_sim/services/assignment_service.py
"""
Assignment Service - Pure Event-Driven Assignment with Assignment-Time Bundling

Mechanism (iii): pairing is not a pre-assignment event. No pair exists before a
driver is committed to it. The pending pool contains only singles. At each
dispatch the service enumerates options -- every pending order as a solo, plus
every bundleable order pair -- scores all options with the same priority formula,
and dispatches the argmax. A pair record is created at the instant a bundle
option wins (state CREATED -> ASSIGNED in the same tick).

Two trigger events, exactly as under mechanism (ii)'s single mode:

  1. Order arrives (OrderCreatedEvent)
       -> the order shops for its best available driver.
       Solo-only by the greedy invariant: if any driver is idle, the pool was
       empty an instant before this arrival, so no bundle partner can exist.

  2. Driver becomes available (DriverAvailableForAssignmentEvent)
       -> the driver enumerates all options over the pending pool and takes the
       best. This is the ONLY path on which bundles ever form, because a backlog
       of two or more pending orders can only exist while drivers were busy.

Under the greedy invariant, idle drivers and pending orders never coexist, so the
two paths are the two faces of one rule: commit at the first event where a match
is feasible. Removing either trigger breaks liveness on that side (an already-idle
driver is never re-woken; a pending order is never picked up).

Priority scoring is a pure scalar function; this service computes each option's
total distance, order count, and oldest-order wait, then calls the scorer. For a
bundle option the route sequence is computed once here (driver known) and carried
to _create_assignment, so no route evaluation is duplicated.
"""

import itertools

from delivery_sim.entities.states import OrderState, DriverState, PairState
from delivery_sim.entities.delivery_unit import DeliveryUnit
from delivery_sim.entities.pair import Pair
from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.events.driver_events import DriverAvailableForAssignmentEvent
from delivery_sim.events.delivery_unit_events import DeliveryUnitAssignedEvent
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType
from delivery_sim.utils.route_evaluator import evaluate_complete
from delivery_sim.utils.bundleability import is_bundleable


class AssignmentService:
    """
    Pure event-driven assignment service with assignment-time bundling.

    Responds to two events:
      1. Order becomes available  -> find the best available driver (solo-only).
      2. Driver becomes available -> enumerate options over the pending pool and
         assign the best (solo or bundle).

    Assignment decisions use multi-criteria priority scoring balancing distance
    efficiency, throughput, and fairness.
    """

    def __init__(self, env, event_dispatcher, order_repository, driver_repository,
                 pair_repository, delivery_unit_repository, priority_scorer, config):
        """
        Initialize the assignment service.

        Args:
            env: SimPy environment
            event_dispatcher: Central event dispatcher
            order_repository: Repository for orders
            driver_repository: Repository for drivers
            pair_repository: Repository for pairs (populated at dispatch under iii)
            delivery_unit_repository: Repository for delivery units
            priority_scorer: PriorityScorer instance (scalar interface)
            config: Configuration object with scoring weights and thresholds
        """
        self.logger = get_logger("services.assignment")

        self.env = env
        self.event_dispatcher = event_dispatcher
        self.order_repository = order_repository
        self.driver_repository = driver_repository
        self.pair_repository = pair_repository
        self.delivery_unit_repository = delivery_unit_repository
        self.priority_scorer = priority_scorer
        self.config = config

        self.logger.info(f"[t={self.env.now:.2f}] Assignment-time bundling AssignmentService initialized")
        self.logger.info(f"[t={self.env.now:.2f}] Priority scoring weights: "
                         f"distance={config.weight_distance:.3f}, "
                         f"throughput={config.weight_throughput:.3f}, "
                         f"fairness={config.weight_fairness:.3f}")
        self.logger.info(f"[t={self.env.now:.2f}] Bundling {'ENABLED' if config.pairing_enabled else 'DISABLED'} "
                         f"(delta_r={config.restaurants_proximity_threshold}km, "
                         f"delta_c={config.customers_proximity_threshold}km)")

        # Both mechanisms subscribe to the same two triggers. Unlike mechanism
        # (ii) there is no arrival-time pairing to intercept OrderCreatedEvent,
        # so orders flow straight to assignment. pairing_enabled controls only
        # whether the driver-triggered path enumerates bundle options.
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for OrderCreatedEvent")
        event_dispatcher.register(OrderCreatedEvent, self.handle_order_created)

        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for DriverAvailableForAssignmentEvent")
        event_dispatcher.register(DriverAvailableForAssignmentEvent, self.handle_driver_available_for_assignment)

        self.logger.info(f"[t={self.env.now:.2f}] Assignment service ready - listening for assignment events")

    # ===== Event Handlers (Entry Points) =====

    def handle_order_created(self, event):
        """
        Handler for OrderCreatedEvent. The new order shops for its best driver.
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling OrderCreatedEvent for order {event.order_id}")

        order = self.order_repository.find_by_id(event.order_id)
        if order is None:
            self.logger.error(f"[t={self.env.now:.2f}] Order {event.order_id} not found in repository")
            return

        self.attempt_assignment_from_order(order)

    def handle_driver_available_for_assignment(self, event):
        """
        Handler for DriverAvailableForAssignmentEvent. The driver enumerates
        options over the pending pool and takes the best.
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling DriverAvailableForAssignmentEvent for driver {event.driver_id}")

        driver = self.driver_repository.find_by_id(event.driver_id)
        if driver is None:
            self.logger.error(f"[t={self.env.now:.2f}] Driver {event.driver_id} not found in repository")
            return

        self.attempt_assignment_from_driver(driver)

    # ===== Core Assignment Logic =====

    def attempt_assignment_from_driver(self, driver):
        """
        Driver-triggered assignment: enumerate options over the pending pool,
        score each against this driver, dispatch the argmax.

        This is the only path on which bundle options are enumerated.

        Returns:
            bool: True if an assignment was made, False if the pool was empty.
        """
        self.logger.info(f"[t={self.env.now:.2f}] Attempting assignment for driver {driver.driver_id}")

        pending = self.order_repository.find_by_state(OrderState.CREATED)
        if not pending:
            # Slack regime: the driver idles. It will be re-woken only by a future
            # order arrival (handle_order_created), never by another driver event.
            self.logger.info(f"[t={self.env.now:.2f}] No pending orders for driver {driver.driver_id}")
            return False

        options = self._enumerate_options(pending)
        self.logger.debug(f"[t={self.env.now:.2f}] Enumerated {len(options)} options "
                          f"({len(pending)} pending orders) for driver {driver.driver_id}")

        best_option = None
        best_score = -1  # Sentinel below any real score
        best_components = None
        for option in options:
            score, components = self._score_driver_option(driver, option)
            if score > best_score:
                best_score = score
                best_option = option
                best_components = components

        self._log_selected_option(driver, best_option, best_score)
        self._create_assignment(driver, best_option, best_components)
        return True

    def attempt_assignment_from_order(self, order):
        """
        Order-triggered assignment: the arriving order is a solo option; score it
        against every available driver, dispatch to the argmax driver.

        Solo-only by construction. The greedy invariant guarantees that if any
        driver is idle, the pending pool behind this arrival is empty, so no
        bundle partner exists. If no driver is idle, the order simply waits and a
        future freed driver will enumerate it (possibly as a bundle).

        Returns:
            bool: True if an assignment was made, False if no driver was available.
        """
        self.logger.info(f"[t={self.env.now:.2f}] Attempting assignment for order {order.order_id}")

        available_drivers = self.driver_repository.find_available_drivers()
        if not available_drivers:
            self.logger.info(f"[t={self.env.now:.2f}] No available drivers for order {order.order_id}")
            return False

        solo = self._make_solo_option(order)

        best_driver = None
        best_score = -1
        best_components = None
        for candidate_driver in available_drivers:
            score, components = self._score_driver_option(candidate_driver, solo)
            if score > best_score:
                best_score = score
                best_driver = candidate_driver
                best_components = components

        self.logger.info(f"[t={self.env.now:.2f}] Assignment: order {order.order_id} to "
                         f"driver {best_driver.driver_id} (priority score {best_score:.2f})")
        self._create_assignment(best_driver, solo, best_components)
        return True

    # ===== Option Enumeration =====

    def _make_solo_option(self, order):
        """Build a solo option (one order, throughput 1)."""
        return {'orders': [order], 'num_orders': 1}

    def _enumerate_options(self, pending):
        """
        Build the option set from the pending pool.

        Always: one solo option per pending order.
        When bundling is enabled: one bundle option per bundleable order pair.

        The pairing_enabled gate is the single point that distinguishes bundling
        from no-bundling. With it False the option set is solo-only, which is pure
        single-order greedy assignment -- identical to mechanism (ii)'s OFF
        condition and to the same RNG stream, so the two can be cross-validated.

        Overlapping bundle options (sharing an order) are fine: argmax dispatches
        exactly one, and the losers dissolve back into the pool as pending singles.
        """
        options = [self._make_solo_option(order) for order in pending]

        if self.config.pairing_enabled:
            delta_r = self.config.restaurants_proximity_threshold
            delta_c = self.config.customers_proximity_threshold
            for order_a, order_b in itertools.combinations(pending, 2):
                if is_bundleable(order_a, order_b, delta_r, delta_c):
                    options.append({'orders': [order_a, order_b], 'num_orders': 2})

        return options

    # ===== Scoring =====

    def _score_driver_option(self, driver, option):
        """
        Score a (driver, option) pair.

        Computes the option's total travel distance against this specific driver
        (for a bundle, jointly with the best route sequence via evaluate_complete),
        the oldest-order wait, and the order count, then delegates to the scalar
        priority scorer. The chosen sequence and route cost (bundle only) are
        attached to the returned components so _create_assignment can write them
        onto the DeliveryUnit without re-evaluating the route.

        Returns:
            tuple: (priority_score_0_to_100, components_dictionary)
        """
        orders = option['orders']
        num_orders = option['num_orders']

        if num_orders == 2:
            order_a, order_b = orders
            route = evaluate_complete(
                order_a.restaurant_location, order_a.customer_location,
                order_b.restaurant_location, order_b.customer_location,
                [driver])
            total_distance = route['total_cost']       # driver leg + pair route
            chosen_sequence = route['stops']
            chosen_route_cost = route['route_cost']     # pair route, excluding driver leg
        else:
            order = orders[0]
            driver_to_restaurant = calculate_distance(driver.location, order.restaurant_location)
            restaurant_to_customer = calculate_distance(order.restaurant_location, order.customer_location)
            total_distance = driver_to_restaurant + restaurant_to_customer
            chosen_sequence = None
            chosen_route_cost = None

        # Fairness input: age of the oldest order in the option
        # (now - earliest arrival). Equal to the mechanism (ii) definition, which
        # used min(order arrivals) rather than the pair's creation time -- so the
        # fairness component means the same thing across mechanisms.
        wait_time = max(self.env.now - o.arrival_time for o in orders)

        priority_score, components = self.priority_scorer.calculate_priority_score(
            total_distance, num_orders, wait_time)

        components['chosen_sequence'] = chosen_sequence
        components['chosen_route_cost'] = chosen_route_cost

        return priority_score, components

    def _log_selected_option(self, driver, option, score):
        """Emit a readable log line describing the winning option."""
        if option['num_orders'] == 2:
            a, b = option['orders']
            self.logger.info(f"[t={self.env.now:.2f}] Assignment: driver {driver.driver_id} to "
                             f"BUNDLE ({a.order_id} + {b.order_id}) (priority score {score:.2f})")
        else:
            self.logger.info(f"[t={self.env.now:.2f}] Assignment: driver {driver.driver_id} to "
                             f"SOLO {option['orders'][0].order_id} (priority score {score:.2f})")

    # ===== Assignment Creation =====

    def _create_assignment(self, driver, option, components):
        """
        Materialize the winning option as a DeliveryUnit and update state.

        For a bundle option the Pair record is created here, at dispatch: this is
        the instant pairing is committed under mechanism (iii). The pair is born
        CREATED and transitioned to ASSIGNED in the same tick (zero-duration
        CREATED state), preserving the existing pair-level metric definitions.

        Returns:
            DeliveryUnit: the created delivery unit, or None if the driver was no
            longer available.
        """
        if driver.state != DriverState.AVAILABLE:
            self.logger.validation(f"[t={self.env.now:.2f}] Critical error: driver {driver.driver_id} "
                                   f"not available when creating assignment")
            return None

        # Resolve the option into the entity the DeliveryUnit wraps.
        if option['num_orders'] == 2:
            entity = self._create_pair_at_dispatch(option['orders'][0], option['orders'][1])
            entity_type = EntityType.PAIR
            entity_id = entity.pair_id
        else:
            entity = option['orders'][0]
            entity_type = EntityType.ORDER
            entity_id = entity.order_id

        self.logger.debug(f"[t={self.env.now:.2f}] Creating delivery unit for driver {driver.driver_id} "
                          f"to {entity_type} {entity_id}")

        delivery_unit = DeliveryUnit(entity, driver, self.env.now)

        delivery_unit.assignment_scores = {
            "distance_score": components["distance_score"],
            "throughput_score": components["throughput_score"],
            "fairness_score": components["fairness_score"],
            "combined_score_0_1": components["combined_score_0_1"],
            "priority_score_0_100": components["combined_score_0_1"] * 100,
            "total_distance": components["total_distance"],
            "num_orders": components["num_orders"],
            "assignment_delay_minutes": components["assignment_delay_minutes"]
        }

        # Binding route sequence for bundles, already computed during scoring.
        # Single orders keep None (driver -> restaurant -> customer needs no stored
        # sequence), exactly as under mechanism (ii).
        delivery_unit.chosen_sequence = components["chosen_sequence"]
        delivery_unit.chosen_route_cost = components["chosen_route_cost"]

        self.delivery_unit_repository.add(delivery_unit)

        # State transitions.
        if entity_type == EntityType.ORDER:
            entity.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.delivery_unit = delivery_unit
            self.logger.debug(f"[t={self.env.now:.2f}] Order {entity.order_id} -> ASSIGNED")
        else:
            # Pair is in CREATED (just created this tick); complete the collapse to ASSIGNED.
            entity.transition_to(PairState.ASSIGNED, self.event_dispatcher, self.env)
            entity.delivery_unit = delivery_unit
            # Constituent orders are in PAIRED (set in _create_pair_at_dispatch); PAIRED -> ASSIGNED.
            entity.order1.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.order1.delivery_unit = delivery_unit
            entity.order2.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.order2.delivery_unit = delivery_unit
            self.logger.debug(f"[t={self.env.now:.2f}] Pair {entity.pair_id} -> ASSIGNED")

        driver.transition_to(DriverState.DELIVERING, self.event_dispatcher, self.env)
        driver.current_delivery_unit = delivery_unit
        self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver.driver_id} -> DELIVERING")

        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DeliveryUnitAssignedEvent for unit {delivery_unit.unit_id}")
        self.event_dispatcher.dispatch(DeliveryUnitAssignedEvent(
            timestamp=self.env.now,
            delivery_unit_id=delivery_unit.unit_id,
            entity_type=entity_type,
            entity_id=entity_id,
            driver_id=driver.driver_id
        ))

        self.logger.info(f"[t={self.env.now:.2f}] Created assignment: driver {driver.driver_id} to "
                         f"{entity_type} {entity_id} "
                         f"(priority score: {delivery_unit.assignment_scores['priority_score_0_100']:.2f}, "
                         f"distance: {components['total_distance']:.2f}km)")

        return delivery_unit

    def _create_pair_at_dispatch(self, order_a, order_b):
        """
        Create the Pair record at dispatch time.

        Mirrors the entity bookkeeping the deleted PairingService.form_pair did --
        construct the pair, register it, set bidirectional references, transition
        the constituent orders to PAIRED -- MINUS the two things that no longer
        apply under mechanism (iii):

          - partial_info_sequence / partial_info_cost: there is no partial-info
            moment; partner and route are decided together at dispatch.
          - PairCreatedEvent: nothing subscribes to it. Under (ii) it re-triggered
            assignment; here we are already inside assignment.

        The pair is left in CREATED; the caller (_create_assignment) transitions it
        to ASSIGNED in the same tick.

        Returns:
            Pair: the newly created pair, in state CREATED.
        """
        pair = Pair(order_a, order_b, self.env.now)
        self.pair_repository.add(pair)

        order_a.pair = pair
        order_b.pair = pair

        order_a.transition_to(OrderState.PAIRED, self.event_dispatcher, self.env)
        order_b.transition_to(OrderState.PAIRED, self.event_dispatcher, self.env)

        self.logger.debug(f"[t={self.env.now:.2f}] Created pair {pair.pair_id} at dispatch "
                          f"({order_a.order_id} + {order_b.order_id})")
        return pair