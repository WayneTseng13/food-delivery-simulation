# delivery_sim/metrics/system/queue_dynamics_metrics.py

def calculate_growth_rate(analysis_data, series_key):
    """
    Growth rate (linear trend) of a queue series over the post-warmup window,
    estimated by ordinary least squares (OLS) slope.
 
    Fits queue(t) ~= a + b*t by minimizing summed squared residuals and returns
    b, in units/minute. Using all snapshots (not just endpoints) averages out
    per-snapshot fluctuation, giving a low-variance trend estimate. Sign and
    interpretation are unchanged: b > 0 => queue growing (unbounded regime),
    b ~ 0 => bounded, b < 0 => draining.
 
    The growth rate is the ONE queue metric that stays meaningful in the
    unbounded regime: unlike average backlog (which scales with run length when
    the queue never settles), the asymptotic slope is a genuine system property
    and is comparable across deteriorating systems (a smaller positive slope =
    slower deterioration).
 
    Args:
        analysis_data: AnalysisData object with post_warmup_snapshots.
        series_key: Snapshot key naming the series, e.g.
                    'unassigned_order_units' or 'unassigned_delivery_entities'.
 
    Returns:
        dict:
            growth_rate     OLS slope (units/minute)
            initial_value   first snapshot value  (kept for continuity)
            terminal_value  last snapshot value   (kept for continuity)
            window_length   t_last - t_first
            n_snapshots     number of snapshots used
            intercept       OLS intercept a (diagnostic; additive)
            r_squared       fraction of variance explained (diagnostic; additive)
    """
    snapshots = analysis_data.post_warmup_snapshots
    n = len(snapshots)
 
    # Need at least 2 points to define a slope; match old guard's return shape.
    if n < 2:
        return {
            'growth_rate': 0.0,
            'initial_value': 0.0,
            'terminal_value': 0.0,
            'window_length': 0.0,
            'n_snapshots': n,
            'intercept': 0.0,
            'r_squared': 0.0,
        }
 
    times = [s['timestamp'] for s in snapshots]
    series = [s[series_key] for s in snapshots]
 
    initial_value = series[0]
    terminal_value = series[-1]
    window_length = times[-1] - times[0]
 
    # ----- OLS slope, closed form -----
    # b = sum((t - t_mean)(y - y_mean)) / sum((t - t_mean)^2)
    # a = y_mean - b * t_mean
    t_mean = sum(times) / n
    y_mean = sum(series) / n
 
    s_tt = 0.0   # sum of (t - t_mean)^2
    s_ty = 0.0   # sum of (t - t_mean)(y - y_mean)
    for t, y in zip(times, series):
        dt = t - t_mean
        s_tt += dt * dt
        s_ty += dt * (y - y_mean)
 
    if s_tt > 0.0:
        slope = s_ty / s_tt
        intercept = y_mean - slope * t_mean
    else:
        # All snapshots at the same timestamp (degenerate); no slope defined.
        slope = 0.0
        intercept = y_mean
 
    # ----- R^2 (diagnostic: how linear is the trend) -----
    # 1 - SS_res / SS_tot. Guards the constant-series case (SS_tot == 0).
    ss_tot = 0.0
    ss_res = 0.0
    for t, y in zip(times, series):
        ss_tot += (y - y_mean) ** 2
        y_hat = intercept + slope * t
        ss_res += (y - y_hat) ** 2
    r_squared = (1.0 - ss_res / ss_tot) if ss_tot > 0.0 else 0.0
 
    return {
        'growth_rate': slope,
        'initial_value': initial_value,
        'terminal_value': terminal_value,
        'window_length': window_length,
        'n_snapshots': n,
        'intercept': intercept,
        'r_squared': r_squared,
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