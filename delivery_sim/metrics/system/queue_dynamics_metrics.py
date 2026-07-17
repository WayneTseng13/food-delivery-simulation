# delivery_sim/metrics/system/queue_dynamics_metrics.py
def calculate_growth_rate(analysis_data, series_key):
    """
    Calculate growth rate of a queue series.

    Args:
        analysis_data: AnalysisData object with post_warmup_snapshots
        series_key: Snapshot key naming the series, e.g.
                    'unassigned_delivery_entities' (entity units) or
                    'unassigned_order_units' (order units)

    Returns:
        dict: growth_rate (units/minute) and supporting metadata
    """
    snapshots = analysis_data.post_warmup_snapshots

    if len(snapshots) < 2:
        return {
            'growth_rate': 0.0,
            'initial_value': 0.0,
            'terminal_value': 0.0,
            'window_length': 0.0,
            'n_snapshots': len(snapshots)
        }

    series = [s[series_key] for s in snapshots]

    initial_value = series[0]
    terminal_value = series[-1]

    initial_time = snapshots[0]['timestamp']
    terminal_time = snapshots[-1]['timestamp']
    window_length = terminal_time - initial_time

    if window_length > 0:
        growth_rate = (terminal_value - initial_value) / window_length
    else:
        growth_rate = 0.0

    return {
        'growth_rate': growth_rate,
        'initial_value': initial_value,
        'terminal_value': terminal_value,
        'window_length': window_length,
        'n_snapshots': len(snapshots)
    }


def calculate_average_queue_size(analysis_data, series_key):
    """
    Calculate time-average queue size for a series over the post-warmup period.

    Args:
        analysis_data: AnalysisData object with post_warmup_snapshots
        series_key: Snapshot key naming the series

    Returns:
        dict: average_queue_size and supporting metadata
    """
    snapshots = analysis_data.post_warmup_snapshots

    if len(snapshots) == 0:
        return {
            'average_queue_size': 0.0,
            'n_snapshots': 0
        }

    series = [s[series_key] for s in snapshots]
    average_queue_size = sum(series) / len(series)

    return {
        'average_queue_size': average_queue_size,
        'n_snapshots': len(snapshots)
    }


# ---- Backward-compatible wrappers (entity units) ----

def calculate_unassigned_entities_growth_rate(analysis_data):
    return calculate_growth_rate(analysis_data, 'unassigned_delivery_entities')


def calculate_average_unassigned_entities(analysis_data):
    return calculate_average_queue_size(analysis_data, 'unassigned_delivery_entities')


def calculate_all_queue_dynamics_metrics(analysis_data):
    """
    Calculate all queue dynamics metrics for a replication.

    Both unit conventions are reported:
    - *_entities:    entity units, a pending pair counts as 1 (dispatcher load).
                     Preserved for continuity with completed (ii) studies.
    - *_order_units: order units, a pending pair counts as 2 (customer backlog).
                     Mechanism-invariant; the series to use for (ii) vs (iii).

    Under assignment-time bundling the two coincide.
    """
    entities_growth = calculate_growth_rate(analysis_data, 'unassigned_delivery_entities')
    entities_average = calculate_average_queue_size(analysis_data, 'unassigned_delivery_entities')

    order_units_growth = calculate_growth_rate(analysis_data, 'unassigned_order_units')
    order_units_average = calculate_average_queue_size(analysis_data, 'unassigned_order_units')

    return {
        'unassigned_entities_growth_rate': entities_growth['growth_rate'],
        'average_unassigned_entities': entities_average['average_queue_size'],
        'unassigned_order_units_growth_rate': order_units_growth['growth_rate'],
        'average_unassigned_order_units': order_units_average['average_queue_size']
    }