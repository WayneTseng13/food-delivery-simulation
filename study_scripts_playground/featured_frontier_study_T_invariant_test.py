
"""

"""

# %% CELL 1: Enable Autoreload
%load_ext autoreload 
%autoreload 2

# %% CELL 2: Setup and Imports
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from delivery_sim.simulation.configuration import (
    StructuralConfig, OperationalConfig, ExperimentConfig, 
    LoggingConfig, ScoringConfig
)
from delivery_sim.infrastructure.infrastructure import Infrastructure
from delivery_sim.infrastructure.infrastructure_analyzer import InfrastructureAnalyzer
from delivery_sim.experimental.design_point import DesignPoint
from delivery_sim.experimental.experimental_runner import ExperimentalRunner
from delivery_sim.utils.logging_system import configure_logging

print("="*80)
print("CUSTOMER COMPLIANCE STUDY: HOW p MODULATES CURATION EFFECTIVENESS")
print("="*80)
print("Research Question: How does customer compliance affect X and X'?")
print("Building on Study 4: relaxes full-compliance assumption to a swept parameter")

# %% CELL 3: Logging Configuration
logging_config = LoggingConfig(
    console_level="INFO",
    component_levels={
        "services": "ERROR",
        "entities": "ERROR",
        "repositories": "ERROR",
        "utils": "ERROR",
        "system_data": "ERROR",
        "simulation.runner": "INFO",
        "infrastructure": "INFO",
        "experimental.runner": "INFO",
    }
)
configure_logging(logging_config)
print("✓ Logging configured")


# %% CELL 4: Infrastructure Configuration(s)
"""
OPERATIONAL STUDY: Single fixed infrastructure.
Focus is on varying operational parameters (compliance, curation, pairing).
"""

infrastructure_configs = [
    {
        'name': 'baseline',
        'config': StructuralConfig(
            delivery_area_size=10,
            num_restaurants=10,
            driver_speed=0.5
        )
    }
]

print(f"✓ Defined {len(infrastructure_configs)} infrastructure configuration")
for config in infrastructure_configs:
    struct_config = config['config']
    density = struct_config.num_restaurants / (struct_config.delivery_area_size ** 2)
    print(f"  • {config['name']}: {struct_config.num_restaurants} restaurants, "
          f"area={struct_config.delivery_area_size}km, density={density:.4f}/km²")

# %% CELL 5: Structural Seeds
"""
OPERATIONAL STUDY: Single seed (consistent with Studies 1-4).
"""

structural_seeds = [42]

print(f"✓ Structural seeds: {structural_seeds} (fixed layout for operational study)")

# %% CELL 6: Create Infrastructure Instances
"""
Create and analyze infrastructure instance.

Even for single infrastructure, we follow the standard pattern.
"""

infrastructure_instances = []

print("\n" + "="*50)
print("INFRASTRUCTURE INSTANCES CREATION")
print("="*50)

for infra_config in infrastructure_configs:
    for structural_seed in structural_seeds:
        
        # Create infrastructure instance
        instance_name = f"{infra_config['name']}_seed{structural_seed}"
        print(f"\n📍 Creating infrastructure: {instance_name}")
        
        infrastructure = Infrastructure(
            infra_config['config'],
            structural_seed
        )
        
        # Analyze infrastructure
        analyzer = InfrastructureAnalyzer(infrastructure)
        analysis_results = analyzer.analyze_complete_infrastructure()
        
        # Store instance with metadata
        infrastructure_instances.append({
            'name': instance_name,
            'infrastructure': infrastructure,
            'analysis': analysis_results,
            'config_name': infra_config['name'],
            'seed': structural_seed
        })
        
        print(f"  ✓ Infrastructure created and analyzed")
        print(f"    • Typical distance: {analysis_results['typical_distance']:.3f}km")
        print(f"    • Restaurant density: {analysis_results['restaurant_density']:.4f}/km²")

print(f"\n{'='*50}")
print(f"✓ Created {len(infrastructure_instances)} infrastructure instance(s)")
print(f"✓ Breakdown: {len(infrastructure_configs)} configs × {len(structural_seeds)} seeds")
print(f"{'='*50}")

# %% CELL 7: Scoring Configuration(s)
scoring_configs = [
    {
        'name': 'baseline',
        'config': ScoringConfig()
    }
]

print(f"✓ Defined {len(scoring_configs)} scoring configuration(s)")
for config in scoring_configs:
    print(f"  • {config['name']}")

