# priority_scoring_weights_study.py
"""
Priority Scoring Weights Strategy Study: Regime-Dependent Weight Optimization

Research Question: How do different priority scoring weight strategies affect 
system performance across stable and stressed operational regimes?

Building on Previous Studies:
- Study 1 established operational regimes based on arrival interval ratio (no pairing)
- Study 2 demonstrated pairing shifts regime boundaries dramatically (~60% improvement)
- Study 3 tested layout robustness across random seeds
- Study 4 found restaurant count has minimal impact (0-15%)
- Study 5 revealed area size as dominant infrastructure constraint (19-213× degradation)
- Study 6 validated 40% threshold proportion as optimal across area scales

This Study (Study 7):
- Tests how priority scoring weight strategies perform in different operational regimes
- Uses empirically-established regime contexts from Studies 5-6:
  - 10×10 km at ratio 7.0: Stable regime (queue ~8, growth ~0.0015)
  - 15×15 km at ratio 7.0: Stressed regime (queue ~55, growth ~0.027)
- Investigates distance-throughput tradeoff within efficiency focus
- Tests whether fairness consideration is viable across regimes
- Determines optimal weight strategy for different operational contexts

Design Pattern:
- 2 delivery area sizes (10×10, 15×15 km) representing stable vs stressed regimes
- 4 weight strategies: efficiency_default, throughput_focused, distance_focused, fairness_consideration
- Fixed pairing thresholds: 40% of area dimension (Study 6's optimal proportion)
- Fixed arrival interval ratio (7.0) and restaurant count (10)
- Single structural seed (42) for focused analysis

Total Design Points: 2 areas × 4 weight strategies = 8
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
print("PRIORITY SCORING WEIGHTS STRATEGY STUDY")
print("="*80)
print("Research Question: How do weight strategies perform across operational regimes?")

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

research_question = """
RESEARCH QUESTION:
How do different priority scoring weight strategies affect system performance 
across stable and stressed operational regimes?
"""

context = """
CONTEXT FROM PREVIOUS STUDIES:

Study 1: Established arrival interval ratio as primary regime determinant (no pairing)
Study 2: Showed pairing shifts regime boundaries dramatically (~60% improvement)
Study 3: Tested layout robustness across random seeds
Study 4: Found restaurant count has minimal impact (0-15%)
Study 5: Demonstrated delivery area as dominant infrastructure constraint
Study 6: Validated 40% threshold proportion as optimal across area scales

Studies 5-6 established clear regime differentiation at ratio 7.0:
- 10×10 km: Stable regime (avg queue ~8, growth ~0.0015)
- 15×15 km: Stressed regime (avg queue ~55, growth ~0.027)

Current default scoring weights: (0.5 distance, 0.5 throughput, 0.0 fairness)
This default creates "level playing field" between pairs and singles.
"""

sub_questions = """
SUB-QUESTIONS:

1. Is the current default (0.5, 0.5, 0.0) already optimal?
   - Or should the distance-throughput balance be adjusted?

2. Does optimal strategy differ between stable and stressed regimes?
   - Can stable regime afford different priorities than stressed regime?

3. Is moderate fairness consideration (0.2) viable?
   - Hypothesis: Viable in stable, costly in stressed

4. What's the distance-throughput tradeoff?
   - Does throughput focus improve capacity utilization?
   - Does distance focus hurt system throughput?
"""

scope = """
SCOPE:
- 2 delivery areas: 10×10 km (stable regime), 15×15 km (stressed regime)
- 4 weight strategies: efficiency spectrum + fairness consideration
- Fixed pairing: ON with 40% threshold proportion (scaled to area)
- Fixed ratio: 7.0 (regime differentiation via area)
- Single seed: 42 (focused main effect analysis)
"""

analysis_focus = """
ANALYSIS FOCUS:
1. Performance comparison across weight strategies within each regime
2. Regime-dependent optimal weight identification
3. Distance-throughput tradeoff within efficiency focus
4. Fairness consideration viability assessment
5. Robustness of current default across regimes
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

Study 6: Pairing Thresholds Study (COMPLETE)
- Validated 40% threshold proportion as optimal
- Established regime differentiation at ratio 7.0 via area size

Study 7: Priority Scoring Weights Strategy Study (THIS STUDY)
- Tests weight strategies in empirically-established regimes
- Investigates distance-throughput-fairness tradeoffs
- Provides operational guidance for weight selection
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
PRIORITY SCORING WEIGHTS STUDY: Test weight strategies at stable and stressed regimes.

