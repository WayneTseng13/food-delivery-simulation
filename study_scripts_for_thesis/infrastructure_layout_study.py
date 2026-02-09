# infrastructure_layout_study.py
"""
Infrastructure Layout Study: Effect of Random Restaurant Spatial Arrangement on System Performance

Research Question: How do random restaurant layouts affect system performance, and do the 
operational findings from Studies 1 and 2 generalize across different spatial configurations?

Building on Previous Studies:
- Study 1 established three operational regimes based on arrival interval ratio (stable, 
  critical, failure) and identified the intensity effect (baseline outperforms 2× baseline)
- Study 2 demonstrated that pairing shifts regime boundaries dramatically (from ~5.5-6.0 
  to beyond 8.0) and exhibits self-regulating properties

This Study (Study 3):
- Tests whether regime patterns from Study 1 hold across different random layouts
- Tests whether pairing benefits from Study 2 hold across different random layouts
- Investigates whether pairing can compensate for structural disadvantages in layout

Design Pattern:
- 3 structural seeds (42, 100, 200) generating different random restaurant layouts
- 3 arrival interval ratios (3.5, 5.0, 7.0) sampling stable, critical, and failure regimes
- 2 pairing conditions (OFF, ON) to test layout × pairing interaction
- Baseline intensity only (intensity effect established in Study 1)

Total Design Points: 3 seeds × 3 ratios × 2 pairing conditions = 18
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
print("INFRASTRUCTURE LAYOUT STUDY")
print("="*80)
print("Research Question: How do random restaurant layouts affect system performance?")
print("Building on Studies 1 & 2: Testing generalizability of regime structure and pairing effects")

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
print("RESEARCH QUESTION DOCUMENTATION")
print("="*80)

# ==============================================================================
# MAIN RESEARCH QUESTION
# ==============================================================================
research_question = """
MAIN RESEARCH QUESTION:
How do random restaurant layouts affect system performance, and do the operational 
findings from Studies 1 and 2 generalize across different spatial configurations?
"""

# ==============================================================================
# CONTEXT & MOTIVATION
# ==============================================================================
context = """
CONTEXT & MOTIVATION:

Studies 1 and 2 used a single infrastructure configuration (seed=42). Key findings were:

Study 1 Findings:
- Three operational regimes: stable (ratio ≤ 4.0), critical (4.5-5.5), failure (≥ 6.0)
- Arrival interval ratio is the primary determinant of regime classification
- Baseline intensity outperforms 2× baseline due to spatial coverage mechanism

Study 2 Findings:
- Pairing shifts regime boundary from ~5.5-6.0 to beyond ratio 8.0
- Pairing rate increases with load (self-regulating property)
- Pairing reduces both mean assignment time and variability

Open Question: Are these findings specific to seed=42, or do they represent general 
system dynamics that hold across different random spatial configurations?

This matters because:
- If findings are seed-specific, our conclusions have limited generalizability
- If findings are robust across layouts, we've identified fundamental system properties
- If layouts interact with pairing effectiveness, infrastructure planning matters
"""

# ==============================================================================
# SUB-QUESTIONS
# ==============================================================================
sub_questions = """
SUB-QUESTIONS:

1. Does the regime structure (stable → critical → failure) hold across layouts?
   - Test: Compare growth rate patterns across seeds at ratios 3.5, 5.0, 7.0
   - Expected: Similar qualitative patterns, possibly different absolute values

2. Does pairing provide consistent benefit across layouts?
   - Test: Compare pairing ON vs OFF at each seed × ratio combination
   - Question: Do some layouts benefit more from pairing than others?

3. Can pairing compensate for structural disadvantage?
   - If one layout performs worse without pairing, does pairing equalize performance?
   - This addresses whether operational optimization can overcome infrastructure limitations
"""

# ==============================================================================
# SCOPE & BOUNDARIES
# ==============================================================================
scope = """
SCOPE & BOUNDARIES:

INCLUDED in this study:
- 3 structural seeds (42, 100, 200) with identical structural parameters
- 3 arrival interval ratios (3.5, 5.0, 7.0) sampling each regime
- 2 pairing conditions (OFF, ON) to test layout × pairing interaction
- Baseline intensity only (order_interval = 1.0 min)

