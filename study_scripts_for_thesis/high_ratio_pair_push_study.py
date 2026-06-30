# customer_compliance_study.py
"""
Customer Compliance Study: Effect of Customer Compliance Probability on
Curation Policy Performance

Research Question: How does customer compliance probability (p) modulate the
effectiveness of curation policies X (R-D proximity) and X' (state-adaptive)?
Where does X' separate from X most cleanly when compliance is partial?

Building on Previous Studies:
- Study 1 (Arrival Interval Ratio) established the regime structure under no
  curation, no pairing.
- Study 2 (Pairing Effect) demonstrated pairing's capacity-expansion effect.
- Study 3 (R-D Curation, p=1) quantified Policy X's pickup-leg saving and the
  collapsing operating envelope at high load.
- Study 4 (State-Adaptive Curation, p=1) introduced Policy X' and showed it
  produces a regime change at p=1 — but the result was contingent on the upper-
  bound full-compliance assumption.

This Study (Customer Compliance):
- Treats p as an explicit experimental parameter rather than a fixed assumption.
- Sweeps p ∈ {0.0, 0.1, 0.5, 1.0}, including p = 1/N = 0.1 
  as the neutral null at which curation has no aggregate effect.
- Tests both X and X' under partial compliance to learn whether X' is more or
  less robust to non-compliance than X.
- Crosses with pairing ON/OFF — lower compliance should leave more queue around
  even at moderate ratios, which may enable X's pair_queued branch to fire more
  often and exercise the "active push for pair formation" mechanism.

Mechanism — customer compliance modelling:
- At each order arrival, the active curation policy attempts to produce a
  recommendation given current system state.
- If a recommendation is produced: the customer accepts it with probability p
  (compliance), and rejects with probability 1-p. On rejection, the customer
  samples uniformly from the remaining restaurants (excluding the recommended
  one).
- If no recommendation is produced (X in fallback when no idle drivers): the
  customer samples uniformly over all restaurants. p is not applied because
  there is no recommendation to comply with.

Design Pattern (4 × 4 × 2 × 3 factorial):
- 4 curation policies: uniform (U), proximity (X),
                       state_adaptive_no_pair_push (X''), state_adaptive (X')
- 4 compliance probabilities: p = 0.0, 0.1, 0.5, 1.0
- 2 pairing conditions: OFF, ON
- 3 arrival interval ratios: 5.0, 6.0, 7.0

Total Design Points: 4 × 4 × 2 × 3 = 96

Redundancy (kept for sanity checking, not engineered away):
- U × {4 p values} → 4 cells per (ratio, pairing) that should be equal.
- X'' and X' under pairing OFF → should be bit-identical cell-by-cell across all p.

Reference points:
- Policy X at p=1.0 reproduces Study 3.
- Policy X' at p=1.0 reproduces Study 4.
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

# %% CELL 3.5: Research Question
"""
Document research question and its evolution.
"""

print("\n" + "="*80)
print("RESEARCH QUESTION")
print("="*80)

research_question = """
(1) How does the curation effect of Policy X and Policy X' scale as customer
    compliance probability decreases from 1.0 to 0.0?
(2) Is X' more or less robust to non-compliance than X — that is, does X' retain
    more of its advantage at low p, or do both policies degrade similarly?
(3) Under partial compliance, does the residual queue create conditions for X''s
    pair_queued branch to fire meaningfully and exercise the "active push for
    pair formation" mechanism that Study 4 could not observe under p=1?
"""

context = """
Study 4 showed Policy X' produces a regime change under full compliance (p=1):
at ratio 7.0 OFF, X' brings queue from 106 (under U or X-in-fallback) down to
under 1, by triggering a reinforcement loop where short driver cycles maintain
D > 0 which maintains short cycles.

The result is contingent on customers always accepting the platform's
recommendation. Under partial compliance, the platform's signal is partially
ignored, and X's effectiveness should degrade. The shape and rate of that
degradation is the central question.

