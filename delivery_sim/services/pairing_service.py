from delivery_sim.events.order_events import OrderCreatedEvent
from delivery_sim.events.pair_events import PairCreatedEvent, PairingFailedEvent
from delivery_sim.entities.pair import Pair
from delivery_sim.entities.states import OrderState
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.route_evaluator import evaluate_partial

class PairingService:
    """
    Service responsible for evaluating pairing opportunities between orders.
    
    This service responds to new order arrivals by checking if they can be
    paired with existing unassigned orders based on proximity criteria.
    """
    
    def __init__(self, env, event_dispatcher, order_repository, pair_repository, config):
        """
        Initialize the pairing service with its dependencies.
        """
        # Get a logger instance specific to this component
        self.logger = get_logger("services.pairing")
        
        # Store dependencies
        self.env = env
        self.event_dispatcher = event_dispatcher
        self.order_repository = order_repository
        self.pair_repository = pair_repository
        self.config = config
        
        # Log service initialization with simulation time
        self.logger.info(f"[t={self.env.now:.2f}] PairingService initialized with configuration: "
                        f"restaurant_threshold={config.restaurants_proximity_threshold}km, "
                        f"customer_threshold={config.customers_proximity_threshold}km")
        
        # Register for events and log with simulation time
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for OrderCreatedEvent")
        self.event_dispatcher.register(OrderCreatedEvent, self.handle_order_created)
    
    # ===== Event Handlers =====
    
    def handle_order_created(self, event):
        """
        Handler for OrderCreatedEvent. Validates the order and attempts pairing if valid.
        
        This handler implements the Entry-Point Validation Pattern by validating
        entities before passing them to operations.
        
        Args:
            event: The OrderCreatedEvent
        """
        # Log event handling with simulation time
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling OrderCreatedEvent for order {event.order_id}")
        
        # Extract identifiers from event
        order_id = event.order_id
        
        # Validate order exists - follow Entry-Point Validation pattern
        new_order = self.order_repository.find_by_id(order_id)
        if not new_order:
            # Log validation failure with simulation time
            self.logger.validation(f"[t={self.env.now:.2f}] Order {order_id} not found, cannot attempt pairing")
            return
        
        # Pass validated entity to operation
        self.attempt_pairing(new_order)
    
    # ===== Operations =====
    
    def attempt_pairing(self, new_order):
        """
        Try to pair the new order with an existing order.
        """
        # Log operation start with simulation time
        self.logger.debug(f"[t={self.env.now:.2f}] Attempting to pair order {new_order.order_id}")
        
        # Find potential candidates for pairing
        candidates = self.find_pairing_candidates(new_order)
        
        # Log candidate results with simulation time
        self.logger.debug(f"[t={self.env.now:.2f}] Found {len(candidates)} qualified pairing candidates for order {new_order.order_id}")
        
        if not candidates:
            # Log business outcome with simulation time
            self.logger.info(f"[t={self.env.now:.2f}] No pairing candidates found for order {new_order.order_id}")
            
            # Log event dispatch with simulation time
            self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching PairingFailedEvent for order {new_order.order_id}")
            
            # Dispatch event
            self.event_dispatcher.dispatch(PairingFailedEvent(
                timestamp=self.env.now,
                order_id=new_order.order_id
            ))
            return False
        
        # Find the best match among candidates
        best_match, best_sequence, best_cost = self.calculate_best_match(new_order, candidates)
        
        # Log match selection with simulation time
        self.logger.debug(f"[t={self.env.now:.2f}] Selected best match for order {new_order.order_id}: "
                          f"order {best_match.order_id} with cost {best_cost:.2f}")
        
        # Log business outcome with simulation time
        self.logger.info(f"[t={self.env.now:.2f}] Pairing order {new_order.order_id} with order {best_match.order_id}")
        
        # Form the pair with the best match
        pair = self.form_pair(new_order, best_match, best_sequence, best_cost)
        return pair
    
    def find_pairing_candidates(self, new_order):
        """
        Find orders that meet proximity criteria for pairing.
        """
        # Get all unassigned single orders - log with simulation time
        all_singles = self.order_repository.find_unassigned_orders()
        self.logger.debug(f"[t={self.env.now:.2f}] Evaluating {len(all_singles)} unassigned orders as potential pairing candidates")
        
        # Filter out the new order itself
        potential_candidates = [
            order for order in all_singles 
            if order.order_id != new_order.order_id
        ]
        
        # Apply proximity filters
        candidates = [
            candidate for candidate in potential_candidates
            if self._check_proximity_constraints(new_order, candidate)
        ]
        
        # Log detailed filter results with simulation time
        self.logger.debug(f"[t={self.env.now:.2f}] After proximity filtering: {len(candidates)} candidates remain")
        
        return candidates
    
    def calculate_best_match(self, new_order, candidates):
        """
        Find the best order to pair with and the optimal delivery sequence.
        """
        # Log method entry with simulation time
        self.logger.debug(f"[t={self.env.now:.2f}] Calculating best match for order {new_order.order_id} among {len(candidates)} candidates")
        
        best_candidate = None
        best_sequence = None
        best_cost = float('inf')
        
        for candidate in candidates:
            # Evaluate this candidate
            sequence, cost = self.evaluate_sequences(new_order, candidate)
            
            # Log individual evaluation with simulation time
            self.logger.debug(f"[t={self.env.now:.2f}] Evaluated candidate {candidate.order_id}: cost={cost:.2f}")
            
            if cost < best_cost:
                best_cost = cost
                best_sequence = sequence
                best_candidate = candidate
        
        return best_candidate, best_sequence, best_cost
    
    def form_pair(self, order1, order2, sequence, cost):
        """
        Create a pair from two orders and update their state.
        """
        # Create the pair entity
        pair = Pair(order1, order2, self.env.now)
        pair.partial_info_sequence = sequence
        pair.partial_info_cost = cost
        
        # Add to repository
        self.pair_repository.add(pair)

        # Set bidirectional references 
        order1.pair = pair
        order2.pair = pair

        # Update order states - assuming transition_to logs its own actions
        order1.transition_to(OrderState.PAIRED, self.event_dispatcher, self.env)
        order2.transition_to(OrderState.PAIRED, self.event_dispatcher, self.env)
        
        # Log event dispatch with simulation time
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching PairCreatedEvent for pair {pair.pair_id}")
        
        # Dispatch pair created event
        self.event_dispatcher.dispatch(PairCreatedEvent(
            timestamp=self.env.now,
            pair_id=pair.pair_id,
            order1_id=order1.order_id,
            order2_id=order2.order_id
        ))
        
        # Log detailed pair formation with simulation time
        self.logger.info(f"[t={self.env.now:.2f}] Formed pair {pair.pair_id} with optimal cost {cost:.2f}")
        
        return pair
    
    # ===== Helper Methods =====
    
    def evaluate_sequences(self, order1, order2):
        """
        Evaluate all valid delivery sequences for a pair of orders.

        Delegates to route_evaluator.evaluate_partial which enumerates all 6
        valid sequences (4 batched + 2 interleaved) and handles same-restaurant
        deduplication. Returns the best route by minimum route cost.
        """
        self.logger.debug(
            f"[t={self.env.now:.2f}] Evaluating delivery sequences for orders "
            f"{order1.order_id} and {order2.order_id}"
        )
        result = evaluate_partial(
            order1.restaurant_location, order1.customer_location,
            order2.restaurant_location, order2.customer_location,
        )
        self.logger.debug(
            f"[t={self.env.now:.2f}] Selected best sequence with cost {result['route_cost']:.2f}"
        )
        return result['stops'], result['route_cost']
    
    
    def _check_proximity_constraints(self, order1, order2):
        """
        Check if two orders satisfy proximity constraints for pairing.
        
        Args:
            order1: First order to check
            order2: Second order to check
            
        Returns:
            bool: True if orders meet proximity criteria, False otherwise
        """
        # Calculate distances
        restaurant_distance = calculate_distance(
            order1.restaurant_location,
            order2.restaurant_location
        )
        customer_distance = calculate_distance(
            order1.customer_location,
            order2.customer_location
        )
        
        # Log constraint check with simulation time (very detailed)
        self.logger.debug(f"[t={self.env.now:.2f}] Proximity check for orders {order1.order_id}-{order2.order_id}: "
                          f"restaurant_distance={restaurant_distance:.2f}km, threshold={self.config.restaurants_proximity_threshold}km, "
                          f"customer_distance={customer_distance:.2f}km, threshold={self.config.customers_proximity_threshold}km")
        
        return (restaurant_distance <= self.config.restaurants_proximity_threshold and
                customer_distance <= self.config.customers_proximity_threshold)
    