Rationale for ratio selection:
- Ratio 3.5: Stable regime - system performs well, tests baseline differences
- Ratio 5.0: Critical regime - system at capacity edge, sensitive to perturbations
- Ratio 7.0: Failure regime (without pairing) - tests if layout affects breakdown severity

NOT included (and why):
- 2× baseline configurations: Intensity mechanism established in Study 1
- Fine-grained ratio sweep: Regime mapping done in Study 1; here we sample representatively
- Different pairing thresholds: Standard thresholds (δ_r=4.0km, δ_c=3.0km) used throughout
"""

# ==============================================================================
# KEY METRICS & ANALYSIS FOCUS
# ==============================================================================
analysis_focus = """
KEY METRICS & ANALYSIS FOCUS:

Primary Metrics:
1. Assignment Time (Mean of Means): Customer-facing performance
   - Compare across seeds at each ratio × pairing combination
   - Quantify layout effect magnitude

2. Growth Rate: Regime classification indicator
   - Verify regime structure holds across layouts
   - Check if some layouts shift regime boundaries

3. Pairing Rate (for pairing=ON conditions): Pairing opportunity indicator
   - Do some layouts enable more pairing than others?
   - Mechanism: clustered restaurants might have more pairing opportunities

Analysis Approach:
- First, verify Study 1 patterns replicate across layouts (pairing OFF conditions)
- Second, verify Study 2 patterns replicate across layouts (pairing ON conditions)
- Third, examine layout × pairing interaction (does pairing benefit vary by layout?)
- Fourth, characterize any layout that behaves differently and investigate mechanism
"""

# ==============================================================================
# EVOLUTION NOTES
# ==============================================================================
evolution_notes = """
STUDY SEQUENCE POSITIONING:

Study 1: Arrival Interval Ratio Study (COMPLETE)
- Established regime structure with single layout (seed=42)
- Identified intensity effect (baseline > 2× baseline)
- Limitation: Single infrastructure configuration

Study 2: Pairing Effect Study (COMPLETE)
- Demonstrated pairing shifts regime boundary dramatically
- Showed pairing has self-regulating properties
- Limitation: Single infrastructure configuration (seed=42)

Study 3: Infrastructure Layout Study (THIS STUDY)
- Tests generalizability of Studies 1 and 2 across layouts
- Investigates layout × pairing interaction
- Answers: Are our findings fundamental or configuration-specific?

Future Studies (potential):
- Study 4: Vary explicit infrastructure parameters (area size, restaurant count)
- Study 5: Pairing threshold sensitivity analysis
"""

print(research_question)
print("\n" + "-"*80)
print(context)
print("\n" + "-"*80)
print(sub_questions)
print("\n" + "-"*80)
print(scope)
print("\n" + "-"*80)
print(analysis_focus)
print("\n" + "-"*80)
print(evolution_notes)
print("\n" + "="*80)
print("✓ Research question documented")
print("="*80)


# %% CELL 4: Infrastructure Configuration(s)
"""
INFRASTRUCTURE STUDY: Single structural configuration, multiple seeds.

Same structural parameters (area size, restaurant count, driver speed) across all seeds.
Only the random seed varies, generating different spatial arrangements.
"""

infrastructure_configs = [
    {
        'name': 'area_10km',
        'config': StructuralConfig(
            delivery_area_size=10,
            num_restaurants=10,
            driver_speed=0.5
        )
    }
]

print(f"✓ Defined {len(infrastructure_configs)} infrastructure configuration(s)")
for config in infrastructure_configs:
    struct_config = config['config']
    density = struct_config.num_restaurants / (struct_config.delivery_area_size ** 2)
    print(f"  • {config['name']}: {struct_config.num_restaurants} restaurants, "
          f"area={struct_config.delivery_area_size}km, density={density:.4f}/km²")


# %% CELL 5: Structural Seeds
"""
CRITICAL: Test multiple structural seeds for layout sensitivity.

These seeds generate different random restaurant placements while keeping
all other structural parameters identical.
"""

structural_seeds = [42, 100, 200]

print(f"✓ Structural seeds: {structural_seeds}")
print(f"✓ Testing layout sensitivity with {len(structural_seeds)} different restaurant configurations")


# %% CELL 6: Create Infrastructure Instances
"""
Create and analyze infrastructure instances for each seed.

