# curation_study.py
"""
R-D Curation Study: Effect of Restaurant-Driver Proximity Curation on System Performance

Research Question: How does R-D proximity curation (recommending restaurants near idle
drivers) affect system performance, and how does it interact with order pairing across
operational regimes?

Building on Previous Studies:
- Study 1 (Arrival Interval Ratio) established three operational regimes and located the
  no-pairing regime boundary around ratio 5.5-6.0.
- Study 2 (Pairing Effect) demonstrated pairing shifts the regime boundary substantially
  (bounded beyond ratio 8.0) and quantified pairing benefit across regimes.

This Study (R-D Curation):
- Tests whether R-D curation (Policy X) improves performance over uniform random
  restaurant selection (Policy U).
- Tests how curation interacts with pairing: is the combined effect additive,
  synergistic, or sub-additive?
- Characterizes the curation operating envelope via fallback rate (how often no idle
  drivers exist, forcing fallback to uniform random).

Mechanism (from Savelsbergh & Ulmer, 2024):
- Policy X ranks restaurants by distance to nearest idle driver, recommends the closest.
- When no idle drivers exist, the R-D signal is unavailable and Policy X falls back to
  uniform random selection (identical to Policy U).
- Full compliance assumed (p=1): customer always accepts the recommendation.

Design Pattern (2 × 2 × 3 factorial):
- 2 curation policies: uniform (U), proximity (X)
- 2 pairing conditions: OFF, ON
- 3 arrival interval ratios: 5.0 (critical), 6.0 (no-pairing boundary), 7.0 (high stress)
- Baseline intensity only (order_interval = 1.0 min)

Four operational conditions per ratio:
- no_pairing_uniform   → neither intervention (Study 1 baseline)
- no_pairing_proximity → curation only
- pairing_uniform      → pairing only (Study 2 condition)
- pairing_proximity    → both interventions

Total Design Points: 2 policies × 2 pairing × 3 ratios = 12
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
print("R-D CURATION STUDY: EFFECT OF RESTAURANT-DRIVER PROXIMITY CURATION")
print("="*80)
print("Research Question: How does R-D curation affect system performance?")
print("Building on Studies 1 & 2: Testing curation effect and curation × pairing interaction")

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

# ==============================================================================
# MAIN RESEARCH QUESTION
# ==============================================================================
research_question = """
(1) How does R-D proximity curation affect system performance relative to uniform
    random restaurant selection?
(2) How does curation interact with order pairing — is the combined effect additive,
    synergistic, or sub-additive?
(3) How does the curation operating envelope (fallback rate) vary across regimes?
"""

# ==============================================================================
# CONTEXT & MOTIVATION
# ==============================================================================
context = """
R-D curation is a demand-shaping mechanism: rather than treating restaurant selection
as exogenous (uniform random), the platform recommends restaurants near idle drivers,
shortening the driver-to-restaurant (pickup) leg. This study tests whether that
upstream intervention produces measurable downstream system benefit, and whether it
compounds with pairing's capacity-expansion effect.

The compounding hypothesis: even small per-trip pickup savings could compound through
faster driver return cycles. Near saturation, modest service-time reductions can produce
disproportionate improvements in queue length and waiting time. This is the primary
source of potentially non-obvious findings.
"""

# ==============================================================================
# SUB-QUESTIONS & HYPOTHESES
# ==============================================================================
sub_questions = """
1. Pickup travel time (order_metrics)
   - Direct mechanism signal: Policy X should reduce pickup travel time vs Policy U.
   - Driver speed is constant, so pickup travel time is proportional to pickup distance.

2. Assignment time / growth rate (order_metrics, queue_dynamics_metrics)
   - Outcome signal: does the per-trip saving propagate to system-level performance?
   - Does curation shift the regime boundary (compare growth rates at ratio 6.0, 7.0)?

3. Curation fallback rate (curation_metrics)
   - Operating envelope: fraction of arrivals with no idle drivers (Policy X only).
   - Expected to rise with load; complement is the curation activation rate.

4. Curation × pairing interaction
   - Compare curation benefit (U→X) when pairing OFF vs pairing ON.
"""

# ==============================================================================
# SCOPE & BOUNDARIES
# ==============================================================================
scope = """
- Single fixed infrastructure (seed=42), consistent with Studies 1 and 2.
- Three ratios: 5.0 (critical), 6.0 (no-pairing boundary), 7.0 (high stress).
- Baseline intensity only (order_interval=1.0).
- Full compliance (p=1) — upper-bound characterization of curation effect.
- Starter design: few representative ratios. Range may be extended later to locate the
  pairing boundary if boundary-shift quantification under pairing is required.
