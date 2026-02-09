# delivery_area_size_study.py
"""
Delivery Area Size Study: Effect of Delivery Area Size on System Performance

Research Question: How does delivery area size affect food delivery system performance?

Building on Previous Studies:
- Study 1 established three operational regimes based on arrival interval ratio (stable, 
  critical, failure) and identified the intensity effect (baseline outperforms 2× baseline)
- Study 2 demonstrated that pairing shifts regime boundaries dramatically (from ~5.5-6.0 
  to beyond 8.0) and exhibits self-regulating properties
- Study 3 tested layout robustness across different random seeds, finding that pairing 
  makes the system robust to spatial variation
- Study 4 found that restaurant count has minimal impact on system performance (0-15% 
  customer benefit), with effects visible primarily when pairing is disabled

This Study (Study 5):
- Tests whether delivery area size affects system performance
- Unlike restaurant count (which primarily affects driver→restaurant leg), area size 
  affects the entire logistics journey - every distance component scales with area
- Investigates interaction between area size and pairing mechanism
- Examines whether area effects are substantially larger than count effects due to 
  system-wide impact

Design Pattern:
- 3 delivery area sizes (5×5, 10×10, 15×15 km) with fixed restaurant count (10)
- Single structural seed (42) for focused analysis
- 2 arrival interval ratios (5.0, 7.0) sampling critical and high-stress regimes
- 2 pairing conditions (OFF, ON) to test area × pairing interaction

Total Design Points: 3 areas × 2 ratios × 2 pairing conditions = 12
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
print("DELIVERY AREA SIZE STUDY")
print("="*80)
print("Research Question: How does delivery area size affect system performance?")
print("Building on Studies 1-4: Testing infrastructure factor while controlling for count")

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

research_question = """
PRIMARY RESEARCH QUESTION:
How does delivery area size affect food delivery system performance?
"""

context = """
CONTEXT & MOTIVATION:

Study 4 revealed that restaurant count has minimal impact on system performance. 
Tripling restaurant count (5→15) in fixed area produced only 0-15% customer 
benefit, with effects visible primarily when pairing is disabled. The nearest-
restaurant effect (7-13% first contact time reduction) is real but affects only 
one leg of the logistics journey.

This study tests a complementary infrastructure factor: delivery area size. Unlike 
restaurant count, which primarily affects the initial driver→restaurant leg, area 
size affects the entire logistics journey - every distance component scales with 
area. This system-wide impact suggests area effects may be substantially larger 
than count effects.

Studies 1-4 established that infrastructure factors (layout, count) are third-order 
compared to operational factors (ratio, pairing). However, all prior studies used 
fixed 10×10 km area. Does this conclusion hold when area varies? Or does area 
emerge as a more significant infrastructure factor?

Platform operators face practical questions: How large can service areas grow 
before performance degrades unacceptably? Does pairing remain effective at larger 
scales? Understanding area effects is essential for expansion planning.
"""

sub_questions = """
SUB-QUESTIONS:

1. How does area size affect performance across different metrics?
   - Travel time components (first contact, pickup, delivery)
   - Assignment time (queueing + matching)
   - Fulfillment time (customer experience)
   - Do all components degrade proportionally, or do some amplify more?

2. Does the area effect interact with system load?
   - Is area more impactful at ratio 5.0 (critical) vs 7.0 (high stress)?
   - Does larger area push system into failure at ratios that were stable in 10×10?
   - Or does area effect remain constant across load levels?

3. Does the area effect interact with pairing?
   - Does pairing remain effective in larger areas?
   - Does pairing rate decline as orders become more spatially dispersed?
   - Can pairing compensate for area-induced performance degradation?
   - Or does area overwhelm pairing's capacity-doubling benefit?

4. How does area size affect spatial efficiency?
   - Does typical distance scale with √(area) as geometry suggests?
   - Does larger area interact with restaurant layout in unexpected ways?
   - Are there path dependency effects (drivers farther from next assignment)?

5. Does the feedback loop amplify area effects?
   - Study 4 showed 13% first contact improvement → 28% assignment improvement (2.5× amplification)
   - Does area degradation amplify similarly through driver availability feedback?
   - Or do larger areas break the feedback loop entirely?