Store infrastructure analysis results for later interpretation of performance differences.
"""

infrastructure_instances = []

print("\n" + "="*50)
print("INFRASTRUCTURE INSTANCES CREATION")
print("="*50)

for infra_config in infrastructure_configs:
    for structural_seed in structural_seeds:
        
        instance_name = f"{infra_config['name']}_seed{structural_seed}"
        print(f"\n📍 Creating infrastructure: {instance_name}")
        
        infrastructure = Infrastructure(
            infra_config['config'],
            structural_seed
        )
        
        analyzer = InfrastructureAnalyzer(infrastructure)
        analysis_results = analyzer.analyze_complete_infrastructure()
        
        infrastructure_instances.append({
            'name': instance_name,
            'infrastructure': infrastructure,
            'analyzer': analyzer,
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


# %% CELL 6.5: Infrastructure Visualization
"""
Visualize infrastructure layouts for comparison.

Visual inspection helps understand what 'layout sensitivity' means in practice.
"""

print("\n" + "="*50)
print("INFRASTRUCTURE LAYOUT VISUALIZATION")
print("="*50)

import matplotlib.pyplot as plt

print(f"\nVisualizing {len(infrastructure_instances)} different restaurant layouts...")
print("Compare spatial patterns to understand what 'layout sensitivity' means.\n")

for instance in infrastructure_instances:
    print(f"{'='*50}")
    print(f"Layout: {instance['name']}")
    print(f"Typical Distance: {instance['analysis']['typical_distance']:.3f}km")
    print(f"Restaurant Density: {instance['analysis']['restaurant_density']:.4f}/km²")
    print(f"{'='*50}")
    
    instance['analyzer'].visualize_infrastructure()
    
    fig = plt.gcf()
    seed = instance['seed']
    typical_dist = instance['analysis']['typical_distance']
    
    custom_title = (f"Infrastructure Layout: Seed {seed}\n"
                   f"Typical Distance: {typical_dist:.3f}km | "
                   f"Area: 10×10km | Restaurants: 10")
    
    fig.suptitle(custom_title, fontsize=14, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    plt.show()
    
    print(f"✓ {instance['name']} visualized\n")

print(f"{'='*50}")
print("✓ All layouts visualized")
print("✓ Compare spatial patterns:")
print("  - Are restaurants clustered or dispersed?")
print("  - Do some layouts have outlier restaurants?")
print("  - How might these patterns affect delivery performance?")
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

print(f"\n✓ Defined {len(scoring_configs)} scoring configuration(s)")
for config in scoring_configs:
    print(f"  • {config['name']}")


# %% CELL 8: Operational Configuration(s)
"""
LAYOUT STUDY: Test each layout across regimes with and without pairing.

Design:
- 3 arrival interval ratios: 3.5 (stable), 5.0 (critical), 7.0 (failure)
- 2 pairing conditions: OFF (control) and ON (intervention)
- Baseline intensity only: order_interval = 1.0 min

This creates 6 operational configurations per infrastructure layout.
"""

# Target ratios sampling each regime
target_arrival_interval_ratios = [3.5, 5.0, 7.0]

# Pairing configurations
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
    # No pairing configuration (baseline intensity only)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_no_pairing',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **no_pairing_params,
            **FIXED_SERVICE_CONFIG
        )
    })
    
    # With pairing configuration (baseline intensity only)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_pairing',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **pairing_params,
            **FIXED_SERVICE_CONFIG
        )
    })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Testing {len(target_arrival_interval_ratios)} arrival interval ratios: {target_arrival_interval_ratios}")
print(f"✓ Each ratio has 2 pairing conditions (OFF, ON)")

print("\nConfiguration breakdown:")
for config in operational_configs:
    op_config = config['config']
    ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
    pairing_status = "PAIRING ON" if op_config.pairing_enabled else "PAIRING OFF"
    print(f"  • {config['name']}: ratio={ratio:.1f}, {pairing_status}")


# %% CELL 9: Design Point Creation
"""
Create design points from all combinations.

