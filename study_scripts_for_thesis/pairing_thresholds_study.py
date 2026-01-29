# pairing_thresholds_study.py
"""
Pairing Thresholds Sensitivity Study: Effect of Pairing Threshold Proportions on System Performance

Research Question: What proportion of area dimension produces optimal pairing performance, 
and is this proportion consistent across different area sizes?

Building on Previous Studies:
- Study 1 established three operational regimes based on arrival interval ratio
- Study 2 demonstrated that pairing shifts regime boundaries dramatically and improves 
  assignment times by ~60%
- Study 3 tested layout robustness across different random seeds
- Study 4 found restaurant count has minimal impact (0-15% customer benefit)
- Study 5 revealed that area size is the dominant infrastructure constraint (19-213× performance 
  degradation), and that fixed pairing thresholds (δ_r=4.0 km, δ_c=3.0 km) become increasingly 
  restrictive with area (80% → 27% of area dimension), yet pairing rate INCREASES with area 
  (stress symptom)

This Study (Study 6):
- Tests whether pairing thresholds should scale proportionally with delivery area size
- Investigates goldilocks pattern: balance between pair quality (route efficiency) and 
  quantity (pairing opportunities)
- Validates whether baseline thresholds (40% of area dimension) used in Studies 1-5 are optimal
- Examines if optimal proportion is consistent across different area sizes

Design Pattern:
- 2 delivery area sizes (10×10, 15×15 km) with fixed restaurant count (10)
- 3 threshold proportions (20%, 40%, 60%) where 40% matches Studies 1-5 baseline
- Single arrival interval ratio (7.0) where pairing is critical
- Single structural seed (42) for focused analysis
- Pairing always enabled (intervention study)

Total Design Points: 2 areas × 3 proportions = 6
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
print("PAIRING THRESHOLDS SENSITIVITY STUDY")
print("="*80)
print("Research Question: What proportion of area dimension produces optimal pairing")
print("performance, and is this proportion consistent across different area sizes?")
print("="*80)


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

# %% CELL 3.5: Research Question Documentation
"""
RESEARCH QUESTION: What proportion of area dimension produces optimal pairing performance?

CONTEXT FROM STUDY 5:
Study 5 revealed a paradox:
- Fixed thresholds (δ_r=4.0, δ_c=3.0) become increasingly restrictive with area:
  • 10×10 km: 40% of area dimension (reasonable)
  • 15×15 km: 27% of area dimension (restrictive)
- Yet pairing rate INCREASES with area (84.46% at 15×15 despite restrictive threshold)
- This suggests system under stress compensates through aggressive pairing
- Question: Are current thresholds optimal, or would adjustment improve performance?

THE GOLDILOCKS PRINCIPLE:
- Too Tight: High quality pairs, insufficient quantity → throughput suffers
- Optimal: Balance between pair quality and quantity → maximize throughput
- Too Loose: Many pairs, poor quality (long routes) → capacity suffers

SUB-QUESTIONS:
1. Does goldilocks pattern exist? (inverted-U performance curve)
2. Is baseline (40%) near optimal, or should we adjust?
3. Is optimal proportion consistent across different area sizes?
4. How does pair quality vs quantity tradeoff manifest?

SCOPE:
- 2 delivery area sizes: 10×10 km (baseline), 15×15 km (stressed)
- 3 threshold proportions: 20% (tight), 40% (baseline), 60% (loose)
- Single ratio: 7.0 (high stress - where pairing most critical)
- Single seed: 42 (focused main effect analysis)

ANALYSIS FOCUS:
1. Performance curves showing inverted-U pattern
2. Optimal proportion identification at each area
3. Quality-quantity tradeoff mechanism (pairing rate vs inter-restaurant distance)
4. Baseline validation (is 40% already optimal?)
5. Scaling consistency (same proportion across areas?)

