# arrival_interval_ratio_study.py
"""
Arrival Interval Ratio Study: Systematic Validation Design

Research Question: How does the ratio of driver to order arrival intervals 
affect system performance and operational regime characteristics?

Arrival Interval Ratio Definition:
    arrival_interval_ratio = mean_driver_inter_arrival_time / mean_order_inter_arrival_time

Interpretation:
    - ratio = 3.0 → drivers arrive 3× slower than orders
    - ratio = 0.8 → drivers arrive 0.8× as slow (faster than orders)
    - Higher ratio → less driver supply relative to order demand

Design Pattern: For each arrival_interval_ratio R:
- Baseline Interval: (1.0, R) → "Higher intensity" (1.0 orders/min, 1/R drivers/min)
- 2x Baseline: (2.0, 2R) → "Half intensity" (0.5 orders/min, 1/2R drivers/min)

Research Hypothesis:
"Operational regime characteristics are determined by the interaction between 
arrival interval ratio and absolute operational intensity, with driver capacity 
serving as the primary system bottleneck."
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
print("ARRIVAL INTERVAL RATIO STUDY: SYSTEMATIC VALIDATION DESIGN")
print("="*80)
print("Research Question: How does arrival interval ratio affect system performance?")
print("Hypothesis: Regime determined by ratio × absolute intensity interaction")

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
Document your research question and its evolution.
"""

print("\n" + "="*80)
print("RESEARCH QUESTION")
print("="*80)

# ==============================================================================
# MAIN RESEARCH QUESTION
# ==============================================================================
research_question = """
(1) How does varying the arrival interval ratio affect system performance? 
By fixing order arrival intensity while varying driver arrival intensity, we systematically explore the transition from supply surplus to supply deficit conditions.
(2) Does absolute arrival intensity affect system performance beyond the arrival interval ratio? 
For a given ratio (relative supply-demand balance), does the absolute scale of operations independently influence system behavior?
"""
# ==============================================================================
# SCOPE & BOUNDARIES
# ==============================================================================
scope = """
Fixed factors (limits generalizability - future work to vary):
- Infrastructure: Single configuration (10km × 10km, 10 restaurants, seed=42)
- Pairing: Disabled throughout study
- Service duration: Fixed distribution (mean=100, std=60, min=30, max=200)
- Driver speed: 0.5 km/min

Varied factors:
- Arrival interval ratio: 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0
- Operational scale: Baseline vs 2× baseline for each ratio
  - Baseline: order_interval=1.0, driver_interval=ratio
  - 2× Baseline: order_interval=2.0, driver_interval=2×ratio

Systematic validation design: 10 ratios × 2 scales = 20 design points
"""


# %% CELL 4: Infrastructure Configuration(s)
"""
OPERATIONAL STUDY: Single fixed infrastructure.
Focus is on varying operational parameters, not infrastructure.
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
OPERATIONAL STUDY: Multiple configurations varying arrival interval ratios.

For each target ratio, create validation pair:
- Baseline: (1.0, ratio) → higher intensity
- 2x Baseline: (2.0, 2×ratio) → half intensity

This tests whether ratio alone determines regime or if absolute scale matters.
"""

# Target arrival interval ratios to test
target_arrival_interval_ratios = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]

# Fixed pairing configuration (pairing disabled for this study)
FIXED_PAIRING_CONFIG = {
    'pairing_enabled': False,
    'restaurants_proximity_threshold': None,
    'customers_proximity_threshold': None
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
    # Baseline configuration: (1.0, ratio)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_baseline',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **FIXED_PAIRING_CONFIG,
            **FIXED_SERVICE_CONFIG
        )
    })
    
    # 2x Baseline configuration: (2.0, 2×ratio)
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_2x_baseline',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=2.0,
            mean_driver_inter_arrival_time=2.0 * ratio,
            **FIXED_PAIRING_CONFIG,
            **FIXED_SERVICE_CONFIG
        )
    })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Testing {len(target_arrival_interval_ratios)} arrival interval ratios")
print(f"✓ Each ratio has 2 validation pairs (baseline + 2x_baseline)")

# Display configurations
for config in operational_configs:
    op_config = config['config']
    ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
    print(f"  • {config['name']}: "
          f"order_interval={op_config.mean_order_inter_arrival_time:.1f}min, "
          f"driver_interval={op_config.mean_driver_inter_arrival_time:.1f}min, "
          f"ratio={ratio:.1f}")

