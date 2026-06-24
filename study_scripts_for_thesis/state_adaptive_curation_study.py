# state_adaptive_curation_study.py
"""
State-Adaptive Curation Study: Effect of State-Adaptive Curation on System Performance

Research Question: How does state-adaptive curation (Policy X') compare to R-D proximity
curation (Policy X) and uniform random selection (Policy U) — particularly in regimes
where Policy X's R-D signal vanishes (high load, no idle drivers)?

Building on Previous Studies:
- Study 1 (Arrival Interval Ratio) established three operational regimes and located the
  no-pairing regime boundary around ratio 5.5-6.0.
- Study 2 (Pairing Effect) demonstrated pairing shifts the regime boundary substantially
  (bounded beyond ratio 8.0) and quantified pairing benefit across regimes.
- Study 3 (R-D Curation) tested Policy X vs Policy U. Established that Policy X reduces
  pickup travel time, but its operating envelope narrows at high load (fallback rate
  rises sharply at ratio ≥ 6.0). Pairing's slack-feeding effect partially restores X's
  envelope but does not eliminate the structural limitation.

This Study (State-Adaptive Curation):
- Tests Policy X', which branches on observable system state rather than relying solely
  on R-D signal availability. When R-D vanishes, X' falls back to alternative actionable
  signals (R-C for single deliveries, route-cost for prospective pairs).
- Compares X' against both U (no curation) and X (R-D curation) to isolate where state-
  adaptive logic provides incremental value over slack-fed proximity curation.
- Tests how X' interacts with pairing: when pairing is enabled, X' can actively recommend
  pair-compatible restaurants in the pair_queued state, complementing pairing's
  spontaneous pair formation.
- Characterises X's operating envelope via branch activation rates (pair_queued,
  single_immediate, single_queued) as a function of ratio and pairing condition.

Mechanism (from "Curation Policy Design — State-Adaptive Curation"):
- Two state checks at each arrival: pair_possible (pairing_enabled AND pair-eligible
  anchor exists) and driver_available (idle drivers exist).
- Branches:
    pair_queued      D=0, pair-eligible anchor exists → minimise pair route cost
    single_immediate D>0, no pair anchor              → minimise R-D + R-C
    single_queued    D=0, no pair anchor              → minimise R-C alone
- (pair_immediate is structurally unreachable under current event-driven assignment.)
- Full compliance assumed (p=1): customer always accepts the recommendation.

Design Pattern (3 × 2 × 3 factorial):
- 3 curation policies: uniform (U), proximity (X), state_adaptive (X')
- 2 pairing conditions: OFF, ON
- 3 arrival interval ratios: 5.0 (critical), 6.0 (no-pairing boundary), 7.0 (high stress)
- Baseline intensity only (order_interval = 1.0 min)

Six operational conditions per ratio:
- no_pairing_uniform        → no curation, no pairing (Study 1 baseline)
- no_pairing_proximity      → R-D curation only (Study 3)
- no_pairing_state_adaptive → state-adaptive curation only (NEW)
- pairing_uniform           → pairing only (Study 2)
- pairing_proximity         → pairing + R-D curation (Study 3)
- pairing_state_adaptive    → pairing + state-adaptive curation (NEW)

Total Design Points: 3 policies × 2 pairing × 3 ratios = 18
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
print("STATE-ADAPTIVE CURATION STUDY: U vs X vs X' ACROSS PAIRING AND RATIO")
print("="*80)
print("Research Question: How does state-adaptive curation compare to U and X?")
print("Building on Study 3: adds X' as third policy alongside U and X")

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
(1) Does state-adaptive curation (X') outperform R-D proximity curation (X) in regimes
    where X's R-D signal frequently vanishes (high load)?
(2) Does X' interact with pairing differently than X — specifically, does X's pair_queued
    branch produce additional pair formation beyond what pairing alone generates?
(3) How do branch activation rates (pair_queued, single_immediate, single_queued) vary
    with ratio and pairing condition, and how does that pattern map onto performance?
"""