"""

# ==============================================================================
# KEY METRICS & ANALYSIS FOCUS
# ==============================================================================
analysis_focus = """
Primary: pickup travel time (mechanism), assignment time (outcome), growth rate (regime).
Secondary: fallback rate (operating envelope), pairing rate (pairing conditions).
Approach: 2×2 comparison at each ratio. Isolate curation main effect within each pairing
level, then compare across pairing levels to assess interaction.
"""

# ==============================================================================
# EVOLUTION NOTES
# ==============================================================================
evolution_notes = """
Study sequence positioning:

Study 1: Arrival Interval Ratio Study (COMPLETE)
- Established regime structure; no-pairing boundary ~5.5-6.0. Pairing disabled.

Study 2: Pairing Effect Study (COMPLETE)
- Pairing shifts regime boundary beyond 8.0; quantified pairing benefit.

R-D Curation Study (THIS STUDY)
- Introduces curation as a second intervention factor alongside pairing.
- 2×2×3 factorial isolates curation main effect and curation × pairing interaction.
- Uniform policy path validated bit-for-bit identical to Study 1/2 baseline.
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
Focus is on varying operational parameters (curation, pairing), not infrastructure.
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
OPERATIONAL STUDY: Single seed.
Layout variation is not the focus of this study.
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
"""
Single baseline scoring configuration for this study.
"""

scoring_configs = [
    {
        'name': 'baseline',
        'config': ScoringConfig()  # Use defaults
    }
]

print(f"✓ Defined {len(scoring_configs)} scoring configuration(s)")
for config in scoring_configs:
    print(f"  • {config['name']}")

# %% CELL 8: Operational Configuration(s)
"""
R-D CURATION STUDY: 2 × 2 × 3 factorial over curation policy, pairing, and ratio.

For each arrival interval ratio, create four configurations:
- no_pairing_uniform   → curation OFF, pairing OFF (Study 1 baseline)
- no_pairing_proximity → curation ON,  pairing OFF
- pairing_uniform      → curation OFF, pairing ON  (Study 2 condition)
- pairing_proximity    → curation ON,  pairing ON

This isolates curation's main effect within each pairing level and the
curation × pairing interaction.
"""

# Target arrival interval ratios (starter set: critical, no-pairing boundary, high stress)
target_arrival_interval_ratios = [5.0, 6.0, 7.0]

# Pairing parameter blocks
pairing_params = {
    'pairing_enabled': True,
    'restaurants_proximity_threshold': 4.0,
    'customers_proximity_threshold': 3.0,
}

no_pairing_params = {
    'pairing_enabled': False,
    'restaurants_proximity_threshold': None,
    'customers_proximity_threshold': None,
}

# Curation policy values (matches OperationalConfig.curation_policy)
UNIFORM = None
PROXIMITY = 'proximity'

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
    # no_pairing_uniform — neither intervention (Study 1 baseline)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_no_pairing_uniform',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **no_pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=UNIFORM
        )
    })

    # no_pairing_proximity — curation only
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_no_pairing_proximity',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **no_pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=PROXIMITY
        )
    })

    # pairing_uniform — pairing only (Study 2 condition)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_pairing_uniform',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=UNIFORM
        )
    })

    # pairing_proximity — both interventions
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_pairing_proximity',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=PROXIMITY
        )
    })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Testing {len(target_arrival_interval_ratios)} arrival interval ratios: {target_arrival_interval_ratios}")
print(f"✓ Each ratio has 4 conditions (2 curation × 2 pairing)")

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
    curation_status = f"CURATION {curation_label}"
    print(f"  • {config['name']}: ratio={ratio:.1f}, {pairing_status}, {curation_status}")

# %% CELL 9: Design Point Creation
"""
Create design points from all combinations.

Simplified loop structure: iterate over pre-created infrastructure instances.
"""

design_points = {}

print("\n" + "="*50)
print("DESIGN POINTS CREATION")
print("="*50)

for infra_instance in infrastructure_instances:
    for op_config in operational_configs:
        for scoring_config_dict in scoring_configs:
            
            # Generate design point name (no need for infra name since it's fixed)
            design_name = op_config['name']
            
            # Create design point
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
    simulation_duration=2000,  # Extended duration for regime pattern analysis
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

# Initialize visualization
viz = WelchMethodVisualization(figsize=(16, 10))

# Group design points by arrival interval ratio for organized display
ratio_groups = {}
for design_name in all_time_series_data.keys():
    # Extract ratio from design name (e.g., "ratio_5.0_no_pairing_uniform")
    ratio_str = design_name.split('_')[1]  # "5.0"
    ratio = float(ratio_str)
    
    if ratio not in ratio_groups:
        ratio_groups[ratio] = []
    ratio_groups[ratio].append(design_name)

