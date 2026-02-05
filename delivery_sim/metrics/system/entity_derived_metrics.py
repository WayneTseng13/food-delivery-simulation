# delivery_sim/metrics/system/entity_derived_metrics.py
"""
Entity-derived system metrics calculation.

This module provides functions to calculate system-level metrics that can be
derived entirely from entity repository data post-simulation, without needing
time-series collection during simulation.

Updated to use AnalysisData with centralized filtering approach.
"""


def calculate_system_completion_rate(analysis_data):
    """
    Calculate system completion rate as proportion of arrived orders that were delivered.
    
    This metric provides the primary measure of system performance by showing what 
    percentage of orders that arrived during the analysis period were successfully completed.
    
    Args:
        analysis_data: AnalysisData object containing pre-filtered populations
        
    Returns:
        dict: Contains total_arrived, total_delivered, and completion_rate
    """
    # Use pre-filtered populations from AnalysisData
    total_arrived = len(analysis_data.cohort_orders)  # All post-warmup orders
    total_delivered = len(analysis_data.cohort_completed_orders)  # Completed cohort orders
    
    # Calculate completion rate
    completion_rate = total_delivered / total_arrived if total_arrived > 0 else 0.0
    
    return {
        'total_arrived': total_arrived,
        'total_delivered': total_delivered, 
        'completion_rate': completion_rate
    }


def calculate_system_pairing_rate(analysis_data):
    """
    Calculate system pairing rate as proportion of arrived orders that were paired.
    
    This metric measures how effectively the pairing system is working by showing
    what percentage of orders that arrived during the analysis period got paired
    with another order, regardless of whether they were ultimately completed.
    
    Args:
        analysis_data: AnalysisData object containing pre-filtered populations
        
    Returns:
        dict: Contains total_arrived, total_paired, and pairing_rate
    """
    # Use pre-filtered populations from AnalysisData  
    total_arrived = len(analysis_data.cohort_orders)  # All post-warmup orders
    total_paired = len(analysis_data.cohort_paired_orders)  # Paired cohort orders
    
    # Calculate pairing rate
    pairing_rate = total_paired / total_arrived if total_arrived > 0 else 0.0
    
    return {
        'total_arrived': total_arrived,
        'total_paired': total_paired,
        'pairing_rate': pairing_rate
    }

def calculate_immediate_assignment_rate(analysis_data):
    """
    Calculate immediate assignment rate as fraction of completed orders with zero assignment time.
    
    This metric measures system responsiveness by showing what percentage of 
    completed orders were assigned to a driver immediately upon arrival (no queueing delay).
    
    Uses the unbiased performance sample (cohort_completed_orders) to ensure 
    the metric reflects typical completed order performance.
    
    Args:
        analysis_data: AnalysisData object containing pre-filtered populations
        
    Returns:
        dict: Contains total_completed, immediate_assignments, and immediate_assignment_rate
    """
    # Import the metric calculation function
    from delivery_sim.metrics.entity.order_metrics import calculate_order_assignment_time
    
    # Use completed orders from AnalysisData (unbiased performance sample)
    completed_orders = analysis_data.cohort_completed_orders
    
    total_completed = len(completed_orders)
    
    # Count orders with assignment_time duration == 0
    # We need to calculate the duration (assignment_time - arrival_time), not use the timestamp
    immediate_assignments = sum(
        1 for order in completed_orders 
        if calculate_order_assignment_time(order) == 0
    )
    
    # Calculate rate
    immediate_assignment_rate = immediate_assignments / total_completed if total_completed > 0 else 0.0
    
    return {
        'total_completed': total_completed,
        'immediate_assignments': immediate_assignments,
        'immediate_assignment_rate': immediate_assignment_rate
    }

def calculate_all_entity_derived_system_metrics(analysis_data):
    """
    Calculate all entity-derived system metrics for a replication.
    
    Uses pre-filtered populations from AnalysisData for consistent, clean calculation.
    
    Args:
        analysis_data: AnalysisData object containing pre-filtered populations
        
    Returns:
        dict: Dictionary with metric names as keys and calculated values
    """
    # Calculate completion metrics
    completion_metrics = calculate_system_completion_rate(analysis_data)
    
    # Calculate pairing rate metrics
    pairing_metrics = calculate_system_pairing_rate(analysis_data)
    
    # Calculate immediate assignment rate metrics
    immediate_assignment_metrics = calculate_immediate_assignment_rate(analysis_data)
    
    return {
        # Completion metrics
        'system_completion_rate': completion_metrics['completion_rate'],
        'total_orders_arrived': completion_metrics['total_arrived'],
        'total_orders_delivered': completion_metrics['total_delivered'],
        
        # Pairing rate metrics
        'system_pairing_rate': pairing_metrics['pairing_rate'],
        'total_orders_paired': pairing_metrics['total_paired'],
        
        # Immediate assignment metrics
        'immediate_assignment_rate': immediate_assignment_metrics['immediate_assignment_rate'],
        'total_immediate_assignments': immediate_assignment_metrics['immediate_assignments']
    }