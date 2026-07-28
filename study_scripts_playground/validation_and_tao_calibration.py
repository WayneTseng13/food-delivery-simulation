# customer_compliance_study.py
"""
# ============================================================================
# VALIDATION + CALIBRATION STUDY  --  cells to replace in the renamed copy of
# (iii)_edge_manufacture_effect_study.py
#
# Purpose:
#   1. VALIDATION: prove 'blended' with tau=0 is bit-identical to 'operational'
#      at matched seeds -- the acceptance test for the whole featuring chain.
#   2. CALIBRATION: from the SAME tau=0 blended run, dump featuring_penalty over
#      cohort orders -> empirical CDF -> place the tau grid at penalty quantiles.
#
# Minimal design: ONE ratio, ONE p, TWO policies. Keep it small until identity
# is confirmed; only then scale up to the real frontier sweep.
#
# Replace CELL 8, CELL 15, CELL 16; ADD CELL 17. Everything else (CELLs 1-7,
# 9-14) is unchanged from the template -- they only consume `operational_configs`
# and `design_points`, which CELL 8 / CELL 9 still produce.
# ============================================================================
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

 
# --- single-cell knobs (widen later for the real study) ---
VALIDATION_RATIO = 7.0
VALIDATION_P = 1.0
FEATURED_ID = 'R10'
 
PAIRING_PARAMS = {
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
 
# Arm 1: operational (X'')
operational_configs.append({
    'name': f"ratio_{VALIDATION_RATIO:.1f}_operational_p{VALIDATION_P:.1f}",
    'config': OperationalConfig(
        mean_order_inter_arrival_time=1.0,
        mean_driver_inter_arrival_time=VALIDATION_RATIO,
        **PAIRING_PARAMS,
        **FIXED_SERVICE_CONFIG,
        curation_policy='operational',
        customer_compliance_probability=VALIDATION_P,
    )
})
 
# Arm 2: blended, tau=0 (must equal Arm 1 on system metrics)
operational_configs.append({
    'name': f"ratio_{VALIDATION_RATIO:.1f}_blended_tau0_p{VALIDATION_P:.1f}",
    'config': OperationalConfig(
        mean_order_inter_arrival_time=1.0,
        mean_driver_inter_arrival_time=VALIDATION_RATIO,
        **PAIRING_PARAMS,
        **FIXED_SERVICE_CONFIG,
        curation_policy='blended',
        featured_restaurant_id=FEATURED_ID,
        featured_tau=0.0,
        customer_compliance_probability=VALIDATION_P,
    )
})
 
print(f"✓ Defined {len(operational_configs)} operational configurations (validation)")
print(f"  • Ratio: {VALIDATION_RATIO}, p: {VALIDATION_P}, featured: {FEATURED_ID}")
print(f"  • Arms: operational (X'')  vs  blended tau=0")
for config in operational_configs:
    print(f"    - {config['name']}")

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
    simulation_duration=1500,  # Same as Studies 3 & 4 for direct comparison
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

# %% CELL 16: VALIDATION -- bit-identity of operational vs blended(tau=0)
#
# If the featuring chain touches no RNG stream differently, the two arms produce
# IDENTICAL system metrics at matched seeds (same recommended restaurant on every
# arrival). We check point estimates are equal to a tight tolerance. NOT "within
# CI" -- identical.
#
# Also surfaces the featuring-only metrics on the blended arm:
#   featured_recommendation_rate  == R10's organic operational share (fire rate
#                                    at tau=0 = P(R_F is R_op)).
#   featured_origin_rate          == same, plus (1-p)/(N-1) rejection landings
#                                    (0 extra at p=1, since no rejections).
 
print("\n" + "="*80)
print("VALIDATION: operational (X'')  vs  blended(tau=0)")
print("="*80)
 
op_name = f"ratio_{VALIDATION_RATIO:.1f}_operational_p{VALIDATION_P:.1f}"
bl_name = f"ratio_{VALIDATION_RATIO:.1f}_blended_tau0_p{VALIDATION_P:.1f}"
 
op_res = design_analysis_results[op_name]
bl_res = design_analysis_results[bl_name]
 
 
def _pe(result, group, key, sub=None):
    block = result.get('statistics_with_cis', {}).get(group, {})
    entry = block.get(key, {})
    if sub is not None:
        entry = entry.get(sub, {})
    return entry.get('point_estimate', None)
 
 
# (group, key, sub) tuples to compare for identity.
CHECKS = [
    ('order_metrics',  'assignment_time',      'mean_of_means'),
    ('order_metrics',  'delivery_travel_time', 'mean_of_means'),
    ('order_metrics',  'fulfillment_time',     'mean_of_means'),
    ('system_metrics', 'system_throughput',    None),
    ('system_metrics', 'system_completion_rate',      None),
    ('system_metrics', 'system_pairing_rate',         None),
    ('system_metrics', 'arrival_immediate_rate', None),
]
 
TOL = 1e-9
print(f"\n{'metric':<40}{'operational':>16}{'blended(0)':>16}{'identical?':>12}")
print("-"*84)
all_identical = True
for group, key, sub in CHECKS:
    a = _pe(op_res, group, key, sub)
    b = _pe(bl_res, group, key, sub)
    if a is None or b is None:
            verdict = "MISSING"
            missing = True          # track separately
    else:
        ok = abs(a - b) <= TOL
        verdict = "yes" if ok else f"NO (d={a-b:.2e})"
        all_identical = all_identical and ok
    label = f"{group.split('_')[0]}.{key}"
    sa = f"{a:.6f}" if a is not None else "None"
    sb = f"{b:.6f}" if b is not None else "None"
    print(f"{label:<40}{sa:>16}{sb:>16}{verdict:>12}")
 
print("-"*84)
if all_identical:
    print("✅ BIT-IDENTICAL: featuring chain is RNG-neutral. tau=0 recovers X''.")
else:
    print("❌ DIVERGENCE: something in the featuring path perturbs an RNG stream.")
    print("   Check: does BlendedCurationPolicy.select consume a draw? does the")
    print("   service take a different branch when curation_policy is not None?")
 
# Featuring-only metrics on the blended arm.
frr = _pe(bl_res, 'curation_metrics', 'featured_recommendation_rate', None)
for_ = _pe(bl_res, 'curation_metrics', 'featured_origin_rate', None)
print(f"\nBlended arm featuring metrics (tau=0):")
print(f"  featured_recommendation_rate = {frr:.4f}   "
      f"(= R10 organic operational share; fire rate at tau=0)")
print(f"  featured_origin_rate         = {for_:.4f}   "
      f"(= same at p=1, no rejection landings)")
# %% CELL 17: TAU CALIBRATION -- penalty CDF from the blended(tau=0) run
#
# featuring_penalty is stamped on EVERY cohort order of the blended arm, whether
# or not featuring fired. penalty is a property of arrival geometry, independent
# of tau, so the empirical CDF gives fire_rate(tau') = P(penalty <= tau') for
# every tau' at once. Place the real study's tau grid at penalty quantiles so
# fire rates spread across [0, 1] instead of guessing round numbers.
#
# CAVEAT: this CDF is measured under the tau=0 (== X'') trajectory. Once featuring
# fires at higher tau, efficiency drops, idle drivers thin, the penalty
# distribution shifts. First-order calibration, not prediction. Compare predicted
# vs realized fire rate per tau in the real study as a state-perturbation
# diagnostic.
 
print("\n" + "="*80)
print("TAU CALIBRATION: featuring_penalty distribution (blended tau=0 run)")
print("="*80)
 
import numpy as np
 
# Pull raw penalties from every replication's cohort orders on the blended arm.
# study_results[bl_name] is the list of raw replication results; each carries
# repositories -> order repo -> orders with .featuring_penalty and .arrival_time.
# We re-apply the warmup filter to match the analysis cohort.
penalties = []
for rep_result in study_results[bl_name]:
    order_repo = rep_result['repositories']['order']
    for o in order_repo.find_all():
        if o.arrival_time is None or o.arrival_time < uniform_warmup_period:
            continue
        if o.featuring_penalty is not None:
            penalties.append(o.featuring_penalty)
 
penalties = np.array(penalties)
n = len(penalties)
print(f"\nCollected {n} cohort-order penalties across "
      f"{len(study_results[bl_name])} replications.")
 
if n == 0:
    print("⚠  No penalties collected. Check that the blended arm stamped "
          "featuring_penalty (order.featuring_penalty) and that arrival_time / "
          "warmup filter are correct.")
else:
    zero_share = (penalties == 0.0).mean()
    print(f"  penalty == 0 share : {zero_share:.4f}  "
          f"(R_F was R_op -> free featuring; matches fire rate at tau=0)")
    print(f"  mean / max         : {penalties.mean():.3f} / {penalties.max():.3f} km")
 
    # Empirical fire-rate curve at a few candidate tau values.
    print(f"\n  fire_rate(tau') = P(penalty <= tau'):")
    for t in [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]:
        fr = (penalties <= t).mean()
        print(f"    tau'={t:4.1f} km  ->  fire rate {fr:.3f}")
 
    # Quantile-placed tau grid: spread fire rate evenly across (0, 1).
    # Use quantiles of the POSITIVE penalties (exclude the free tau=0 mass, which
    # already fires at tau=0), so the grid resolves the interesting interior.
    pos = penalties[penalties > 0.0]
    print(f"\n  Suggested tau grid (quantiles of positive penalties, "
          f"n_pos={len(pos)}):")
    if len(pos) > 0:
        qs = [0.10, 0.25, 0.50, 0.75, 0.90]
        grid = np.quantile(pos, qs)
        for q, g in zip(qs, grid):
            fr = (penalties <= g).mean()
            print(f"    q{int(q*100):02d} -> tau={g:6.3f} km  (fire rate {fr:.3f})")
        print(f"\n  => candidate TAU_GRID = "
              f"[0.0, {', '.join(f'{g:.2f}' for g in grid)}, inf]")
        print(f"     (0.0 = X'' anchor; inf = Policy F; interior spreads the frontier)")