Test 2 delivery area sizes while holding restaurant count constant at 10.
These area sizes represent empirically-established operational regimes from Studies 5-6.
"""

# Define infrastructure configurations
infrastructure_configs = []

# Stable regime context: 10×10 km
infrastructure_configs.append({
    'name': 'area_10',
    'config': StructuralConfig(
        delivery_area_size=10,
        num_restaurants=10,
        driver_speed=0.5
    ),
    'area_size': 10
})

# Stressed regime context: 15×15 km  
infrastructure_configs.append({
    'name': 'area_15',
    'config': StructuralConfig(
        delivery_area_size=15,
        num_restaurants=10,
        driver_speed=0.5
    ),
    'area_size': 15
})

print(f"✓ Defined {len(infrastructure_configs)} infrastructure configuration(s)")
for config in infrastructure_configs:
    area_size = config['area_size']
    regime = 'stable' if area_size == 10 else 'stressed'
    print(f"  • {config['name']}: {area_size}×{area_size} km ({regime} regime)")


# %% CELL 5: Structural Seed Selection
"""
Single seed approach for focused main effect analysis.

Using seed 42 (baseline from previous studies) to test primary research question.
"""

structural_seeds = [42]

print(f"✓ Structural seeds: {structural_seeds}")
print(f"✓ Single seed approach: Focus on main effect of weight strategies")


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
PRIORITY SCORING WEIGHTS STUDY: Test different weight strategies.

Four weight strategies to test:
1. efficiency_default (0.5, 0.5, 0.0): Current system default
2. throughput_focused (0.3, 0.7, 0.0): Prioritize capacity/pairing
3. distance_focused (0.7, 0.3, 0.0): Prioritize geographic efficiency
4. fairness_consideration (0.4, 0.4, 0.2): Moderate fairness incorporation
"""

scoring_configs = [
    {
        'name': 'efficiency_default',
        'config': ScoringConfig(
            weight_distance=0.5,
            weight_throughput=0.5,
            weight_fairness=0.0
        )
    },
    {
        'name': 'throughput_focused',
        'config': ScoringConfig(
            weight_distance=0.3,
            weight_throughput=0.7,
            weight_fairness=0.0
        )
    },
    {
        'name': 'distance_focused',
        'config': ScoringConfig(
            weight_distance=0.7,
            weight_throughput=0.3,
            weight_fairness=0.0
        )
    },
    {
        'name': 'fairness_consideration',
        'config': ScoringConfig(
            weight_distance=0.4,
            weight_throughput=0.4,
            weight_fairness=0.2
        )
    },
]

print(f"\n✓ Defined {len(scoring_configs)} scoring configuration(s)")
for config in scoring_configs:
    sc = config['config']
    print(f"  • {config['name']}: "
          f"distance={sc.weight_distance:.1f}, "
          f"throughput={sc.weight_throughput:.1f}, "
          f"fairness={sc.weight_fairness:.1f}")


# %% CELL 8: Operational Configuration(s)
"""
PRIORITY SCORING WEIGHTS STUDY: Test weight strategies at high stress ratio with optimal thresholds.

Design:
- 1 arrival interval ratio: 7.0 (high stress - regime differentiation via area)
- 1 threshold proportion: 40% (optimal from Study 6)
  - Proportion defines δ_r as fraction of area dimension
  - δ_c maintains 3:4 ratio with δ_r
- Pairing always enabled
- Baseline intensity only: mean_order_inter_arrival_time = 1.0 min

Threshold calculation:
- δ_r = 0.40 × area_size
- δ_c = 0.75 × δ_r

For 10×10 km: δ_r = 4.0 km, δ_c = 3.0 km
For 15×15 km: δ_r = 6.0 km, δ_c = 4.5 km

This creates 1 operational configuration per delivery area size.
Weight strategies will be varied via scoring configurations.
"""

# Target ratio (single value for focused study)
target_ratio = 7.0

# Optimal threshold proportion from Study 6
optimal_proportion = 0.40

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
    
    # Calculate thresholds based on optimal proportion
    delta_r = optimal_proportion * area_size
    delta_c = 0.75 * delta_r  # Maintain 3:4 ratio
    
    # Pairing parameters with calculated thresholds
    pairing_params = {
        'pairing_enabled': True,
        'restaurants_proximity_threshold': delta_r,
        'customers_proximity_threshold': delta_c,
    }
    
    config_name = f"{infra_instance['config_name']}_ratio_{target_ratio:.1f}"
    
    operational_configs.append({
        'name': config_name,
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=target_ratio,
            **pairing_params,
            **FIXED_SERVICE_CONFIG
        ),
        'area_size': area_size,
        'delta_r': delta_r,
        'delta_c': delta_c
    })

print(f"\n✓ Defined {len(operational_configs)} operational configuration(s)")
print(f"✓ Testing ratio: {target_ratio}")
print(f"✓ Using optimal threshold proportion: {optimal_proportion} (40%)")