Compliance acts on the same axis curation does — demand-side coordination —
but in the opposite direction: curation tries to steer customer choice, while
non-compliance is the customer ignoring the steering. p indexes how much of
the platform's curation signal actually reaches the system.

A secondary expectation: under partial compliance, X's reinforcement loop may
not fully form, leaving residual queue. That residual queue is exactly what
X''s pair_queued branch needs to act on — so partial compliance may be the
regime where the multi-branch design of X' actually exercises all its branches.
Study 4 could not see this because the reinforcement loop emptied the queue.
"""

sub_questions = """
1. Performance degradation curve (assignment time, queue size, growth rate)
   - For each (ratio, pairing, curation) cell, sweep p ∈ {0.0, 0.5, 1.0}.
   - Expected: monotonic degradation as p decreases. Magnitude and shape of the
     curve characterises how much of the curation effect depends on compliance.
   - Endpoint check: p=1.0 reproduces Study 4 results; p=0.0 with X should
     resemble Policy U (recommendation produced but always ignored, customer
     samples among remaining restaurants — very close to uniform).

2. X vs X' separation under partial compliance
   - At p=1.0 (Study 4), X' dominated X by orders of magnitude at high load.
   - At p=0.5, does X' still dominate, or does the gap close? If the gap closes
     proportionally, X's benefit was primarily from "joint R-D+R-C optimisation
     under full compliance" rather than from the multi-branch architecture.
     If X' is more robust than X (larger relative advantage at lower p), the
     architecture itself adds value.

3. Branch activation rates of X' under partial compliance
   - Study 4 found single_immediate dominated (76-97% of arrivals) because the
     reinforcement loop kept D > 0.
   - Hypothesis: at p < 1, the loop weakens, queue accumulates, and pair_queued
     and single_queued branches activate more often. Track how the branch mix
     shifts with p — this is where the multi-branch design earns its keep.

4. Pairing rate under partial compliance
   - At p=1 with X', the queue emptied so quickly that pairing rate dropped
     even with pairing ON.
   - At p < 1, the residual queue should re-enable pair formation. Does X' raise
     the pairing rate above what U or X would produce at the same p? If yes, the
     pair_queued branch is doing real pair-construction work.
"""

scope = """
- Single fixed infrastructure (seed=42), consistent with Studies 1-4.
- Three ratios: 5.0 (critical), 6.0 (no-pairing boundary), 7.0 (high stress).
- Four compliance levels spanning the parameter range:
  - p=1.0: upper-bound reference (full compliance; reproduces Study 4 design points).
  - p=0.5: realistic partial-compliance operating point.
  - p=0.1 (= 1/N): neutral null — post-curation selection probability equals
    the uniform baseline 1/N. At this point curation has no aggregate effect on
    the order stream; the system should behave statistically identically to
    Policy U (Study 4 reference) within Monte Carlo noise. Serves as both a
    consistency check on the compliance machinery and the natural reference
    point against which curation effects are measured.
  - p=0.0: lower-bound worst-case (anti-recommendation regime; recommendation
    always rejected, customer samples uniformly from non-recommended
    restaurants). Not behaviorally realistic but informative as a worst-case
    bound on the curation-compliance interaction.
- Four curation policies: U,X,X'',X'
- Baseline intensity only (order_interval=1.0).
"""

analysis_focus = """
Primary: assignment time, queue size, and growth rate as functions of p, holding
ratio, pairing, and curation policy fixed. The shape of this curve characterises
compliance sensitivity.
Secondary: branch activation rates for X' under partial compliance (do
pair_queued and single_queued fire more often when the reinforcement loop
breaks?); pairing rate under partial compliance (does X' construct pairs
beyond what pairing alone produces when the queue is non-empty?).
Tertiary: endpoint reproducibility checks — X at p=1.0 should match Study 3
results within Monte Carlo noise; X' at p=1.0 should match Study 4.
"""

evolution_notes = """
Study sequence positioning:

Study 1: Arrival Interval Ratio Study (COMPLETE) — regime structure.
Study 2: Pairing Effect Study (COMPLETE) — supply-side coordination mechanism.
Study 3: R-D Curation Study (COMPLETE, p=1) — demand-side coordination mechanism
         under upper-bound compliance.
Study 4: State-Adaptive Curation Study (COMPLETE, p=1) — state-adaptive demand-
         side coordination under upper-bound compliance. X' produced a regime
         change but the result is contingent on p=1.

Customer Compliance Study (THIS STUDY)
- Relaxes the full-compliance assumption that was held fixed in Studies 3 and 4.
- Treats p as an explicit experimental parameter.
- Architecturally, this study is enabled by the customer-compliance machinery
  added after Study 4: the curation policy produces a recommendation (or None),
  and the customer-behaviour layer decides whether to accept it based on p.
"""

print(research_question)
print("\n" + "-"*80)
print("CONTEXT & MOTIVATION")
print("-"*80)
print(context)
print("\n" + "-"*80)
print("SUB-QUESTIONS & HYPOTHESES")
print("-"*80)
print(sub_questions)
print("\n" + "-"*80)
print("SCOPE & BOUNDARIES")
print("-"*80)
print(scope)
print("\n" + "-"*80)
print("KEY METRICS & ANALYSIS FOCUS")
print("-"*80)
print(analysis_focus)
print("\n" + "-"*80)
print("EVOLUTION NOTES")
print("-"*80)
print(evolution_notes)
print("\n" + "="*80)
print("✓ Research question documented - reference this to guide analysis decisions")
print("="*80)

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
CUSTOMER COMPLIANCE STUDY: 4 × 4 × 2 × 3 factorial over compliance probability,
curation policy, pairing condition, and arrival interval ratio.

For each (ratio, pairing, curation) cell, sweep p ∈ {0.0, 0.1, 0.5, 1.0}.
p = 1/N = 0.1 is the neutral null at which curation has no aggregate effect.


"""

# Compliance probability sweep.
# p = 0.0       : worst-case lower bound (anti-recommendation regime)
# p = 1/N = 0.1 : neutral null — post-curation selection probability equals
#                 baseline; should reproduce U behavior within MC noise.
# p = 0.5       : realistic partial-compliance operating point
# p = 1.0       : full-compliance upper bound
compliance_probabilities = [0.1, 0.5, 1.0]

# Arrival interval ratios (same as Studies 3 and 4 for direct comparison)
target_arrival_interval_ratios = [10.0,12.0]

# Pairing parameter blocks
pairing_params = {
    'pairing_enabled': True,
    'restaurants_proximity_threshold': 4.0,
    'customers_proximity_threshold': 3.0,
}



# Curation policy values
UNIFORM = None
PROXIMITY = 'proximity'
STATE_ADAPTIVE_NO_PAIR_PUSH = 'state_adaptive_no_pair_push'
STATE_ADAPTIVE = 'state_adaptive'

# Fixed service duration configuration
FIXED_SERVICE_CONFIG = {
    'mean_service_duration': 100,
    'service_duration_std_dev': 60,
    'min_service_duration': 30,
    'max_service_duration': 200
}

# Build operational configs
operational_configs = []

for ratio in target_arrival_interval_ratios:
    for pairing_label, pairing_block in [('pairing', pairing_params)]:
                                         
        for curation_label, curation_value in [
            ('uniform',                     UNIFORM),
            ('proximity',                   PROXIMITY),
            ('state_adaptive_no_pair_push', STATE_ADAPTIVE_NO_PAIR_PUSH),
            ('state_adaptive',              STATE_ADAPTIVE),
        ]:
            for p in compliance_probabilities:
                config_name = (
                    f"ratio_{ratio:.1f}_{pairing_label}_{curation_label}_p{p:.1f}"
                )
                operational_configs.append({
                    'name': config_name,
                    'config': OperationalConfig(
                        mean_order_inter_arrival_time=1.0,
                        mean_driver_inter_arrival_time=ratio,
                        **pairing_block,
                        **FIXED_SERVICE_CONFIG,
                        curation_policy=curation_value,
                        customer_compliance_probability=p,
                    )
                })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Sweep dimensions:")
