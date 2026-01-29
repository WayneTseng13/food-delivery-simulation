# analysis_pipeline_redesigned/metric_configurations.py
"""
Metric configuration system for pattern-based analysis pipeline.

This module defines how different metric types should be processed through
the analysis pipeline. Uses robust configuration format for experiment statistics
instead of brittle string parsing.
"""

from delivery_sim.utils.logging_system import get_logger

logger = get_logger("analysis_pipeline_redesigned.metric_configurations")

# ==============================================================================
# CORE METRIC CONFIGURATIONS
# ==============================================================================

METRIC_CONFIGURATIONS = {
    
    # ==========================================================================
    # TWO-LEVEL PATTERN: ENTITY-BASED METRICS
    # ==========================================================================
    # Characteristics:
    # - Metrics calculated POST-SIMULATION from preserved entity attributes
    # - Each entity produces multiple metrics (e.g., assignment_time, fulfillment_time)
    # - Aggregation: entities → statistics (replication) → statistics-of-statistics (experiment)
    # - Example: calculate_all_order_metrics(order) reads order.arrival_time, order.assignment_time
    
    'order_metrics': {
        'aggregation_pattern': 'two_level',
        'metric_module': 'delivery_sim.metrics.entity.order_metrics',
        'metric_function': 'calculate_all_order_metrics',
        'data_key': 'cohort_completed_orders',
        'experiment_stats': [
            {
                'name': 'mean_of_means', 
                'extract': 'mean', 
                'compute': 'mean',
                'construct_ci': True,
                'description': 'Average of assignment time means across replications'
            },
            {
                'name': 'std_of_means', 
                'extract': 'mean', 
                'compute': 'std',
                'construct_ci': False,  # Descriptive only for presentation
                'description': 'Standard deviation of assignment time means across replications (system consistency)'
            },
            {
                'name': 'mean_of_stds', 
                'extract': 'std', 
                'compute': 'mean',
                'construct_ci': False,  # Descriptive only for presentation
                'description': 'Average within-replication standard deviation (average volatility)'
            }
        ],
        'description': 'Individual order performance metrics'
    },
    'pair_metrics': {
        'aggregation_pattern': 'two_level',
        'metric_module': 'delivery_sim.metrics.entity.pair_metrics',
        'metric_function': 'calculate_all_pair_metrics',
        'data_key': 'cohort_completed_pairs',
        'experiment_stats': [
            {
                'name': 'mean_of_means', 
                'extract': 'mean', 
                'compute': 'mean',
                'construct_ci': True,
                'description': 'Average of metric means across replications'
            },
            {
                'name': 'std_of_means', 
                'extract': 'mean', 
                'compute': 'std',
                'construct_ci': False,
                'description': 'Between-replication consistency'
            },
            {
                'name': 'mean_of_stds', 
                'extract': 'std', 
                'compute': 'mean',
                'construct_ci': False,
                'description': 'Average within-replication volatility'
            }
        ]
    },    
    'delivery_unit_metrics': {
        'aggregation_pattern': 'two_level', 
        'metric_module': 'delivery_sim.metrics.entity.delivery_unit_metrics',
        'metric_function': 'calculate_all_delivery_unit_metrics',
        'data_key': 'cohort_completed_delivery_units',
        'experiment_stats': [
            {
                'name': 'mean_of_means', 
                'extract': 'mean', 
                'compute': 'mean',
                'construct_ci': True
            },
            {
                'name': 'std_of_means', 
                'extract': 'mean', 
                'compute': 'std',
                'construct_ci': False  # Descriptive only
            }
        ],
        'description': 'Delivery unit performance metrics'
    },

    # ==========================================================================
    # TWO-LEVEL PATTERN: SYSTEM STATE METRICS  
    # ==========================================================================
    # Characteristics:
    # - Metrics calculated DURING-SIMULATION (transient state captured in real-time)
    # - Each snapshot already contains multiple metrics (e.g., available_drivers, active_drivers)
    # - Aggregation: snapshots → statistics (replication) → statistics-of-statistics (experiment)
    # - Example: extract_snapshot_metrics(snapshot) just filters out timestamp
    # - Why different timing: Cannot reconstruct "drivers available at t=501" post-simulation
    
    'system_state_metrics': {
        'aggregation_pattern': 'two_level',
        'metric_module': 'delivery_sim.metrics.system.state_metrics',
        'metric_function': 'extract_snapshot_metrics',  # EXTRACTS from snapshot
        'data_key': 'post_warmup_snapshots',
        'experiment_stats': [
            {'name': 'mean_of_means', 'extract': 'mean', 'compute': 'mean', 'construct_ci': True},
            {'name': 'std_of_means', 'extract': 'mean', 'compute': 'std', 'construct_ci': False},
            {'name': 'mean_of_stds', 'extract': 'std', 'compute': 'mean', 'construct_ci': False}
        ],
        'description': 'System state metrics from time series snapshots (calculated during simulation)'
    },

    # ==========================================================================
    # ONE-LEVEL PATTERN: ENTITY-DERIVED SYSTEM METRICS
    # ==========================================================================
    # Characteristics:
    # - System-level metrics derived from entity populations
    # - Direct calculation returns scalar values (no entity-level aggregation)
    # - Aggregation: direct calculation (replication) → statistics (experiment)
    # - Example: system_completion_rate = len(completed) / len(total)

    'system_metrics': {
        'aggregation_pattern': 'one_level',
        'metric_module': 'delivery_sim.metrics.system.entity_derived_metrics', 
        'metric_function': 'calculate_all_entity_derived_system_metrics',
        'data_key': None,
        'ci_config': [
            {
                'metric_name': 'system_completion_rate',  # ✅ Changed from 'completion_rate'
                'target_statistic': 'mean',
                'construct_ci': True,
                'description': 'Mean completion rate with CI'
            },
            {
                'metric_name': 'system_pairing_rate',  # ✅ Changed from 'pairing_rate'
                'target_statistic': 'mean',
                'construct_ci': True,
                'description': 'Mean pairing rate with CI'
            },
        ],
        'description': 'System-wide performance metrics'
    },
    # ==========================================================================
    # ONE-LEVEL PATTERN: QUEUE DYNAMICS METRICS
    # ==========================================================================
    # Characteristics:
    # - Calculated from post-warmup snapshots (time series)
    # - Requires custom logic (growth rate = endpoint difference / window)
    # - Returns scalar values directly (no entity iteration)
    # - Aggregation: scalars → statistics (experiment)
    # - Why one-level: Not a standard statistic; needs custom calculation
    # - Example: growth_rate needs (terminal - initial) / window_length
    
    'queue_dynamics_metrics': {
        'aggregation_pattern': 'one_level',
        'metric_module': 'delivery_sim.metrics.system.queue_dynamics_metrics',
        'metric_function': 'calculate_all_queue_dynamics_metrics',
        'data_key': None,  # Uses analysis_data directly
        'ci_config': [
            {
                'metric_name': 'unassigned_entities_growth_rate',
                'target_statistic': 'mean',
                'construct_ci': True
            },
            {
                'metric_name': 'average_unassigned_entities',  # NEW METRIC
                'target_statistic': 'mean',
                'construct_ci': True
            }
        ],
        'description': 'Queue dynamics metrics (growth rate, average queue size, trend analysis)'
    }
}

