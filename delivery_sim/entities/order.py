from delivery_sim.entities.states import OrderState
from delivery_sim.events.order_events import OrderStateChangedEvent
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.entity_type_utils import EntityType

class Order:
    """
    Represents a food delivery order in the system.
    
    This is a fundamental entity in the simulation that contains
    all necessary information about an individual order.
    """
    
    def __init__(self, order_id, restaurant_location, customer_location,
                arrival_time, curation_result=None, customer_complied=None,
                curation_computed_tax=None, curation_realized_tax=None):
        """Initialize a new order with its basic properties."""
        self.logger = get_logger("entities.order")

        # Basic properties
        self.order_id = order_id
        self.entity_type = EntityType.ORDER
        self.restaurant_location = restaurant_location
        self.customer_location = customer_location
        self.arrival_time = arrival_time

        # Curation metadata — records the platform's recommendation state.
        # None:                no curation policy was active
        # 'fallback':          policy was active but produced no recommendation
        #                      (Policy X with no idle drivers)
        # 'curated':           Policy X selected via R-D proximity
        # 'pair_queued',
        # 'single_immediate',
        # 'single_queued':     Policy X' branch labels
        self.curation_result = curation_result

        # Customer compliance metadata — records the customer's response to the
        # recommendation. Independent of curation_result.
        # None:   no recommendation was produced (compliance not applicable)
        # True:   recommendation produced and customer accepted it
        # False:  recommendation produced and customer rejected it
        self.customer_complied = customer_complied                           # NEW

        self.curation_computed_tax = curation_computed_tax   # tax offered; set only when edge_manufacture fires
        self.curation_realized_tax = curation_realized_tax   # tax paid; set only when fired AND complied
        
        # State and relationships
        self.state = OrderState.CREATED
        self.pair = None
        self.delivery_unit = None

        # Timing information for lifecycle events
        self.pair_time = None
        self.assignment_time = None
        self.pickup_time = None
        self.delivery_time = None

        self.logger.debug(f"Order {order_id} created")

    def can_transition_to(self, new_state):
        """Check if this order can transition to the specified state."""
        valid_transitions = {
            OrderState.CREATED: [OrderState.PAIRED, OrderState.ASSIGNED],
            OrderState.PAIRED: [OrderState.ASSIGNED],
            OrderState.ASSIGNED: [OrderState.PICKED_UP],
            OrderState.PICKED_UP: [OrderState.DELIVERED],
            OrderState.DELIVERED: []  # Explicitly terminal
        }
        
        return new_state in valid_transitions.get(self.state, [])

    def transition_to(self, new_state, event_dispatcher=None, env=None):
        """
        Change the order's state with validation.
        
        Args:
            new_state: The new state to transition to
            event_dispatcher: Optional event dispatcher for events
            env: SimPy environment for current time
        """
        # Validate transition
        if not self.can_transition_to(new_state):
            # Log validation failure - with or without timestamp
            if env:
                self.logger.validation(f"[t={env.now:.2f}] Cannot transition order {self.order_id} from {self.state} to {new_state}")
            else:
                self.logger.validation(f"Cannot transition order {self.order_id} from {self.state} to {new_state}")
                
            # Also raise exception to prevent invalid state
            raise ValueError(f"Cannot transition order {self.order_id} from {self.state} to {new_state}")
        
        # Store old state for event
        old_state = self.state
        
        # Update state
        self.state = new_state
        
        # Update timing information based on new state
        if env:
            if new_state == OrderState.PAIRED:
                self.pair_time = env.now
                self.logger.debug(f"[t={env.now:.2f}] Set pair_time for order {self.order_id}")
                
            elif new_state == OrderState.ASSIGNED:
                self.assignment_time = env.now
                self.logger.debug(f"[t={env.now:.2f}] Set assignment_time for order {self.order_id}")
                
            elif new_state == OrderState.PICKED_UP:
                self.pickup_time = env.now
                self.logger.debug(f"[t={env.now:.2f}] Set pickup_time for order {self.order_id}")
                
            elif new_state == OrderState.DELIVERED:
                self.delivery_time = env.now
                self.logger.debug(f"[t={env.now:.2f}] Set delivery_time for order {self.order_id}")
        
        # Log the state transition
        if env:
            self.logger.info(f"[t={env.now:.2f}] Order {self.order_id} transitioned from {old_state} to {new_state}")
        else:
            self.logger.info(f"Order {self.order_id} transitioned from {old_state} to {new_state}")
        
        # Dispatch event if dispatcher provided
        if event_dispatcher and env:
            # Log event dispatch at SIMULATION_EVENT level
            self.logger.simulation_event(f"[t={env.now:.2f}] Dispatching OrderStateChangedEvent for order {self.order_id}: {old_state} -> {new_state}")
    
            event_dispatcher.dispatch(OrderStateChangedEvent(
                timestamp=env.now,
                order_id=self.order_id,
                old_state=old_state,
                new_state=new_state
            ))
        
        return True
    
    def __str__(self):
        """String representation of the order"""
        return f"Order(id={self.order_id}, state={self.state})"