print(f"  • Compliance probabilities: {compliance_probabilities}")
print(f"  • Arrival interval ratios:  {target_arrival_interval_ratios}")
print(f"  • Pairing conditions:       OFF, ON")
print(f"  • Curation policies:        U, X, X'', X'")
print(f"✓ Each (ratio, pairing, curation) cell has {len(compliance_probabilities)} p values")

print("\nConfiguration breakdown:")
for config in operational_configs:
    op_config = config['config']
    ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
    pairing_status = "PAIRING ON" if op_config.pairing_enabled else "PAIRING OFF"
    curation_label = (
        op_config.curation_policy.upper()
        if op_config.curation_policy is not None
        else "NONE"
    )
    p = op_config.customer_compliance_probability
    print(f"  • {config['name']}: ratio={ratio:.1f}, {pairing_status}, "
          f"CURATION {curation_label}, p={p:.1f}")

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
    simulation_duration=2000,  # Same as Studies 3 & 4 for direct comparison
    num_replications=5,
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

# %% CELL 16: Extract and Present Key Metrics (TABLE FORMAT)
"""
Two tables are produced:

Table A — Main performance metrics with compliance probability as a fourth
          dimension. Rows are grouped by (ratio, pairing, curation), with the
          p sweep inside each cell.
Table B — Curation diagnostic metrics: fallback rate (X) and branch activation
          rates (X'), to characterise how the operating envelope and the X'
          branch mix shift with p.
"""

print("\n" + "="*80)
print("KEY PERFORMANCE METRICS: CUSTOMER COMPLIANCE STUDY")
print("="*80)

import re

def extract_design_dims(design_name):
    """Extract ratio, pairing, curation, and p from a design point name."""
    match = re.match(
        r'ratio_([\d.]+)_(no_pairing|pairing)_'
        r'(state_adaptive_no_pair_push|state_adaptive|proximity|uniform)_'
        r'p([\d.]+)',
        design_name,
    )
    if match:
        return (
            float(match.group(1)),
            match.group(2),
            match.group(3),
            float(match.group(4)),
        )
    return None, None, None, None

