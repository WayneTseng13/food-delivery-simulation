# delivery_sim/metrics/system/queue_dynamics_metrics.py
"""
Queue dynamics metrics for system state analysis.

These metrics capture the temporal dynamics of queue behavior,
particularly for diagnosing system deterioration vs stability.
"""

def calculate_unassigned_entities_growth_rate(analysis_data):
    """
    Calculate growth rate of unassigned delivery entities.
    
    Growth rate measures the trend/trajectory of queue accumulation:
    - Growth ≈ 0: Bounded system (stable or oscillatory)
    - Growth > 0: Unbounded accumulation (deteriorating system)
    
    Calculation: (terminal_value - initial_value) / window_length
    
    This simple endpoint-based approach is:
    - Robust across replications (noise averages out)
    - Appropriate for linear growth patterns
    - Valid for oscillatory systems (random endpoints average to ≈0)
    
    Args:
        analysis_data: AnalysisData object with post_warmup_snapshots
        
    Returns:
        dict: Contains growth_rate (entities/minute) and supporting metadata
    """
    snapshots = analysis_data.post_warmup_snapshots
    
    # Handle edge case of insufficient data
    if len(snapshots) < 2:
        return {
            'growth_rate': 0.0,
            'initial_value': 0.0,
            'terminal_value': 0.0,
            'window_length': 0.0,
            'n_snapshots': len(snapshots)
        }
    
    # Extract unassigned entities time series
    unassigned_series = [s['unassigned_delivery_entities'] for s in snapshots]
    
    # Get endpoint values
    initial_value = unassigned_series[0]  # Value at warmup end
    terminal_value = unassigned_series[-1]  # Value at simulation end
    
    # Calculate time window length
    initial_time = snapshots[0]['timestamp']
    terminal_time = snapshots[-1]['timestamp']
    window_length = terminal_time - initial_time
    
    # Calculate growth rate
    if window_length > 0:
        growth_rate = (terminal_value - initial_value) / window_length
    else:
        growth_rate = 0.0
    
    return {
        'growth_rate': growth_rate,  # entities per minute
        'initial_value': initial_value,
        'terminal_value': terminal_value,
        'window_length': window_length,
        'n_snapshots': len(snapshots)
    }


def calculate_average_unassigned_entities(analysis_data):
    """
    Calculate average (mean) number of unassigned delivery entities over the post-warmup period.
    
    This metric provides a simple measure of queue size over time:
    - Low average: System handles load well
    - High average: Chronic queue buildup (even if stable)
    
    Complements growth_rate:
    - growth_rate ≈ 0, low average: healthy system
    - growth_rate ≈ 0, high average: stable but congested
    - growth_rate > 0: deteriorating (average less meaningful)
    
    Args:
        analysis_data: AnalysisData object with post_warmup_snapshots
        
    Returns:
        dict: Contains average_queue_size and supporting metadata
    """
    snapshots = analysis_data.post_warmup_snapshots
    
    # Handle edge case of no data
    if len(snapshots) == 0:
        return {
            'average_queue_size': 0.0,
            'n_snapshots': 0
        }
    
    # Extract unassigned entities time series
    unassigned_series = [s['unassigned_delivery_entities'] for s in snapshots]
    
    # Calculate average
    average_queue_size = sum(unassigned_series) / len(unassigned_series)
    
    return {
        'average_queue_size': average_queue_size,
        'n_snapshots': len(snapshots)
    }


def calculate_all_queue_dynamics_metrics(analysis_data):
    """
    Calculate all queue dynamics metrics for a replication.
    
    This is the main entry point called by the analysis pipeline.
    Returns a dict of scalar metrics (one-level pattern).
    
    Args:
        analysis_data: AnalysisData object
        
    Returns:
        dict: All queue dynamics metrics as scalars
    """
    growth_result = calculate_unassigned_entities_growth_rate(analysis_data)
    average_result = calculate_average_unassigned_entities(analysis_data)
    
    # Return only the scalar metrics for pipeline aggregation
    # Supporting metadata is available but not needed for results table
    return {
        'unassigned_entities_growth_rate': growth_result['growth_rate'],
        'average_unassigned_entities': average_result['average_queue_size']
    }