EVOLUTION NOTES:
Study sequence positioning:
- Studies 1-2: Established operational regimes and pairing as first-order intervention
- Studies 3-4: Tested infrastructure robustness (layout, restaurant count)
- Study 5: Identified area size as dominant constraint, revealed threshold scaling issue
- Study 6 (THIS STUDY): Validates threshold scaling and identifies optimal proportion
- Study 7 (Future): Priority scoring weights strategy
"""

research_question = """
RESEARCH QUESTION: What proportion of area dimension produces optimal pairing performance?
"""

context = """
CONTEXT FROM STUDY 5:
Study 5 revealed a paradox:
- Fixed thresholds (δ_r=4.0, δ_c=3.0) become increasingly restrictive with area:
  • 10×10 km: 40% of area dimension (reasonable)
  • 15×15 km: 27% of area dimension (restrictive)
- Yet pairing rate INCREASES with area (84.46% at 15×15 despite restrictive threshold)
- This suggests system under stress compensates through aggressive pairing
- Question: Are current thresholds optimal, or would adjustment improve performance?
"""

sub_questions = """
SUB-QUESTIONS:
1. Does goldilocks pattern exist? (inverted-U performance curve)
2. Is baseline (40%) near optimal, or should we adjust?
3. Is optimal proportion consistent across different area sizes?
4. How does pair quality vs quantity tradeoff manifest?
"""

scope = """
SCOPE:
- 2 delivery area sizes: 10×10 km (baseline), 15×15 km (stressed)
- 3 threshold proportions: 20% (tight), 40% (baseline), 60% (loose)
- Single ratio: 7.0 (high stress - where pairing most critical)
- Single seed: 42 (focused main effect analysis)
"""

analysis_focus = """
ANALYSIS FOCUS:
1. Performance curves showing inverted-U pattern
2. Optimal proportion identification at each area
3. Quality-quantity tradeoff mechanism (pairing rate)
4. Baseline validation (is 40% already optimal?)
5. Scaling consistency (same proportion across areas?)
"""

evolution_notes = """
STUDY SEQUENCE POSITIONING:

Study 1: Arrival Interval Ratio Study (COMPLETE)
- Established regime structure and ratio as primary determinant

Study 2: Pairing Effect Study (COMPLETE)
- Demonstrated pairing shifts regime boundary dramatically (~60% improvement)

Study 3: Infrastructure Layout Study (COMPLETE)
- Tested layout robustness across random seeds
- Found pairing makes system robust to spatial variation

Study 4: Restaurant Count Study (COMPLETE)
- Tested count effect: minimal impact (0-15%)
- Established count as third-order factor

Study 5: Delivery Area Size Study (COMPLETE)
- Identified area size as dominant infrastructure constraint (19-213× degradation)
- Revealed fixed thresholds become increasingly restrictive with area
- Paradox: pairing rate increases despite restrictive thresholds (stress symptom)

Study 6: Pairing Thresholds Study (THIS STUDY)
- Validates threshold scaling with delivery area size
- Tests goldilocks pattern: quality-quantity tradeoff
- Determines optimal proportion for threshold setting
- Validates whether baseline (40%) already optimal

Future Studies:
- Study 7: Priority scoring weights strategy
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
PAIRING THRESHOLDS STUDY: Test threshold sensitivity at baseline and stressed areas.

Test 2 delivery area sizes while holding restaurant count constant at 10.
- 10×10 km: Baseline area from all previous studies
- 15×15 km: Stressed area where threshold optimization most impactful
"""

infrastructure_configs = [
    {
        'name': 'area_10',
        'config': StructuralConfig(
            delivery_area_size=10,
            num_restaurants=10,
            driver_speed=0.5
        ),
        'area_size': 10
    },
    {
        'name': 'area_15',
        'config': StructuralConfig(
            delivery_area_size=15,
            num_restaurants=10,
            driver_speed=0.5
        ),
        'area_size': 15
    }
]

print(f"✓ Defined {len(infrastructure_configs)} infrastructure configuration(s)")
for config in infrastructure_configs:
    struct_config = config['config']
    density = struct_config.num_restaurants / (struct_config.delivery_area_size ** 2)
    print(f"  • {config['name']}: area={struct_config.delivery_area_size}×{struct_config.delivery_area_size}km, "
          f"{struct_config.num_restaurants} restaurants, density={density:.4f}/km²")


# %% CELL 5: Structural Seeds
"""
FOCUSED STUDY: Single seed for main effect analysis.

