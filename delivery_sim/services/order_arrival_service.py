from delivery_sim.entities.order import Order
from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.location_utils import format_location
from delivery_sim.utils.curation_policy import UniformPolicy          # NEW


class OrderArrivalService:
    """
    Service responsible for generating new orders entering the system.

    This service runs as a continuous SimPy process, creating new orders
    based on configured inter-arrival times and dispatching events when
    orders are created.
    """

    def __init__(self, env, event_dispatcher, order_repository,
                 restaurant_repository, config, id_generator,
                 operational_rng_manager, curation_policy=None):       # NEW parameter
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

        # Wire up curation policy.
        # If one was injected (by SimulationRunner), use it directly.
        # Otherwise default to UniformPolicy — identical to the original behavior,
        # so existing call sites that don't pass a policy continue to work.
        if curation_policy is not None:
            self.curation_policy = curation_policy
        else:
            self.curation_policy = UniformPolicy(
                restaurant_repository=self.restaurant_repository,
                restaurant_selection_stream=self.restaurant_selection_stream
            )

        self.logger.info(
            f"[t={self.env.now:.2f}] OrderArrivalService initialized "
            f"with mean inter-arrival time: {config.mean_order_inter_arrival_time} minutes, "
            f"curation policy: {type(self.curation_policy).__name__}"
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
            restaurant_location, curation_result = self._select_restaurant_location(customer_location)

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
                curation_result=curation_result
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
        Select a restaurant location for a new order via the active curation policy.

        Returns:
            tuple: (location, curation_result)
                   curation_result is None (uniform), 'curated', or 'fallback'.
        """
        selected_restaurant, curation_result = self.curation_policy.select(customer_location)

        self.logger.debug(
            f"[t={self.env.now:.2f}] Selected restaurant "
            f"{selected_restaurant.restaurant_id} "
            f"at {format_location(selected_restaurant.location)} "
            f"(curation={curation_result})"
        )
        return selected_restaurant.location, curation_result

    def _generate_customer_location(self):
        """Generate a customer location for a new order."""
        area_size = self.config.delivery_area_size
        location = self.location_stream.uniform(0, area_size, size=2).tolist()
        return location