# %% CELL 8: Operational Configuration(s)
"""
FEATURED / BLENDED CURATION FRONTIER STUDY.
 
Curation axis is a TAU SWEEP with two named endpoints, plus the U baseline:
 
    U            no curation (uniform). Fixed reference; p-invariant.
    operational  Policy X'' -- pure operational optimum. The tau=0 pole.
    blended(tau) Blend -- feature R_F when featuring penalty <= tau, else R_op.
                 tau in {1, 3, 5} km (chosen from the penalty-CDF calibration:
                 fire rate ~0.24 / 0.54 / 0.86 at ratio 7 -- spread across the
                 frontier interior).
    featured     Policy F -- always feature R_F. The tau=inf pole.
 
Ratios:
    7.0   control: comfortable; expect a SMOOTH frontier, no stability cliff.
    10.0  probe:   stressed but stable at X'' baseline (backlog growth ~ -0.003
                   at p=0.5, headroom to break). Where a cliff can be LOCATED.
    12.0  extreme: already near/at the cliff at X'' baseline (growth +0.012 at
                   p=0.5). The 'past-the-edge' reference; featuring can only
                   deepen an already-saturated regime here.
 
Compliance:
    0.5   realistic partial compliance (headline operating point).
    1.0   full-compliance upper bound (max featuring signal).
 
Featured restaurant: R10 (fixed, moderately off-center; E[leg] large, so the
operational cost of featuring is visible rather than marginal).
 
The design reads two ways from the SAME runs:
  - frontier view: operational-vs-business trade-off across tau (per ratio, p).
  - cliff view: at ratio 10/12, watch backlog growth cross zero and the business
    split (featured_origin_rate keeps rising while featured_throughput stalls)
    as tau increases.
"""
 
FEATURED_ID = 'R10'
 
compliance_probabilities = [0.5, 1.0]
target_arrival_interval_ratios = [10.0]
 
# Curation arm spec: (label, curation_policy, featured_id, tau)
#   tau is None where inapplicable (U, operational, featured).
#   The label encodes tau so CELL 16 can parse the frontier position.
CURATION_ARMS = [
    ('tau0',   'operational', FEATURED_ID,        None),
    ('tau3',   'blended',     FEATURED_ID, 3.0),
    ('tau5',   'blended',     FEATURED_ID, 5.0),
    ('tauInf', 'featured',    FEATURED_ID, None),   # tau fixed to +inf internally
]
 
pairing_params = {
    'pairing_enabled': True,
    'restaurants_proximity_threshold': 4.0,
    'customers_proximity_threshold': 3.0,
}
 
FIXED_SERVICE_CONFIG = {
    'mean_service_duration': 100,
    'service_duration_std_dev': 60,
    'min_service_duration': 30,
    'max_service_duration': 200,
}
 
operational_configs = []
 
for ratio in target_arrival_interval_ratios:
    for arm_label, curation_value, featured_id, tau in CURATION_ARMS:
        for p in compliance_probabilities:
            config_name = f"ratio_{ratio:.1f}_{arm_label}_p{p:.1f}"
 
            # Build kwargs, only passing featuring params when the arm uses them.
            config_kwargs = dict(
                mean_order_inter_arrival_time=1.0,
                mean_driver_inter_arrival_time=ratio,
                **pairing_params,
                **FIXED_SERVICE_CONFIG,
                curation_policy=curation_value,
                customer_compliance_probability=p,
            )
            if featured_id is not None:
                config_kwargs['featured_restaurant_id'] = featured_id
            if tau is not None:
                config_kwargs['featured_tau'] = tau
 
            operational_configs.append({
                'name': config_name,
                'config': OperationalConfig(**config_kwargs),
            })
 
print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Sweep dimensions:")
print(f"  • Compliance probabilities: {compliance_probabilities}")
print(f"  • Arrival interval ratios:  {target_arrival_interval_ratios}")
print(f"  • Curation arms (tau sweep): {[a[0] for a in CURATION_ARMS]}")
print(f"  • Featured restaurant:      {FEATURED_ID}")
print(f"✓ Cells = {len(target_arrival_interval_ratios)} ratios "
      f"× {len(CURATION_ARMS)} arms × {len(compliance_probabilities)} p "
      f"= {len(operational_configs)}")
 