Using seed 42 (baseline from previous studies) to test primary research question.
"""

structural_seeds = [42]

print(f"✓ Structural seeds: {structural_seeds}")
print(f"✓ Single seed approach: Focus on main effect of pairing thresholds")


# %% CELL 6: Create Infrastructure Instances
"""
Create and analyze infrastructure instances for each delivery area size.

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
            'seed': structural_seed,
            'area_size': infra_config['area_size']
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

Visual inspection helps understand how delivery area size affects spatial coverage.
"""

print("\n" + "="*50)
print("INFRASTRUCTURE LAYOUT VISUALIZATION")
print("="*50)

import matplotlib.pyplot as plt

print(f"\nVisualizing {len(infrastructure_instances)} delivery area size configurations...")
print("Compare spatial coverage as area size increases.\n")

for instance in infrastructure_instances:
    print(f"{'='*50}")
    print(f"Configuration: {instance['name']}")
    print(f"Area Size: {instance['area_size']}×{instance['area_size']} km")
    print(f"Typical Distance: {instance['analysis']['typical_distance']:.3f}km")
    print(f"Restaurant Density: {instance['analysis']['restaurant_density']:.4f}/km²")
    print(f"{'='*50}")
    
    instance['analyzer'].visualize_infrastructure()
    
    fig = plt.gcf()
    area_size = instance['area_size']
    typical_dist = instance['analysis']['typical_distance']
    
    custom_title = (f"Delivery Area Size: {area_size}×{area_size}km\n"
                   f"Typical Distance: {typical_dist:.3f}km | "
                   f"Restaurants: 10 | Seed: 42")
    
    fig.suptitle(custom_title, fontsize=14, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    plt.show()
    
    print(f"✓ {instance['name']} visualized\n")

print(f"{'='*50}")
print("✓ All configurations visualized")
print("✓ Observe spatial coverage patterns:")
print("  - How does typical distance change with area size?")
print("  - Does restaurant spacing increase as expected?")
print("  - Are there areas with poor coverage at large sizes?")
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
PAIRING THRESHOLDS STUDY: Test threshold proportions at high stress ratio.

Design:
- 1 arrival interval ratio: 7.0 (high stress - where pairing critical)
- 3 threshold proportions: 20% (tight), 40% (baseline), 60% (loose)
  - Proportion defines δ_r as fraction of area dimension
  - δ_c maintains 3:4 ratio with δ_r (from original configuration)
- Pairing always enabled (intervention study)
- Baseline intensity only: mean_order_inter_arrival_time = 1.0 min

Threshold calculation:
- δ_r = proportion × area_size
- δ_c = 0.75 × δ_r

Example for 10×10 km area:
- Tight (20%): δ_r = 2.0 km, δ_c = 1.5 km
- Baseline (40%): δ_r = 4.0 km, δ_c = 3.0 km (matches Studies 1-5)
- Loose (60%): δ_r = 6.0 km, δ_c = 4.5 km

This creates 3 operational configurations per delivery area size.
"""

# Target ratio (single value for focused study)
target_ratio = 7.0

# Threshold proportions to test
threshold_proportions = [0.20, 0.40, 0.60]
proportion_names = {0.20: '20pct', 0.40: '40pct', 0.60: '60pct'}
proportion_labels = {0.20: 'Tight (20%)', 0.40: 'Baseline (40%)', 0.60: 'Loose (60%)'}

# Fixed service duration configuration
FIXED_SERVICE_CONFIG = {
    'mean_service_duration': 100,
    'service_duration_std_dev': 60,
    'min_service_duration': 30,
    'max_service_duration': 200
}

# Build operational configs
operational_configs = []

for infra_instance in infrastructure_instances:
    area_size = infra_instance['area_size']
    
    for proportion in threshold_proportions:
        # Calculate thresholds based on proportion
        delta_r = proportion * area_size
        delta_c = 0.75 * delta_r  # Maintain 3:4 ratio
        
        # Pairing parameters with calculated thresholds
        pairing_params = {
            'pairing_enabled': True,
            'restaurants_proximity_threshold': delta_r,
            'customers_proximity_threshold': delta_c,
        }
        
        config_name = f"{infra_instance['config_name']}_ratio_{target_ratio:.1f}_thres_{proportion_names[proportion]}"
        
        operational_configs.append({
            'name': config_name,
            'config': OperationalConfig(
                mean_order_inter_arrival_time=1.0,
                mean_driver_inter_arrival_time=target_ratio,
                **pairing_params,
                **FIXED_SERVICE_CONFIG
            ),
            'area_size': area_size,
            'proportion': proportion,
            'delta_r': delta_r,
            'delta_c': delta_c
        })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Testing ratio: {target_ratio}")