print(f"✓ Grouped {len(all_time_series_data)} design points by {len(ratio_groups)} ratios")

# Create plots systematically by ratio
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
print(f"✓ Organized by {len(ratio_groups)} arrival interval ratios")

# %% CELL 14: Warmup Period Determination
print("\n" + "="*50)
print("WARMUP PERIOD DETERMINATION")
print("="*50)

# Set warmup period based on visual inspection of Cell 13 plots
uniform_warmup_period = 500  # UPDATE THIS based on visual inspection

print(f"✓ Warmup period set: {uniform_warmup_period} minutes")
print(f"✓ Based on visual inspection of active drivers oscillation around Little's Law values")
print(f"✓ Analysis window: {experiment_config.simulation_duration - uniform_warmup_period} minutes of post-warmup data")

# %% CELL 15: Process Through Analysis Pipeline
print("\n" + "="*80)
print("PROCESSING THROUGH ANALYSIS PIPELINE")
print("="*80)

from delivery_sim.analysis_pipeline.pipeline_coordinator import ExperimentAnalysisPipeline

# Initialize pipeline
# NOTE: 'curation_metrics' is enabled here so the fallback rate (operating envelope)
# is computed. This metric type is new to this study; earlier studies predate it.
pipeline = ExperimentAnalysisPipeline(
    warmup_period=uniform_warmup_period,
    enabled_metric_types=['order_metrics', 'system_metrics', 
                         'system_state_metrics', 'queue_dynamics_metrics',
                         'curation_metrics'],
    confidence_level=0.95
)

# Process each design point
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
print("\n" + "="*80)
print("KEY PERFORMANCE METRICS: R-D CURATION STUDY")
print("="*80)

import re

def extract_ratio_pairing_curation(design_name):
    """Extract ratio, pairing condition, and curation policy from design point name."""
    # Pattern: ratio_5.0_no_pairing_uniform / ratio_5.0_pairing_proximity
    match = re.match(r'ratio_([\d.]+)_(no_pairing|pairing)_(uniform|proximity)', design_name)
    if match:
        ratio = float(match.group(1))
        pairing_condition = match.group(2)
        curation_policy = match.group(3)
        return ratio, pairing_condition, curation_policy
    return None, None, None

# Build metrics data rows
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    ratio, pairing_condition, curation_policy = extract_ratio_pairing_curation(design_name)
    if ratio is None:
        continue

    stats_with_cis = analysis_result['statistics_with_cis']

    # Order metrics — assignment time (mean of means) and pickup travel time
    order_metrics = stats_with_cis.get('order_metrics', {})

    assignment = order_metrics.get('assignment_time', {}).get('mean_of_means', {})
    mom_estimate = assignment.get('point_estimate', 0)
    mom_ci = assignment.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0

    pickup = order_metrics.get('pickup_travel_time', {}).get('mean_of_means', {})
    pickup_estimate = pickup.get('point_estimate', 0)
    pickup_ci = pickup.get('confidence_interval', [0, 0])
    pickup_ci_width = (pickup_ci[1] - pickup_ci[0]) / 2 if pickup_ci[0] is not None else 0

    # Queue dynamics — growth rate and average queue size
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})

    growth_rate = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate.get('point_estimate', 0)
    growth_rate_ci = growth_rate.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0

    avg_queue = queue_dynamics_metrics.get('average_unassigned_entities', {})
    avg_queue_estimate = avg_queue.get('point_estimate', 0)
    avg_queue_ci = avg_queue.get('confidence_interval', [0, 0])
    avg_queue_ci_width = (avg_queue_ci[1] - avg_queue_ci[0]) / 2 if avg_queue_ci[0] is not None else 0

    # System metrics — pairing rate
    system_metrics = stats_with_cis.get('system_metrics', {})
    pairing_rate = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate.get('point_estimate', None)
    pairing_rate_ci = pairing_rate.get('confidence_interval', [None, None])
    pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2 if pairing_rate_ci[0] is not None else None

    # Curation metrics — fallback rate (meaningful only for proximity policy)
    curation_metrics = stats_with_cis.get('curation_metrics', {})
    fallback_rate = curation_metrics.get('curation_fallback_rate', {})
    fallback_rate_estimate = fallback_rate.get('point_estimate', None)
    fallback_rate_ci = fallback_rate.get('confidence_interval', [None, None])
    fallback_rate_ci_width = (fallback_rate_ci[1] - fallback_rate_ci[0]) / 2 if fallback_rate_ci[0] is not None else None

    metrics_data.append({
        'ratio': ratio,
        'pairing_condition': pairing_condition,
        'curation_policy': curation_policy,
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'pickup_estimate': pickup_estimate,
        'pickup_ci_width': pickup_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width,
        'fallback_rate_estimate': fallback_rate_estimate,
        'fallback_rate_ci_width': fallback_rate_ci_width,
    })