# ==============================================================================
# CONTEXT & MOTIVATION
# ==============================================================================
context = """
Policy X (R-D proximity curation, Savelsbergh & Ulmer 2024) shortens the pickup leg when
idle drivers exist, but it has a structural limitation: when no idle drivers are
available, R-D is undefined and X falls back to uniform random selection. Study 3
quantified this — the fallback rate rises sharply with load and dominates at ratio ≥ 6.0.

Policy X' (state-adaptive curation) addresses this by branching on observable system
state. When R-D vanishes (no idle drivers), X' switches to alternative actionable
signals:
- pair_queued branch: if a pair-eligible anchor exists, recommend the restaurant
  that, paired with the anchor, minimises total route cost. This actively pushes for
  pair formation rather than waiting for it to happen opportunistically.
- single_queued branch: if no pair anchor exists, recommend the restaurant closest to
  the customer (R-C). This minimises the customer-side leg even when the driver-side
  leg cannot be optimised.

When idle drivers DO exist (single_immediate branch), X' minimises R-D + R-C jointly,
extending X's R-D-only criterion with a customer-side term.

The structural hypothesis: X' should match X at low load (both operate on R-D-rich
state) and exceed X at high load (where X is in fallback while X' is still acting on
signal). The interaction with pairing is open: X' could either complement pairing by
actively constructing pairs, or duplicate what pairing already achieves.
"""

# ==============================================================================
# SUB-QUESTIONS & HYPOTHESES
# ==============================================================================
sub_questions = """
1. Pickup travel time (order_metrics)
   - Mechanism signal at low/mid load: X and X' should both reduce pickup travel
     vs U via R-D-aware selection.
   - At high load: X loses this advantage (mostly in fallback); X' retains R-D
     awareness in single_immediate (still rare at high load) but its main lever
     becomes pair_queued/single_queued, which act on different metrics.

2. Assignment time / growth rate / avg queue (order_metrics, queue_dynamics_metrics)
   - Outcome signal: do X's branch-specific levers translate to system-level benefit
     where X cannot act?

3. Pairing rate (system_metrics)
   - When pairing is ON, does X' actively raise pairing rate above what pairing alone
     achieves under U or X? If yes, X is doing real pair-construction work; if no, the
     pair_queued branch is duplicating what pairing forms opportunistically.

4. Branch activation rates (curation_metrics)
   - Operating envelope characterisation: how does (pair_queued, single_immediate,
     single_queued) shift across ratios and pairing conditions? Expectation:
     single_immediate dominant at low load; pair_queued rising with load when pairing
     is enabled; single_queued dominant at high load when pairing is disabled.

5. X vs X' decomposition
   - Where X is mostly active (low/mid load): X' ≈ X expected.
   - Where X is mostly in fallback (high load): X' > X expected if the branch
     alternatives add value.
"""

# ==============================================================================
# SCOPE & BOUNDARIES
# ==============================================================================
scope = """
- Single fixed infrastructure (seed=42), consistent with Studies 1-3.
- Three ratios: 5.0 (critical), 6.0 (no-pairing boundary), 7.0 (high stress) — same
  ratios as Study 3 to allow direct U/X/X' comparison.
- Baseline intensity only (order_interval=1.0).
- Full compliance (p=1) — upper-bound characterisation of curation effect.
- Pair_immediate branch (D>0 AND pair-eligible anchor) is structurally unreachable
  under current event-driven greedy assignment and is asserted-against in the policy.
  Its absence is a property of the assignment architecture, not of X' itself.
"""