print("\nConfiguration breakdown:")
for config in operational_configs:
    oc = config['config']
    ratio = oc.mean_driver_inter_arrival_time / oc.mean_order_inter_arrival_time
    pol = oc.curation_policy if oc.curation_policy is not None else "U"
    fid = getattr(oc, 'featured_restaurant_id', None)
    tau = getattr(oc, 'featured_tau', None)
    print(f"  • {config['name']}: ratio={ratio:.1f}, policy={pol}, "
          f"featured={fid}, tau={tau}, p={oc.customer_compliance_probability:.1f}")

# %% CELL 9: Design Point Creation
design_points = {}

print("\n" + "="*50)
print("DESIGN POINTS CREATION")
print("="*50)

for infra_instance in infrastructure_instances:
    for op_config in operational_configs:
        for scoring_config_dict in scoring_configs:
            design_name = op_config['name']
            design_points[design_name] = DesignPoint(
                infrastructure=infra_instance['infrastructure'],
                operational_config=op_config['config'],
                scoring_config=scoring_config_dict['config'],
                name=design_name
            )
            print(f"  ✓ Design point: {design_name}")

print(f"\n{'='*50}")
print(f"✓ Created {len(design_points)} design points")
print(f"✓ Breakdown: {len(infrastructure_instances)} infra × "
      f"{len(operational_configs)} operational × {len(scoring_configs)} scoring")
print(f"{'='*50}")

# %% CELL 10: Experiment Configuration
experiment_config = ExperimentConfig(
    simulation_duration=2500,  # Same as Studies 3 & 4 for direct comparison
    num_replications=10,
    operational_master_seed=42,
    collection_interval=1.0
)

total_runs = len(design_points) * experiment_config.num_replications
estimated_time = total_runs * 5

print(f"✓ Experiment configuration:")
print(f"  • Simulation duration: {experiment_config.simulation_duration} minutes")
print(f"  • Replications per design point: {experiment_config.num_replications}")
print(f"  • Operational master seed: {experiment_config.operational_master_seed}")
print(f"  • Collection interval: {experiment_config.collection_interval} minutes")
print(f"\n✓ Execution plan:")
print(f"  • Total simulation runs: {total_runs}")
print(f"  • Estimated time: ~{estimated_time:.0f} seconds (~{estimated_time/60:.1f} minutes)")

# %% CELL 11: Execute Experimental Study
print("\n" + "="*50)
print("EXECUTING EXPERIMENTAL STUDY")
print("="*50)

runner = ExperimentalRunner()
study_results = runner.run_experimental_study(design_points, experiment_config)

print(f"\n{'='*50}")
print("✅ EXPERIMENTAL STUDY COMPLETE")
print(f"{'='*50}")
print(f"✓ Executed {len(design_points)} design points")
print(f"✓ Total simulations: {total_runs}")

# %% CELL 12: Time Series Data Processing for Warmup Analysis
print("\n" + "="*50)
print("TIME SERIES DATA PROCESSING FOR WARMUP ANALYSIS")
print("="*50)

from delivery_sim.warmup_analysis.time_series_processing import extract_warmup_time_series

print("Processing time series data for warmup detection...")

all_time_series_data = extract_warmup_time_series(
    study_results=study_results,
    design_points=design_points,
    metrics=['active_drivers', 'available_drivers', 'unassigned_delivery_entities'],
    moving_average_window=100
)

print(f"✓ Time series processing complete for {len(all_time_series_data)} design points")
print(f"✓ Metrics extracted: active_drivers, available_drivers, unassigned_delivery_entities")
print(f"✓ Ready for warmup analysis visualization")

# %% CELL 13: Warmup Analysis Visualization
print("\n" + "="*50)
print("WARMUP ANALYSIS VISUALIZATION")
print("="*50)

from delivery_sim.warmup_analysis.visualization import WelchMethodVisualization
import matplotlib.pyplot as plt

print("Creating warmup analysis plots...")

viz = WelchMethodVisualization(figsize=(16, 10))

# Group design points by arrival interval ratio
ratio_groups = {}
for design_name in all_time_series_data.keys():
    ratio_str = design_name.split('_')[1]
    ratio = float(ratio_str)
    if ratio not in ratio_groups:
        ratio_groups[ratio] = []
    ratio_groups[ratio].append(design_name)

print(f"✓ Grouped {len(all_time_series_data)} design points by {len(ratio_groups)} ratios")

plot_count = 0
for ratio in sorted(ratio_groups.keys()):
    print(f"\nRatio {ratio:.1f} (Driver intervals {ratio:.1f}× order intervals):")
    for design_name in sorted(ratio_groups[ratio]):
        plot_title = f"Warmup Analysis: {design_name}"
        time_series_data = all_time_series_data[design_name]
        fig = viz.create_warmup_analysis_plot(time_series_data, title=plot_title)
        plt.show()
        print(f"    ✓ {design_name} plot displayed")
        plot_count += 1

print(f"\n✓ Warmup analysis visualization complete")
print(f"✓ Created {plot_count} warmup analysis plots")

# %% CELL 14: Warmup Period Determination
print("\n" + "="*50)
print("WARMUP PERIOD DETERMINATION")
print("="*50)

# Same warmup as Studies 3 & 4: infrastructure and ratio range are identical.
# Driver capacity (which the warmup criterion is based on) is independent of
# curation policy and compliance probability, so this carries over.
uniform_warmup_period = 500  # UPDATE based on visual inspection if needed

print(f"✓ Warmup period set: {uniform_warmup_period} minutes")
print(f"✓ Based on driver-capacity convergence (Welch's method)")
print(f"✓ Analysis window: {experiment_config.simulation_duration - uniform_warmup_period} minutes of post-warmup data")

# %% CELL 15: Process Through Analysis Pipeline
print("\n" + "="*80)
print("PROCESSING THROUGH ANALYSIS PIPELINE")
print("="*80)

from delivery_sim.analysis_pipeline.pipeline_coordinator import ExperimentAnalysisPipeline

# Initialize pipeline.
# 'curation_metrics' enabled to capture X's fallback rate and X's branch activation rates.
pipeline = ExperimentAnalysisPipeline(
    warmup_period=uniform_warmup_period,
    enabled_metric_types=['order_metrics', 'system_metrics',
                          'system_state_metrics', 'queue_dynamics_metrics',
                          'curation_metrics'], 
    confidence_level=0.95
)

design_analysis_results = {}

print(f"\nProcessing {len(study_results)} design points...")
print(f"Warmup period: {uniform_warmup_period} minutes")
print(f"Confidence level: 95%\n")

for i, (design_name, replication_results) in enumerate(study_results.items(), 1):
    print(f"[{i:2d}/{len(study_results)}] Analyzing {design_name}...")
    analysis_result = pipeline.analyze_experiment(replication_results)
    design_analysis_results[design_name] = analysis_result
    print(f"    ✓ Processed {analysis_result['num_replications']} replications")

print(f"\n✓ Analysis pipeline complete for all {len(design_analysis_results)} design points")
print(f"✓ Results stored in 'design_analysis_results'")

# %% CELL 16: Extract and Present Key Metrics
# ==============================================================================
# FEATURED / BLENDED CURATION FRONTIER STUDY -- settled minimal metric matrix.
#
# One flat table: every (ratio, arm, p) cell is a row, sorted ratio -> tau -> p.
# Every value is point estimate +/- 95% CI half-width.
#
# Columns, by purpose:
#   REGIME ID        : BacklogGrowth (OLS slope; CI vs 0 classifies regime),
#                      AvgBacklog (level; run-length-dependent when unstable)
#   CUSTOMER EXP     : Fulfillment; + Assign / Pickup / Delivery (decomposition)
#   MECHANISM        : PairingRate (consolidation-buyback probe)
#   BUSINESS         : F_origin (demand captured at R10)
#
# Dropped (deliberately): F_thru, F_complete, F_recomm -- see metric-matrix notes.
# Regime rule: in UNSTABLE cells (growth CI clears 0), compare growth ONLY; other
# columns are run-length-biased there and are descriptive, not comparative.
# ==============================================================================

print("\n" + "="*160)
print("KEY PERFORMANCE METRICS: FEATURED / BLENDED CURATION FRONTIER STUDY  (featured = R10)")
print("="*160)

import re

_DESIGN_NAME_RE = re.compile(
    r'ratio_([\d.]+)_(U|tau0|tau1|tau3|tau5|tauInf)_p([\d.]+)')

_ARM_ORDER = {'U': 0, 'tau0': 1, 'tau1': 2, 'tau3': 3, 'tau5': 4, 'tauInf': 5}
_ARM_LABEL = {
    'U': 'U', 'tau0': "X''", 'tau1': 'blend(1)', 'tau3': 'blend(3)',
    'tau5': 'blend(5)', 'tauInf': 'F',
}


def extract_design_point(design_name):
    m = _DESIGN_NAME_RE.match(design_name)
    if not m:
        return None, None, None
    return float(m.group(1)), m.group(2), float(m.group(3))


