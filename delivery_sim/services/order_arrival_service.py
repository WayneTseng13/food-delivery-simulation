from delivery_sim.entities.order import Order
from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.location_utils import format_location


class OrderArrivalService:
    """
    Service responsible for generating new orders entering the system.

    This service runs as a continuous SimPy process, creating new orders
    based on configured inter-arrival times and dispatching events when
    orders are created.
    """

    def __init__(self, env, event_dispatcher, order_repository,
                    restaurant_repository, config, id_generator,
                    operational_rng_manager, curation_policy=None):
            
            """Initialize the order arrival service."""
            self.logger = get_logger("services.order_arrival")

            # Store dependencies
            self.env = env
            self.event_dispatcher = event_dispatcher
            self.order_repository = order_repository
            self.restaurant_repository = restaurant_repository
            self.config = config
            self.id_generator = id_generator

            # Get all random streams at initialization time
            self.arrival_stream = operational_rng_manager.get_stream('order_arrivals')
            self.location_stream = operational_rng_manager.get_stream('customer_locations')
            self.restaurant_selection_stream = operational_rng_manager.get_stream('restaurant_selection')
            self.compliance_stream = operational_rng_manager.get_stream('customer_compliance')   # NEW

            # Curation policy (may be None — meaning no curation is active and the
            # customer samples a restaurant uniformly at random).
            self.curation_policy = curation_policy

            # Customer compliance probability. Inert when curation_policy is None.
            self.compliance_probability = config.customer_compliance_probability

            if self.curation_policy is None and self.compliance_probability != 1.0:
                self.logger.warning(
                    f"customer_compliance_probability={self.compliance_probability} "
                    f"is set but curation_policy is None — parameter has no effect "
                    f"(no recommendation is produced for the customer to comply with)."
                )

            policy_name = (
                type(self.curation_policy).__name__
                if self.curation_policy is not None
                else "None (no curation)"
            )
            self.logger.info(
                f"[t={self.env.now:.2f}] OrderArrivalService initialized "
                f"with mean inter-arrival time: {config.mean_order_inter_arrival_time} minutes, "
                f"curation policy: {policy_name}, "
                f"compliance probability: {self.compliance_probability}"
            )

            self.logger.info(f"[t={self.env.now:.2f}] Starting order arrival process")
            self.process = env.process(self._arrival_process())

    def _arrival_process(self):
        """SimPy process that generates new orders at configured intervals."""
        while True:
            inter_arrival_time = self._generate_inter_arrival_time()
            self.logger.debug(
                f"[t={self.env.now:.2f}] Next order will arrive "
                f"in {inter_arrival_time:.2f} minutes"
            )

            yield self.env.timeout(inter_arrival_time)

            order_id = self.id_generator.next()
            customer_location = self._generate_customer_location()
            # Read arrival-state BEFORE any recommendation, for every policy
            # (including U). This is the honest "was an idle driver present?"
            # read the curation policy also uses internally, but stamped here so
            # it exists uniformly across policies.
            idle_at_arrival = self.driver_repository.find_available_drivers()
            arrival_state = 'immediate' if idle_at_arrival else 'queued'

            (restaurant_location, curation_result, customer_complied,
            featuring_penalty, origin_restaurant_id) = \
                self._select_restaurant_location(customer_location)

            self.logger.debug(
                f"[t={self.env.now:.2f}] Generated attributes for order {order_id}: "
                f"restaurant at {format_location(restaurant_location)}, "
                f"customer at {format_location(customer_location)}"
            )

            new_order = Order(
                        order_id=order_id,
                        restaurant_location=restaurant_location,
                        customer_location=customer_location,
                        arrival_time=self.env.now,
                        curation_result=curation_result,
                        customer_complied=customer_complied,
                        featuring_penalty=featuring_penalty,
                        arrival_state=arrival_state,                  # NEW
                        origin_restaurant_id=origin_restaurant_id,    # NEW
                    )

            self.order_repository.add(new_order)

            self.logger.info(
                f"[t={self.env.now:.2f}] Created order {order_id} from restaurant at "
                f"{format_location(restaurant_location)} to customer at "
                f"{format_location(customer_location)}"
            )

            self.logger.simulation_event(
                f"[t={self.env.now:.2f}] Dispatching OrderCreatedEvent for order {order_id}"
            )
            self.event_dispatcher.dispatch(OrderCreatedEvent(
                timestamp=self.env.now,
                order_id=order_id,
                restaurant_id=0,
                restaurant_location=restaurant_location,
                customer_location=customer_location
            ))

    def _generate_inter_arrival_time(self):
        """Generate the time until the next order arrival using an exponential distribution."""
        return self.arrival_stream.exponential(self.config.mean_order_inter_arrival_time)

    def _select_restaurant_location(self, customer_location):
        """
        Determine the restaurant a customer ends up ordering from, given the active
        curation policy and the customer's compliance behavior.
    
        Flow:
        - Policy U (curation_policy is None): no recommendation. The customer
            samples uniformly over ALL restaurants on restaurant_selection_stream.
            compliance is not applicable (None).
        - Any curation policy: a recommendation is ALWAYS produced. Apply the
            compliance gate on compliance_stream. On acceptance the customer takes
            the recommendation; on rejection the customer samples uniformly over the
            remaining restaurants on restaurant_selection_stream.
    
        Returns:
            tuple: (location, curation_result, customer_complied, featuring_penalty)
                curation_result:
                    None                          -- Policy U (no curation)
                    'operational_immediate' /
                    'operational_queued'          -- R_op recommended
                    'featured_immediate' /
                    'featured_queued'             -- R_F recommended
                customer_complied:
                    None   -- no recommendation (U)
                    True   -- recommendation accepted
                    False  -- recommendation rejected
                featuring_penalty:
                    None   -- U, or operational mode (no featuring decision)
                    float  -- featuring penalty (>= 0), whether or not it fired
        """
        # Policy U: no recommendation, no compliance concept.
        if self.curation_policy is None:
            restaurants = self.restaurant_repository.find_all()
            selected = self.restaurant_selection_stream.choice(restaurants)
            self.logger.debug(
                f"[t={self.env.now:.2f}] No curation (U); customer chose "
                f"restaurant {selected.restaurant_id} uniformly")
            return selected.location, None, None, None, selected.restaurant_id
    
        # A curation policy is active: it ALWAYS produces a recommendation.
        recommendation, curation_result, featuring_penalty = \
            self.curation_policy.select(customer_location)
    
        assert recommendation is not None, (
            f"{type(self.curation_policy).__name__} returned no recommendation. "
            f"Every curation policy in this module must always recommend; the "
            f"no-recommendation path belongs to Policy U (curation_policy is None).")
    
        # Compliance gate.
        u = self.compliance_stream.uniform(0.0, 1.0)
        if u < self.compliance_probability:
            self.logger.debug(
                f"[t={self.env.now:.2f}] Recommendation accepted; "
                f"restaurant {recommendation.restaurant_id} "
                f"(curation_result={curation_result})")
            return (recommendation.location, curation_result, True,
                featuring_penalty, recommendation.restaurant_id)
    
        # Rejection: sample uniformly from the other restaurants. With N=10 the
        # single-restaurant pathological case cannot occur, so no forced-comply guard.
        restaurants = self.restaurant_repository.find_all()
        others = [r for r in restaurants
                if r.restaurant_id != recommendation.restaurant_id]
        selected = self.restaurant_selection_stream.choice(others)
        self.logger.debug(
            f"[t={self.env.now:.2f}] Recommendation rejected; customer chose "
            f"restaurant {selected.restaurant_id} uniformly from {len(others)} "
            f"(recommendation was {recommendation.restaurant_id}, "
            f"curation_result={curation_result})")
        return (selected.location, curation_result, False,
            featuring_penalty, selected.restaurant_id)
 

    def _generate_customer_location(self):
        """Generate a customer location for a new order."""
        area_size = self.config.delivery_area_size
        location = self.location_stream.uniform(0, area_size, size=2).tolist()
        return location