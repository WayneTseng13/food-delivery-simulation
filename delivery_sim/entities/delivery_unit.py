from delivery_sim.entities.states import DeliveryUnitState
from delivery_sim.events.delivery_unit_events import DeliveryUnitStateChangedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType

class DeliveryUnit:
    """
    Represents the assignment contract between a driver and a delivery entity.
    
    DeliveryUnit captures the relationship created when a driver is assigned
    to deliver either a single order or a pair of orders, including the 
    priority scoring rationale behind the assignment decision.
    """
    
    def __init__(self, delivery_entity, driver, assignment_time):
        """
        Initialize a new delivery unit.
        
        Args:
            delivery_entity: The Order or Pair being delivered
            driver: The Driver performing the delivery
            assignment_time: When this assignment was made
        """
        # Get a logger instance
        self.logger = get_logger("entities.delivery_unit")
        
        # Core relationships
        self.delivery_entity = delivery_entity
        self.entity_type = EntityType.DELIVERY_UNIT
        self.driver = driver
        
        # Generate ID based on delivery_entity's entity type
        # For consistency: DU-{entity_id}-{driver_id}
        entity_type = delivery_entity.entity_type
        if entity_type == EntityType.PAIR:
            # It's a pair: DU-P-O1_O2-D1
            self.unit_id = f"DU-{delivery_entity.pair_id}-{driver.driver_id}"
        else:  # Must be ORDER
            # It's a single order: DU-O1-D1
            self.unit_id = f"DU-{delivery_entity.order_id}-{driver.driver_id}"
        
        # State and timing
        self.state = DeliveryUnitState.IN_PROGRESS
        self.assignment_time = assignment_time
        self.completion_time = None
        
        # Assignment decision information (priority scoring system)
        self.assignment_scores = {
            "distance_score": None,        # Distance efficiency score (0-1)
            "throughput_score": None,      # Throughput optimization score (0-1) 
            "fairness_score": None,        # Fairness/wait time score (0-1)
            "combined_score_0_1": None,    # Weighted combination (0-1)
            "priority_score_0_100": None,  # Final score (0-100)
            "total_distance": None,        # Actual distance in km
            "num_orders": None,            # Number of orders in this delivery
            "assignment_delay_minutes": None      # Wait time for this assignment
        }

        # Binding delivery sequence for pair units. Written by AssignmentService
        # using evaluate_complete (driver position known at that point).
        # Stays None for single-order delivery units.
        self.chosen_sequence = None
        self.chosen_route_cost = None
        
        # Log creation
        self.logger.debug(f"DeliveryUnit {self.unit_id} created at time {assignment_time}")
    
    def can_transition_to(self, new_state):
        """
        Check if this delivery unit can transition to the specified state.
        
        Args:
            new_state: The state to check transition to
            
        Returns:
            bool: True if transition is valid, False otherwise
        """
        valid_transitions = {
            DeliveryUnitState.IN_PROGRESS: [DeliveryUnitState.COMPLETED],
            DeliveryUnitState.COMPLETED: []  # Explicitly terminal
        }
        
        return new_state in valid_transitions.get(self.state, [])
    
    def transition_to(self, new_state, event_dispatcher=None, env=None):
        """
        Change the delivery unit's state with validation.
        
        Args:
            new_state: The new state to transition to
            event_dispatcher: Optional event dispatcher for events
            env: SimPy environment for current time
            
        Returns:
            bool: True if transition succeeded, False otherwise
            
        Raises:
            ValueError: If transition is invalid
        """
        # Validate transition
        if not self.can_transition_to(new_state):
            # Log validation failure - with or without timestamp
            if env:
                self.logger.validation(f"[t={env.now:.2f}] Cannot transition delivery unit {self.unit_id} from {self.state} to {new_state}")
            else:
                self.logger.validation(f"Cannot transition delivery unit {self.unit_id} from {self.state} to {new_state}")
                
            # Also raise exception to prevent invalid state
            raise ValueError(f"Cannot transition delivery unit {self.unit_id} from {self.state} to {new_state}")
        
        # Store old state for event
        old_state = self.state
        
        # Update state and timing information
        self.state = new_state
        
        if new_state == DeliveryUnitState.COMPLETED:
            self.completion_time = env.now if env else None
            if env:
                self.logger.debug(f"[t={env.now:.2f}] Set completion_time for delivery unit {self.unit_id}")
        
        # Log the state transition
        if env:
            self.logger.info(f"[t={env.now:.2f}] DeliveryUnit {self.unit_id} transitioned from {old_state} to {new_state}")
        else:
            self.logger.info(f"DeliveryUnit {self.unit_id} transitioned from {old_state} to {new_state}")
        
        # Dispatch event if dispatcher provided
        if event_dispatcher and env:
            # Log event dispatch at SIMULATION_EVENT level
            self.logger.simulation_event(f"[t={env.now:.2f}] Dispatching DeliveryUnitStateChangedEvent for unit {self.unit_id}: {old_state} -> {new_state}")
            
            event_dispatcher.dispatch(DeliveryUnitStateChangedEvent(
                timestamp=env.now,
                delivery_unit_id=self.unit_id,
                old_state=old_state,
                new_state=new_state
            ))
        
        return True