Total: 3 seeds × 6 operational configs = 18 design points
"""

design_points = {}

print("\n" + "="*50)
print("DESIGN POINTS CREATION")
print("="*50)

for infra_instance in infrastructure_instances:
    for op_config in operational_configs:
        for scoring_config_dict in scoring_configs:
            
            design_name = f"{infra_instance['name']}_{op_config['name']}"
            
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
    simulation_duration=2000,
    num_replications=5,
    operational_master_seed=100,
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

# Group design points by seed for organized display
seed_groups = {}
for design_name in all_time_series_data.keys():
    # Extract seed from design name (e.g., "area_10km_seed42_ratio_3.5_no_pairing")
    parts = design_name.split('_')
    seed_str = parts[2].replace('seed', '')  # "42"
    seed = int(seed_str)
    
    if seed not in seed_groups:
        seed_groups[seed] = []
    seed_groups[seed].append(design_name)

print(f"✓ Grouped {len(all_time_series_data)} design points by {len(seed_groups)} seeds")

# Create plots systematically by seed
plot_count = 0
for seed in sorted(seed_groups.keys()):
    print(f"\nSeed {seed}:")
    
    for design_name in sorted(seed_groups[seed]):
        plot_title = f"Warmup Analysis: {design_name}"
        time_series_data = all_time_series_data[design_name]
        fig = viz.create_warmup_analysis_plot(time_series_data, title=plot_title)
        
        plt.show()
        print(f"    ✓ {design_name} plot displayed")
        plot_count += 1

print(f"\n✓ Warmup analysis visualization complete")
print(f"✓ Created {plot_count} warmup analysis plots")
print(f"✓ Organized by {len(seed_groups)} seeds")


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
pipeline = ExperimentAnalysisPipeline(
    warmup_period=uniform_warmup_period,
    enabled_metric_types=['order_metrics', 'system_metrics', 
                         'system_state_metrics', 'queue_dynamics_metrics'],
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
print("KEY PERFORMANCE METRICS: INFRASTRUCTURE LAYOUT STUDY")
print("="*80)

import re

def extract_seed_ratio_and_pairing(design_name):
    """Extract seed, ratio, and pairing status from design point name."""
    # Pattern: area_10km_seed42_ratio_3.5_no_pairing or area_10km_seed42_ratio_3.5_pairing
    match = re.match(r'area_10km_seed(\d+)_ratio_([\d.]+)_(no_pairing|pairing)', design_name)
    if match:
        seed = int(match.group(1))
        ratio = float(match.group(2))
        pairing_status = match.group(3)
        return seed, ratio, pairing_status
    return None, None, None

# Extract comprehensive metrics for table
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    seed, ratio, pairing_status = extract_seed_ratio_and_pairing(design_name)
    if seed is None:
        continue
    
    stats_with_cis = analysis_result.get('statistics_with_cis', {})
    
    # Assignment Time Statistics
    order_metrics = stats_with_cis.get('order_metrics', {})
    assignment_time = order_metrics.get('assignment_time', {})
    
    mean_of_means = assignment_time.get('mean_of_means', {})
    mom_estimate = mean_of_means.get('point_estimate', 0)
    mom_ci = mean_of_means.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0
    
    std_of_means = assignment_time.get('std_of_means', {})
    som_estimate = std_of_means.get('point_estimate', 0)
    
    mean_of_stds = assignment_time.get('mean_of_stds', {})
    mos_estimate = mean_of_stds.get('point_estimate', 0)
    
    # Pickup Travel Time
    pickup_travel_time = order_metrics.get('pickup_travel_time', {})
    pickup_travel_time_mom = pickup_travel_time.get('mean_of_means', {})
    pickup_travel_time_estimate = pickup_travel_time_mom.get('point_estimate', 0)
    pickup_travel_time_ci = pickup_travel_time_mom.get('confidence_interval', [0, 0])
    pickup_travel_time_ci_width = (pickup_travel_time_ci[1] - pickup_travel_time_ci[0]) / 2 if pickup_travel_time_ci[0] is not None else 0
    
    # Delivery Travel Time
    delivery_travel_time = order_metrics.get('delivery_travel_time', {})
    delivery_travel_time_mom = delivery_travel_time.get('mean_of_means', {})
    delivery_travel_time_estimate = delivery_travel_time_mom.get('point_estimate', 0)
    delivery_travel_time_ci = delivery_travel_time_mom.get('confidence_interval', [0, 0])
    delivery_travel_time_ci_width = (delivery_travel_time_ci[1] - delivery_travel_time_ci[0]) / 2 if delivery_travel_time_ci[0] is not None else 0
    
    # Queue Dynamics Metrics
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})
    
    # Growth Rate
    growth_rate = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate.get('point_estimate', 0)
    growth_rate_ci = growth_rate.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0
    
    # Average Queue Size
    avg_queue = queue_dynamics_metrics.get('average_unassigned_entities', {})
    avg_queue_estimate = avg_queue.get('point_estimate', 0)
    avg_queue_ci = avg_queue.get('confidence_interval', [0, 0])
    avg_queue_ci_width = (avg_queue_ci[1] - avg_queue_ci[0]) / 2 if avg_queue_ci[0] is not None else 0
    
    # Pairing Rate (only for pairing=ON)
    system_metrics = stats_with_cis.get('system_metrics', {})
    pairing_rate_data = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate_data.get('point_estimate', None)
    pairing_rate_ci = pairing_rate_data.get('confidence_interval', [None, None])
    if pairing_rate_ci[0] is not None and pairing_rate_ci[1] is not None:
        pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2
    else:
        pairing_rate_ci_width = None
    
    metrics_data.append({
        'design_name': design_name,
        'seed': seed,
        'ratio': ratio,
        'pairing_status': pairing_status,
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'som_estimate': som_estimate,
        'mos_estimate': mos_estimate,
        'pickup_travel_time_estimate': pickup_travel_time_estimate,
        'pickup_travel_time_ci_width': pickup_travel_time_ci_width,
        'delivery_travel_time_estimate': delivery_travel_time_estimate,
        'delivery_travel_time_ci_width': delivery_travel_time_ci_width,
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width,
    })

# Sort by seed, ratio, then pairing status (no_pairing first, then pairing)
metrics_data.sort(key=lambda x: (x['seed'], x['ratio'], 0 if x['pairing_status'] == 'no_pairing' else 1))

# =========================================================================
# PRINT FORMATTED TABLE: GROUPED BY SEED
# =========================================================================
print("\n🎯 KEY PERFORMANCE METRICS: GROUPED BY INFRASTRUCTURE LAYOUT")
print("="*230)
print(f"  {'Seed':<6} {'Ratio':<6} {'Pairing':<12} {'Mean of Means':>18} {'Std of':>10} {'Mean of':>10} {'Pickup Travel':>18} {'Delivery Travel':>18} {'Avg Queue Size':>18} {'Growth Rate':>22} {'Pairing Rate':>18}")
print(f"  {'':6} {'':6} {'Status':<12} {'(Assignment Time)':>18} {'Means':>10} {'Stds':>10} {'(mean ± CI)':>18} {'(mean ± CI)':>18} {'(mean ± CI)':>18} {'(entities/min)':>22} {'(% paired)':>18}")
print("="*230)

current_seed = None
for row in metrics_data:
    # Add separator between seeds
    if current_seed is not None and row['seed'] != current_seed:
        print("-"*230)
    current_seed = row['seed']
    
    seed = row['seed']
    ratio = row['ratio']
    pairing_status = row['pairing_status']
    pairing_display = "Pairing ON" if pairing_status == 'pairing' else "No Pairing"
    
    # Format all metrics: mean ± CI_width
    assignment_str = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
    som_str = f"{row['som_estimate']:6.3f}"
    mos_str = f"{row['mos_estimate']:6.3f}"
    pickup_str = f"{row['pickup_travel_time_estimate']:5.2f} ± {row['pickup_travel_time_ci_width']:5.2f}"
    delivery_str = f"{row['delivery_travel_time_estimate']:5.2f} ± {row['delivery_travel_time_ci_width']:5.2f}"
    avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
    growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"
    
    if row['pairing_rate_estimate'] is not None:
        pairing_rate_str = f"{row['pairing_rate_estimate']*100:5.2f} ± {row['pairing_rate_ci_width']*100:5.2f}"
    else:
        pairing_rate_str = "N/A"
    
    print(f"  {seed:<6} {ratio:<6.1f} {pairing_display:<12} {assignment_str:>18} {som_str:>10} {mos_str:>10} {pickup_str:>18} {delivery_str:>18} {avg_queue_str:>18} {growth_rate_str:>22} {pairing_rate_str:>18}")

print("="*230)

# =========================================================================
# ALTERNATIVE VIEW: LAYOUT SENSITIVITY ACROSS SEEDS
# =========================================================================
print("\n\n🎯 LAYOUT SENSITIVITY VIEW: ASSIGNMENT TIME ACROSS SEEDS")
print("="*130)
print("  Compare the same (ratio, pairing) condition across all three seeds to see layout effect")
print("-"*130)
print(f"  {'Ratio':<6} {'Pairing':<12} │ {'Seed 42':>20} {'Seed 100':>20} {'Seed 200':>20} │ {'Max Diff':>12}")
print(f"  {'':6} {'Status':<12} │ {'Assignment Time':>20} {'Assignment Time':>20} {'Assignment Time':>20} │ {'(across seeds)':>12}")
print("="*130)

# Get all unique (ratio, pairing_status) combinations
conditions = sorted(set((d['ratio'], d['pairing_status']) for d in metrics_data))

for ratio, pairing_status in conditions:
    pairing_display = "Pairing ON" if pairing_status == 'pairing' else "No Pairing"
    
    # Collect assignment times for all seeds
    times = {}
    for seed in [42, 100, 200]:
        row = next((r for r in metrics_data if r['seed'] == seed and r['ratio'] == ratio and r['pairing_status'] == pairing_status), None)
        if row:
            times[seed] = row['mom_estimate']
    
    if times:
        t42 = f"{times.get(42, 0):5.2f}" if 42 in times else "N/A"
        t100 = f"{times.get(100, 0):5.2f}" if 100 in times else "N/A"
        t200 = f"{times.get(200, 0):5.2f}" if 200 in times else "N/A"
        max_diff = max(times.values()) - min(times.values()) if len(times) > 1 else 0
        diff_str = f"{max_diff:5.2f} min"
        
        print(f"  {ratio:<6.1f} {pairing_display:<10} │ {t42:>20} {t100:>20} {t200:>20} │ {diff_str:>12}")

print("-"*130)

print("="*130)

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("ASSIGNMENT TIME METRICS:")
print("  • Mean of Means: Average customer wait time (with 95% CI)")
print("  • Std of Means: System consistency across replications")
print("  • Mean of Stds: Within-replication volatility")
print()
print("TRAVEL TIME METRICS:")
print("  • Pickup Travel: Time for driver to reach restaurant (mean ± 95% CI)")
print("  • Delivery Travel: Time for driver to deliver to customer (mean ± 95% CI)")
print()
print("QUEUE DYNAMICS METRICS:")
print("  • Avg Queue Size: Average number of unassigned entities (mean ± 95% CI)")
print("  • Growth Rate: System trajectory (≈0 = bounded, >0 = deteriorating)")
print()
print("PAIRING METRIC:")
print("  • Pairing Rate: % of arrived orders that were paired (with 95% CI)")
print()
print("REGIME REFERENCE (from Study 1, without pairing):")
print("  • Ratio 3.5: Stable regime - low assignment time, growth ≈ 0")
print("  • Ratio 5.0: Critical regime - moderate time, high variability, growth ≈ 0")
print("  • Ratio 7.0: Failure regime - high time, positive growth rate")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  1. Do all seeds show similar regime patterns? (Study 1 generalizability)")
print("  2. Does pairing help consistently across all seeds? (Study 2 generalizability)")
print("  3. Is layout sensitivity greater or smaller with pairing enabled?")
print("  4. Which seed (if any) behaves differently, and why?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for layout effect analysis")


# %% CELL 17: Ad-hoc Analysis (Placeholder)
"""
PLACEHOLDER FOR AD-HOC ANALYSIS

This cell is reserved for exploratory analysis based on the results.
Potential analyses:
- Visualization of layout effect across ratios
- Statistical tests for layout sensitivity significance
- Pairing × layout interaction analysis
- Investigation of any anomalous layout behavior

To be developed based on Cell 16 findings.
"""

print("\n" + "="*80)
print("AD-HOC ANALYSIS PLACEHOLDER")
print("="*80)
print("Reserved for exploratory analysis based on results.")
print("Potential analyses:")
print("  • Layout effect visualization")
print("  • Statistical significance testing")
print("  • Pairing × layout interaction analysis")
print("="*80)

# %%