print(f"✓ Testing {len(threshold_proportions)} threshold proportions: {threshold_proportions}")

print("\nConfiguration breakdown:")
for config in operational_configs:
    op_config = config['config']
    ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
    proportion_pct = int(config['proportion'] * 100)
    print(f"  • {config['name']}: ratio={ratio:.1f}, "
          f"{proportion_labels[config['proportion']]}, "
          f"δ_r={config['delta_r']:.2f}km, δ_c={config['delta_c']:.2f}km")


# %% CELL 9: Design Point Creation
"""
Create design points from all combinations.

Total: 2 areas × 3 threshold proportions = 6 design points
"""

design_points = {}

print("\n" + "="*50)
print("DESIGN POINTS CREATION")
print("="*50)

for infra_instance in infrastructure_instances:
    # Find operational configs for this infrastructure
    matching_op_configs = [op for op in operational_configs if op['area_size'] == infra_instance['area_size']]
    
    for op_config_dict in matching_op_configs:
        for scoring_config_dict in scoring_configs:
            
            design_name = f"{infra_instance['name']}_{op_config_dict['name']}"
            
            design_points[design_name] = DesignPoint(
                infrastructure=infra_instance['infrastructure'],
                operational_config=op_config_dict['config'],
                scoring_config=scoring_config_dict['config'],
                name=design_name
            )
            
            print(f"  ✓ Design point: {design_name}")

print(f"\n{'='*50}")
print(f"✓ Created {len(design_points)} design points")
print(f"✓ Breakdown: {len(infrastructure_instances)} areas × "
      f"{len(threshold_proportions)} threshold proportions × {len(scoring_configs)} scoring")
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
print(f"  • Collection interval: {experiment_config.collection_interval} minute(s)")
print(f"  • Total runs: {total_runs}")
print(f"  • Estimated time: ~{estimated_time} seconds (~{estimated_time/60:.1f} minutes)")


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

# Group design points by area for organized display
area_groups = {}
for design_name in all_time_series_data.keys():
    # Extract area from design name (e.g., "area_10_seed42_area_10_ratio_7.0_thres_20pct")
    parts = design_name.split('_')
    area_str = parts[1]  # "10" or "15"
    area = int(area_str)
    
    if area not in area_groups:
        area_groups[area] = []
    area_groups[area].append(design_name)

print(f"✓ Grouped {len(all_time_series_data)} design points by {len(area_groups)} areas")

# Create plots systematically by area
plot_count = 0
for area in sorted(area_groups.keys()):
    print(f"\nArea {area}×{area} km:")
    
    for design_name in sorted(area_groups[area]):
        plot_title = f"Warmup Analysis: {design_name}"
        time_series_data = all_time_series_data[design_name]
        fig = viz.create_warmup_analysis_plot(time_series_data, title=plot_title)
        
        plt.show()
        print(f"    ✓ {design_name} plot displayed")
        plot_count += 1

print(f"\n✓ Warmup analysis visualization complete")
print(f"✓ Created {plot_count} warmup analysis plots")
print(f"✓ Organized by {len(area_groups)} areas")


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
                         'system_state_metrics', 'queue_dynamics_metrics', 'delivery_unit_metrics'],
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
print("KEY PERFORMANCE METRICS: PAIRING THRESHOLDS STUDY")
print("="*80)

import re

def extract_area_ratio_and_threshold(design_name):
    """Extract area size, ratio, and threshold proportion from design point name."""
    # Pattern: area_10_seed42_area_10_ratio_7.0_thres_20pct
    match = re.match(r'area_(\d+)_seed\d+_area_\d+_ratio_([\d.]+)_thres_(\d+)pct', design_name)
    if match:
        area_size = int(match.group(1))
        ratio = float(match.group(2))
        proportion_pct = int(match.group(3))
        return area_size, ratio, proportion_pct
    else:
        raise ValueError(f"Could not parse design name: {design_name}")

