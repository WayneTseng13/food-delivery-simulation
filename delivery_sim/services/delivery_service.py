from delivery_sim.entities.states import OrderState, PairState, DriverState, DeliveryUnitState
from delivery_sim.events.delivery_unit_events import DeliveryUnitCompletedEvent, DeliveryUnitAssignedEvent
from delivery_sim.utils.location_utils import calculate_distance, locations_are_equal
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType
from delivery_sim.utils.location_utils import format_location

class DeliveryService:
    """
    Service responsible for executing delivery processes once assignments are made.
    
    This service manages the physical delivery process from start to finish,
    including driver movement, restaurant pickups, and customer deliveries.
    It handles both single orders and pairs with clear tracking of completion status.
    """
    
    def __init__(self, env, event_dispatcher, driver_repository, order_repository, 
                pair_repository, delivery_unit_repository, restaurant_repository, config):
        """
        Initialize the delivery service with its dependencies.
        
        Args:
            env: SimPy environment
            event_dispatcher: Central event dispatcher
            driver_repository: Repository for accessing drivers
            order_repository: Repository for accessing orders
            pair_repository: Repository for accessing pairs
            delivery_unit_repository: Repository for accessing delivery units
            restaurant_repository: Repository for accessing restaurants
            config: Configuration containing delivery parameters
        """
        # Get a logger instance specific to this component
        self.logger = get_logger("services.delivery")
        
        # Store dependencies
        self.env = env
        self.event_dispatcher = event_dispatcher
        self.driver_repository = driver_repository
        self.order_repository = order_repository
        self.pair_repository = pair_repository
        self.delivery_unit_repository = delivery_unit_repository
        self.restaurant_repository = restaurant_repository
        self.config = config
        
        # Log service initialization with configuration details
        self.logger.info(f"[t={self.env.now:.2f}] DeliveryService initialized with driver_speed={config.driver_speed} km/min")
        
        # Register for assignment events
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for DeliveryUnitAssignedEvent")
        event_dispatcher.register(DeliveryUnitAssignedEvent, self.handle_delivery_assigned)
    
    # === Event Handlers (Entry Points) ===
    
    def handle_delivery_assigned(self, event):
        """
        Handler for DeliveryUnitAssignedEvent.
        
        Validates all entities needed for delivery and delegates to the appropriate
        operation if validation succeeds.
        
        Args:
            event: The DeliveryUnitAssignedEvent
        """
        # Log event handling
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling DeliveryUnitAssignedEvent for unit {event.delivery_unit_id}")
        
        # Extract identifiers from event
        delivery_unit_id = event.delivery_unit_id
        entity_type = event.entity_type  # "order" or "pair"
        entity_id = event.entity_id
        driver_id = event.driver_id
        
        # Validate delivery unit
        delivery_unit = self.delivery_unit_repository.find_by_id(delivery_unit_id)
        if not delivery_unit:
            self.logger.validation(f"[t={self.env.now:.2f}] DeliveryUnit {delivery_unit_id} not found, cannot start delivery")
            return
        
        # Validate driver
        driver = self.driver_repository.find_by_id(driver_id)
        if not driver:
            self.logger.validation(f"[t={self.env.now:.2f}] Driver {driver_id} not found, cannot start delivery")
            return
        
        # Validate delivery entity (order or pair)
        if entity_type == EntityType.ORDER:
            entity = self.order_repository.find_by_id(entity_id)
            if not entity:
                self.logger.validation(f"[t={self.env.now:.2f}] Order {entity_id} not found, cannot start delivery")
                return
        else:  # entity_type == EntityType.PAIR
            entity = self.pair_repository.find_by_id(entity_id)
            if not entity:
                self.logger.validation(f"[t={self.env.now:.2f}] Pair {entity_id} not found, cannot start delivery")
                return
        
        # Pass fully validated entities to operation
        self.start_delivery(driver, entity, delivery_unit)
    
    # === Operations (Business Logic) ===
    
    def start_delivery(self, driver, entity, delivery_unit):
        """
        Start the delivery process for a validated assignment.
        
        This operation focuses purely on business logic, assuming all entities
        have been validated by the calling handler.
        
        Args:
            driver: The validated Driver object
            entity: The validated Order or Pair object
            delivery_unit: The validated DeliveryUnit object
            
        Returns:
            bool: True if delivery started successfully
        """
        # Determine entity type and start appropriate process
        entity_type = entity.entity_type
        
        if entity_type == EntityType.ORDER:
            # Start the single order delivery process
            self.logger.info(f"[t={self.env.now:.2f}] Starting single order delivery process for order {entity.order_id} by driver {driver.driver_id}")
            self.env.process(self._single_order_delivery_process(driver, entity, delivery_unit))
        else:  # Must be PAIR
            # Start the pair delivery process
            self.logger.info(f"[t={self.env.now:.2f}] Starting paired delivery process for pair {entity.pair_id} by driver {driver.driver_id}")
            self.env.process(self._pair_delivery_process(driver, entity, delivery_unit))
        
        return True
    
    # === SimPy Processes ===

    def _single_order_delivery_process(self, driver, order, delivery_unit):
        """
        SimPy process for delivering a single order.
        
        This process manages:
        1. Travel to restaurant
        2. Pickup at restaurant
        3. Travel to customer
        4. Delivery to customer
        5. Completion of delivery unit
        
        Args:
            driver: The driver performing the delivery
            order: The order being delivered
            delivery_unit: The delivery unit being fulfilled
        """
        
        # Get current location
        current_location = driver.location
        
        # Step 1: Travel to restaurant
        travel_time = self._calculate_travel_time(current_location, order.restaurant_location)
        restaurant_location_formatted = format_location(order.restaurant_location)
        self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver.driver_id} traveling to restaurant at {restaurant_location_formatted} for order {order.order_id}, ETA: {self.env.now + travel_time:.2f}")
        yield self.env.timeout(travel_time)
        
        # Process pickup
        previous_location = current_location
        current_location = order.restaurant_location
        driver.update_location(current_location)
        
        # Update order state and log with restaurant ID
        order.transition_to(OrderState.PICKED_UP, self.event_dispatcher, self.env)
        
        # Find restaurant ID for enhanced logging
        restaurant = self._find_restaurant_by_location(order.restaurant_location)
        restaurant_info = f"restaurant {restaurant.restaurant_id}" if restaurant else "restaurant"
        
        self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} picked up Order {order.order_id} from {restaurant_info}")
        
        # Step 2: Travel to customer
        travel_time = self._calculate_travel_time(current_location, order.customer_location)
        customer_location_formatted = format_location(order.customer_location)
        self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver.driver_id} traveling to customer at {customer_location_formatted} for order {order.order_id}, ETA: {self.env.now + travel_time:.2f}")
        yield self.env.timeout(travel_time)
        
        # Process delivery
        previous_location = current_location
        current_location = order.customer_location
        driver.update_location(current_location)
        
        # Update order state and log without redundant timestamp
        order.transition_to(OrderState.DELIVERED, self.event_dispatcher, self.env)
        self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} delivered Order {order.order_id} to customer")
        
        # Complete delivery unit
        self._complete_delivery_unit(driver, delivery_unit)
    
    def _pair_delivery_process(self, driver, pair, delivery_unit):
        """
        SimPy process for delivering a pair of orders.
        
        This process follows the optimal sequence determined during pair formation
        and properly handles pickups and deliveries at each stop.
        
        Args:
            driver: The driver performing the delivery
            pair: The pair being delivered
            delivery_unit: The delivery unit being fulfilled
        """
        # Get current location
        current_location = driver.location
        
        # Log the delivery sequence
        sequence_description = self._generate_sequence_description(delivery_unit.chosen_sequence)
        self.logger.debug(f"[t={self.env.now:.2f}] Following delivery sequence for pair {pair.pair_id}: {sequence_description}")
        
        # Follow the optimal sequence determined during pair formation
        for i, stop in enumerate(delivery_unit.chosen_sequence):
            # Travel to the next stop
            travel_time = self._calculate_travel_time(current_location, stop)
            next_stop_index = i + 1
            self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver.driver_id} traveling to stop {i+1}/{len(delivery_unit.chosen_sequence)} " 
                              f"for pair {pair.pair_id}, ETA: {self.env.now + travel_time:.2f}")
            yield self.env.timeout(travel_time)
            
            # Update driver location
            previous_location = current_location
            current_location = stop
            driver.update_location(current_location)
            
            # Determine what action to take at this location
            self._process_pair_stop(driver, pair, stop)
        
        # Complete delivery unit
        self._complete_delivery_unit(driver, delivery_unit)
    
    def _process_pair_stop(self, driver, pair, location):
        """
        Process a stop in a pair delivery sequence.
        
        Determines if this is a restaurant or customer location and handles
        the appropriate pickup or delivery action.
        
        Args:
            driver: The driver making the stop
            pair: The pair being delivered
            location: The current stop location
        """      
        # Format location for logging (2 decimal places by default)
        formatted_location = format_location(location)
        self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver.driver_id} arrived at location {formatted_location} for pair {pair.pair_id}")
        
        # Check if this is a restaurant location
        for order in [pair.order1, pair.order2]:
            if locations_are_equal(location, order.restaurant_location):
                # Update order state
                order.transition_to(OrderState.PICKED_UP, self.event_dispatcher, self.env)
                
                # Track pickup in pair
                pair.record_order_pickup(order.order_id)
                
                # Find restaurant ID for enhanced logging
                restaurant = self._find_restaurant_by_location(order.restaurant_location)
                restaurant_info = f"restaurant {restaurant.restaurant_id}" if restaurant else "restaurant"
                
                # Log pickup with restaurant ID, no redundant timestamp
                self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} picked up Order {order.order_id} (of Pair {pair.pair_id}) from {restaurant_info}")
        
        # Check if this is a customer location
        for order in [pair.order1, pair.order2]:
            if locations_are_equal(location, order.customer_location):
                # Update order state
                order.transition_to(OrderState.DELIVERED, self.event_dispatcher, self.env)
                
                # Track delivery in pair
                is_complete = pair.record_order_delivery(order.order_id)
                
                # Log delivery without redundant timestamp
                self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} delivered Order {order.order_id} (of Pair {pair.pair_id}) to customer")
                
                if is_complete:
                    pair.transition_to(PairState.COMPLETED, self.event_dispatcher, self.env)
                    self.logger.info(f"[t={self.env.now:.2f}] All orders in Pair {pair.pair_id} have been delivered")
    
    def _complete_delivery_unit(self, driver, delivery_unit):
        """
        Mark a delivery unit as completed.
        
        Updates delivery unit state, driver state, and dispatches completion event.
        This is a critical method that signals to the rest of the system that
        the driver is now available for new assignments.
        
        Args:
            driver: The driver who completed the delivery
            delivery_unit: The delivery unit to complete
        """
        # Update delivery unit state
        self.logger.info(f"[t={self.env.now:.2f}] Completing delivery unit {delivery_unit.unit_id}")
        delivery_unit.transition_to(DeliveryUnitState.COMPLETED, self.event_dispatcher, self.env)
        
        # Clear the current delivery reference (this line is missing)
        driver.current_delivery = None

        # Add to driver's completed deliveries
        driver.completed_deliveries.append(delivery_unit)
        
        # Update driver state to available
        driver.transition_to(DriverState.AVAILABLE, self.event_dispatcher, self.env)
        
        # Dispatch completion event - this is the main event other services listen for
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DeliveryUnitCompletedEvent for unit {delivery_unit.unit_id}")
        self.event_dispatcher.dispatch(DeliveryUnitCompletedEvent(
            timestamp=self.env.now,
            delivery_unit_id=delivery_unit.unit_id,
            driver_id=driver.driver_id
        ))
    
    # === Utility Methods ===
    
    def _calculate_travel_time(self, origin, destination):
        """
        Calculate travel time between two locations.
        
        Args:
            origin: Starting location [x, y]
            destination: Ending location [x, y]
            
        Returns:
            float: Time in minutes to travel between locations
        """
        distance = calculate_distance(origin, destination)
        # Use speed from config or default value
        speed = getattr(self.config, 'driver_speed', 0.5)  # km per minute
        travel_time = distance / speed
        self.logger.debug(f"[t={self.env.now:.2f}] Calculated travel time: {travel_time:.2f} min for distance: {distance:.2f} km at speed: {speed} km/min")
        return travel_time
    
    def _generate_sequence_description(self, sequence):
        """
        Generate a human-readable description of a delivery sequence.
        
        Args:
            sequence: List of location coordinates
            
        Returns:
            str: Description of the sequence
        """
        return " -> ".join([f"[{loc[0]:.2f}, {loc[1]:.2f}]" for loc in sequence])
    
    def _find_restaurant_by_location(self, location):
        """
        Helper method to find restaurant by location for enhanced logging.
        
        Args:
            location: [x, y] coordinates of the restaurant location
            
        Returns:
            Restaurant: The restaurant at this location, or None if not found
        """
        return self.restaurant_repository.find_by_location(location)    