# Build metrics data rows
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    ratio, pairing_condition, curation_policy, p = extract_design_dims(design_name)
    if ratio is None:
        continue

    stats_with_cis = analysis_result['statistics_with_cis']

    # Order metrics
    order_metrics = stats_with_cis.get('order_metrics', {})

    assignment = order_metrics.get('assignment_time', {}).get('mean_of_means', {})
    mom_estimate = assignment.get('point_estimate', 0)
    mom_ci = assignment.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0

    pickup = order_metrics.get('pickup_travel_time', {}).get('mean_of_means', {})
    pickup_estimate = pickup.get('point_estimate', 0)
    pickup_ci = pickup.get('confidence_interval', [0, 0])
    pickup_ci_width = (pickup_ci[1] - pickup_ci[0]) / 2 if pickup_ci[0] is not None else 0

    delivery = order_metrics.get('delivery_travel_time', {}).get('mean_of_means', {})
    delivery_estimate = delivery.get('point_estimate', 0)
    delivery_ci = delivery.get('confidence_interval', [0, 0])
    delivery_ci_width = (delivery_ci[1] - delivery_ci[0]) / 2 if delivery_ci[0] is not None else 0

    fulfillment = order_metrics.get('fulfillment_time', {}).get('mean_of_means', {})
    fulfillment_estimate = fulfillment.get('point_estimate', 0)
    fulfillment_ci = fulfillment.get('confidence_interval', [0, 0])
    fulfillment_ci_width = (fulfillment_ci[1] - fulfillment_ci[0]) / 2 if fulfillment_ci[0] is not None else 0

    # Queue dynamics
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})

    growth_rate = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate.get('point_estimate', 0)
    growth_rate_ci = growth_rate.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0

    avg_queue = queue_dynamics_metrics.get('average_unassigned_entities', {})
    avg_queue_estimate = avg_queue.get('point_estimate', 0)
    avg_queue_ci = avg_queue.get('confidence_interval', [0, 0])
    avg_queue_ci_width = (avg_queue_ci[1] - avg_queue_ci[0]) / 2 if avg_queue_ci[0] is not None else 0

    # System state metrics
    system_state_metrics = stats_with_cis.get('system_state_metrics', {})

    driver_util = system_state_metrics.get('driver_utilization', {}).get('mean_of_means', {})
    driver_util_estimate = driver_util.get('point_estimate', 0)
    driver_util_ci = driver_util.get('confidence_interval', [0, 0])
    driver_util_ci_width = (driver_util_ci[1] - driver_util_ci[0]) / 2 if driver_util_ci[0] is not None else 0

    # System metrics
    system_metrics = stats_with_cis.get('system_metrics', {})

    pairing_rate = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate.get('point_estimate', None)
    pairing_rate_ci = pairing_rate.get('confidence_interval', [None, None])
    pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2 if pairing_rate_ci[0] is not None else None

    immediate_assign = system_metrics.get('immediate_assignment_rate', {})
    immediate_assign_estimate = immediate_assign.get('point_estimate', 0)
    immediate_assign_ci = immediate_assign.get('confidence_interval', [0, 0])
    immediate_assign_ci_width = (immediate_assign_ci[1] - immediate_assign_ci[0]) / 2 if immediate_assign_ci[0] is not None else 0

    # Curation metrics
    curation_metrics = stats_with_cis.get('curation_metrics', {})

    def _extract_rate(metric_key):
        rate = curation_metrics.get(metric_key, {})
        est = rate.get('point_estimate', None)
        ci = rate.get('confidence_interval', [None, None])
        ci_width = (ci[1] - ci[0]) / 2 if ci[0] is not None else None
        return est, ci_width

    fallback_rate_estimate, fallback_rate_ci_width = _extract_rate('curation_fallback_rate')
    pair_queued_estimate, pair_queued_ci_width = _extract_rate('curation_pair_queued_rate')
    single_imm_estimate, single_imm_ci_width = _extract_rate('curation_single_immediate_rate')
    single_q_estimate, single_q_ci_width = _extract_rate('curation_single_queued_rate')

    metrics_data.append({
        'ratio': ratio,
        'pairing_condition': pairing_condition,
        'curation_policy': curation_policy,
        'p': p,
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'pickup_estimate': pickup_estimate,
        'pickup_ci_width': pickup_ci_width,
        'delivery_estimate': delivery_estimate,
        'delivery_ci_width': delivery_ci_width,
        'fulfillment_estimate': fulfillment_estimate,
        'fulfillment_ci_width': fulfillment_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'driver_util_estimate': driver_util_estimate,
        'driver_util_ci_width': driver_util_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width,
        'immediate_assign_estimate': immediate_assign_estimate,
        'immediate_assign_ci_width': immediate_assign_ci_width,
        'fallback_rate_estimate': fallback_rate_estimate,
        'fallback_rate_ci_width': fallback_rate_ci_width,
        'pair_queued_estimate': pair_queued_estimate,
        'pair_queued_ci_width': pair_queued_ci_width,
        'single_imm_estimate': single_imm_estimate,
        'single_imm_ci_width': single_imm_ci_width,
        'single_q_estimate': single_q_estimate,
        'single_q_ci_width': single_q_ci_width,
    })

# Sort: ratio asc → pairing OFF/ON → curation X/X' → p asc
pairing_order = {'no_pairing': 0, 'pairing': 1}
curation_order = {
    'uniform': 0,
    'proximity': 1,
    'state_adaptive_no_pair_push': 2,
    'state_adaptive': 3,
}
curation_label_map = {
    'uniform': 'U',
    'proximity': 'X',
    'state_adaptive_no_pair_push': "X''",
    'state_adaptive': "X'",
}
metrics_data.sort(key=lambda r: (r['ratio'],
                                 pairing_order[r['pairing_condition']],
                                 curation_order[r['curation_policy']],
                                 r['p']))