def point_and_ci_width(metric_dict, default_estimate=None):
    """Return (point_estimate, ci_half_width) from a metric's stats dict."""
    if not metric_dict:
        return default_estimate, None
    est = metric_dict.get('point_estimate', default_estimate)
    ci = metric_dict.get('confidence_interval', [None, None])
    half = (ci[1] - ci[0]) / 2 if ci[0] is not None else None
    return est, half


# ----- pull every cell -----
rows = []
for design_name, analysis_result in design_analysis_results.items():
    ratio, arm, p = extract_design_point(design_name)
    if ratio is None:
        continue

    scis = analysis_result.get('statistics_with_cis', {})
    om = scis.get('order_metrics', {})
    qd = scis.get('queue_dynamics_metrics', {})
    sm = scis.get('system_metrics', {})
    cm = scis.get('curation_metrics', {})

    r = dict(ratio=ratio, arm=arm, p=p)

    # customer experience + attribution (order_metrics, mean_of_means)
    r['fulfil'], r['fulfil_ci'] = point_and_ci_width(om.get('fulfillment_time', {}).get('mean_of_means', {}))
    r['assign'], r['assign_ci'] = point_and_ci_width(om.get('assignment_time', {}).get('mean_of_means', {}))
    r['pickup'], r['pickup_ci'] = point_and_ci_width(om.get('pickup_travel_time', {}).get('mean_of_means', {}))
    r['deliv'],  r['deliv_ci']  = point_and_ci_width(om.get('delivery_travel_time', {}).get('mean_of_means', {}))

    # regime id (queue_dynamics; order-unit series, mechanism-invariant)
    r['growth'],  r['growth_ci']  = point_and_ci_width(qd.get('unassigned_order_units_growth_rate', {}))
    r['backlog'], r['backlog_ci'] = point_and_ci_width(qd.get('average_unassigned_order_units', {}))

    # mechanism
    r['pair'], r['pair_ci'] = point_and_ci_width(sm.get('system_pairing_rate', {}), default_estimate=None)

    # business
    r['orig'], r['orig_ci'] = point_and_ci_width(cm.get('featured_origin_rate', {}))

    rows.append(r)

rows.sort(key=lambda r: (r['ratio'], _ARM_ORDER.get(r['arm'], 99), r['p']))


# ----- formatters -----
def val(est, half, w=6, d=3):
    if est is None:
        return f"{'--':>{w}}"
    if half is None:
        return f"{est:{w}.{d}f}"
    return f"{est:{w}.{d}f} ±{half:.{d}f}"


def pct(est, half, d=1):
    if est is None:
        return f"{'--':>6}"
    if half is None:
        return f"{est*100:.{d}f}%"
    return f"{est*100:.{d}f} ±{half*100:.{d}f}%"


# ----- header -----
H = (f"{'Ratio':>5} {'Policy':>9} {'p':>4} "
     f"| {'Growth':>16} {'Backlog':>14} "
     f"| {'Fulfil':>13} {'Assign':>13} {'Pickup':>13} {'Deliv':>13} "
     f"| {'Pairing':>14} "
     f"| {'F_origin':>14}")
print(H)
print("=" * len(H))

prev_ratio = None
for r in rows:
    if prev_ratio is not None and r['ratio'] != prev_ratio:
        print("-" * len(H))
    prev_ratio = r['ratio']

    line = (
        f"{r['ratio']:>5.1f} {_ARM_LABEL.get(r['arm'], r['arm']):>9} {r['p']:>4.1f} "
        f"| {val(r['growth'], r['growth_ci'], 6, 4):>15}"
        f"{val(r['backlog'], r['backlog_ci'], 6, 2):>14} "
        f"| {val(r['fulfil'], r['fulfil_ci'], 5, 2):>13}"
        f" {val(r['assign'], r['assign_ci'], 5, 2):>13}"
        f" {val(r['pickup'], r['pickup_ci'], 5, 2):>13}"
        f" {val(r['deliv'], r['deliv_ci'], 5, 2):>13} "
        f"| {pct(r['pair'], r['pair_ci']):>14} "
        f"| {pct(r['orig'], r['orig_ci']):>14}"
    )
    print(line)

