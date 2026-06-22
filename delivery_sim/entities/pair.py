from delivery_sim.entities.states import PairState
from delivery_sim.events.pair_events import PairStateChangedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType

class Pair:
    """
    Represents a pair of orders that will be delivered together.
    
    A pair maintains references to its constituent orders and manages
    the coordinated delivery of both orders.
    """
    
    def __init__(self, order1, order2, creation_time):
        """Initialize a new pair from two orders."""
        # Get a logger instance
        self.logger = get_logger("entities.pair")
        
        # Core identification
        # Updated format: P-O1_O2 (using underscore to separate order IDs)
        self.pair_id = f"P-{order1.order_id}_{order2.order_id}"
        self.entity_type = EntityType.PAIR
        self.order1 = order1
        self.order2 = order2
        
        # Timing information
        self.creation_time = creation_time
        self.assignment_time = None
        self.completion_time = None
        
        # State tracking
        self.state = PairState.CREATED
        # Partial-info routing hint computed at pairing time.
        # Not used for any operational decision — the binding sequence lives on
        # DeliveryUnit and is determined at assignment with driver position known.
        # Kept for optional post-hoc diagnostic (partial vs complete sequence divergence).
        self.partial_info_sequence = None
        self.partial_info_cost = None
        
        # Delivery planning
        self.optimal_sequence = None  # List of locations in optimal visiting order
        self.optimal_cost = None      # Total travel distance for optimal sequence
        
        # Relationship tracking
        self.delivery_unit = None
        
        # Log creation
        self.logger.debug(f"Pair {self.pair_id} created at time {creation_time}")
    
    def can_transition_to(self, new_state):
        """Check if this pair can transition to the specified state."""
        valid_transitions = {
            PairState.CREATED: [PairState.ASSIGNED],
            PairState.ASSIGNED: [PairState.COMPLETED],
            PairState.COMPLETED: []  # Explicitly terminal
        }
        
        # Special case for COMPLETED - requires both orders to be delivered
        if new_state == PairState.COMPLETED:
            return (self.state == PairState.ASSIGNED and 
                   len(self.delivered_orders) == 2)
        
        # Standard transition check
        return new_state in valid_transitions.get(self.state, [])
    
    def transition_to(self, new_state, event_dispatcher=None, env=None):
        """Change the pair's state with validation."""
        # Validate transition
        if not self.can_transition_to(new_state):
            # Log validation failure - with or without timestamp
            if env:
                self.logger.validation(f"[t={env.now:.2f}] Cannot transition pair {self.pair_id} from {self.state} to {new_state}")
            else:
                self.logger.validation(f"Cannot transition pair {self.pair_id} from {self.state} to {new_state}")
                
            # Also raise exception to prevent invalid state
            raise ValueError(f"Cannot transition pair {self.pair_id} from {self.state} to {new_state}")
        
        # Store old state for event
        old_state = self.state
        
        # Update state and timing information
        self.state = new_state
        
        if new_state == PairState.ASSIGNED:
            self.assignment_time = env.now if env else None
            if env:
                self.logger.debug(f"[t={env.now:.2f}] Set assignment_time for pair {self.pair_id}")
                
        elif new_state == PairState.COMPLETED:
            self.completion_time = env.now if env else None
            if env:
                self.logger.debug(f"[t={env.now:.2f}] Set completion_time for pair {self.pair_id}")
        
        # Log the state transition
        if env:
            self.logger.info(f"[t={env.now:.2f}] Pair {self.pair_id} transitioned from {old_state} to {new_state}")
        else:
            self.logger.info(f"Pair {self.pair_id} transitioned from {old_state} to {new_state}")
        
        # Dispatch event if dispatcher provided
        if event_dispatcher and env:
            # Log event dispatch at SIMULATION_EVENT level
            self.logger.simulation_event(f"[t={env.now:.2f}] Dispatching PairStateChangedEvent for pair {self.pair_id}: {old_state} -> {new_state}")
            
            event_dispatcher.dispatch(PairStateChangedEvent(
                timestamp=env.now,
                pair_id=self.pair_id,
                old_state=old_state,
                new_state=new_state
            ))
        
        return True
    
    def record_order_pickup(self, order_id):
        """Record that an order in this pair has been picked up."""
        if order_id not in [self.order1.order_id, self.order2.order_id]:
            self.logger.validation(f"Cannot record pickup for order {order_id}: not part of pair {self.pair_id}")
            return False
        
        self.picked_up_orders.add(order_id)
        self.logger.debug(f"Recorded pickup of order {order_id} in pair {self.pair_id}")
        return True
    
    def record_order_delivery(self, order_id):
        """Record that an order in this pair has been delivered."""
        if order_id not in [self.order1.order_id, self.order2.order_id]:
            self.logger.validation(f"Cannot record delivery for order {order_id}: not part of pair {self.pair_id}")
            return False
        
        self.delivered_orders.add(order_id)
        is_complete = len(self.delivered_orders) == 2
        
        self.logger.debug(f"Recorded delivery of order {order_id} in pair {self.pair_id}")
        if is_complete:
            self.logger.info(f"Pair {self.pair_id} delivery complete - all orders delivered")
            
        return is_complete