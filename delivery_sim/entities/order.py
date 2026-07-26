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
                featuring_penalty=None, arrival_state=None,
                origin_restaurant_id=None):
        """Initialize a new order with its basic properties."""
        self.logger = get_logger("entities.order")

        # Basic properties
        self.order_id = order_id
        self.entity_type = EntityType.ORDER
        self.restaurant_location = restaurant_location
        self.customer_location = customer_location
        self.arrival_time = arrival_time

        # Curation metadata — records the platform's recommendation state.
        #    curation_result:
        #        None                          -- Policy U (no curation)
        #        'operational_immediate' /
        #        'operational_queued'          -- R_op recommended
        #        'featured_immediate' /
        #        'featured_queued'             -- R_F recommended
        self.curation_result = curation_result

        # Customer compliance metadata — records the customer's response to the
        # recommendation. Independent of curation_result.
        # None:   no recommendation was produced (compliance not applicable)
        # True:   recommendation produced and customer accepted it
        # False:  recommendation produced and customer rejected it
        self.customer_complied = customer_complied                           # NEW

        # Operational cost of the featuring decision for this order, in km.
        # None under Policy U and under 'operational' mode (no featuring decision).
        # Under 'blended'/'featured' it is c(R_F) - c(R_op) >= 0, recorded whether
        # or not featuring fired -- so the per-order distribution calibrates tau.
        self.featuring_penalty = featuring_penalty
        
        # System state at the moment this order arrived, read BEFORE any
        # recommendation was produced. Stamped for EVERY policy including U, so
        # arrival_immediate_rate / arrival_queued_rate are computable
        # policy-independently.
        #   'immediate' : at least one idle driver existed at arrival
        #   'queued'    : no idle driver existed at arrival
        #   None        : not recorded (should not happen in normal runs)
        # This is the true arrival-state mix, uncensored by completion -- unlike
        # immediate_assignment_rate, which conditions on delivered orders and so
        # is optimistic in the unbounded regime.
        self.arrival_state = arrival_state                                   # NEW

        # The restaurant this order ACTUALLY originated from -- i.e. the one the
        # customer ended up ordering from after the compliance gate:
        #   - the recommendation, if the customer complied
        #   - a uniform random pick, if the customer rejected
        #   - a uniform random pick, under Policy U (no recommendation)
        # NOT the recommended restaurant when they differ. Used for
        # featured_origin_rate (business capture) and per-restaurant load shares.
        self.origin_restaurant_id = origin_restaurant_id                     # NEW

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