print("=" * len(H))
print("All values: point estimate ± 95% CI half-width.  '--' = not applicable.")
print("REGIME: classify by Growth CI. In UNSTABLE cells, compare Growth ONLY --")
print("        Backlog/Fulfil/Assign/etc. are run-length-biased there (descriptive, not comparative).")
print("Customer exp: Fulfil = Assign + Pickup + Deliv (min). Attribution: featuring should inflate Deliv (R-C leg).")
print("Mechanism: Pairing = consolidation-buyback probe (flat/falling across tau => no buyback).")
print("Business: F_origin = arrivals routed to R10 (organic share at U/X''; rises with tau).")
# %% CELL 17: Frontier Plot — business capture vs operational cost
# ==============================================================================
# The operational-business trade-off traced by tau.
#   x = F_origin (% of demand at R10);  y = fulfillment time (min)
#   frontier line = X'' -> tau1 -> tau3 -> tau5 -> F, in tau order, per (ratio,p).
#   U shown as a separate REFERENCE MARKER (no-curation baseline; not a tau point).
#   CI shown as a light shaded band (not error bars) for visual calm.
#   One panel per ratio; ratio 12 omitted (unbounded -> fulfillment run-length-biased).
# Reads `rows` from CELL 16.
# ==============================================================================

import matplotlib.pyplot as plt

assert 'rows' in dir(), "CELL 17 needs `rows` from CELL 16. Run CELL 16 first."

STABLE_RATIOS = [7.0, 10.0]
FEATURED_ID = 'R10'
YCOL, YCI, YLABEL = 'fulfil', 'fulfil_ci', 'Fulfillment time (min)'

_ARM_ORDER = {'tau0': 0, 'tau1': 1, 'tau3': 2, 'tau5': 3, 'tauInf': 4}   # frontier arms
_ARM_LABEL = {'tau0': "X''", 'tau1': 'τ1', 'tau3': 'τ3', 'tau5': 'τ5', 'tauInf': 'F'}

_pcolor = {0.5: '#1565C0', 1.0: '#2E7D32'}
_pstyle = {0.5: '--', 1.0: '-'}

plot_ratios = [r for r in sorted(set(r['ratio'] for r in rows)) if r in STABLE_RATIOS]
ps = sorted(set(r['p'] for r in rows))


def series(ratio, p, arms_filter):
    block = [r for r in rows
             if r['ratio'] == ratio and r['p'] == p and r['arm'] in arms_filter]
    block.sort(key=lambda r: _ARM_ORDER.get(r['arm'], 99))
    xs = [r['orig'] * 100 for r in block]
    ys = [r[YCOL] for r in block]
    ye = [(r[YCI] or 0) for r in block]
    arms = [r['arm'] for r in block]
    return xs, ys, ye, arms


fig, axes = plt.subplots(1, len(plot_ratios), figsize=(6.4 * len(plot_ratios), 5))
if len(plot_ratios) == 1:
    axes = [axes]

for ax, ratio in zip(axes, plot_ratios):
    for p in ps:
        # frontier line (X''..F)
        xs, ys, ye, arms = series(ratio, p, _ARM_ORDER)
        if xs and not any(v is None for v in xs + ys):
            color = _pcolor[p]
            ax.fill_between(xs, [y - e for y, e in zip(ys, ye)],
                            [y + e for y, e in zip(ys, ye)],
                            color=color, alpha=0.12, zorder=1)
            ax.plot(xs, ys, color=color, linestyle=_pstyle[p], marker='o',
                    markersize=6, linewidth=2, label=f"p = {p:.1f}", zorder=3)
            if p == 1.0:
                for x, y, arm in zip(xs, ys, arms):
                    if arm in ('tau0', 'tauInf'):
                        ax.annotate(_ARM_LABEL[arm], (x, y),
                                    textcoords="offset points", xytext=(6, 6),
                                    fontsize=10, fontweight='bold', color=color)


    ax.set_title(f"Ratio {ratio:.0f}", fontsize=12)
    ax.set_xlabel("Business capture — F_origin (% of demand at R10)")
    ax.set_ylabel(YLABEL)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.set_xlim(left=0)

fig.suptitle(
    f"Operational–business frontier traced by τ   (featured = {FEATURED_ID})\n"
    f"frontier = X'' → τ1 → τ3 → τ5 → F;  ★ = U (no-curation reference)",
    fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.92])
plt.show()

print("Reading it: along a line, left→right raises τ (X''→F), buying capture at")
print("operational cost. Convex = capture cheap near X'', expensive near F. U (★)")
print("sits off the frontier — same organic capture as X'' but far worse fulfillment,")
print("showing curation's operational value independent of featuring.")

# %%