# %% CELL 9: Design Point Creation (SIMPLIFIED)
"""
Create design points from combinations.

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
    metrics=['active_drivers', 'available_drivers', 'unassigned_delivery_entities'],  # ← Added 'available_drivers'
    moving_average_window=100
)

print(f"✓ Time series processing complete for {len(all_time_series_data)} design points")
print(f"✓ Metrics extracted: active_drivers, available_drivers, unassigned_delivery_entities")  # ← Updated
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
    # Extract ratio from design name (e.g., "ratio_3.0_baseline")
    ratio_str = design_name.split('_')[1]  # "3.0"
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
print("KEY PERFORMANCE METRICS EXTRACTION AND PRESENTATION")
print("="*80)

import re

def extract_ratio_and_type(design_name):
    """Extract arrival interval ratio and interval type from design point name."""
    # Pattern: ratio_3.0_baseline or ratio_3.0_2x_baseline
    match = re.match(r'ratio_([\d.]+)_(2x_)?baseline', design_name)
    if not match:
        raise ValueError(f"Cannot parse design name: {design_name}")
    
    ratio = float(match.group(1))
    interval_type = '2x_baseline' if match.group(2) else 'baseline'
    
    return ratio, interval_type

# =========================================================================
# EXTRACT METRICS FROM ALL DESIGN POINTS
# =========================================================================
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    ratio, interval_type = extract_ratio_and_type(design_name)
    
    stats_with_cis = analysis_result.get('statistics_with_cis', {})
    
    # =====================================================================
    # ASSIGNMENT TIME (ORDER METRICS)
    # =====================================================================
    order_metrics = stats_with_cis.get('order_metrics', {})
    assignment_time = order_metrics.get('assignment_time', {})
    
    # Mean of Means
    mom = assignment_time.get('mean_of_means', {})
    mom_estimate = mom.get('point_estimate', 0)
    mom_ci = mom.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0
    
    # =====================================================================
    # TRAVEL TIME METRICS (ORDER METRICS)
    # =====================================================================
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
    
    # Fulfillment Time
    fulfillment_time = order_metrics.get('fulfillment_time', {})
    fulfillment_time_mom = fulfillment_time.get('mean_of_means', {})
    fulfillment_time_estimate = fulfillment_time_mom.get('point_estimate', 0)
    fulfillment_time_ci = fulfillment_time_mom.get('confidence_interval', [0, 0])
    fulfillment_time_ci_width = (fulfillment_time_ci[1] - fulfillment_time_ci[0]) / 2 if fulfillment_time_ci[0] is not None else 0
    
    # =====================================================================
    # QUEUE DYNAMICS METRICS
    # =====================================================================
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})
    
    # Growth Rate
    growth_rate_metric = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate_metric.get('point_estimate', 0)
    growth_rate_ci = growth_rate_metric.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0
    
    # Average Queue Size
    avg_queue = queue_dynamics_metrics.get('average_unassigned_entities', {})
    avg_queue_estimate = avg_queue.get('point_estimate', 0)
    avg_queue_ci = avg_queue.get('confidence_interval', [0, 0])
    avg_queue_ci_width = (avg_queue_ci[1] - avg_queue_ci[0]) / 2 if avg_queue_ci[0] is not None else 0
    
    # =====================================================================
    # SYSTEM STATE METRICS
    # =====================================================================
    system_state_metrics = stats_with_cis.get('system_state_metrics', {})
    
    # Driver Utilization
    driver_utilization = system_state_metrics.get('driver_utilization', {})
    driver_utilization_mom = driver_utilization.get('mean_of_means', {})
    driver_utilization_estimate = driver_utilization_mom.get('point_estimate', 0)
    driver_utilization_ci = driver_utilization_mom.get('confidence_interval', [0, 0])
    driver_utilization_ci_width = (driver_utilization_ci[1] - driver_utilization_ci[0]) / 2 if driver_utilization_ci[0] is not None else 0
    
    # =====================================================================
    # SYSTEM METRICS (ONE-LEVEL PATTERN)
    # =====================================================================
    system_metrics = stats_with_cis.get('system_metrics', {})
    
    # Immediate Assignment Rate
    immediate_assignment_rate = system_metrics.get('immediate_assignment_rate', {})
    immediate_assignment_rate_estimate = immediate_assignment_rate.get('point_estimate', 0)
    immediate_assignment_rate_ci = immediate_assignment_rate.get('confidence_interval', [0, 0])
    immediate_assignment_rate_ci_width = (immediate_assignment_rate_ci[1] - immediate_assignment_rate_ci[0]) / 2 if immediate_assignment_rate_ci[0] is not None else 0
    
    # =====================================================================
    # BUILD ROW
    # =====================================================================
    metrics_data.append({
        'ratio': ratio,
        'interval_type': interval_type,
        # Assignment time
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        # Travel time metrics
        'pickup_travel_time_estimate': pickup_travel_time_estimate,
        'pickup_travel_time_ci_width': pickup_travel_time_ci_width,
        'delivery_travel_time_estimate': delivery_travel_time_estimate,
        'delivery_travel_time_ci_width': delivery_travel_time_ci_width,
        'fulfillment_time_estimate': fulfillment_time_estimate,
        'fulfillment_time_ci_width': fulfillment_time_ci_width,
        # Queue dynamics
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        # System state
        'driver_utilization_estimate': driver_utilization_estimate,
        'driver_utilization_ci_width': driver_utilization_ci_width,
        # System metrics
        'immediate_assignment_rate_estimate': immediate_assignment_rate_estimate,
        'immediate_assignment_rate_ci_width': immediate_assignment_rate_ci_width,
    })

# Sort by ratio then interval type
metrics_data.sort(key=lambda x: (x['ratio'], x['interval_type']))

# =========================================================================
# PRINT FORMATTED TABLE
# =========================================================================
print("\n🎯 KEY PERFORMANCE METRICS: ASSIGNMENT TIME, TRAVEL METRICS & QUEUE DYNAMICS")
print("="*230)
print(" Ratio    Interval        Assignment Time      Pickup Travel      Delivery Travel      Fulfillment Time      Avg Queue Size      Growth Rate         Driver Utilization    Immediate Assign Rate")
print("              Type           (mean ± CI)          (mean ± CI)         (mean ± CI)          (mean ± CI)          (mean ± CI)     (entities/min)            (mean ± CI)             (mean ± CI)")
print("="*230)

for row in metrics_data:
    ratio = row['ratio']
    interval_display = "2x Baseline" if row['interval_type'] == '2x_baseline' else "Baseline"
    
    # Format all metrics: mean ± CI_width
    assignment_str = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
    pickup_str = f"{row['pickup_travel_time_estimate']:5.2f} ± {row['pickup_travel_time_ci_width']:5.2f}"
    delivery_str = f"{row['delivery_travel_time_estimate']:5.2f} ± {row['delivery_travel_time_ci_width']:5.2f}"
    fulfillment_str = f"{row['fulfillment_time_estimate']:6.2f} ± {row['fulfillment_time_ci_width']:6.2f}"
    avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
    growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"
    driver_util_str = f"{row['driver_utilization_estimate']:5.4f} ± {row['driver_utilization_ci_width']:5.4f}"
    immediate_assign_str = f"{row['immediate_assignment_rate_estimate']:5.4f} ± {row['immediate_assignment_rate_ci_width']:5.4f}"
    
    print(f"  {ratio:3.1f}  {interval_display:12s}     {assignment_str:>16s}    {pickup_str:>16s}    {delivery_str:>18s}    {fulfillment_str:>18s}    {avg_queue_str:>18s}    {growth_rate_str:>21s}    {driver_util_str:>20s}    {immediate_assign_str:>22s}")

print("="*230)

# %%
"""
VISUALIZATION OBJECTIVE: Test the hypothesis that "Arrival interval ratio determines 
which regime the system is in (qualitative behavior), but absolute intensity determines 
how severe the regime behavior is (quantitative magnitude)."