# ==============================================================================
# KEY METRICS & ANALYSIS FOCUS
# ==============================================================================
analysis_focus = """
Primary: assignment time and growth rate (X vs X' separation at high load), pickup
travel time (mechanism, where R-D is still active), pairing rate (does X' construct
pairs beyond pairing's opportunistic formation).
Secondary: branch activation rates (operating envelope), fallback rate (X only —
characterises where X' is expected to gain).
Approach: U serves as no-curation baseline. X is the Study 3 anchor. X' is the new
condition. The U vs X comparison reproduces Study 3 under the routing architecture
fix; the X vs X' comparison is the main contribution of this study.
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

Study 3: R-D Curation Study (COMPLETE)
- Policy X reduces pickup travel time; operating envelope narrows at high load.
- Established the limitation that motivates state-adaptive curation.

State-Adaptive Curation Study (THIS STUDY)
- Introduces X' as a third policy condition. 3×2×3 factorial isolates the X vs X'
  separation and the X' × pairing interaction.
- Both U and X are rerun (not referenced from Study 3) so all three policies share the
  same operational seeds within this study — proper CRN alignment across policies.
- Curation metrics now report both X's fallback rate and X's branch activation rates.
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
STATE-ADAPTIVE CURATION STUDY: 3 × 2 × 3 factorial over curation policy, pairing, and ratio.

For each arrival interval ratio, create six configurations:
- no_pairing_uniform        → no curation, no pairing (Study 1 baseline)
- no_pairing_proximity      → R-D curation only (Study 3 condition)
- no_pairing_state_adaptive → state-adaptive curation only (NEW)
- pairing_uniform           → pairing only (Study 2 condition)
- pairing_proximity         → pairing + R-D curation (Study 3 condition)
- pairing_state_adaptive    → pairing + state-adaptive curation (NEW)

This isolates the X vs X' main effect within each pairing level and the
state_adaptive × pairing interaction.
"""

# Target arrival interval ratios (same as Study 3 for direct comparison)
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
UNIFORM = None                # CHANGED: no curation policy
PROXIMITY = 'proximity'
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
    # no_pairing_uniform — Study 1 baseline
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

    # no_pairing_proximity — Study 3 condition
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

    # no_pairing_state_adaptive — NEW
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_no_pairing_state_adaptive',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **no_pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=STATE_ADAPTIVE
        )
    })

    # pairing_uniform — Study 2 condition
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

    # pairing_proximity — Study 3 condition
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

    # pairing_state_adaptive — NEW
    operational_configs.append({
        'name': f'ratio_{ratio:.1f}_pairing_state_adaptive',
        'config': OperationalConfig(
            mean_order_inter_arrival_time=1.0,
            mean_driver_inter_arrival_time=ratio,
            **pairing_params,
            **FIXED_SERVICE_CONFIG,
            curation_policy=STATE_ADAPTIVE
        )
    })

print(f"✓ Defined {len(operational_configs)} operational configurations")
print(f"✓ Testing {len(target_arrival_interval_ratios)} arrival interval ratios: {target_arrival_interval_ratios}")
print(f"✓ Each ratio has 6 conditions (3 curation × 2 pairing)")

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
    simulation_duration=2000,  # Same as Study 3
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

# Set warmup period based on visual inspection of Cell 13 plots.
# Same value as Study 3 since infrastructure and ratio range are identical.
uniform_warmup_period = 500  # UPDATE THIS based on visual inspection if needed

print(f"✓ Warmup period set: {uniform_warmup_period} minutes")
print(f"✓ Based on visual inspection of active drivers oscillation around Little's Law values")
print(f"✓ Analysis window: {experiment_config.simulation_duration - uniform_warmup_period} minutes of post-warmup data")

# %% CELL 15: Process Through Analysis Pipeline
print("\n" + "="*80)
print("PROCESSING THROUGH ANALYSIS PIPELINE")
print("="*80)

from delivery_sim.analysis_pipeline.pipeline_coordinator import ExperimentAnalysisPipeline