print("\nConfiguration breakdown:")
for config in operational_configs:
    op_config = config['config']
    ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
    regime = 'stable' if config['area_size'] == 10 else 'stressed'
    print(f"  • {config['name']}: ratio={ratio:.1f}, {regime} regime, "
          f"δ_r={config['delta_r']:.2f}km, δ_c={config['delta_c']:.2f}km")


# %% CELL 9: Design Point Creation
"""
Create design points from all combinations.

Pattern: Area (regime) × Weight Strategy
Total: 2 areas × 4 weight strategies = 8 design points
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
            
            design_name = f"{infra_instance['name']}_{op_config_dict['name']}_weight_{scoring_config_dict['name']}"
            
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
      f"{len(operational_configs)} operational × {len(scoring_configs)} weight strategies")
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

print(f"\n✓ Experiment configuration:")
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
    # Extract area from design name (e.g., "area_10_seed42_area_10_ratio_7.0_weight_efficiency_default")
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
    regime = 'stable' if area == 10 else 'stressed'
    print(f"\nArea {area}×{area} km ({regime} regime):")
    
    for design_name in sorted(area_groups[area]):
        plot_title = f"Warmup Analysis: {design_name}"
        time_series_data = all_time_series_data[design_name]
        fig = viz.create_warmup_analysis_plot(time_series_data, title=plot_title)
        
        plt.show()
        print(f"    ✓ {design_name} plot displayed")
        plot_count += 1

print(f"\n✓ Warmup analysis visualization complete")
print(f"✓ Created {plot_count} warmup analysis plots")
print(f"✓ Organized by {len(area_groups)} areas (regimes)")


# %% CELL 14: Warmup Period Determination
print("\n" + "="*50)
print("WARMUP PERIOD DETERMINATION")
print("="*50)

# Use consistent warmup period from Studies 5-6
uniform_warmup_period = 500

print(f"✓ Warmup period set: {uniform_warmup_period} minutes")
print(f"✓ Based on visual inspection of active drivers oscillation around Little's Law values")
print(f"✓ Consistent with Studies 5-6 pairing thresholds studies")
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
print("KEY PERFORMANCE METRICS: PRIORITY SCORING WEIGHTS STUDY")
print("="*80)

import re

def extract_area_ratio_and_weight(design_name):
    """Extract area size, ratio, and weight strategy from design point name."""
    # Pattern: area_10_seed42_area_10_ratio_7.0_weight_efficiency_default
    match = re.match(r'area_(\d+)_seed\d+_area_\d+_ratio_([\d.]+)_weight_(\w+)', design_name)
    if match:
        area_size = int(match.group(1))
        ratio = float(match.group(2))
        weight_strategy = match.group(3)
        return area_size, ratio, weight_strategy
    return None, None, None

# Extract comprehensive metrics for table
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    area_size, ratio, weight_strategy = extract_area_ratio_and_weight(design_name)
    if area_size is None:
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
    
    # First Contact Time Statistics
    delivery_unit_metrics = stats_with_cis.get('delivery_unit_metrics', {})
    first_contact_time = delivery_unit_metrics.get('first_contact_time', {})
    first_contact_time_mom = first_contact_time.get('mean_of_means', {})
    first_contact_time_estimate = first_contact_time_mom.get('point_estimate', 0)
    first_contact_time_ci = first_contact_time_mom.get('confidence_interval', [0, 0])
    first_contact_time_ci_width = (first_contact_time_ci[1] - first_contact_time_ci[0]) / 2 if first_contact_time_ci[0] is not None else 0
    
    # Pickup Travel Time Statistics
    pickup_travel_time = order_metrics.get('pickup_travel_time', {})
    pickup_travel_time_mom = pickup_travel_time.get('mean_of_means', {})
    pickup_travel_time_estimate = pickup_travel_time_mom.get('point_estimate', 0)
    pickup_travel_time_ci = pickup_travel_time_mom.get('confidence_interval', [0, 0])
    pickup_travel_time_ci_width = (pickup_travel_time_ci[1] - pickup_travel_time_ci[0]) / 2 if pickup_travel_time_ci[0] is not None else 0
    
    # Delivery Travel Time Statistics
    delivery_travel_time = order_metrics.get('delivery_travel_time', {})
    delivery_travel_time_mom = delivery_travel_time.get('mean_of_means', {})
    delivery_travel_time_estimate = delivery_travel_time_mom.get('point_estimate', 0)
    delivery_travel_time_ci = delivery_travel_time_mom.get('confidence_interval', [0, 0])
    delivery_travel_time_ci_width = (delivery_travel_time_ci[1] - delivery_travel_time_ci[0]) / 2 if delivery_travel_time_ci[0] is not None else 0
    
    # Travel Time Statistics (Total)
    travel_time = order_metrics.get('travel_time', {})
    travel_time_mom = travel_time.get('mean_of_means', {})
    travel_time_estimate = travel_time_mom.get('point_estimate', 0)
    travel_time_ci = travel_time_mom.get('confidence_interval', [0, 0])
    travel_time_ci_width = (travel_time_ci[1] - travel_time_ci[0]) / 2 if travel_time_ci[0] is not None else 0
    
    # Fulfillment Time Statistics
    fulfillment_time = order_metrics.get('fulfillment_time', {})
    fulfillment_time_mom = fulfillment_time.get('mean_of_means', {})
    fulfillment_time_estimate = fulfillment_time_mom.get('point_estimate', 0)
    fulfillment_time_ci = fulfillment_time_mom.get('confidence_interval', [0, 0])
    fulfillment_time_ci_width = (fulfillment_time_ci[1] - fulfillment_time_ci[0]) / 2 if fulfillment_time_ci[0] is not None else 0
    
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
    
    # Pairing Rate
    system_metrics = stats_with_cis.get('system_metrics', {})
    pairing_rate = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate.get('point_estimate', None)
    pairing_rate_ci = pairing_rate.get('confidence_interval', [None, None])
    pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2 if pairing_rate_ci[0] is not None else None
    
    metrics_data.append({
        'area_size': area_size,
        'ratio': ratio,
        'weight_strategy': weight_strategy,
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
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width
    })

# Sort by area size, then weight strategy
strategy_order = {
    'efficiency_default': 0,
    'throughput_focused': 1,
    'distance_focused': 2,
    'fairness_consideration': 3
}
metrics_data.sort(key=lambda x: (x['area_size'], strategy_order.get(x['weight_strategy'], 99)))

# Display table grouped by area size
print("\n🎯 PRIMARY VIEW: GROUPED BY DELIVERY AREA SIZE")
print("="*280)
print(f"  {'Area':<6} {'Ratio':<6} {'Weight':<25} │ {'Mean of Means':>18} {'Std of':>10} {'Mean of':>10} │ {'First Contact':>18} │ {'Pickup':>18} │ {'Delivery':>18} │ {'Travel Time':>18} │ {'Fulfillment':>18} │ {'Avg Queue':>18} │ {'Growth Rate':>22} │ {'Pairing Rate':>18}")
print(f"  {'(km²)':<6} {'':6} {'Strategy':25} │ {'(Assign Time)':>18} {'Means':>10} {'Stds':>10} │ {'Time':>18} │ {'Travel':>18} │ {'Travel':>18} │ {'(Total)':>18} │ {'Time':>18} │ {'Size':>18} │ {'(entities/min)':>22} │ {'(% paired)':>18}")
print("="*280)

current_area = None
for row in metrics_data:
    # Add separator between different area sizes
    if current_area is not None and row['area_size'] != current_area:
        print("-" * 280)
    current_area = row['area_size']
    
    # Format metrics
    mom_str = f"{row['mom_estimate']:6.2f} ± {row['mom_ci_width']:5.2f}"
    som_str = f"{row['som_estimate']:6.2f}"
    mos_str = f"{row['mos_estimate']:6.2f}"
    first_contact_str = f"{row['first_contact_time_estimate']:6.2f} ± {row['first_contact_time_ci_width']:5.2f}"
    pickup_str = f"{row['pickup_travel_time_estimate']:6.2f} ± {row['pickup_travel_time_ci_width']:5.2f}"
    delivery_str = f"{row['delivery_travel_time_estimate']:6.2f} ± {row['delivery_travel_time_ci_width']:5.2f}"
    travel_str = f"{row['travel_time_estimate']:6.2f} ± {row['travel_time_ci_width']:5.2f}"
    fulfill_str = f"{row['fulfillment_time_estimate']:6.2f} ± {row['fulfillment_time_ci_width']:5.2f}"
    avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:5.2f}"
    growth_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:6.4f}"
    
    if row['pairing_rate_estimate'] is not None:
        pairing_pct = row['pairing_rate_estimate'] * 100
        pairing_ci_pct = row['pairing_rate_ci_width'] * 100 if row['pairing_rate_ci_width'] else 0
        pairing_str = f"{pairing_pct:6.2f} ± {pairing_ci_pct:5.2f}%"
    else:
        pairing_str = "N/A"
    
    # Format weight strategy name
    weight_display = row['weight_strategy'].replace('_', ' ').title()
    
    print(f"  {row['area_size']:>4}   {row['ratio']:>4.1f}   {weight_display:<25} │ {mom_str:>18s} {som_str:>10s} {mos_str:>10s} │ {first_contact_str:>18s} │ {pickup_str:>18s} │ {delivery_str:>18s} │ {travel_str:>18s} │ {fulfill_str:>18s} │ {avg_queue_str:>18s} │ {growth_str:>22s} │ {pairing_str:>18s}")

print("="*280)

print("\n✓ Metric extraction complete")
print("✓ Results table includes all comprehensive metrics")
# %%