# ==============================================================================
# CORE CONFIGURATION ACCESS
# ==============================================================================

def get_metric_configuration(metric_type):
    """Get configuration for a specific metric type."""
    if metric_type not in METRIC_CONFIGURATIONS:
        available_types = list(METRIC_CONFIGURATIONS.keys())
        logger.error(f"Unknown metric type: {metric_type}. Available types: {available_types}")
        raise KeyError(f"Metric type '{metric_type}' not found in configurations")
    
    return METRIC_CONFIGURATIONS[metric_type]

def list_available_metric_types():
    """Get list of all configured metric types."""
    return list(METRIC_CONFIGURATIONS.keys())


def list_metric_types_by_pattern(pattern):
    """Get list of metric types that use a specific aggregation pattern."""
    return [
        metric_type for metric_type, config in METRIC_CONFIGURATIONS.items()
        if config['aggregation_pattern'] == pattern
    ]


# ==============================================================================
# EXPERIMENT STATISTICS HELPER FUNCTIONS
# ==============================================================================

def add_experiment_statistic(metric_type, name, extract, compute):
    """
    Dynamically add an experiment statistic to a metric type configuration.
    
    Args:
        metric_type: Metric type key
        name: Display name for the statistic
        extract: Base statistic to extract ('mean', 'std', 'variance', etc.)
        compute: Statistic to compute on extracted values ('mean', 'std', etc.)
    """
    config = get_metric_configuration(metric_type)
    
    if config['aggregation_pattern'] != 'two_level':
        raise ValueError(f"Cannot add experiment statistics to one-level pattern: {metric_type}")
    
    new_stat = {'name': name, 'extract': extract, 'compute': compute}
    config['experiment_stats'].append(new_stat)
    
    logger.info(f"Added experiment statistic to {metric_type}: {new_stat}")