# =========================================================================
# TABLE A — MAIN PERFORMANCE METRICS
# =========================================================================
print("\nTABLE A — MAIN PERFORMANCE METRICS")
header_a = (f"  {'Ratio':>5}  {'Pairing':>9}  {'Curation':>9}  {'p':>4}  "
            f"{'Assign Time':>16}  {'Pickup Travel':>16}  "
            f"{'Delivery Travel':>16}  {'Fulfillment':>16}  "
            f"{'Avg Queue':>17}  {'Growth Rate':>18}  "
            f"{'Driver Util':>16}  {'Immed. Rate':>16}  "
            f"{'Pairing Rate':>16}")
print(header_a)
print("="*len(header_a))

prev_cell = (None, None, None)
for row in metrics_data:
    cell = (row['ratio'], row['pairing_condition'], row['curation_policy'])
    if prev_cell != (None, None, None) and cell != prev_cell:
        # Separator: ratio change is heavier, pairing/curation change is lighter.
        if cell[0] != prev_cell[0]:
            print("="*len(header_a))
        else:
            print("-"*len(header_a))
    prev_cell = cell

    assignment_str  = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
    pickup_str      = f"{row['pickup_estimate']:5.2f} ± {row['pickup_ci_width']:5.2f}"
    delivery_str    = f"{row['delivery_estimate']:5.2f} ± {row['delivery_ci_width']:5.2f}"
    fulfillment_str = f"{row['fulfillment_estimate']:5.2f} ± {row['fulfillment_ci_width']:5.2f}"
    avg_queue_str   = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
    growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"
    driver_util_str = f"{row['driver_util_estimate']:.4f} ± {row['driver_util_ci_width']:.4f}"
    immediate_str   = f"{row['immediate_assign_estimate']:.4f} ± {row['immediate_assign_ci_width']:.4f}"

    if row['pairing_rate_estimate'] is not None and row['pairing_rate_ci_width'] is not None:
        pairing_rate_str = f"{row['pairing_rate_estimate']*100:5.2f} ± {row['pairing_rate_ci_width']*100:5.2f}%"
    else:
        pairing_rate_str = "N/A"

    pairing_label  = "ON" if row['pairing_condition'] == 'pairing' else "OFF"
    curation_label = curation_label_map[row['curation_policy']]
    p_label = f"{row['p']:.1f}"

    print(f"  {row['ratio']:>5.1f}  {pairing_label:>9}  {curation_label:>9}  {p_label:>4}  "
          f"{assignment_str:>16}  {pickup_str:>16}  "
          f"{delivery_str:>16}  {fulfillment_str:>16}  "
          f"{avg_queue_str:>17}  {growth_rate_str:>18}  "
          f"{driver_util_str:>16}  {immediate_str:>16}  "
          f"{pairing_rate_str:>16}")

print("="*len(header_a))

# =========================================================================
# TABLE B — CURATION DIAGNOSTIC METRICS
# =========================================================================
print("\nTABLE B — CURATION DIAGNOSTIC METRICS")
print("(Fallback rate: Policy X envelope. Branch rates: Policy X' envelope.)")
header_b = (f"  {'Ratio':>5}  {'Pairing':>9}  {'Curation':>9}  {'p':>4}  "
            f"{'Fallback':>16}  {'pair_queued':>16}  "
            f"{'single_imm':>16}  {'single_q':>16}")
print(header_b)
print("="*len(header_b))

def _fmt_rate(est, ci_width):
    if est is None:
        return "N/A"
    if ci_width is None:
        return f"{est*100:5.2f}%"
    return f"{est*100:5.2f} ± {ci_width*100:4.2f}%"