Expected Evidence:
1. Zero-crossing (regime boundary) occurs at similar ratio for both configurations
2. Assignment time shows parallel behavior with absolute differences
"""

import matplotlib.pyplot as plt
import numpy as np

print("\n" + "="*80)
print("REGIME-INTENSITY HYPOTHESIS VISUALIZATION")
print("="*80)

# Prepare data for plotting
ratios = sorted(list(set([d['ratio'] for d in metrics_data])))

# Separate baseline and 2x baseline data
baseline_data = {r: None for r in ratios}
baseline_2x_data = {r: None for r in ratios}

for row in metrics_data:
    if row['interval_type'] == 'baseline':
        baseline_data[row['ratio']] = row
    else:  # 2x_baseline
        baseline_2x_data[row['ratio']] = row

# Extract metrics for each configuration
def extract_metrics(data_dict):
    ratios_list = sorted(data_dict.keys())
    growth_rate = [data_dict[r]['growth_rate_estimate'] for r in ratios_list]
    growth_rate_err = [data_dict[r]['growth_rate_ci_width'] for r in ratios_list]
    assignment_time = [data_dict[r]['mom_estimate'] for r in ratios_list]
    assignment_time_err = [data_dict[r]['mom_ci_width'] for r in ratios_list]
    
    return {
        'ratios': ratios_list,
        'growth_rate': growth_rate,
        'growth_rate_err': growth_rate_err,
        'assignment_time': assignment_time,
        'assignment_time_err': assignment_time_err,
    }

baseline_metrics = extract_metrics(baseline_data)
baseline_2x_metrics = extract_metrics(baseline_2x_data)

# ============================================================================
# PLOT 1: Growth Rate vs Ratio (Regime Boundary Identification)
# ============================================================================
plt.figure(figsize=(10, 6))

# Plot baseline
plt.errorbar(baseline_metrics['ratios'], baseline_metrics['growth_rate'], 
             yerr=baseline_metrics['growth_rate_err'],
             marker='o', linewidth=2, markersize=8, capsize=5,
             label='Baseline (higher intensity)', color='#2E86AB', linestyle='-')

# Plot 2x baseline
plt.errorbar(baseline_2x_metrics['ratios'], baseline_2x_metrics['growth_rate'],
             yerr=baseline_2x_metrics['growth_rate_err'],
             marker='s', linewidth=2, markersize=8, capsize=5,
             label='2× Baseline (half intensity)', color='#A23B72', linestyle='--')

# Add horizontal line at y=0 (regime boundary)
plt.axhline(y=0, color='black', linestyle=':', linewidth=1.5, alpha=0.7, label='Regime boundary (growth=0)')

plt.xlabel('Arrival Interval Ratio (driver/order)', fontsize=12, fontweight='bold')
plt.ylabel('Growth Rate (entities/min)', fontsize=12, fontweight='bold')
plt.title('Plot 1: Regime Boundary Identification', fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='upper left', fontsize=11)
plt.grid(True, alpha=0.3, linestyle='--')
plt.xlim([2.25, 7.25])

# Add regime labels
y_top = plt.gca().get_ylim()[1]
plt.text(3.0, y_top*0.9, 'Stable\nRegime', 
         ha='center', va='top', fontsize=10, style='italic', 
         bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.3))
plt.text(6.0, y_top*0.9, 'Deteriorating\nRegime', 
         ha='center', va='top', fontsize=10, style='italic',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.3))

plt.tight_layout()
plt.show()

# ============================================================================
# PLOT 4: Assignment Time Comparison - LINEAR SCALE
# ============================================================================
plt.figure(figsize=(10, 6))

# Plot baseline
plt.errorbar(baseline_metrics['ratios'], baseline_metrics['assignment_time'],
             yerr=baseline_metrics['assignment_time_err'],
             marker='o', linewidth=2, markersize=8, capsize=5,
             label='Baseline (higher intensity)', color='#17BEBB', linestyle='-')

# Plot 2x baseline
plt.errorbar(baseline_2x_metrics['ratios'], baseline_2x_metrics['assignment_time'],
             yerr=baseline_2x_metrics['assignment_time_err'],
             marker='s', linewidth=2, markersize=8, capsize=5,
             label='2× Baseline (half intensity)', color='#9B59B6', linestyle='--')

plt.xlabel('Arrival Interval Ratio (driver/order)', fontsize=12, fontweight='bold')
plt.ylabel('Mean Assignment Time (min)', fontsize=12, fontweight='bold')
plt.title('Assignment Time: Customer-Facing Performance', fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='upper left', fontsize=11)
plt.grid(True, alpha=0.3, linestyle='--')
plt.xlim([2.25, 7.25])
plt.ylim([0, 50])  # Linear scale from 0 to 50 minutes

plt.tight_layout()
plt.show()


# %%