def validate_experiment_statistic_config(stat_config):
    """
    Validate that an experiment statistic configuration is properly formatted.
    
    Args:
        stat_config: Dictionary with 'name', 'extract', 'compute' keys
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ['name', 'extract', 'compute']
    
    if not isinstance(stat_config, dict):
        raise ValueError("Experiment statistic configuration must be a dictionary")
    
    for key in required_keys:
        if key not in stat_config:
            raise ValueError(f"Missing required key '{key}' in experiment statistic configuration")
    
    # Validate that extract and compute refer to valid statistics
    valid_statistics = ['mean', 'std', 'variance', 'min', 'max', 'p25', 'p50', 'p75', 'p95', 'full_stats']
    
    if stat_config['extract'] not in valid_statistics:
        raise ValueError(f"Invalid extract statistic: {stat_config['extract']}. Must be one of {valid_statistics}")
    
    if stat_config['compute'] not in valid_statistics:
        raise ValueError(f"Invalid compute statistic: {stat_config['compute']}. Must be one of {valid_statistics}")
    
    return True


# ==============================================================================
# CONFIGURATION VALIDATION
# ==============================================================================

def validate_configurations():
    """Validate that all metric configurations are properly structured."""
    required_fields = {
        'two_level': ['aggregation_pattern', 'metric_module', 'metric_function', 
                      'data_key', 'experiment_stats'],
        'one_level': ['aggregation_pattern', 'metric_module', 'metric_function']
    }
    
    for metric_type, config in METRIC_CONFIGURATIONS.items():
        pattern = config.get('aggregation_pattern')
        
        if pattern not in ['two_level', 'one_level']:
            raise ValueError(f"Invalid aggregation pattern for {metric_type}: {pattern}")
        
        # Check required fields
        required = required_fields[pattern]
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in {metric_type} configuration")
        
        # Pattern-specific validation
        if pattern == 'two_level':
            if config['data_key'] is None:
                raise ValueError(f"Two-level pattern {metric_type} must specify entity_data_key")
            
            # Validate experiment statistics configurations
            for stat_config in config['experiment_stats']:
                validate_experiment_statistic_config(stat_config)
                
                # Validate compute field for CI construction
                if stat_config.get('construct_ci', False):
                    compute_type = stat_config.get('compute')
                    if compute_type not in ['mean', 'std', 'variance']:
                        raise ValueError(f"Invalid compute type '{compute_type}' in {metric_type}. "
                                       f"Supported types: mean, std, variance")
        
        elif pattern == 'one_level':
            # Validate CI configuration if present
            if 'ci_config' in config:
                for ci_config in config['ci_config']:
                    required_ci_fields = ['metric_name', 'construct_ci']
                    for field in required_ci_fields:
                        if field not in ci_config:
                            raise ValueError(f"Missing CI config field '{field}' in {metric_type}")
            
            if 'experiment_stats' in config:
                logger.warning(f"One-level pattern {metric_type} should not specify experiment_stats")
    
    logger.info(f"Configuration validation passed for {len(METRIC_CONFIGURATIONS)} metric types")
    return True




# Run validation on import to catch configuration errors early
if __name__ != "__main__":
    try:
        validate_configurations()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise