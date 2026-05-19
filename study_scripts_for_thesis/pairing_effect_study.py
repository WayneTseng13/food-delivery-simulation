# pairing_effect_study.py
"""
Pairing Effect Study: Impact of Order Pairing on System Performance

Research Question: How does enabling order pairing affect system performance 
and regime characteristics across different operational regimes?

Building on Study 1 (Arrival Interval Ratio Study):
- Study 1 established three operational regimes based on arrival interval ratio:
  - Stable regime (ratio ≤ 4.0): Near-zero assignment time, bounded queues
  - Critical regime (ratio 4.5-5.5): Moderate assignment time, system at capacity
  - Failure regime (ratio ≥ 6.0): Unbounded queue growth, system breakdown
- Study 1 limitation: Order pairing was disabled throughout

This Study (Study 2):
- Tests whether enabling order pairing shifts regime boundaries
- Measures pairing benefit across different system load levels
- Quantifies pairing rate as function of operational regime

Design Pattern:
- 7 arrival interval ratios spanning all regimes: 3.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0
- For each ratio: Compare pairing=OFF vs pairing=ON
- Baseline intensity only (order_interval=1.0, driver_interval=ratio)
- Pairing thresholds: δ_r = 4.0 km (restaurant), δ_c = 3.0 km (customer)

Total Design Points: 7 ratios × 2 pairing conditions = 14
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
print("PAIRING EFFECT STUDY: IMPACT OF ORDER PAIRING ON SYSTEM PERFORMANCE")
print("="*80)
print("Research Question: How does enabling order pairing affect system performance?")
print("Building on Study 1: Testing pairing effect across established regime structure")

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
How does enabling order pairing affect system performance and regime 
characteristics across different operational regimes?

This study extends Study 1 (Arrival Interval Ratio Study) by introducing
order pairing as an experimental factor. Study 1 established the regime
structure with pairing disabled - this study tests whether pairing can
shift regime boundaries or improve performance within each regime.
"""

# ==============================================================================
# CONTEXT & MOTIVATION
# ==============================================================================
context = """
Study 1 established clear regime structure based on arrival interval ratio:
- Stable regime (ratio ≤ 4.0): Bounded queues, low assignment time
- Critical regime (ratio 4.5-5.5): System operating near capacity
- Failure regime (ratio ≥ 6.0): Unbounded growth, system breakdown

Study 1 Limitation Addressed:
"No order pairing" was explicitly listed as a limitation in Study 1.
This study directly addresses that limitation by systematically testing
the pairing mechanism across the established regime structure.

Order Pairing Mechanism:
When enabled, the system can assign two orders to a single driver if:
- Both restaurants are within δ_r = 4.0 km of each other
- Both customers are within δ_c = 3.0 km of each other
This effectively increases driver capacity when spatial clustering permits.
"""

# ==============================================================================
# SUB-QUESTIONS & HYPOTHESES
# ==============================================================================
sub_questions = """
Sub-questions to investigate:

1. Does pairing shift regime boundaries?
   - Hypothesis: Pairing may allow system to remain stable at higher ratios
   - Test: Compare regime classification at boundary ratios (5.5, 6.0, 6.5)

2. At which ratios does pairing provide most benefit?
   - Hypothesis: Greatest benefit in critical regime where system is constrained
   - Test: Compare assignment time reduction across ratios

3. How does pairing rate vary with system load?
   - Hypothesis: Pairing rate may be limited by spatial opportunity, not demand
   - Test: Measure pairing rate as function of ratio

4. Is pairing benefit consistent or regime-dependent?
   - Hypothesis: Pairing effect may interact with operational regime
   - Test: Examine pairing × regime interaction patterns
"""

# ==============================================================================
# SCOPE & BOUNDARIES
# ==============================================================================
scope = """
Fixed factors (consistent with Study 1):
- Infrastructure: Single configuration (10km × 10km, 10 restaurants, seed=42)
- Service duration: Fixed distribution (mean=100, std=60, min=30, max=200)
- Driver speed: 0.5 km/min

Varied factors:
- Arrival interval ratio: 3.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0 (7 levels)
- Pairing condition: OFF vs ON
  - OFF: pairing_enabled=False
  - ON: pairing_enabled=True, δ_r=4.0km, δ_c=3.0km

Design rationale:
- Ratio selection spans all three regimes with fine granularity at boundaries
- Includes no-pairing conditions for clean within-study comparison
- Baseline intensity only (2× baseline validation already done in Study 1)

Systematic design: 7 ratios × 2 pairing conditions = 14 design points
"""

# ==============================================================================
# KEY METRICS & ANALYSIS FOCUS
# ==============================================================================
analysis_focus = """
Primary metrics for pairing effect analysis:

1. Assignment time (order_metrics)
   - Mean of means: Customer-facing performance
   - Compare pairing=ON vs OFF at each ratio
   - Quantify absolute and relative benefit

2. Growth rate (queue_dynamics_metrics)
   - Regime indicator: bounded vs unbounded
   - Test if pairing shifts regime boundary
   - Key ratios: 5.5, 6.0, 6.5 (boundary region)

3. Pairing rate (system_metrics - for pairing=ON only)
   - Fraction of deliveries involving paired orders
   - How pairing opportunity varies with load

Analysis approach:
- Side-by-side comparison at each ratio
- Focus on regime boundary behavior (5.5-6.5)
- Quantify pairing benefit: Δ assignment time, Δ growth rate
"""

# ==============================================================================
# EVOLUTION NOTES
# ==============================================================================
evolution_notes = """
Study sequence positioning:

Study 1: Arrival Interval Ratio Study (COMPLETE)
- Established regime structure: Stable / Critical / Failure
- Identified regime boundary around ratio 5.5-6.0
- Found intensity effect: baseline outperforms 2× baseline
- Limitation: Pairing disabled

Study 2: Pairing Effect Study (THIS STUDY)
- Tests pairing mechanism across established regime structure
- Addresses Study 1 limitation directly
- Provides foundation for Study 3

Study 3: Layout Robustness Study (PLANNED)
- Tests generalizability across random infrastructure layouts
- Will use findings from Studies 1 and 2
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
PAIRING EFFECT STUDY: Multiple configurations varying pairing condition.

For each arrival interval ratio, create two configurations:
- Pairing OFF: pairing_enabled=False
- Pairing ON: pairing_enabled=True with proximity thresholds

This tests how order pairing affects system performance across regimes.
"""

# Target arrival interval ratios to test (spans all three regimes)
# - 3.5: Stable regime
# - 5.0, 5.5: Critical regime / approaching boundary
# - 6.0, 6.5: Boundary region
# - 7.0, 8.0: Failure regime
target_arrival_interval_ratios = [3.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0]

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
    # No pairing configuration
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_no_pairing',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **no_pairing_params,
            **FIXED_SERVICE_CONFIG
        )
    })
    
    # Pairing configuration
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
print(f"✓ Testing {len(target_arrival_interval_ratios)} arrival interval ratios")
print(f"✓ Each ratio has 2 pairing conditions (OFF + ON)")

# Display configurations
print("\nConfigurations by pairing condition:")
print("-"*70)
print("NO PAIRING:")
for config in operational_configs:
    if 'no_pairing' in config['name']:
        op_config = config['config']
        ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
        print(f"  • {config['name']}: ratio={ratio:.1f}, pairing=OFF")

print("\nPAIRING ENABLED:")
for config in operational_configs:
    if '_pairing' in config['name'] and 'no_pairing' not in config['name']:
        op_config = config['config']
        ratio = op_config.mean_driver_inter_arrival_time / op_config.mean_order_inter_arrival_time
        print(f"  • {config['name']}: ratio={ratio:.1f}, pairing=ON (δ_r=4.0km, δ_c=3.0km)")

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
    # Extract ratio from design name (e.g., "ratio_3.5_no_pairing")
    ratio_str = design_name.split('_')[1]  # "3.5"
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
print("KEY PERFORMANCE METRICS: PAIRING EFFECT COMPARISON")
print("="*80)

import re

def extract_ratio_and_pairing(design_name):
    """Extract arrival interval ratio and pairing condition from design point name."""
    # Pattern: ratio_3.5_no_pairing or ratio_3.5_pairing
    match = re.match(r'ratio_([\d.]+)_(no_pairing|pairing)', design_name)
    if match:
        ratio = float(match.group(1))
        pairing_condition = match.group(2)
        return ratio, pairing_condition
    return None, None

# Extract comprehensive metrics for table
metrics_data = []

for design_name, analysis_result in design_analysis_results.items():
    ratio, pairing_condition = extract_ratio_and_pairing(design_name)
    if ratio is None:
        continue
    
    stats_with_cis = analysis_result.get('statistics_with_cis', {})
    
    # =====================================================================
    # ASSIGNMENT TIME STATISTICS (nested under order_metrics)
    # =====================================================================
    order_metrics = stats_with_cis.get('order_metrics', {})
    assignment_time = order_metrics.get('assignment_time', {})
    
    # Mean of means with CI
    mean_of_means = assignment_time.get('mean_of_means', {})
    mom_estimate = mean_of_means.get('point_estimate', 0)
    mom_ci = mean_of_means.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0
    
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
    # SYSTEM METRICS
    # =====================================================================
    system_metrics = stats_with_cis.get('system_metrics', {})
    
    # Pairing Rate (only for pairing=ON)
    pairing_rate_data = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate_data.get('point_estimate', None)
    pairing_rate_ci = pairing_rate_data.get('confidence_interval', [None, None])
    if pairing_rate_ci[0] is not None and pairing_rate_ci[1] is not None:
        pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2
    else:
        pairing_rate_ci_width = None
    
    # Immediate Assignment Rate
    immediate_assignment_rate_data = system_metrics.get('immediate_assignment_rate', {})
    immediate_assignment_rate_estimate = immediate_assignment_rate_data.get('point_estimate', None)
    immediate_assignment_rate_ci = immediate_assignment_rate_data.get('confidence_interval', [None, None])
    if immediate_assignment_rate_ci[0] is not None and immediate_assignment_rate_ci[1] is not None:
        immediate_assignment_rate_ci_width = (immediate_assignment_rate_ci[1] - immediate_assignment_rate_ci[0]) / 2
    else:
        immediate_assignment_rate_ci_width = None
    
    # =====================================================================
    # BUILD ROW
    # =====================================================================
    metrics_data.append({
        'ratio': ratio,
        'pairing_condition': pairing_condition,
        # Assignment time
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        # Queue dynamics
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        # System state
        'driver_utilization_estimate': driver_utilization_estimate,
        'driver_utilization_ci_width': driver_utilization_ci_width,
        # System metrics
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width,
        'immediate_assignment_rate_estimate': immediate_assignment_rate_estimate,
        'immediate_assignment_rate_ci_width': immediate_assignment_rate_ci_width,
    })

# Sort by ratio then pairing condition (no_pairing first, then pairing)
metrics_data.sort(key=lambda x: (x['ratio'], 0 if x['pairing_condition'] == 'no_pairing' else 1))

# =========================================================================
# PRINT FORMATTED TABLE: GROUPED BY PAIRING CONDITION
# =========================================================================
print("\n🎯 KEY PERFORMANCE METRICS: GROUPED BY PAIRING CONDITION")
print("="*195)
print(" Ratio  Pairing    Assignment Time    Avg Queue Size    Growth Rate       Driver Utilization   Immediate Assign.    Pairing Rate")
print("        Status       (mean ± CI)        (mean ± CI)    (entities/min)        (mean ± CI)          (mean ± CI)        (mean ± CI)")
print("="*195)

print("NO PAIRING:")
print("-"*195)
for row in metrics_data:
    if row['pairing_condition'] == 'no_pairing':
        ratio = row['ratio']
        assignment_str = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
        avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
        growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"
        driver_util_str = f"{row['driver_utilization_estimate']:6.4f} ± {row['driver_utilization_ci_width']:6.4f}"
        
        # Immediate assignment rate
        if row['immediate_assignment_rate_estimate'] is not None and row['immediate_assignment_rate_ci_width'] is not None:
            imm_assign_str = f"{row['immediate_assignment_rate_estimate']*100:5.2f} ± {row['immediate_assignment_rate_ci_width']*100:5.2f}%"
        elif row['immediate_assignment_rate_estimate'] is not None:
            imm_assign_str = f"{row['immediate_assignment_rate_estimate']*100:5.2f}%"
        else:
            imm_assign_str = "N/A"
        
        print(f"  {ratio:4.1f}   OFF      {assignment_str:>16s}   {avg_queue_str:>17s}   {growth_rate_str:>17s}   {driver_util_str:>18s}   {imm_assign_str:>18s}        N/A")

print("\nPAIRING ENABLED:")
print("-"*195)
for row in metrics_data:
    if row['pairing_condition'] == 'pairing':
        ratio = row['ratio']
        assignment_str = f"{row['mom_estimate']:5.2f} ± {row['mom_ci_width']:5.2f}"
        avg_queue_str = f"{row['avg_queue_estimate']:6.2f} ± {row['avg_queue_ci_width']:6.2f}"
        growth_rate_str = f"{row['growth_rate_estimate']:7.4f} ± {row['growth_rate_ci_width']:7.4f}"
        driver_util_str = f"{row['driver_utilization_estimate']:6.4f} ± {row['driver_utilization_ci_width']:6.4f}"
        
        # Immediate assignment rate
        if row['immediate_assignment_rate_estimate'] is not None and row['immediate_assignment_rate_ci_width'] is not None:
            imm_assign_str = f"{row['immediate_assignment_rate_estimate']*100:5.2f} ± {row['immediate_assignment_rate_ci_width']*100:5.2f}%"
        elif row['immediate_assignment_rate_estimate'] is not None:
            imm_assign_str = f"{row['immediate_assignment_rate_estimate']*100:5.2f}%"
        else:
            imm_assign_str = "N/A"
        
        # Pairing rate
        if row['pairing_rate_estimate'] is not None and row['pairing_rate_ci_width'] is not None:
            pr_str = f"{row['pairing_rate_estimate']*100:5.2f} ± {row['pairing_rate_ci_width']*100:5.2f}%"
        elif row['pairing_rate_estimate'] is not None:
            pr_str = f"{row['pairing_rate_estimate']*100:5.2f}%"
        else:
            pr_str = "N/A"
        
        print(f"  {ratio:4.1f}   ON       {assignment_str:>16s}   {avg_queue_str:>17s}   {growth_rate_str:>17s}   {driver_util_str:>18s}   {imm_assign_str:>18s}   {pr_str:>16s}")

print("="*195)

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("ASSIGNMENT TIME:")
print("  • Mean of Means: Average customer wait time (with 95% CI)")
print()
print("QUEUE DYNAMICS METRICS:")
print("  • Avg Queue Size: Time-weighted mean unassigned entities")
print("  • Growth Rate: System trajectory (≈0 = bounded, >0 = deteriorating)")
print()
print("SYSTEM EFFICIENCY METRICS:")
print("  • Driver Utilization: Fraction of active drivers in DELIVERING state")
print("  • Immediate Assign. Rate: % of orders assigned instantly (assignment_time = 0)")
print("  • Pairing Rate: % of deliveries with paired orders (with 95% CI)")
print()
print("REGIME REFERENCE (from Study 1):")
print("  • Stable (ratio ≤4.0):        Low assignment time, growth ≈0")
print("  • Critical (ratio 4.5-5.5):   Moderate assignment time, growth ≈0")
print("  • Deteriorating (ratio ≥6.0): High assignment time, growth >0")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  • Does pairing shift the regime boundary (compare growth rates at 5.5-6.5)?")
print("  • Where is pairing benefit greatest (compare assignment times across ratios)?")
print("  • How do queue size and utilization respond to pairing?")
print("  • Does pairing improve immediate assignment rates?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for pairing effect analysis")

# %% CELL 17: Ad-hoc Analysis (Placeholder)
"""
PLACEHOLDER FOR AD-HOC ANALYSIS

This cell is reserved for exploratory analysis based on the results.
Potential analyses:
- Visualization of pairing effect across ratios
- Statistical tests for pairing benefit significance
- Regime boundary shift analysis
- Pairing rate patterns

To be developed based on Cell 16 findings.
"""

print("\n" + "="*80)
print("AD-HOC ANALYSIS PLACEHOLDER")
print("="*80)
print("Reserved for exploratory analysis based on results.")
print("Potential analyses:")
print("  • Pairing effect visualization")
print("  • Statistical significance testing")
print("  • Regime boundary shift analysis")
print("="*80)

# %% AD HOC VISUALIZATION CELL
"""
VISUALIZATION OBJECTIVE:
    Produce the two figures for Slide 6 (Study 2 — Order Pairing Effects).

    Figure 4.3 — Regime Boundary Shift
        Growth rate vs arrival interval ratio, pairing OFF vs ON.
        The y=0 horizontal line is the regime boundary indicator.
        A vertical reference line marks the Study 1 boundary (~ratio 6.0)
        to show where the OFF curve crosses into unbounded territory —
        and the ON curve never does.

    Figure 4.4 — Customer-Facing Performance
        Mean assignment time vs arrival interval ratio, pairing OFF vs ON.
        No shading — the widening gap between curves is the story.

DATA SOURCE:
    metrics_data — built in Cell 16. Each row has:
        'ratio', 'pairing_condition' ('no_pairing' or 'pairing'),
        'growth_rate_estimate', 'growth_rate_ci_width',
        'mom_estimate', 'mom_ci_width'
"""

import matplotlib.pyplot as plt
import numpy as np

print("\n" + "="*80)
print("SLIDE 6 FIGURE PRODUCTION")
print("="*80)

# ============================================================================
# STEP 1: SEPARATE DATA BY PAIRING CONDITION
# ============================================================================
ratios_all = sorted(set(r['ratio'] for r in metrics_data))

no_pairing_data = {r: None for r in ratios_all}
pairing_data    = {r: None for r in ratios_all}

for row in metrics_data:
    if row['pairing_condition'] == 'no_pairing':
        no_pairing_data[row['ratio']] = row
    else:
        pairing_data[row['ratio']] = row

def extract_metrics(data_dict):
    ratios_list = sorted(k for k, v in data_dict.items() if v is not None)
    return {
        'ratios':          ratios_list,
        'growth_rate':     [data_dict[r]['growth_rate_estimate'] for r in ratios_list],
        'growth_rate_err': [data_dict[r]['growth_rate_ci_width']  for r in ratios_list],
        'assignment_time': [data_dict[r]['mom_estimate']           for r in ratios_list],
        'assignment_err':  [data_dict[r]['mom_ci_width']           for r in ratios_list],
    }

off_m = extract_metrics(no_pairing_data)
on_m  = extract_metrics(pairing_data)

print(f"Pairing OFF — {len(off_m['ratios'])} ratio points: {off_m['ratios']}")
print(f"Pairing ON  — {len(on_m['ratios'])}  ratio points: {on_m['ratios']}")

# ============================================================================
# STEP 2: SHARED STYLE CONSTANTS
# ============================================================================
COLOR_OFF = '#E63946'   # red  — pairing OFF
COLOR_ON  = '#2A9D8F'   # teal — pairing ON

X_MIN, X_MAX = 3.25, 8.25

# Study 1 regime boundary: the ratio where the OFF curve crosses y=0.
# From Study 1 results this sits between 5.5 and 6.0; use 6.0 as the
# reference line so the label reads "Study 1 boundary (pairing OFF)".
STUDY1_BOUNDARY = 6.0

# ============================================================================
# FIGURE 4.3 — GROWTH RATE VS RATIO (REGIME BOUNDARY SHIFT)
# ============================================================================
fig1, ax1 = plt.subplots(figsize=(10, 6))

ax1.errorbar(off_m['ratios'], off_m['growth_rate'],
             yerr=off_m['growth_rate_err'],
             marker='s', linewidth=2, markersize=8, capsize=5,
             label='Pairing OFF', color=COLOR_OFF, linestyle='--', zorder=3)

ax1.errorbar(on_m['ratios'], on_m['growth_rate'],
             yerr=on_m['growth_rate_err'],
             marker='o', linewidth=2, markersize=8, capsize=5,
             label='Pairing ON', color=COLOR_ON, linestyle='-', zorder=3)

# Regime boundary: y = 0
ax1.axhline(y=0, color='black', linestyle=':', linewidth=1.5, alpha=0.7,
            label='Regime boundary (growth = 0)')



ax1.set_xlabel('Arrival Interval Ratio (driver/order)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Growth Rate (entities/min)', fontsize=12, fontweight='bold')
ax1.set_title('Figure 4.3: Regime Boundary Shift', fontsize=14, fontweight='bold', pad=15)
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.set_xlim([X_MIN, X_MAX])

plt.tight_layout()
plt.show()
print("✓ Figure 4.3 rendered")

# ============================================================================
# FIGURE 4.4 — ASSIGNMENT TIME VS RATIO (CUSTOMER-FACING PERFORMANCE)
# ============================================================================
fig2, ax2 = plt.subplots(figsize=(10, 6))

ax2.errorbar(off_m['ratios'], off_m['assignment_time'],
             yerr=off_m['assignment_err'],
             marker='s', linewidth=2, markersize=8, capsize=5,
             label='Pairing OFF', color=COLOR_OFF, linestyle='--', zorder=3)

ax2.errorbar(on_m['ratios'], on_m['assignment_time'],
             yerr=on_m['assignment_err'],
             marker='o', linewidth=2, markersize=8, capsize=5,
             label='Pairing ON', color=COLOR_ON, linestyle='-', zorder=3)

ax2.set_xlabel('Arrival Interval Ratio (driver/order)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Mean Assignment Time (min)', fontsize=12, fontweight='bold')
ax2.set_title('Figure 4.4: Assignment Time: Customer-Facing Performance',
              fontsize=14, fontweight='bold', pad=15)
ax2.legend(loc='upper left', fontsize=11)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.set_xlim([X_MIN, X_MAX])
ax2.set_ylim(bottom=0)

plt.tight_layout()
plt.show()
print("✓ Figure 4.4 rendered")

# ============================================================================
# STEP 3: SANITY PRINT — absolute and relative improvement at each ratio
# ============================================================================
print("\n📊 PAIRING BENEFIT SUMMARY")
print("-"*60)
print(f"  {'Ratio':>6}  {'OFF (min)':>10}  {'ON (min)':>9}  {'Δ (min)':>9}  {'Δ (%)':>7}")
print("-"*60)

for r in off_m['ratios']:
    if pairing_data[r] is not None:
        off_val = no_pairing_data[r]['mom_estimate']
        on_val  = pairing_data[r]['mom_estimate']
        delta   = off_val - on_val
        pct     = (delta / off_val * 100) if off_val > 0 else 0
        print(f"  {r:>6.1f}  {off_val:>10.2f}  {on_val:>9.2f}  {delta:>9.2f}  {pct:>6.1f}%")

print("-"*60)
print("✓ Sanity check complete")
# %% SLIDE 7 — INFRASTRUCTURE FACTOR SYNTHESIS CHART
"""
PURPOSE:
    Figure 4.5 for Slide 7 (Studies 3–5 — Infrastructure Factor Effects).
    Horizontal bar chart comparing effect magnitudes of three infrastructure
    factors, with pairing OFF and ON shown as paired bars.

EFFECT MAGNITUDE DEFINITION:
    Range of assignment time (max − min) across factor levels at ratio 5.0.
    Ratio 5.0 chosen because:
      - It is the only ratio present in all three study datasets
      - It sits in the critical regime where effects become meaningful
      - It avoids unbounded-regime survivorship bias present at ratio 7.0

DATA SOURCE (hardcoded from provided result tables):

    Study 3 — Spatial Arrangement (ratio 5.0, assignment time mean)
        Pairing OFF:  Seed 42 = 9.20,  Seed 100 = 9.30,  Seed 200 = 16.69
        Pairing ON:   Seed 42 = 2.28,  Seed 100 = 2.46,  Seed 200 = 2.92

    Study 4 — Restaurant Count (ratio 5.0, assignment time mean)
        Pairing OFF:  Count 5  = 10.77, Count 10 = 9.20,  Count 15 = 7.72
        Pairing ON:   Count 5  = 2.11,  Count 10 = 2.28,  Count 15 = 2.14

    Study 5 — Delivery Area Size (ratio 5.0, assignment time mean)
        Pairing OFF:  5×5 km = 0.13,  10×10 km = 9.20,  15×15 km = 25.38
        Pairing ON:   5×5 km = 0.07,  10×10 km = 2.28,  15×15 km = 14.96

COLORS: match Slides 5 & 6 (pairing OFF = red, pairing ON = teal)
"""

import matplotlib.pyplot as plt
import numpy as np

# ============================================================================
# STEP 1: RAW DATA FROM RESULT TABLES
# ============================================================================
layout_off = [9.20, 9.30, 16.69]   # seeds 42, 100, 200
layout_on  = [2.28, 2.46,  2.92]

count_off  = [10.77, 9.20, 7.72]   # restaurant counts 5, 10, 15
count_on   = [ 2.11, 2.28, 2.14]

area_off   = [ 0.13, 9.20, 25.38]  # area sizes 5×5, 10×10, 15×15 km
area_on    = [ 0.07, 2.28, 14.96]

# ============================================================================
# STEP 2: COMPUTE EFFECT MAGNITUDES (max − min)
# ============================================================================
def effect_range(values):
    return max(values) - min(values)

off_effects = [
    effect_range(area_off),     # Study 5
    effect_range(count_off),    # Study 4
    effect_range(layout_off),   # Study 3
]

on_effects = [
    effect_range(area_on),      # Study 5
    effect_range(count_on),     # Study 4
    effect_range(layout_on),    # Study 3
]

# Sanity print
labels = ['Area Size\n(Study 5)', 'Restaurant Count\n(Study 4)', 'Spatial Arrangement\n(Study 3)']
print("📊 EFFECT MAGNITUDES (max − min assignment time at ratio 5.0)")
print("-"*55)
for lbl, off, on in zip(labels, off_effects, on_effects):
    print(f"  {lbl.replace(chr(10), ' '):<35}  OFF: {off:5.2f} min   ON: {on:5.2f} min")
print("-"*55)

# ============================================================================
# STEP 3: HORIZONTAL BAR CHART
# ============================================================================
COLOR_OFF = '#E63946'   # red  — pairing OFF  (matches slides 5 & 6)
COLOR_ON  = '#2A9D8F'   # teal — pairing ON

fig, ax = plt.subplots(figsize=(10, 5))

y = np.arange(len(labels))
bar_h = 0.32

bars_off = ax.barh(y + bar_h / 2, off_effects, bar_h,
                   label='Pairing OFF', color=COLOR_OFF, alpha=0.85, zorder=3)
bars_on  = ax.barh(y - bar_h / 2, on_effects,  bar_h,
                   label='Pairing ON',  color=COLOR_ON,  alpha=0.85, zorder=3)

# Value labels on bar ends
for bar, val in zip(bars_off, off_effects):
    ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
            f'{val:.1f} min', va='center', ha='left', fontsize=10.5, color='black')

for bar, val in zip(bars_on, on_effects):
    ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
            f'{val:.1f} min', va='center', ha='left', fontsize=10.5, color='black')

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=11)
ax.set_xlabel('Assignment Time Range  max − min across factor levels  (min)',
              fontsize=11, fontweight='bold')
ax.set_title('Figure 4.5: Infrastructure Factor Effect Magnitudes  (ratio 5.0)',
             fontsize=13, fontweight='bold', pad=12)
ax.legend(fontsize=11, loc='lower right')
ax.grid(True, axis='x', alpha=0.3, linestyle='--')
ax.set_xlim([0, 32])   # extra room for value labels

plt.tight_layout()
plt.show()
print("✓ Figure 4.5 rendered")

# %%
