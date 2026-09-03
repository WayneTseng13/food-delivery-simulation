# delivery_sim/simulation/configuration.py

class StructuralConfig:
    """Configuration for fixed infrastructure elements of the simulation."""
    
    def __init__(self, 
                 delivery_area_size,  # km (square area)
                 num_restaurants,
                 driver_speed,        # km per minute
                 typical_distance_samples=1000):  # Add this parameter
        
        self.delivery_area_size = delivery_area_size
        self.num_restaurants = num_restaurants
        self.driver_speed = driver_speed
        self.typical_distance_samples = typical_distance_samples  # Add this line
        
    def __str__(self):
        """String representation for debugging and logging."""
        return (f"StructuralConfig("
                f"area_size={self.delivery_area_size}km, "
                f"restaurants={self.num_restaurants}, "
                f"driver_speed={self.driver_speed}km/min, "
                f"typical_distance_samples={self.typical_distance_samples})")
    
class OperationalConfig:
    """Configuration for dynamic operational elements of the simulation."""

    def __init__(self,
                 # Arrival intervals (minutes)
                 mean_order_inter_arrival_time,
                 mean_driver_inter_arrival_time,

                 # Pairing configuration
                 pairing_enabled,
                 restaurants_proximity_threshold,  # km
                 customers_proximity_threshold,    # km

                 # Driver service configuration
                 mean_service_duration,            # minutes
                 service_duration_std_dev,         # minutes
                 min_service_duration,             # minutes
                 max_service_duration,             # minutes

                 # Curation policy
                 curation_policy=None,        # None | 'operational' | 'blended' | 'featured'
                 featured_restaurant_id=None, # required for 'blended'/'featured'
                 customer_compliance_probability=1.0):

        # Arrival process parameters
        self.mean_order_inter_arrival_time = mean_order_inter_arrival_time
        self.mean_driver_inter_arrival_time = mean_driver_inter_arrival_time

        # Pairing configuration
        self.pairing_enabled = pairing_enabled
        self.restaurants_proximity_threshold = restaurants_proximity_threshold
        self.customers_proximity_threshold = customers_proximity_threshold

        # Driver service duration parameters
        self.mean_service_duration = mean_service_duration
        self.service_duration_std_dev = service_duration_std_dev
        self.min_service_duration = min_service_duration
        self.max_service_duration = max_service_duration

        # Curation policy.
        # Valid values:
        #   None            — no curation (Policy U); customer selects unaided
        #   'operational'   — Policy X'' (single_immediate + single_queued)
        #   'featured'      — Policy F (always feature R_F)
        valid_policies = {None, 'operational', 'featured'}
        if curation_policy not in valid_policies:
            raise ValueError(
                f"Invalid curation_policy: {curation_policy!r}. "
                f"Must be one of {valid_policies}."
            )
        self.curation_policy = curation_policy
        self.featured_restaurant_id = featured_restaurant_id

        # Featured mode requires a featured restaurant.
        # (The policy class re-validates, but failing here gives a clearer error
        # at config-construction time, before a run starts.)
        if curation_policy == 'featured' and featured_restaurant_id is None:
            raise ValueError(
                f"curation_policy={curation_policy!r} requires featured_restaurant_id."
            )

        # Customer compliance probability
        # Probability that a customer accepts the platform's restaurant recommendation
        # when one is produced. Only meaningful when curation_policy is not None.
        # Under curation_policy=None, this parameter is inert (no recommendation is
        # produced, so the customer samples uniformly regardless of p).
        if not (0.0 <= customer_compliance_probability <= 1.0):
            raise ValueError(
                f"customer_compliance_probability must be in [0.0, 1.0], "
                f"got {customer_compliance_probability}."
            )
        self.customer_compliance_probability = customer_compliance_probability

    def __str__(self):
        return (f"OperationalConfig("
                f"order_interval={self.mean_order_inter_arrival_time}min, "
                f"driver_interval={self.mean_driver_inter_arrival_time}min, "
                f"pairing={'on' if self.pairing_enabled else 'off'}, "
                f"restaurants_threshold={self.restaurants_proximity_threshold}km, "
                f"customers_threshold={self.customers_proximity_threshold}km, "
                f"service_duration={self.mean_service_duration}±{self.service_duration_std_dev}min, "
                f"curation={self.curation_policy}, "
                f"featured={self.featured_restaurant_id}, "
                f"compliance_p={self.customer_compliance_probability})")

class ExperimentConfig:
    def __init__(self, simulation_duration, num_replications, operational_master_seed, 
                 collection_interval=1.0):
        self.simulation_duration = simulation_duration
        self.num_replications = num_replications
        self.operational_master_seed = operational_master_seed  # CHANGED
        self.collection_interval = collection_interval

    def __str__(self):
        return (f"ExperimentConfig("
                f"simulation_duration={self.simulation_duration}min, "
                f"replications={self.num_replications}, "
                f"operational_master_seed={self.operational_master_seed}, "  # CHANGED
                f"collection_interval={self.collection_interval}min)")
    

class LoggingConfig:
    """Configuration for logging system behavior."""
    
    def __init__(self,
                 console_level="INFO",      # Level for console output
                 file_level="DEBUG",        # Level for file output
                 log_to_file=False,         # Whether to log to file
                 log_dir="logs",            # Directory for log files
                 log_file=None,             # Specific log file name (optional)
                 component_levels=None):    # Dict of component-specific levels
        
        # Convert string levels to numeric values if needed
        from delivery_sim.utils.logging_system import get_level_from_name
        self.console_level = (get_level_from_name(console_level) 
                             if isinstance(console_level, str) 
                             else console_level)
        self.file_level = (get_level_from_name(file_level) 
                          if isinstance(file_level, str) 
                          else file_level)
        self.log_to_file = log_to_file
        self.log_dir = log_dir
        self.log_file = log_file
        self.component_levels = component_levels or {}
        
        # If component_levels contains string levels, convert them
        if component_levels:
            for component, level in list(self.component_levels.items()):
                if isinstance(level, str):
                    self.component_levels[component] = get_level_from_name(level)

    def __str__(self):
        """String representation for debugging and logging."""
        # Convert numeric levels back to names for readability
        def level_name(level):
            level_map = {10: "DEBUG", 20: "INFO", 25: "SIMULATION",
                        30: "WARNING", 35: "VALIDATION", 40: "ERROR", 50: "CRITICAL"}
            return level_map.get(level, str(level))
        
        component_str = ", ".join([f"{comp}:{level_name(level)}" 
                                for comp, level in self.component_levels.items()]) if self.component_levels else "none"
        
        return (f"LoggingConfig("
                f"console={level_name(self.console_level)}, "
                f"file={level_name(self.file_level)}, "
                f"to_file={self.log_to_file}, "
                f"components=[{component_str}])")


class ScoringConfig:
    """
    Configuration for the priority scoring system.
    
    Separates infrastructure reality from business policy as outlined
    in the Priority Scoring System design document.
    """
    
    def __init__(self, 
                 # Business policy parameters (constant across configurations)
                 max_distance_ratio_multiplier=2.0,
                 max_acceptable_delay=30.0,
                 max_orders_per_trip=2,
                 
                 # Strategic weights (business preferences)
                 weight_distance=0.5,
                 weight_throughput=0.5,
                 weight_fairness=0):

        
        # Business policy parameters
        self.max_distance_ratio_multiplier = max_distance_ratio_multiplier
        self.max_acceptable_delay = max_acceptable_delay
        self.max_orders_per_trip = max_orders_per_trip
        
        # Strategic weights
        self.weight_distance = weight_distance
        self.weight_throughput = weight_throughput
        self.weight_fairness = weight_fairness
        

    
    def __str__(self):
        """String representation for debugging and logging."""
        return (f"ScoringConfig("
                f"weights=({self.weight_distance:.3f},{self.weight_throughput:.3f},{self.weight_fairness:.3f}), "
                f"max_ratio={self.max_distance_ratio_multiplier}, "
                f"max_wait={self.max_acceptable_delay}min, "
                f"max_orders={self.max_orders_per_trip})")

class FlatConfig:
    """
    A wrapper class that presents a flat interface for configuration attributes.
    
    This allows services to access attributes without knowing which config 
    object they belong to, simplifying service implementation.
    """
    def __init__(self, structural_config, operational_config, experiment_config, 
                 logging_config, scoring_config):
        self.structural_config = structural_config
        self.operational_config = operational_config
        self.experiment_config = experiment_config
        self.logging_config = logging_config
        self.scoring_config = scoring_config
    
    def __getattr__(self, name):
        # Try to find the attribute in each config object
        for config in [self.operational_config, self.structural_config, 
                      self.experiment_config, self.logging_config, 
                      self.scoring_config]:
            if hasattr(config, name):
                return getattr(config, name)
        
        raise AttributeError(f"'FlatConfig' object has no attribute '{name}'")

class SimulationConfig:
    """Complete configuration for a simulation experiment."""
    
    def __init__(self, structural_config, operational_config, 
                 experiment_config, logging_config, scoring_config):
        self.structural_config = structural_config
        self.operational_config = operational_config
        self.experiment_config = experiment_config
        self.logging_config = logging_config
        self.scoring_config = scoring_config
        
        # Create flat config for convenient service access
        self.flat_config = FlatConfig(
            structural_config, operational_config, experiment_config,
            logging_config, scoring_config
        )
    
    def __str__(self):
        """String representation for debugging and logging."""
        return (f"SimulationConfig:\n"
                f"  {self.structural_config}\n"
                f"  {self.operational_config}\n"
                f"  {self.experiment_config}\n"
                f"  {self.logging_config}\n"
                f"  {self.scoring_config}")