# Initialize pipeline
# NOTE: 'curation_metrics' is enabled here so both the fallback rate (Policy X envelope)
# and the branch activation rates (Policy X' envelope) are computed in a single pass.
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
"""
Two tables are produced:

Table A — Main performance metrics: same shape as Study 3's table, with X' added
          as a third curation policy row per ratio block. Expanded to include the
          full delivery chain (delivery travel time, fulfillment time) and two
          load/mechanism indicators (driver utilization, immediate assignment rate)
          for richer R-C and operational-relaxation visibility.
Table B — Curation diagnostic metrics: fallback rate (Policy X's operating envelope)
          alongside branch activation rates (Policy X's operating envelope).

For Table B's columns: Policy U shows N/A everywhere (no curation attempted). Policy
X populates fallback_rate; branch rates are 0 (no branch labels stamped) and shown as
N/A. Policy X' populates branch rates; fallback_rate is 0 and shown as N/A.
"""

print("\n" + "="*80)
print("KEY PERFORMANCE METRICS: STATE-ADAPTIVE CURATION STUDY")
print("="*80)

import re

def extract_ratio_pairing_curation(design_name):
    """Extract ratio, pairing condition, and curation policy from design point name."""
    match = re.match(
        r'ratio_([\d.]+)_(no_pairing|pairing)_(uniform|proximity|state_adaptive)',
        design_name
    )
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

    # ------------------------------------------------------------------
    # ORDER METRICS
    # ------------------------------------------------------------------
    order_metrics = stats_with_cis.get('order_metrics', {})

    # Assignment time
    assignment = order_metrics.get('assignment_time', {}).get('mean_of_means', {})
    mom_estimate = assignment.get('point_estimate', 0)
    mom_ci = assignment.get('confidence_interval', [0, 0])
    mom_ci_width = (mom_ci[1] - mom_ci[0]) / 2 if mom_ci[0] is not None else 0

    # Pickup travel time (driver → restaurant)
    pickup = order_metrics.get('pickup_travel_time', {}).get('mean_of_means', {})
    pickup_estimate = pickup.get('point_estimate', 0)
    pickup_ci = pickup.get('confidence_interval', [0, 0])
    pickup_ci_width = (pickup_ci[1] - pickup_ci[0]) / 2 if pickup_ci[0] is not None else 0

    # Delivery travel time (restaurant → customer, direct R-C leg)
    delivery = order_metrics.get('delivery_travel_time', {}).get('mean_of_means', {})
    delivery_estimate = delivery.get('point_estimate', 0)
    delivery_ci = delivery.get('confidence_interval', [0, 0])
    delivery_ci_width = (delivery_ci[1] - delivery_ci[0]) / 2 if delivery_ci[0] is not None else 0

    # Fulfillment time (assignment + pickup + delivery — full customer experience)
    fulfillment = order_metrics.get('fulfillment_time', {}).get('mean_of_means', {})
    fulfillment_estimate = fulfillment.get('point_estimate', 0)
    fulfillment_ci = fulfillment.get('confidence_interval', [0, 0])
    fulfillment_ci_width = (fulfillment_ci[1] - fulfillment_ci[0]) / 2 if fulfillment_ci[0] is not None else 0

    # ------------------------------------------------------------------
    # QUEUE DYNAMICS METRICS
    # ------------------------------------------------------------------
    queue_dynamics_metrics = stats_with_cis.get('queue_dynamics_metrics', {})

    growth_rate = queue_dynamics_metrics.get('unassigned_entities_growth_rate', {})
    growth_rate_estimate = growth_rate.get('point_estimate', 0)
    growth_rate_ci = growth_rate.get('confidence_interval', [0, 0])
    growth_rate_ci_width = (growth_rate_ci[1] - growth_rate_ci[0]) / 2 if growth_rate_ci[0] is not None else 0

    avg_queue = queue_dynamics_metrics.get('average_unassigned_entities', {})
    avg_queue_estimate = avg_queue.get('point_estimate', 0)
    avg_queue_ci = avg_queue.get('confidence_interval', [0, 0])
    avg_queue_ci_width = (avg_queue_ci[1] - avg_queue_ci[0]) / 2 if avg_queue_ci[0] is not None else 0

    # ------------------------------------------------------------------
    # SYSTEM STATE METRICS (two-level: mean_of_means pattern)
    # ------------------------------------------------------------------
    system_state_metrics = stats_with_cis.get('system_state_metrics', {})

    # Driver utilization — delivering_drivers / active_drivers (shows operational relaxation)
    driver_util = system_state_metrics.get('driver_utilization', {}).get('mean_of_means', {})
    driver_util_estimate = driver_util.get('point_estimate', 0)
    driver_util_ci = driver_util.get('confidence_interval', [0, 0])
    driver_util_ci_width = (driver_util_ci[1] - driver_util_ci[0]) / 2 if driver_util_ci[0] is not None else 0

    # ------------------------------------------------------------------
    # SYSTEM METRICS (one-level pattern — no mean_of_means wrapper)
    # ------------------------------------------------------------------
    system_metrics = stats_with_cis.get('system_metrics', {})

    # Pairing rate
    pairing_rate = system_metrics.get('system_pairing_rate', {})
    pairing_rate_estimate = pairing_rate.get('point_estimate', None)
    pairing_rate_ci = pairing_rate.get('confidence_interval', [None, None])
    pairing_rate_ci_width = (pairing_rate_ci[1] - pairing_rate_ci[0]) / 2 if pairing_rate_ci[0] is not None else None

    # Immediate assignment rate — fraction of orders assigned at arrival (D > 0)
    immediate_assign = system_metrics.get('immediate_assignment_rate', {})
    immediate_assign_estimate = immediate_assign.get('point_estimate', 0)
    immediate_assign_ci = immediate_assign.get('confidence_interval', [0, 0])
    immediate_assign_ci_width = (immediate_assign_ci[1] - immediate_assign_ci[0]) / 2 if immediate_assign_ci[0] is not None else 0

    # ------------------------------------------------------------------
    # CURATION METRICS
    # ------------------------------------------------------------------
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
        # Order metrics
        'mom_estimate': mom_estimate,
        'mom_ci_width': mom_ci_width,
        'pickup_estimate': pickup_estimate,
        'pickup_ci_width': pickup_ci_width,
        'delivery_estimate': delivery_estimate,
        'delivery_ci_width': delivery_ci_width,
        'fulfillment_estimate': fulfillment_estimate,
        'fulfillment_ci_width': fulfillment_ci_width,
        # Queue dynamics
        'growth_rate_estimate': growth_rate_estimate,
        'growth_rate_ci_width': growth_rate_ci_width,
        'avg_queue_estimate': avg_queue_estimate,
        'avg_queue_ci_width': avg_queue_ci_width,
        # System state
        'driver_util_estimate': driver_util_estimate,
        'driver_util_ci_width': driver_util_ci_width,
        # System metrics
        'pairing_rate_estimate': pairing_rate_estimate,
        'pairing_rate_ci_width': pairing_rate_ci_width,
        'immediate_assign_estimate': immediate_assign_estimate,
        'immediate_assign_ci_width': immediate_assign_ci_width,
        # Curation metrics
        'fallback_rate_estimate': fallback_rate_estimate,
        'fallback_rate_ci_width': fallback_rate_ci_width,
        'pair_queued_estimate': pair_queued_estimate,
        'pair_queued_ci_width': pair_queued_ci_width,
        'single_imm_estimate': single_imm_estimate,
        'single_imm_ci_width': single_imm_ci_width,
        'single_q_estimate': single_q_estimate,
        'single_q_ci_width': single_q_ci_width,
    })

# Sort by ratio, then pairing condition, then curation policy for stable grouping
pairing_order = {'no_pairing': 0, 'pairing': 1}
curation_order = {'uniform': 0, 'proximity': 1, 'state_adaptive': 2}
curation_label_map = {'uniform': 'U', 'proximity': 'X', 'state_adaptive': "X'"}
metrics_data.sort(key=lambda r: (r['ratio'],
                                 pairing_order[r['pairing_condition']],
                                 curation_order[r['curation_policy']]))

# =========================================================================
# TABLE A — MAIN PERFORMANCE METRICS
# =========================================================================
print("\nTABLE A — MAIN PERFORMANCE METRICS")
header_a = (f"  {'Ratio':>5}  {'Pairing':>9}  {'Curation':>9}  "
            f"{'Assign Time':>16}  {'Pickup Travel':>16}  "
            f"{'Delivery Travel':>16}  {'Fulfillment':>16}  "
            f"{'Avg Queue':>17}  {'Growth Rate':>18}  "
            f"{'Driver Util':>14}  {'Immed. Rate':>14}  "
            f"{'Pairing Rate':>16}")
print(header_a)
print("="*len(header_a))

current_ratio = None
for row in metrics_data:
    if current_ratio is not None and row['ratio'] != current_ratio:
        print("-"*len(header_a))
    current_ratio = row['ratio']

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

    print(f"  {row['ratio']:>5.1f}  {pairing_label:>9}  {curation_label:>9}  "
          f"{assignment_str:>16}  {pickup_str:>16}  "
          f"{delivery_str:>16}  {fulfillment_str:>16}  "
          f"{avg_queue_str:>17}  {growth_rate_str:>18}  "
          f"{driver_util_str:>14}  {immediate_str:>14}  "
          f"{pairing_rate_str:>16}")

print("="*len(header_a))

# =========================================================================
# TABLE B — CURATION DIAGNOSTIC METRICS
# =========================================================================
print("\nTABLE B — CURATION DIAGNOSTIC METRICS")
print("(Fallback rate: Policy X envelope. Branch rates: Policy X' envelope.)")
header_b = (f"  {'Ratio':>5}  {'Pairing':>9}  {'Curation':>9}  "
            f"{'Fallback':>16}  {'pair_queued':>16}  "
            f"{'single_imm':>16}  {'single_q':>16}")
print(header_b)
print("="*len(header_b))

def _fmt_rate(est, ci_width):
    """Format a rate as 'XX.XX ± Y.YY%', or N/A if not populated."""
    if est is None:
        return "N/A"
    if ci_width is None:
        return f"{est*100:5.2f}%"
    return f"{est*100:5.2f} ± {ci_width*100:4.2f}%"

current_ratio = None
for row in metrics_data:
    if current_ratio is not None and row['ratio'] != current_ratio:
        print("-"*len(header_b))
    current_ratio = row['ratio']

    pairing_label  = "ON" if row['pairing_condition'] == 'pairing' else "OFF"
    curation_label = curation_label_map[row['curation_policy']]

    if row['curation_policy'] == 'uniform':
        fallback_str = "N/A"
        pq_str       = "N/A"
        si_str       = "N/A"
        sq_str       = "N/A"
    elif row['curation_policy'] == 'proximity':
        fallback_str = _fmt_rate(row['fallback_rate_estimate'], row['fallback_rate_ci_width'])
        pq_str       = "N/A"
        si_str       = "N/A"
        sq_str       = "N/A"
    else:  # state_adaptive
        fallback_str = "N/A"
        pq_str       = _fmt_rate(row['pair_queued_estimate'], row['pair_queued_ci_width'])
        si_str       = _fmt_rate(row['single_imm_estimate'], row['single_imm_ci_width'])
        sq_str       = _fmt_rate(row['single_q_estimate'], row['single_q_ci_width'])

    print(f"  {row['ratio']:>5.1f}  {pairing_label:>9}  {curation_label:>9}  "
          f"{fallback_str:>16}  {pq_str:>16}  "
          f"{si_str:>16}  {sq_str:>16}")

print("="*len(header_b))

# =========================================================================
# INTERPRETATION GUIDE
# =========================================================================
print("\n📊 METRIC INTERPRETATION GUIDE:")
print("-"*80)
print("CURATION POLICY:  U = uniform random,  X = R-D proximity,  X' = state-adaptive")
print()
print("TABLE A — PERFORMANCE METRICS:")
print("  • Assign Time: driver assigned to order. Primary outcome; sensitive to D > 0")
print("    frequency (immediate rate) and queue depth.")
print("  • Pickup Travel: driver→restaurant leg. X and X' both act here (R-D signal).")
print("    Separation vs U expected at low/mid load where idle drivers are available.")
print("  • Delivery Travel: restaurant→customer leg. Direct R-C effect; X' acts via")
print("    pair_queued and single_queued branches. Should differ from pickup pattern.")
print("  • Fulfillment: assignment + pickup + delivery — full customer experience.")
print("    Integrates all three legs; pairing effect visible here (paired orders absorb")
print("    more travel but may offset via faster assignment).")
print("  • Avg Queue / Growth Rate: system-level load signals. X vs X' separation")
print("    expected primarily at high load (ratio ≥ 6.0) where X's envelope narrows.")
print("  • Driver Util: delivering_drivers / active_drivers. Lower util under X' vs X")
print("    at high load means the system is operationally more relaxed (fewer drivers")
print("    locked in delivery, more available for assignment).")
print("  • Immed. Rate: fraction of orders assigned at arrival (D > 0). Directly")
print("    determines single_immediate branch activation rate in X'. Higher rate at")
print("    low load; near-zero at high load when queue dominates.")
print("  • Pairing Rate: under pairing ON, does X' construct pairs beyond what U/X")
print("    achieve opportunistically? Rise vs U/X signals active pair construction.")
print()
print("TABLE B — CURATION DIAGNOSTIC METRICS:")
print("  • Fallback (Policy X only): fraction of arrivals where no idle drivers existed")
print("    and X reverted to uniform. Rises with load — characterises X's operating")
print("    envelope narrowing.")
print("  • pair_queued / single_immediate / single_queued (Policy X' only): branch")
print("    activation rates. Expected pattern:")
print("      - single_immediate dominant at low load (idle drivers present).")
print("      - pair_queued rising with load when pairing ON (D=0 AND anchor exists).")
print("      - single_queued dominant at high load with pairing OFF (D=0 AND no anchor).")
print()
print("KEY QUESTIONS TO ANSWER:")
print("  • At low/mid load: is X' ≈ X (both operate on R-D-rich state)?")
print("  • At high load: does X' outperform X on assignment time / growth rate?")
print("  • Does X' raise the pairing rate beyond what X or U achieve under pairing ON?")
print("  • Do branch activation rates match the expected pattern across ratios?")
print("="*80)

print("\n✓ Metric extraction complete")
print("✓ Results ready for state-adaptive curation analysis")
# %% CELL 17: Ad-hoc Analysis (Placeholder)
"""
PLACEHOLDER FOR AD-HOC ANALYSIS

This cell is reserved for exploratory analysis specific to the state-adaptive curation
study. Potential analyses:
- X vs X' performance comparison across ratios, faceted by pairing condition
- Pairing rate decomposition: how much of X's pairing rate uplift comes from
  pair_queued branch activations?
- Branch activation rate visualization (stacked area chart vs ratio, faceted by pairing)
- X' branch-conditional performance: at high load with pairing ON, do pair_queued
  arrivals translate to actually-formed pairs (alignment intention vs realisation)?
- Mechanism decomposition: where U vs X separation came from in Study 3, where does
  the additional X vs X' separation come from?

To be developed based on Cell 16 findings.
"""

print("\n" + "="*80)
print("AD-HOC ANALYSIS PLACEHOLDER")
print("="*80)
print("Reserved for exploratory analysis based on results.")
print("="*80)

# %%