6. What is the magnitude of area effects compared to other factors?
   - Study 4: Count effects were 0-15% (third-order factor)
   - Study 2: Pairing effects were ~60% (first-order factor)
   - Where do area effects fall in this hierarchy?
"""

scope = """
SCOPE & BOUNDARIES:

Tested:
- Area sizes: 5×5, 10×10, 15×15 km (9× range from compact to sprawling)
- Fixed restaurant count: 10 (controls for count effect, isolates area effect)
- Single seed: 42 (controls for layout variation, tests main effect)
- Ratios: 5.0 (critical), 7.0 (high stress) - where effects likely detectable
- Pairing: OFF and ON (tests interaction)
- Fixed pairing thresholds: δ_r = 4.0 km, δ_c = 3.0 km (tests how fixed policies scale)

Note on density:
- Varying area with fixed count implicitly varies density
- 5×5, n=10: 0.40 restaurants/km² (very dense)
- 10×10, n=10: 0.10 restaurants/km² (baseline)
- 15×15, n=10: 0.044 restaurants/km² (sparse)
- After Study 5, can analyze whether density or area is fundamental

Not tested:
- Different restaurant counts (Study 4 addressed this)
- Different area-count combinations (factorial design left for future)
- Scaled pairing thresholds (tests fixed policy across scales)
- Multiple seeds (robustness check if area effects are significant)
- Full ratio range (stable regime unlikely to show large effects)
"""

analysis_focus = """
KEY METRICS & ANALYSIS FOCUS:

1. Travel time decomposition (critical for understanding area effects)
   - First contact time: driver → first restaurant
   - Pickup travel: complete restaurant pickup phase
   - Delivery travel: restaurant → customer phase
   - Total travel time: sum of all components
   → Hypothesis: All components should scale with area, but by how much?

2. Assignment time (tests feedback loop amplification)
   - Does area affect assignment through driver cycle feedback?
   - Or is assignment time independent of area when ratio is controlled?
   → Study 4 showed 2.5× amplification - does area show similar dynamics?

3. Fulfillment time (customer experience)
   - Net effect of travel + assignment changes
   - How much does area degrade customer experience?
   - Compare magnitude to Study 4's count effects (0-15%)

4. Growth rate (system stability)
   - Does larger area push system into unbounded growth?
   - What ratios are sustainable in each area size?
   - Can pairing rescue stability in large areas?

5. Pairing effectiveness metrics
   - Pairing rate: Does dispersion reduce pairing opportunities?
   - Inter-restaurant distances in pairs
   - Does fixed 4km threshold become increasingly restrictive?

6. Infrastructure characteristics
   - Typical distance: Does it scale with √(area)?
   - Deviations indicate path dependency or layout interactions

Analysis Approach:
- Primary: Main effect of area (compare 5×5 vs 10×10 vs 15×15)
- Secondary: Area × ratio interaction (does effect vary by load?)
- Tertiary: Area × pairing interaction (does pairing compensate?)
- Mechanism: Component-level metrics showing where area effects manifest
- Context: Compare magnitude to Studies 1, 2, 4 (factor hierarchy)
- Explanation: Develop mechanistic explanations based on observed patterns
"""

evolution_notes = """
STUDY SEQUENCE POSITIONING:

Study 1: Arrival Interval Ratio Study (COMPLETE)
- Established regime structure and ratio as primary determinant
- Limitation: Single infrastructure configuration (10×10, n=10, seed=42)

Study 2: Pairing Effect Study (COMPLETE)
- Demonstrated pairing shifts regime boundary dramatically (~60% improvement)
- Limitation: Single infrastructure configuration

Study 3: Infrastructure Layout Study (COMPLETE)
- Tested layout robustness across random seeds
- Found pairing makes system robust to spatial variation
- Limitation: Fixed area (10×10) and count (10)

Study 4: Restaurant Count Study (COMPLETE)
- Tested count effect: minimal impact (0-15%)
- Identified nearest-restaurant effect (universal) vs layout efficiency (stochastic)
- Revealed seed × count interaction determining layout quality
- Established count as third-order factor
- Limitation: Fixed area (10×10), single seed (42)

Study 5: Delivery Area Size Study (THIS STUDY)
- Tests infrastructure factor: delivery area size
- Uses single seed (42) and fixed count (10) for focused main effect analysis
- Investigates area × pairing interaction
- Compares magnitude to count effects
- Key question: Is area a third-order factor like count, or does it emerge 
  as more significant due to system-wide impact?

Future Studies:
- Study 6: Operational policy refinement (pairing thresholds sensitivity)
- Study 7: Priority scoring weights strategy
- Potential: Area × count interaction study (is density the fundamental parameter?)
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
INFRASTRUCTURE STUDY: Vary delivery area size while holding restaurant count constant.

Test 3 levels of delivery area size while holding restaurant count at 10.
This isolates the effect of delivery area size from restaurant count effects.
"""

infrastructure_configs = [
    {
        'name': 'area_5',
        'config': StructuralConfig(
            delivery_area_size=5,
            num_restaurants=10,
            driver_speed=0.5
        ),
        'area_size': 5
    },
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
If area effects are significant, robustness across seeds can be tested in follow-up.
"""

structural_seeds = [42]

print(f"✓ Structural seeds: {structural_seeds}")
print(f"✓ Single seed approach: Focus on main effect of delivery area size")


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
DELIVERY AREA SIZE STUDY: Test each area at stressed ratios with/without pairing.

Design:
- 2 arrival interval ratios: 5.0 (critical), 7.0 (high stress)
- 2 pairing conditions: OFF (control) and ON (intervention)
- Baseline intensity only: order_interval = 1.0 min

This creates 4 operational configurations per delivery area size.
"""

# Target ratios focused on stressed regimes
target_arrival_interval_ratios = [5.0, 7.0]

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

Total: 3 areas × 4 operational configs = 12 design points
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
print(f"✓ Breakdown: {len(infrastructure_instances)} areas × "
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

# Initialize visualization
viz = WelchMethodVisualization(figsize=(16, 10))

# Group design points by delivery area size for organized display
area_groups = {}
for design_name in all_time_series_data.keys():
    # Extract area from design name (e.g., "area_5_seed42_ratio_5.0_no_pairing")
    parts = design_name.split('_')
    area_str = parts[1]  # "5", "10", or "15"
    area = int(area_str)
    
    if area not in area_groups:
        area_groups[area] = []
    area_groups[area].append(design_name)

print(f"✓ Grouped {len(all_time_series_data)} design points by {len(area_groups)} delivery area sizes")

# Create plots systematically by delivery area size
plot_count = 0
for area in sorted(area_groups.keys()):
    print(f"\nDelivery Area Size {area}×{area} km:")
    
    for design_name in sorted(area_groups[area]):
        plot_title = f"Warmup Analysis: {design_name}"
        time_series_data = all_time_series_data[design_name]
        fig = viz.create_warmup_analysis_plot(time_series_data, title=plot_title)
        
        plt.show()
        print(f"    ✓ {design_name} plot displayed")
        plot_count += 1

print(f"\n✓ Warmup analysis visualization complete")
print(f"✓ Created {plot_count} warmup analysis plots")
print(f"✓ Organized by {len(area_groups)} delivery area sizes")


# %% CELL 14: Warmup Period Detection
print("\n" + "="*80)
print("WARMUP PERIOD DETECTION")
print("="*80)

uniform_warmup_period = 500

print(f"✓ Using uniform warmup period: {uniform_warmup_period} minutes")
print(f"  (Based on previous studies using same infrastructure configuration)")
print(f"  • Simulation duration: {experiment_config.simulation_duration} minutes")
print(f"  • Analysis will use: {experiment_config.simulation_duration - uniform_warmup_period} minutes of post-warmup data")


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
print("KEY PERFORMANCE METRICS: DELIVERY AREA SIZE STUDY")
print("="*80)

import re

def extract_area_ratio_and_pairing(design_name):
    """Extract area size, ratio, and pairing status from design point name."""
    # Pattern: area_5_seed42_ratio_5.0_no_pairing or area_5_seed42_ratio_5.0_pairing
    match = re.match(r'area_(\d+)_seed\d+_ratio_([\d.]+)_(no_pairing|pairing)', design_name)
    if match:
        area_size = int(match.group(1))
        ratio = float(match.group(2))
        pairing_status = match.group(3)
        return area_size, ratio, pairing_status
    else:
        raise ValueError(f"Could not parse design name: {design_name}")

# Extract metrics for tabular display
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    area_size, ratio, pairing_status = extract_area_ratio_and_pairing(design_name)
    
    stats_with_cis = analysis_result.get('statistics_with_cis', {})
    
    # Assignment Time Statistics
    order_metrics = stats_with_cis.get('order_metrics', {})
    assignment_time = order_metrics.get('assignment_time', {})
    
    mean_of_means = assignment_time.get('mean_of_means', {})
    mom_estimate = mean_of_means.get('point_estimate', 0)
    mom_ci = mean_of_means.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0
    
    # First Contact Time Statistics
    delivery_unit_metrics = stats_with_cis.get('delivery_unit_metrics', {})
    first_contact_time = delivery_unit_metrics.get('first_contact_time', {})
    first_contact_time_mom = first_contact_time.get('mean_of_means', {})
    first_contact_time_estimate = first_contact_time_mom.get('point_estimate', 0)
    first_contact_time_ci = first_contact_time_mom.get('confidence_interval', [0, 0])
    first_contact_time_ci_width = (first_contact_time_ci[1] - first_contact_time_ci[0]) / 2 if first_contact_time_ci[0] is not None else 0
    
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
    pairing_rate_data = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate_data.get('point_estimate', None)
    pairing_rate_ci = pairing_rate_data.get('confidence_interval', [None, None])
    if pairing_rate_ci[0] is not None and pairing_rate_ci[1] is not None:
        pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2
    else:
        pairing_rate_ci_width = None
    
    metrics_data.append({
        'area_size': area_size,
        'ratio': ratio,
        'pairing_status': pairing_status,
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'first_contact_time_estimate': first_contact_time_estimate,
        'first_contact_time_ci_width': first_contact_time_ci_width,
        'pickup_travel_time_estimate': pickup_travel_time_estimate,
        'pickup_travel_time_ci_width': pickup_travel_time_ci_width,
        'delivery_travel_time_estimate': delivery_travel_time_estimate,
        'delivery_travel_time_ci_width': delivery_travel_time_ci_width,
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width
    })

# Sort by area_size, then ratio, then pairing
metrics_data.sort(key=lambda x: (x['area_size'], x['ratio'], x['pairing_status']))

# Display table grouped by area size
print("\n🎯 PRIMARY VIEW: GROUPED BY DELIVERY AREA SIZE")
print("="*230)
print(f"  {'Area':<6} {'Ratio':<6} {'Pairing':<12} │ {'Assignment':>18} │ {'First Contact':>18} │ {'Pickup':>18} │ {'Delivery':>18} │ {'Avg Queue':>18} │ {'Growth Rate':>22} │ {'Pairing Rate':>18}")
print(f"  {'(km²)':<6} {'':6} {'Status':12} │ {'Time':>18} │ {'Time':>18} │ {'Travel':>18} │ {'Travel':>18} │ {'Size':>18} │ {'(entities/min)':>22} │ {'(% paired)':>18}")
print("="*230)

current_area = None
for row in metrics_data:
    # Add separator between different area sizes
    if current_area is not None and row['area_size'] != current_area:
        print("-" * 230)
    current_area = row['area_size']
    
    # Format metrics
    pairing_display = "ON" if row['pairing_status'] == 'pairing' else "OFF"
    mom_str = f"{row['mom_estimate']:6.2f} ± {row['mom_ci_width']:5.2f}"
    first_contact_str = f"{row['first_contact_time_estimate']:6.2f} ± {row['first_contact_time_ci_width']:5.2f}"
    pickup_str = f"{row['pickup_travel_time_estimate']:6.2f} ± {row['pickup_travel_time_ci_width']:5.2f}"
    delivery_str = f"{row['delivery_travel_time_estimate']:6.2f} ± {row['delivery_travel_time_ci_width']:5.2f}"
    avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:5.2f}"
    growth_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:6.4f}"
    
    if row['pairing_rate_estimate'] is not None:
        pairing_pct = row['pairing_rate_estimate'] * 100
        pairing_ci_pct = row['pairing_rate_ci_width'] * 100 if row['pairing_rate_ci_width'] else 0
        pairing_str = f"{pairing_pct:6.2f} ± {pairing_ci_pct:5.2f}%"
    else:
        pairing_str = "N/A"
    
    print(f"  {row['area_size']:>4}   {row['ratio']:>4.1f}   {pairing_display:<12} │ {mom_str:>18} │ {first_contact_str:>18} │ {pickup_str:>18} │ {delivery_str:>18} │ {avg_queue_str:>18} │ {growth_str:>22} │ {pairing_str:>18}")

print("="*230)

# =========================================================================
# ALTERNATIVE VIEW: COMPARING ASSIGNMENT TIMES ACROSS AREA SIZES
# =========================================================================
print("\n📊 ALTERNATIVE VIEW: ASSIGNMENT TIME BY AREA SIZE")
print("Quickly see how delivery area size affects assignment time for each condition")
print("="*130)
print(f"  {'Ratio':<6} {'Pairing':<12} │ {'Area = 5×5 km':>24} {'Area = 10×10 km':>24} {'Area = 15×15 km':>24} │ {'Area Effect':>20}")
print(f"  {'':6} {'Status':12} │ {'Assignment Time (min)':>24} {'Assignment Time (min)':>24} {'Assignment Time (min)':>24} │ {'(Max - Min)':>20}")
print("="*130)

# Group by ratio and pairing for comparison
for ratio in sorted(set(r['ratio'] for r in metrics_data)):
    for pairing_status in ['no_pairing', 'pairing']:
        pairing_display = "ON" if pairing_status == 'pairing' else "OFF"
        
        # Collect assignment times for each area size
        times = {}
        for area in [5, 10, 15]:
            row = next((r for r in metrics_data if r['area_size'] == area and r['ratio'] == ratio and r['pairing_status'] == pairing_status), None)
            if row:
                times[area] = row['mom_estimate']
        
        if times:
            t5 = f"{times.get(5, 0):5.2f}" if 5 in times else "N/A"
            t10 = f"{times.get(10, 0):5.2f}" if 10 in times else "N/A"
            t15 = f"{times.get(15, 0):5.2f}" if 15 in times else "N/A"
            max_diff = max(times.values()) - min(times.values()) if len(times) > 1 else 0
            diff_str = f"{max_diff:5.2f} min"
            
            print(f"  {ratio:<6.1f} {pairing_display:<12} │ {t5:>24} {t10:>24} {t15:>24} │ {diff_str:>20}")

print("="*130)

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("ASSIGNMENT TIME:")
print("  • Average customer wait time from order placement to driver assignment")
print()
print("FIRST CONTACT TIME:")
print("  • Time until driver first contacts the restaurant")
print()
print("TRAVEL TIMES:")
print("  • Pickup Travel: Time from driver location to restaurant")
print("  • Delivery Travel: Time from restaurant to customer")
print()
print("QUEUE DYNAMICS:")
print("  • Avg Queue Size: Average number of unassigned delivery entities")
print("  • Growth Rate: System trajectory (≈0 = bounded, >0 = deteriorating)")
print()
print("PAIRING METRIC:")
print("  • Pairing Rate: % of arrived orders that were paired (with 95% CI)")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  1. Does delivery area size affect assignment time? By how much?")
print("  2. Does area size affect travel times as expected? (larger area → longer trips)")
print("  3. Is the area effect monotonic or does it plateau?")
print("  4. Does area effect interact with pairing? (larger without pairing?)")
print("  5. Does area effect interact with ratio? (larger at ratio 7.0?)")
print("  6. How does avg queue size scale with area size?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for delivery area size effect analysis")

# %%