# Extract metrics for tabular display
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    area_size, ratio, proportion_pct = extract_area_ratio_and_threshold(design_name)
    
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
    
    # Pickup Travel Time Statistics (Mean of Means with CI)
    pickup_travel_time = order_metrics.get('pickup_travel_time', {})
    pickup_travel_time_mom = pickup_travel_time.get('mean_of_means', {})
    pickup_travel_time_estimate = pickup_travel_time_mom.get('point_estimate', 0)
    pickup_travel_time_ci = pickup_travel_time_mom.get('confidence_interval', [0, 0])
    pickup_travel_time_ci_width = (pickup_travel_time_ci[1] - pickup_travel_time_ci[0]) / 2 if pickup_travel_time_ci[0] is not None else 0
    
    # Delivery Travel Time Statistics (Mean of Means with CI)
    delivery_travel_time = order_metrics.get('delivery_travel_time', {})
    delivery_travel_time_mom = delivery_travel_time.get('mean_of_means', {})
    delivery_travel_time_estimate = delivery_travel_time_mom.get('point_estimate', 0)
    delivery_travel_time_ci = delivery_travel_time_mom.get('confidence_interval', [0, 0])
    delivery_travel_time_ci_width = (delivery_travel_time_ci[1] - delivery_travel_time_ci[0]) / 2 if delivery_travel_time_ci[0] is not None else 0
    
    # Travel Time Statistics (Mean of Means with CI)
    travel_time = order_metrics.get('travel_time', {})
    travel_time_mom = travel_time.get('mean_of_means', {})
    travel_time_estimate = travel_time_mom.get('point_estimate', 0)
    travel_time_ci = travel_time_mom.get('confidence_interval', [0, 0])
    travel_time_ci_width = (travel_time_ci[1] - travel_time_ci[0]) / 2 if travel_time_ci[0] is not None else 0
    
    # Fulfillment Time Statistics (Mean of Means with CI)
    fulfillment_time = order_metrics.get('fulfillment_time', {})
    fulfillment_time_mom = fulfillment_time.get('mean_of_means', {})
    fulfillment_time_estimate = fulfillment_time_mom.get('point_estimate', 0)
    fulfillment_time_ci = fulfillment_time_mom.get('confidence_interval', [0, 0])
    fulfillment_time_ci_width = (fulfillment_time_ci[1] - fulfillment_time_ci[0]) / 2 if fulfillment_time_ci[0] is not None else 0
    
    # First Contact Time Statistics (Mean of Means with CI) - from delivery_unit_metrics
    delivery_unit_metrics = stats_with_cis.get('delivery_unit_metrics', {})
    first_contact_time = delivery_unit_metrics.get('first_contact_time', {})
    first_contact_time_mom = first_contact_time.get('mean_of_means', {})
    first_contact_time_estimate = first_contact_time_mom.get('point_estimate', 0)
    first_contact_time_ci = first_contact_time_mom.get('confidence_interval', [0, 0])
    first_contact_time_ci_width = (first_contact_time_ci[1] - first_contact_time_ci[0]) / 2 if first_contact_time_ci[0] is not None else 0
    
    # Growth Rate
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})
    growth_rate = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate.get('point_estimate', 0)
    growth_rate_ci = growth_rate.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0
    
    # Pairing Rate - from system_metrics
    system_metrics = stats_with_cis.get('system_metrics', {})
    pairing_rate = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate.get('point_estimate', None)
    pairing_rate_ci = pairing_rate.get('confidence_interval', [None, None])
    pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2 if pairing_rate_ci[0] is not None else None
    
    metrics_data.append({
        'area_size': area_size,
        'ratio': ratio,
        'proportion_pct': proportion_pct,
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'som_estimate': som_estimate,
        'mos_estimate': mos_estimate,
        'first_contact_time_estimate': first_contact_time_estimate,
        'first_contact_time_ci_width': first_contact_time_ci_width,
        'pickup_travel_time_estimate': pickup_travel_time_estimate,
        'pickup_travel_time_ci_width': pickup_travel_time_ci_width,
        'delivery_travel_time_estimate': delivery_travel_time_estimate,
        'delivery_travel_time_ci_width': delivery_travel_time_ci_width,
        'travel_time_estimate': travel_time_estimate,
        'travel_time_ci_width': travel_time_ci_width,
        'fulfillment_time_estimate': fulfillment_time_estimate,
        'fulfillment_time_ci_width': fulfillment_time_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width
    })

