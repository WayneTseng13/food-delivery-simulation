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


def calculate_system_throughput(analysis_data):
    """
    Throughput as delivered orders per unit time over the fixed post-warmup window.
 
    Regime behaviour:
      - Bounded: throughput -> arrival rate. Equal across policies under CRN at a
        given ratio, so UNINFORMATIVE there; backlog / wait discriminate.
      - Unbounded: throughput -> server clearing capacity. Discriminates here -- a
        policy that realizes bundles (one driver clears two orders per trip) raises
        the clearing rate, which backlog (measuring distance-past-cliff) cannot
        isolate. Note the benefit is consolidation-mediated, not travel-mediated:
        edge-manufacture LENGTHENS individual trips (pays tax); throughput rises
        only if realized bundling outweighs that per-delivery cost.
 
    Contrast system_completion_rate (delivered / arrived): horizon-censored, and
    with inter-arrival 1.0 and a hard sim end it is strictly < 1.0 even for healthy
    bounded systems. Keep completion_rate as a DESCRIPTIVE regime flag; do not
    attribute policy effects on it. Throughput's shared truncation is a CONSTANT
    offset at fixed (ratio, window), so it differences out cleanly in X' - X''.
 
    Window denominator is analysis_data.analysis_window_length
    (= simulation_duration - warmup_period), identical across every replication and
    policy -- exact and comparable, unlike a snapshot-derived span.
 
    Args:
        analysis_data: AnalysisData with cohort_completed_orders and
                       analysis_window_length populated.
 
    Returns:
        dict: system_throughput (orders/min), total_delivered, window_length.
    """
    total_delivered = len(analysis_data.cohort_completed_orders)
    window_length = analysis_data.analysis_window_length
 
    if window_length is None or window_length <= 0:
        # Window not supplied (older prepare_analysis_data call site) or invalid.
        # Return 0.0 rather than raising, so the metric degrades gracefully; the
        # 0.0 will be visible in results as a signal that the window wasn't wired.
        throughput = 0.0
        window_length = 0.0
    else:
        throughput = total_delivered / window_length
 
    return {
        'system_throughput': throughput,
        'total_delivered': total_delivered,
        'window_length': window_length,
    }


def calculate_arrival_state_rates(analysis_data): 
    """ 
    Fraction of arrivals that found the system in each state at arrival time.

    Read from order.arrival_state, stamped at arrival for EVERY policy (U
    included) BEFORE any recommendation. One degree of freedom: an arrival is
    either 'immediate' (>=1 idle driver present) or 'queued' (none), so the two
    rates sum to 1.

    Denominator is ALL cohort orders (post-warmup arrivals) -- NOT completed
    orders. This is the key difference from immediate_assignment_rate:

        immediate_assignment_rate  -- numerator/denominator over COMPLETED orders.
            Conditions on completion, so in the unbounded regime it drops the
            (disproportionately queued) censored backlog and OVERSTATES the
            immediate share. A performance metric ("of served orders, how many
            instant"), regime-sensitive.

        arrival_immediate_rate     -- over ALL arrivals. Uncensored, regime-robust.
            A system-state metric ("at arrival, how often was a driver idle").

    Both are legitimate; they answer different questions. Prefer this one for the
    true arrival-state mix and for the endogenous-state diagnostic vs tau (as
    featuring bites, efficiency drops, idle drivers thin out, this shifts toward
    'queued').

    Args:
        analysis_data: AnalysisData with cohort_orders.

    Returns:
        dict: total_arrivals, immediate_arrivals,
            arrival_immediate_rate, arrival_queued_rate.
    """
    cohort_orders = analysis_data.cohort_orders
    total = len(cohort_orders)

    # Orders with arrival_state stamped. Guards against pre-instrumentation runs
    # or any order that missed the stamp (should be none in normal runs).
    stamped = [o for o in cohort_orders if o.arrival_state is not None]
    n = len(stamped)

    if n == 0:
        return {
            'total_arrivals': total,
            'immediate_arrivals': 0,
            'arrival_immediate_rate': 0.0,
            'arrival_queued_rate': 0.0,
        }

    immediate = sum(1 for o in stamped if o.arrival_state == 'immediate')

    return {
        'total_arrivals': n,
        'immediate_arrivals': immediate,
        'arrival_immediate_rate': immediate / n,
        'arrival_queued_rate':    (n - immediate) / n,
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

    throughput_metrics = calculate_system_throughput(analysis_data)    # NEW

    arrival_state_metrics = calculate_arrival_state_rates(analysis_data)   # NEW
    
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
        'total_immediate_assignments': immediate_assignment_metrics['immediate_assignments'],
        
        #Throughput metrics
        'system_throughput': throughput_metrics['system_throughput'],        # NEW

        # Arrival-state mix (uncensored; all policies)                     # NEW
        'arrival_immediate_rate': arrival_state_metrics['arrival_immediate_rate'],
        'arrival_queued_rate':    arrival_state_metrics['arrival_queued_rate'],
        'total_arrivals':         arrival_state_metrics['total_arrivals'],
    }