# Sort by ratio, then pairing condition, then curation policy for stable grouping
pairing_order = {'no_pairing': 0, 'pairing': 1}
curation_order = {'uniform': 0, 'proximity': 1}
metrics_data.sort(key=lambda r: (r['ratio'],
                                 pairing_order[r['pairing_condition']],
                                 curation_order[r['curation_policy']]))

# Print table
header = (f"  {'Ratio':>5}  {'Pairing':>9}  {'Curation':>9}  "
         f"{'Assign Time':>16}  {'Pickup Travel':>16}  "
         f"{'Avg Queue':>17}  {'Growth Rate':>17}  "
         f"{'Pairing Rate':>16}  {'Fallback Rate':>16}")
print(header)
print("="*len(header))

current_ratio = None
for row in metrics_data:
    # Separator between ratios
    if current_ratio is not None and row['ratio'] != current_ratio:
        print("-"*len(header))
    current_ratio = row['ratio']

    assignment_str = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
    pickup_str = f"{row['pickup_estimate']:5.2f} ± {row['pickup_ci_width']:5.2f}"
    avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
    growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"

    # Pairing rate (N/A for no_pairing conditions)
    if row['pairing_rate_estimate'] is not None and row['pairing_rate_ci_width'] is not None:
        pairing_rate_str = f"{row['pairing_rate_estimate']*100:5.2f} ± {row['pairing_rate_ci_width']*100:5.2f}%"
    else:
        pairing_rate_str = "N/A"

    # Fallback rate (meaningful only for proximity; uniform reports ~0 by construction)
    if row['curation_policy'] == 'proximity' and row['fallback_rate_estimate'] is not None:
        if row['fallback_rate_ci_width'] is not None:
            fallback_str = f"{row['fallback_rate_estimate']*100:5.2f} ± {row['fallback_rate_ci_width']*100:5.2f}%"
        else:
            fallback_str = f"{row['fallback_rate_estimate']*100:5.2f}%"
    else:
        fallback_str = "N/A"

    pairing_label = "ON" if row['pairing_condition'] == 'pairing' else "OFF"
    curation_label = "X" if row['curation_policy'] == 'proximity' else "U"

    print(f"  {row['ratio']:>5.1f}  {pairing_label:>9}  {curation_label:>9}  "
          f"{assignment_str:>16}  {pickup_str:>16}  "
          f"{avg_queue_str:>17}  {growth_rate_str:>17}  "
          f"{pairing_rate_str:>16}  {fallback_str:>16}")

print("="*len(header))

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("CURATION POLICY:  U = uniform random,  X = R-D proximity curation")
print()
print("MECHANISM SIGNAL:")
print("  • Pickup Travel: driver→restaurant leg. Policy X should be lower than Policy U.")
print()
print("OUTCOME SIGNALS:")
print("  • Assign Time: customer wait (order arrival → driver assignment).")
print("  • Avg Queue Size: time-weighted mean unassigned entities.")
print("  • Growth Rate: system trajectory (≈0 = bounded, >0 = deteriorating).")
print()
print("OPERATING ENVELOPE:")
print("  • Fallback Rate: fraction of arrivals with no idle drivers (Policy X only).")
print("    Complement (1 − fallback) is the curation activation rate.")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  • Does Policy X reduce pickup travel time vs Policy U (within each pairing level)?")
print("  • Does the per-trip saving propagate to assignment time and growth rate?")
print("  • Is curation's benefit different with pairing ON vs OFF (interaction)?")
print("  • How does fallback rate rise from ratio 5.0 → 7.0 (envelope narrowing)?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for R-D curation analysis")

# %% CELL 17: Ad-hoc Analysis (Placeholder)
"""
PLACEHOLDER FOR AD-HOC ANALYSIS

This cell is reserved for exploratory analysis specific to the R-D curation study.
Potential analyses:
- Curation effect visualization (U vs X) across ratios, faceted by pairing condition
- Curation × pairing interaction plot
- Fallback rate vs ratio (operating envelope characterization)
- Mechanism-to-outcome decomposition (pickup saving → assignment time saving)

To be developed based on Cell 16 findings.
"""

print("\n" + "="*80)
print("AD-HOC ANALYSIS PLACEHOLDER")
print("="*80)
print("Reserved for exploratory analysis based on results.")
print("="*80)