# Sort by area size, then proportion
metrics_data.sort(key=lambda x: (x['area_size'], x['proportion_pct']))

# Display table grouped by area size
print("\n🎯 PRIMARY VIEW: GROUPED BY DELIVERY AREA SIZE")
print("="*260)
print(f"  {'Area':<6} {'Ratio':<6} {'Threshold':<12} │ {'Mean of Means':>18} {'Std of':>10} {'Mean of':>10} │ {'First Contact':>18} │ {'Pickup':>18} │ {'Delivery':>18} │ {'Travel Time':>18} │ {'Fulfillment':>18} │ {'Growth Rate':>22} │ {'Pairing Rate':>18}")
print(f"  {'(km²)':<6} {'':6} {'Proportion':12} │ {'(Assign Time)':>18} {'Means':>10} {'Stds':>10} │ {'Time':>18} │ {'Travel':>18} │ {'Travel':>18} │ {'(Total)':>18} │ {'Time':>18} │ {'(entities/min)':>22} │ {'(% paired)':>18}")
print("="*260)

current_area = None
for row in metrics_data:
    # Add separator between different area sizes
    if current_area is not None and row['area_size'] != current_area:
        print("-" * 260)
    current_area = row['area_size']
    
    # Format metrics
    proportion_display = f"{row['proportion_pct']}%"
    mom_str = f"{row['mom_estimate']:6.2f} ± {row['mom_ci_width']:5.2f}"
    som_str = f"{row['som_estimate']:6.2f}"
    mos_str = f"{row['mos_estimate']:6.2f}"
    first_contact_str = f"{row['first_contact_time_estimate']:6.2f} ± {row['first_contact_time_ci_width']:5.2f}"
    pickup_str = f"{row['pickup_travel_time_estimate']:6.2f} ± {row['pickup_travel_time_ci_width']:5.2f}"
    delivery_str = f"{row['delivery_travel_time_estimate']:6.2f} ± {row['delivery_travel_time_ci_width']:5.2f}"
    travel_str = f"{row['travel_time_estimate']:6.2f} ± {row['travel_time_ci_width']:5.2f}"
    fulfill_str = f"{row['fulfillment_time_estimate']:6.2f} ± {row['fulfillment_time_ci_width']:5.2f}"
    growth_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:6.4f}"
    
    if row['pairing_rate_estimate'] is not None:
        pairing_pct = row['pairing_rate_estimate'] * 100
        pairing_ci_pct = row['pairing_rate_ci_width'] * 100 if row['pairing_rate_ci_width'] else 0
        pairing_str = f"{pairing_pct:6.2f} ± {pairing_ci_pct:5.2f}"
    else:
        pairing_str = "N/A"
    
    print(f"  {row['area_size']:<6} {row['ratio']:<6.1f} {proportion_display:<12} │ "
          f"{mom_str:>18} {som_str:>10} {mos_str:>10} │ "
          f"{first_contact_str:>18} │ "
          f"{pickup_str:>18} │ "
          f"{delivery_str:>18} │ "
          f"{travel_str:>18} │ "
          f"{fulfill_str:>18} │ "
          f"{growth_str:>22} │ "
          f"{pairing_str:>18}")

print("="*260)

print("\n📊 KEY OBSERVATIONS:")
print("  • Assignment Time: Primary customer-facing metric (Mean of Means with 95% CI)")
print("  • Growth Rate: System stability indicator (positive = unstable)")
print("  • Pairing Rate: Proportion of orders assigned as pairs")
print("  • Threshold Proportion: % of area dimension used for pairing thresholds")
print("  • Compare across threshold proportions within each area size")
print("  • Look for goldilocks pattern: optimal proportion balancing quality and quantity")

print("\n" + "="*80)
print("✓ PAIRING THRESHOLDS STUDY COMPLETE")
print("="*80)
# %%
