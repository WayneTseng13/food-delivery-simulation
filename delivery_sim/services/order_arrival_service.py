from delivery_sim.entities.order import Order
from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.location_utils import format_location
from delivery_sim.utils.customer_choice_model import CustomerChoiceModel


class OrderArrivalService:
    """
    Service responsible for generating new orders entering the system.

    This service runs as a continuous SimPy process, creating new orders
    based on configured inter-arrival times and dispatching events when
    orders are created.

    Restaurant selection is delegated to a CustomerChoiceModel: every arrival,
    the customer picks a restaurant by softmax over -beta*distance (+ boost b on
    the one restaurant the curation policy slotted, if any). This one draw
    replaces both the old uniform pick (Policy U) and the old
    compliance-coin-plus-uniform-fallback (curated). There is no exogenous
    compliance probability; compliance is endogenous -- the realized chance the
    customer lands on the slotted restaurant.
    """

    def __init__(self, env, event_dispatcher, order_repository,
                    restaurant_repository, driver_repository, config, id_generator,
                    operational_rng_manager, curation_policy=None):

            """Initialize the order arrival service."""
            self.logger = get_logger("services.order_arrival")

            # Store dependencies
            self.env = env
            self.event_dispatcher = event_dispatcher
            self.order_repository = order_repository
            self.restaurant_repository = restaurant_repository
            self.driver_repository = driver_repository
            self.config = config
            self.id_generator = id_generator

            # Get all random streams at initialization time. The customer's
            # restaurant choice is drawn on restaurant_selection; there is no
            # separate compliance stream anymore (the choice is one softmax draw).
            self.arrival_stream = operational_rng_manager.get_stream('order_arrivals')
            self.location_stream = operational_rng_manager.get_stream('customer_locations')
            self.restaurant_selection_stream = operational_rng_manager.get_stream('restaurant_selection')

            # Curation policy (may be None — Policy U, no restaurant is slotted and
            # the customer chooses by distance alone).
            self.curation_policy = curation_policy

            # Customer choice model. beta = proximity sensitivity, b = boost applied
            # to the slotted restaurant. The model draws on restaurant_selection.
            self.choice_model = CustomerChoiceModel(
                beta=config.customer_distance_sensitivity,
                b=config.recommendation_boost,
                selection_stream=self.restaurant_selection_stream,
            )

            # Under Policy U nothing is ever slotted, so the boost is inert whatever
            # its value. Warn if a nonzero boost is configured but can never apply.
            if self.curation_policy is None and config.recommendation_boost != 0.0:
                self.logger.warning(
                    f"recommendation_boost={config.recommendation_boost} is set but "
                    f"curation_policy is None — the boost has no effect (no "
                    f"restaurant is slotted for the customer to be steered toward)."
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
                f"distance sensitivity beta={config.customer_distance_sensitivity}, "
                f"recommendation boost b={config.recommendation_boost}"
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
                        arrival_state=arrival_state,
                        origin_restaurant_id=origin_restaurant_id,
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
        Determine the restaurant a customer ends up ordering from, under the
        customer choice model and the active curation policy.

        Flow (one softmax draw for every policy):
        - Policy U (curation_policy is None): nothing is slotted (boost_id=None).
            The customer chooses by -beta*distance alone. curation_result and
            featuring_penalty are None; compliance is not applicable.
        - Any curation policy: the policy names the restaurant to slot (boost_id).
            The customer chooses by -beta*distance + b on the slotted restaurant.
            customer_complied records whether the draw landed on the slot -- this
            is the endogenous, distance-dependent compliance that replaced the old
            constant p.

        Returns:
            tuple: (location, curation_result, customer_complied,
                    featuring_penalty, origin_restaurant_id)
                curation_result:
                    None                          -- Policy U (no curation)
                    'operational_immediate' /
                    'operational_queued'          -- R_op slotted
                    'featured_immediate' /
                    'featured_queued'             -- R_F slotted
                customer_complied:
                    None   -- no restaurant slotted (U)
                    True   -- the customer's choice landed on the slotted restaurant
                    False  -- the customer chose a different restaurant
                featuring_penalty:
                    None   -- U, or operational mode (no featuring decision)
                    float  -- featuring penalty (>= 0), stamped whether or not the
                              customer took R_F
                origin_restaurant_id:
                    the restaurant the customer actually ordered from.
        """
        restaurants = self.restaurant_repository.find_all()

        # Decide which restaurant, if any, carries the boost.
        if self.curation_policy is None:
            boost_id = None
            curation_result = None
            featuring_penalty = None
        else:
            recommendation, curation_result, featuring_penalty = \
                self.curation_policy.select(customer_location)
            assert recommendation is not None, (
                f"{type(self.curation_policy).__name__} returned no recommendation. "
                f"Every curation policy in this module must always slot a "
                f"restaurant; the no-slot path belongs to Policy U "
                f"(curation_policy is None).")
            boost_id = recommendation.restaurant_id

        # One softmax draw resolves the customer's choice for every policy.
        selected = self.choice_model.select(customer_location, restaurants, boost_id)

        # Endogenous compliance: did the customer land on the slotted restaurant?
        if boost_id is None:
            customer_complied = None
        else:
            customer_complied = (selected.restaurant_id == boost_id)

        self.logger.debug(
            f"[t={self.env.now:.2f}] Customer chose restaurant "
            f"{selected.restaurant_id} "
            f"(slotted={boost_id}, complied={customer_complied}, "
            f"curation_result={curation_result})")

        return (selected.location, curation_result, customer_complied,
            featuring_penalty, selected.restaurant_id)

    def _generate_customer_location(self):
        """Generate a customer location for a new order."""
        area_size = self.config.delivery_area_size
        location = self.location_stream.uniform(0, area_size, size=2).tolist()
        return location