prev_cell = (None, None, None)
for row in metrics_data:
    cell = (row['ratio'], row['pairing_condition'], row['curation_policy'])
    if prev_cell != (None, None, None) and cell != prev_cell:
        if cell[0] != prev_cell[0]:
            print("="*len(header_b))
        else:
            print("-"*len(header_b))
    prev_cell = cell

    pairing_label  = "ON" if row['pairing_condition'] == 'pairing' else "OFF"
    curation_label = curation_label_map[row['curation_policy']]
    p_label = f"{row['p']:.1f}"

    if row['curation_policy'] == 'proximity':
        fallback_str = _fmt_rate(row['fallback_rate_estimate'], row['fallback_rate_ci_width'])
        pq_str = "N/A"
        si_str = "N/A"
        sq_str = "N/A"
    else:  # state_adaptive
        fallback_str = "N/A"
        pq_str = _fmt_rate(row['pair_queued_estimate'], row['pair_queued_ci_width'])
        si_str = _fmt_rate(row['single_imm_estimate'], row['single_imm_ci_width'])
        sq_str = _fmt_rate(row['single_q_estimate'], row['single_q_ci_width'])

    print(f"  {row['ratio']:>5.1f}  {pairing_label:>9}  {curation_label:>9}  {p_label:>4}  "
          f"{fallback_str:>16}  {pq_str:>16}  "
          f"{si_str:>16}  {sq_str:>16}")

print("="*len(header_b))

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("CURATION POLICY:  X = R-D proximity,  X' = state-adaptive")
print("COMPLIANCE p:     1.0 = always accept recommendation")
print("                  0.0 = always reject (sample from rest uniformly)")
print("                  0.5 = midpoint sensitivity")
print()
print("HOW TO READ:")
print("  • Within a (ratio, pairing, curation) cell, the three rows show how")
print("    performance degrades as compliance drops.")
print("  • Monotonic degradation expected: worse on all primary metrics as p ↓.")
print("  • Compare X' degradation vs X degradation at the same (ratio, pairing):")
print("    if X' degrades more slowly, the state-adaptive architecture is more")
print("    robust to non-compliance.")
print("  • For X', watch the branch activation rates (Table B) shift with p:")
print("    lower p should weaken the reinforcement loop, leaving more queue,")
print("    which should increase pair_queued and single_queued shares.")
print()
print("ENDPOINT REPRODUCIBILITY CHECKS:")
print("  • X  at p=1.0 should match Study 3 results within Monte Carlo noise.")
print("  • X' at p=1.0 should match Study 4 results within Monte Carlo noise.")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  • How fast does the curation effect decay as p decreases?")
print("  • Does X' separate from X more clearly under partial compliance, or")
print("    do they converge as p drops?")
print("  • Under partial compliance, does X''s pair_queued branch finally")
print("    exercise the 'active push for pair formation' mechanism?")
print("  • Does X' raise the pairing rate above what X produces at the same p,")
print("    signalling real pair-construction work?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for customer compliance analysis")

# %% CELL 17: Ad-hoc Analysis (Placeholder)
"""
PLACEHOLDER FOR AD-HOC ANALYSIS

Reserved for exploratory analysis specific to the compliance study. Potential
analyses:
- Compliance sensitivity curves: assignment time / queue size vs p, faceted by
  (ratio, pairing), with X and X' as two lines.
- X' branch mix vs p: stacked-area plot showing how (pair_queued, single_imm,
  single_queued) shares shift as p decreases.
- Pairing rate vs p: does X' construct pairs more actively under partial
  compliance than X does?
- Robustness ratio: at each (ratio, pairing), compute (X' improvement over X)
  at each p — does the ratio shrink, hold, or grow as p decreases?
- Endpoint reproducibility check: numerical comparison of p=1.0 results with
  Study 3 and Study 4 results for the corresponding design points.

To be developed based on Cell 16 findings.
"""

print("\n" + "="*80)
print("AD-HOC ANALYSIS PLACEHOLDER")
print("="*80)
print("Reserved for exploratory analysis based on results.")
print("="*80)

# %%