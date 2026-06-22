# delivery_sim/utils/priority_scoring.py
"""
Priority Scoring System for Food Delivery Assignment Decisions

This module implements a multi-criteria scoring system that evaluates
driver-entity assignment opportunities based on distance efficiency,
throughput optimization, and fairness considerations.

Configuration is handled by ScoringConfig in configuration.py.
Infrastructure analysis (like typical_distance calculation) is now handled 
by the infrastructure_analysis module for better separation of concerns.
"""

import numpy as np
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.entity_type_utils import EntityType
from delivery_sim.utils.logging_system import get_logger
from delivery_sim.utils.route_evaluator import evaluate_complete


class PriorityScorer:
    """
    Main scoring system that evaluates driver-entity assignment opportunities.
    
    """
    
    def __init__(self, scoring_config, typical_distance, env):
        """
        Initialize scorer with configuration and infrastructure characteristics.
        
        Args:
            scoring_config: ScoringConfig instance from configuration.py
            typical_distance: Pre-calculated typical distance for this infrastructure
            env: SimPy environment for this replication
        """
        self.config = scoring_config
        self.typical_distance = typical_distance
        self.env = env
        self.logger = get_logger("utils.priority_scorer")
        
        self.logger.debug(f"PriorityScorer initialized with typical_distance={typical_distance:.3f}km")
    
    def calculate_priority_score(self, driver, entity):
        """
        Calculate priority score for a driver-entity assignment.
        
        Args:
            driver: Driver being evaluated
            entity: Order or Pair being evaluated
            
        Returns:
            tuple: (priority_score_0_to_100, components_dictionary)
        """
        # Calculate total distance once and cache it
        total_distance = self._calculate_total_distance(driver, entity)
        
        # Calculate individual component scores (all in [0,1] range)
        distance_score = self._calculate_distance_score(total_distance)
        throughput_score = self._calculate_throughput_score(entity)
        fairness_score = self._calculate_fairness_score(entity)
        
        # Weighted combination
        combined_score = (
            self.config.weight_distance * distance_score +
            self.config.weight_throughput * throughput_score +
            self.config.weight_fairness * fairness_score
        )
        
        # Scale to 0-100 range for interpretability
        priority_score = combined_score * 100
        
        # Determine entity type and ID for logging
        entity_type = entity.entity_type
        entity_id = entity.order_id if entity_type == EntityType.ORDER else entity.pair_id
        
        # Log detailed calculation with entity information
        self.logger.info(
            f"[t={self.env.now:.2f}] Priority score calculation for {entity_type} {entity_id}: "
            f"distance={distance_score:.3f}, throughput={throughput_score:.3f}, "
            f"fairness={fairness_score:.3f}, combined={priority_score:.2f}"
        )
        
        # Return score and components for logging/analysis
        components = {
            "distance_score": distance_score,
            "throughput_score": throughput_score,
            "fairness_score": fairness_score,
            "combined_score_0_1": combined_score,
            "total_distance": total_distance,
            "num_orders": self._get_order_count(entity),
            "assignment_delay_minutes": self._calculate_assignment_delay(entity)  # Updated key name
        }
        
        return priority_score, components
        
    def _calculate_distance_score(self, total_distance):
        """
        Calculate distance efficiency score using two-step normalization.
        
        Distance is a relational measure that requires geographical contextualization.
        The score represents how efficient this assignment is compared to typical
        distances in this delivery area.
        
        Step 1: Contextualization - normalize by typical distance for this geography
        Step 2: Performance assessment - apply universal acceptability standard
        
        Args:
            total_distance (float): Pre-calculated total travel distance in km
            
        Returns:
            float: Distance efficiency score in [0,1] range, where:
                - 1.0 = perfect efficiency (zero distance)
                - 0.5 = typical efficiency (1× typical distance) 
                - 0.0 = unacceptable efficiency (≥2× typical distance)
        """
        # Step 1: Contextualization (acknowledge geographical reality)
        distance_ratio = total_distance / self.typical_distance
        
        # Step 2: Performance assessment (apply universal standard)
        distance_score = max(0, 1 - distance_ratio / self.config.max_distance_ratio_multiplier)
        
        return distance_score

    def _calculate_throughput_score(self, entity):
        """
        Calculate throughput optimization score based on order count.
        
        Throughput represents capacity utilization - how many orders can be
        delivered in a single trip. This is an absolute measure with discrete
        values since drivers can only handle 1 or 2 orders per trip.
        
        Args:
            entity (Order or Pair): The delivery entity being evaluated
            
        Returns:
            float: Throughput score in [0,1] range, where:
                - 1.0 = maximum throughput (2 orders, full capacity)
                - 0.5 = partial throughput (1 order, half capacity)
                - Values are discrete, not continuous
        """
        num_orders = self._get_order_count(entity)
        max_orders = self.config.max_orders_per_trip
        
        # Direct proportion: num_orders / max_orders_per_trip
        throughput_score = num_orders / max_orders
        
        return throughput_score

    def _calculate_fairness_score(self, entity):
        """
        Calculate fairness score based on assignment urgency.
        
        Fairness represents how urgently this entity needs assignment based on
        how long it has been waiting for driver assignment. Longer assignment
        delays indicate higher priority to maintain fairness in assignment opportunities.
        
        Args:
            entity (Order or Pair): The delivery entity being evaluated
            
        Returns:
            float: Fairness urgency score in [0,1] range, where:
                - 0.0 = just arrived, no assignment urgency
                - 0.5 = moderate urgency (e.g., 15 min delay if max_acceptable=30 min)
                - 1.0 = maximum urgency (≥max_acceptable delay, critical assignment priority)
        """
        assignment_delay = self._calculate_assignment_delay(entity)
        max_acceptable_delay = self.config.max_acceptable_delay
        
        # Direct normalization with ceiling: min(1.0, assignment_delay / max_acceptable_delay)
        fairness_score = min(1.0, assignment_delay / max_acceptable_delay)
        
        return fairness_score
    
    def _calculate_total_distance(self, driver, entity):
        """
        Calculate total travel distance for this assignment.
        
        For single orders: driver → restaurant → customer
        For pairs: driver → first_location_in_optimal_sequence + pre_calculated_optimal_cost
        
        Args:
            driver: Driver entity with location
            entity: Order or Pair entity
            
        Returns:
            float: Total travel distance in km
        """
        if entity.entity_type == EntityType.PAIR:
                    # evaluate_complete jointly selects the best sequence and accounts for
                    # driver position. This is what assignment will also do, so priority
                    # scoring and assignment are aligned by construction.
                    result = evaluate_complete(
                        entity.order1.restaurant_location,
                        entity.order1.customer_location,
                        entity.order2.restaurant_location,
                        entity.order2.customer_location,
                        [driver],
                    )
                    self.logger.debug(
                        f"Pair {entity.pair_id}: r_d={result['r_d']:.3f}km + "
                        f"route_cost={result['route_cost']:.3f}km = {result['total_cost']:.3f}km"
                    )
                    return result['total_cost']
            
        else:  # EntityType.ORDER
            # Driver → Restaurant → Customer
            driver_to_restaurant = calculate_distance(driver.location, entity.restaurant_location)
            restaurant_to_customer = calculate_distance(entity.restaurant_location, entity.customer_location)
            total_distance = driver_to_restaurant + restaurant_to_customer
            
            self.logger.debug(f"Order {entity.order_id}: driver_to_restaurant={driver_to_restaurant:.3f}km + restaurant_to_customer={restaurant_to_customer:.3f}km = {total_distance:.3f}km")
            return total_distance
    
    def _get_order_count(self, entity):
        """Get number of orders in this entity."""
        return 2 if entity.entity_type == EntityType.PAIR else 1
    
    def _calculate_assignment_delay(self, entity):
        """
        Calculate assignment delay from the customer fairness perspective.
        
        For single orders: Time from order arrival until current assignment consideration.
        For pairs: Time from the EARLIEST order arrival (worst-case customer experience)
                until current assignment consideration, regardless of when the pair was formed.
        
        This ensures fairness prioritization reflects the longest-waiting customer's experience,
        not just when the delivery entity became available for assignment.
        
        Args:
            entity (Order or Pair): The delivery entity being evaluated
            
        Returns:
            float: Assignment delay in minutes from customer perspective
        """
        if entity.entity_type == EntityType.PAIR:
            # Use earliest arrival time for pairs (when first order arrived)
            earliest_arrival = min(entity.order1.arrival_time, entity.order2.arrival_time)
        else:
            earliest_arrival = entity.arrival_time
        
        assignment_delay_minutes = self.env.now - earliest_arrival
        return assignment_delay_minutes
