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
            restaurant_location, curation_result, customer_complied = \
                self._select_restaurant_location(customer_location)        # CHANGED: 3-tuple

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
                customer_complied=customer_complied,                       # NEW
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
            Determine the restaurant a customer ends up ordering from, given the
            active curation policy and the customer's compliance behavior.

            Returns:
                tuple: (location, curation_result, customer_complied)
                    curation_result:
                        None       — no curation policy was active
                        'fallback' — policy was active but produced no recommendation
                        'curated' / 'pair_queued' / 'single_immediate' / 'single_queued'
                                    — policy produced a recommendation
                    customer_complied:
                        None  — no recommendation to comply with
                        True  — recommendation produced and customer accepted
                        False — recommendation produced and customer rejected
            """
            # Step 1: ask the curation policy for a recommendation.
            if self.curation_policy is None:
                recommendation = None
                curation_result = None
            else:
                recommendation, curation_result = self.curation_policy.select(customer_location)

            # Step 2: customer-behavior decision.
            if recommendation is None:
                # No recommendation produced. Customer samples uniformly over all
                # restaurants using restaurant_selection_stream (matches prior behavior
                # for both U and X-in-fallback).
                restaurants = self.restaurant_repository.find_all()
                selected = self.restaurant_selection_stream.choice(restaurants)
                customer_complied = None
                self.logger.debug(
                    f"[t={self.env.now:.2f}] No recommendation; "
                    f"customer chose restaurant {selected.restaurant_id} uniformly "
                    f"(curation_result={curation_result})"
                )
                return selected.location, curation_result, customer_complied

            # Recommendation produced. Apply compliance gate.
            u = self.compliance_stream.uniform(0.0, 1.0)
            if u < self.compliance_probability:
                selected = recommendation
                customer_complied = True
                self.logger.debug(
                    f"[t={self.env.now:.2f}] Recommendation accepted; "
                    f"customer chose restaurant {selected.restaurant_id} "
                    f"(curation_result={curation_result})"
                )
            else:
                # Customer rejects the recommendation and samples uniformly from the
                # remaining restaurants (excluding the recommended one).
                restaurants = self.restaurant_repository.find_all()
                others = [r for r in restaurants if r.restaurant_id != recommendation.restaurant_id]
                if not others:
                    # Pathological single-restaurant case: there is no alternative,
                    # so the customer is forced to comply.
                    selected = recommendation
                    customer_complied = True
                    self.logger.debug(
                        f"[t={self.env.now:.2f}] Recommendation rejected but no other "
                        f"restaurants exist; customer forced to accept "
                        f"restaurant {selected.restaurant_id}"
                    )
                else:
                    selected = self.compliance_stream.choice(others)
                    customer_complied = False
                    self.logger.debug(
                        f"[t={self.env.now:.2f}] Recommendation rejected; "
                        f"customer chose restaurant {selected.restaurant_id} "
                        f"uniformly from remaining {len(others)} "
                        f"(recommendation was {recommendation.restaurant_id}, "
                        f"curation_result={curation_result})"
                    )

            return selected.location, curation_result, customer_complied

    def _generate_customer_location(self):
        """Generate a customer location for a new order."""
        area_size = self.config.delivery_area_size
        location = self.location_stream.uniform(0, area_size, size=2).tolist()
        return location