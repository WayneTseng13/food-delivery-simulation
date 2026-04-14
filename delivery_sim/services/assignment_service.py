# delivery_sim/services/assignment_service.py
"""
Assignment Service - Pure Event-Driven Driver-Entity Assignment

This service implements a pure event-driven assignment approach that responds
immediately to system events without artificial delays or batch optimization.

Key characteristics:
1. Responds to driver availability events (login, delivery completion)
2. Responds to delivery entity availability events (order creation, pair formation/failure)
3. Always assigns the best available match using priority scoring
4. No thresholds or delays - pure responsiveness optimization

The priority scoring system balances multiple objectives:
- Distance efficiency (infrastructure-aware geographical optimization)
- Throughput optimization (orders per trip maximization)
- Fairness considerations (wait time-based priority)
"""

from delivery_sim.entities.states import OrderState, DriverState, PairState
from delivery_sim.entities.delivery_unit import DeliveryUnit
from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.events.pair_events import PairCreatedEvent, PairingFailedEvent
from delivery_sim.events.driver_events import DriverAvailableForAssignmentEvent
from delivery_sim.events.delivery_unit_events import DeliveryUnitAssignedEvent
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType


class AssignmentService:
    """
    Pure event-driven assignment service for food delivery systems.
    
    This service responds immediately to two types of events:
    1. Driver becomes available → Find best waiting entity to assign
    2. Delivery entity becomes available → Find best available driver to assign
    
    Assignment decisions use multi-criteria priority scoring that balances:
    - Distance efficiency (geographical optimization)
    - Throughput optimization (capacity utilization)
    - Fairness considerations (service equity)
    """
    
    def __init__(self, env, event_dispatcher, order_repository, driver_repository, 
                 pair_repository, delivery_unit_repository, priority_scorer, config):
        """
        Initialize the pure event-driven assignment service.
        
        Args:
            env: SimPy environment
            event_dispatcher: Central event dispatcher
            order_repository: Repository for orders
            driver_repository: Repository for drivers
            pair_repository: Repository for pairs
            delivery_unit_repository: Repository for delivery units
            priority_scorer: PriorityScorer instance for assignment evaluation
            config: Configuration object containing priority scoring weights
        """
        # Get a logger instance specific to this component
        self.logger = get_logger("services.assignment")
        
        # Store dependencies
        self.env = env
        self.event_dispatcher = event_dispatcher
        self.order_repository = order_repository
        self.driver_repository = driver_repository
        self.pair_repository = pair_repository
        self.delivery_unit_repository = delivery_unit_repository
        self.priority_scorer = priority_scorer
        self.config = config
        
        # Log service initialization
        self.logger.info(f"[t={self.env.now:.2f}] Pure event-driven AssignmentService initialized")
        self.logger.info(f"[t={self.env.now:.2f}] Priority scoring weights: "
                        f"distance={config.weight_distance:.3f}, "
                        f"throughput={config.weight_throughput:.3f}, "
                        f"fairness={config.weight_fairness:.3f}")
        
        # Register event handlers based on pairing configuration
        if config.pairing_enabled:
            # In pair mode, listen for pairing outcomes
            self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for PairCreatedEvent")
            event_dispatcher.register(PairCreatedEvent, self.handle_pair_created)
            
            self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for PairingFailedEvent")
            event_dispatcher.register(PairingFailedEvent, self.handle_pairing_failed)
        else:
            # In single mode, orders directly go to assignment
            self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for OrderCreatedEvent")
            event_dispatcher.register(OrderCreatedEvent, self.handle_order_created)
        
        # Register DriverAvailableForAssignmentEvent
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for DriverAvailableForAssignmentEvent")
        event_dispatcher.register(DriverAvailableForAssignmentEvent, self.handle_driver_available_for_assignment)
        
        self.logger.info(f"[t={self.env.now:.2f}] Event-driven assignment service ready - listening for assignment events")
    
    # ===== Event Handlers (Entry Points) =====
    
    def handle_order_created(self, event):
        """
        Handler for OrderCreatedEvent in single mode.
        
        Args:
            event: OrderCreatedEvent containing order_id
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling OrderCreatedEvent for order {event.order_id}")
        
        # Get the order from repository
        order = self.order_repository.find_by_id(event.order_id)
        if order is None:
            self.logger.error(f"[t={self.env.now:.2f}] Order {event.order_id} not found in repository")
            return
        
        # Attempt event-driven assignment
        self.attempt_event_driven_assignment_from_delivery_entity(order)
    
    def handle_pair_created(self, event):
        """
        Handler for PairCreatedEvent in pairing mode.
        
        Args:
            event: PairCreatedEvent containing pair_id
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling PairCreatedEvent for pair {event.pair_id}")
        
        # Get the pair from repository
        pair = self.pair_repository.find_by_id(event.pair_id)
        if pair is None:
            self.logger.error(f"[t={self.env.now:.2f}] Pair {event.pair_id} not found in repository")
            return
        
        # Attempt event-driven assignment
        self.attempt_event_driven_assignment_from_delivery_entity(pair)
    
    def handle_pairing_failed(self, event):
        """
        Handler for PairingFailedEvent - order failed to pair and needs assignment.
        
        Args:
            event: PairingFailedEvent containing order_id
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling PairingFailedEvent for order {event.order_id}")
        
        # Get the order from repository
        order = self.order_repository.find_by_id(event.order_id)
        if order is None:
            self.logger.error(f"[t={self.env.now:.2f}] Order {event.order_id} not found in repository")
            return
        
        # Attempt event-driven assignment
        self.attempt_event_driven_assignment_from_delivery_entity(order)
    
    def handle_driver_available_for_assignment(self, event):
        """
        Handler for DriverAvailableForAssignmentEvent - driver completed delivery and ready for new work.
        
        Args:
            event: DriverAvailableForAssignmentEvent containing driver_id
        """
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling DriverAvailableForAssignmentEvent for driver {event.driver_id}")
        
        # Get the driver from repository
        driver = self.driver_repository.find_by_id(event.driver_id)
        if driver is None:
            self.logger.error(f"[t={self.env.now:.2f}] Driver {event.driver_id} not found in repository")
            return
        
        # Attempt event-driven assignment
        self.attempt_event_driven_assignment_from_driver(driver)
    
    # ===== Core Assignment Logic =====
    
    def attempt_event_driven_assignment_from_driver(self, driver):
        """
        Event-driven assignment when driver becomes available.
        Always assigns to the best available entity using priority scoring.
        
        Args:
            driver: The driver to find work for
            
        Returns:
            bool: True if assignment succeeded, False otherwise
        """
        self.logger.info(f"[t={self.env.now:.2f}] Attempting event-driven assignment for driver {driver.driver_id}")
        
        # Business logic: Collect all available delivery entities
        waiting_entities = []
        waiting_entities.extend(self.order_repository.find_by_state(OrderState.CREATED))
        waiting_entities.extend(self.pair_repository.find_by_state(PairState.CREATED))
        
        if not waiting_entities:
            # Business outcome: No entities available for assignment
            self.logger.info(f"[t={self.env.now:.2f}] No waiting entities for driver {driver.driver_id}")
            return False
        
        self.logger.debug(f"[t={self.env.now:.2f}] Found {len(waiting_entities)} waiting entities for driver {driver.driver_id}")
        
        # Find best entity for this driver using unified matching logic
        best_entity, priority_score, score_components = self._find_best_match(driver, waiting_entities)
        
        entity_type = best_entity.entity_type
        entity_id = best_entity.order_id if entity_type == EntityType.ORDER else best_entity.pair_id
        
        self.logger.debug(f"[t={self.env.now:.2f}] Best match for driver {driver.driver_id}: "
                        f"{entity_type} {entity_id} with priority score {priority_score:.2f}")
        
        # Always assign the best match - no threshold checking
        self.logger.info(f"[t={self.env.now:.2f}] Event-driven assignment: driver {driver.driver_id} to {entity_type} {entity_id} "
                       f"with priority score {priority_score:.2f}")
        
        self._create_assignment(driver, best_entity, score_components)
        return True
    
    def attempt_event_driven_assignment_from_delivery_entity(self, entity):
        """
        Event-driven assignment when delivery entity becomes available.
        Always assigns to the best available driver using priority scoring.
        
        Args:
            entity: The delivery entity (order or pair) needing assignment
            
        Returns:
            bool: True if assignment succeeded, False otherwise
        """
        entity_type = entity.entity_type
        entity_id = entity.order_id if entity_type == EntityType.ORDER else entity.pair_id
        
        self.logger.info(f"[t={self.env.now:.2f}] Attempting event-driven assignment for {entity_type} {entity_id}")
        
        # Business logic: Find all available drivers
        available_drivers = self.driver_repository.find_available_drivers()
        
        if not available_drivers:
            # Business outcome: No drivers available for assignment
            self.logger.info(f"[t={self.env.now:.2f}] No available drivers for {entity_type} {entity_id}")
            return False
        
        self.logger.debug(f"[t={self.env.now:.2f}] Found {len(available_drivers)} available drivers for {entity_type} {entity_id}")
        
        # Find best driver for this entity using unified matching logic
        best_driver, priority_score, score_components = self._find_best_match(entity, available_drivers)
        
        self.logger.debug(f"[t={self.env.now:.2f}] Best match for {entity_type} {entity_id}: "
                        f"driver {best_driver.driver_id} with priority score {priority_score:.2f}")
        
        # Always assign to best driver - no threshold checking
        self.logger.info(f"[t={self.env.now:.2f}] Event-driven assignment: {entity_type} {entity_id} to driver {best_driver.driver_id} "
                       f"with priority score {priority_score:.2f}")
        
        self._create_assignment(best_driver, entity, score_components)
        return True
    
    # ===== Helper Methods =====
    
    def _find_best_match(self, fixed_entity, candidates):
        """
        Find the best matching entity from a list of candidates.
        
        Args:
            fixed_entity: Either a driver or delivery entity we're finding a match for
            candidates: List of potential matches (drivers or delivery entities)
        
        Returns:
            tuple: (best_match, best_score, best_components) or (None, 0.0, None) if no candidates
        """
        best_match = None
        best_priority_score = -1  # Sentinel value, below any possible real score
        best_components = None
        
        # Determine entity type for role assignment
        fixed_entity_type = fixed_entity.entity_type
        is_driver = fixed_entity_type == EntityType.DRIVER
        
        for candidate in candidates:
            # Determine which is the driver and which is the entity
            if is_driver:
                driver = fixed_entity
                entity = candidate
            else:
                driver = candidate
                entity = fixed_entity
            
            # Calculate priority score
            priority_score, components = self.priority_scorer.calculate_priority_score(driver, entity)
            
            # Higher scores are better (opposite of cost minimization)
            if priority_score > best_priority_score:
                best_priority_score = priority_score
                best_match = candidate
                best_components = components
        
        return best_match, best_priority_score, best_components
    
    def _create_assignment(self, driver, entity, score_components):
        """
        Create a delivery unit and update entity states.
        
        Args:
            driver: The driver to assign
            entity: The order or pair to assign
            assignment_path: How this assignment was made ('event_driven')
            score_components: Dictionary with score calculation components
            
        Returns:
            DeliveryUnit: The created delivery unit
        """
        # Critical validation - ensure driver is still available
        if driver.state != DriverState.AVAILABLE:
            self.logger.validation(f"[t={self.env.now:.2f}] Critical error: Driver {driver.driver_id} not available when creating assignment")
            return None
        
        # Get entity type once
        entity_type = entity.entity_type
        entity_id = entity.order_id if entity_type == EntityType.ORDER else entity.pair_id
            
        # Create delivery unit
        self.logger.debug(f"[t={self.env.now:.2f}] Creating delivery unit for assignment of driver {driver.driver_id} to "
                        f"{entity_type} {entity_id}")
        
        delivery_unit = DeliveryUnit(entity, driver, self.env.now)
        
        # Record score components (replacing old cost storage)
        delivery_unit.assignment_scores = {
            "distance_score": score_components["distance_score"],
            "throughput_score": score_components["throughput_score"],
            "fairness_score": score_components["fairness_score"],
            "combined_score_0_1": score_components["combined_score_0_1"],
            "priority_score_0_100": score_components["combined_score_0_1"] * 100,
            "total_distance": score_components["total_distance"],
            "num_orders": score_components["num_orders"],
            "assignment_delay_minutes": score_components["assignment_delay_minutes"]
        }
        
        # Add to repository
        self.delivery_unit_repository.add(delivery_unit)
        
        # Update entity state based on type
        if entity_type == EntityType.ORDER:
            entity.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.delivery_unit = delivery_unit
            self.logger.debug(f"[t={self.env.now:.2f}] Updated order {entity.order_id} state to ASSIGNED")
        else:  # Must be PAIR
            entity.transition_to(PairState.ASSIGNED, self.event_dispatcher, self.env)
            entity.delivery_unit = delivery_unit
            # Also update constituent orders
            entity.order1.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.order1.delivery_unit = delivery_unit
            entity.order2.transition_to(OrderState.ASSIGNED, self.event_dispatcher, self.env)
            entity.order2.delivery_unit = delivery_unit
            self.logger.debug(f"[t={self.env.now:.2f}] Updated pair {entity.pair_id} state to ASSIGNED")
        
        # Update driver state
        driver.transition_to(DriverState.DELIVERING, self.event_dispatcher, self.env)
        driver.current_delivery_unit = delivery_unit
        self.logger.debug(f"[t={self.env.now:.2f}] Updated driver {driver.driver_id} state to DELIVERING")
        
        # Dispatch event
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DeliveryUnitAssignedEvent for unit {delivery_unit.unit_id}")
        self.event_dispatcher.dispatch(DeliveryUnitAssignedEvent(
            timestamp=self.env.now,
            delivery_unit_id=delivery_unit.unit_id,
            entity_type=entity_type,  
            entity_id=entity_id,
            driver_id=driver.driver_id
        ))
        
        # Log assignment completion
        self.logger.info(f"[t={self.env.now:.2f}] Created assignment: "
                       f"Driver {driver.driver_id} assigned to {entity_type} {entity_id} "
                       f"(priority score: {delivery_unit.assignment_scores['priority_score_0_100']:.2f}, "
                       f"distance: {score_components['total_distance']:.2f}km)")
        
        return delivery_unit