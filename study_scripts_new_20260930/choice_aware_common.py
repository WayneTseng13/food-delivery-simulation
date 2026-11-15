"""
Shared helpers for the choice-aware curation study: build a design point, run
it, and summarize each replication directly from the order repository.

Per-replication summary (post-warmup arrival cohort):
    assign      mean wait from arrival to driver assignment (min), delivered orders
    fulfil      mean arrival -> delivery (min), delivered orders
    leg_km      mean restaurant -> customer leg (km), ALL cohort orders (choice-level)
    rf_share    share of cohort orders originating at R_F
    backlog     mean number of unassigned cohort orders sampled each minute
    delivered   share of cohort orders delivered by the end of the run
    agree       share of curated arrivals where the aware pick equals the greedy pick
    agree_imm   same, among immediate-branch arrivals only
    imm_rate    share of arrivals with an idle driver present
"""
import sys
import os
import math
import time
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from delivery_sim.simulation.configuration import (
    StructuralConfig, OperationalConfig, ExperimentConfig, LoggingConfig, ScoringConfig)
from delivery_sim.infrastructure.infrastructure import Infrastructure
from delivery_sim.infrastructure.infrastructure_analyzer import InfrastructureAnalyzer
from delivery_sim.simulation.simulation_runner import SimulationRunner
from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import configure_logging

LABEL_BETAS = {"10%": 0.0, "25%": 0.3013, "40%": 0.5737,
               "55%": 0.9358, "70%": 1.5944, "85%": 3.6442}
K = 2.0
B = math.log(K)

PAIRING = dict(pairing_enabled=True, restaurants_proximity_threshold=4.0,
               customers_proximity_threshold=3.0)
SERVICE = dict(mean_service_duration=100, service_duration_std_dev=60,
               min_service_duration=30, max_service_duration=200)

_INFRA = None


def quiet_logging():
    configure_logging(LoggingConfig(console_level="ERROR", component_levels={
        "services": "ERROR", "entities": "ERROR", "repositories": "ERROR",
        "utils": "ERROR", "system_data": "ERROR", "simulation.runner": "ERROR",
        "infrastructure": "ERROR", "experimental.runner": "ERROR"}))


def get_infrastructure():
    global _INFRA
    if _INFRA is None:
        infra = Infrastructure(StructuralConfig(10, 10, 0.5), 42)
        InfrastructureAnalyzer(infra).analyze_complete_infrastructure()
        _INFRA = infra
    return _INFRA


def make_config(ratio, beta, policy, featured_id=None, lam=0.0, platform_beta=None, rule='delta_v'):
    kw = dict(mean_order_inter_arrival_time=1.0,
              mean_driver_inter_arrival_time=ratio,
              **PAIRING, **SERVICE,
              curation_policy=policy,
              customer_distance_sensitivity=beta,
              recommendation_boost=B if policy is not None else 0.0,
              curation_lambda=lam, platform_beta=platform_beta, curation_rule=rule)
    if featured_id is not None:
        kw['featured_restaurant_id'] = featured_id
    return OperationalConfig(**kw)


def summarize(rep, warmup, featured_id):
    orders = rep['repositories']['order'].find_all()
    end = rep['run_context']['simulation_duration']
    cohort = [o for o in orders if o.arrival_time >= warmup]
    done = [o for o in cohort if o.delivery_time is not None]
    assigned = [o for o in cohort if o.assignment_time is not None]
    out = {}
    out['n'] = len(cohort)
    out['assign'] = np.mean([o.assignment_time - o.arrival_time for o in assigned]) if assigned else np.nan
    out['pickup'] = np.mean([o.pickup_time - o.assignment_time for o in done]) if done else np.nan
    out['fulfil'] = np.mean([o.delivery_time - o.arrival_time for o in done]) if done else np.nan
    out['leg_km'] = np.mean([calculate_distance(o.restaurant_location, o.customer_location) for o in cohort])
    out['rf_share'] = (np.mean([o.origin_restaurant_id == featured_id for o in cohort])
                       if featured_id else np.nan)
    out['delivered'] = len(done) / len(cohort)
    # time-average of unassigned cohort orders, sampled every minute post-warmup
    a = np.array([o.arrival_time for o in cohort])
    s = np.array([o.assignment_time if o.assignment_time is not None else np.inf for o in cohort])
    grid = np.arange(warmup, end, 1.0)
    unassigned = np.array([np.sum((a <= t) & (s > t)) for t in grid])
    out['backlog'] = unassigned.mean()
    out['backlog_slope'] = np.polyfit(grid, unassigned, 1)[0]
    out['imm_rate'] = np.mean([o.arrival_state == 'immediate' for o in cohort])
    dec = [o for o in cohort if getattr(o, 'curation_decision', None)]
    if dec:
        out['agree'] = np.mean([o.curation_decision['agrees_with_greedy'] for o in dec])
        imm = [o for o in dec if o.arrival_state == 'immediate']
        out['agree_imm'] = np.mean([o.curation_decision['agrees_with_greedy'] for o in imm]) if imm else np.nan
        out['slot_rf'] = np.mean([o.curation_decision['slotted_featured'] for o in dec])
    else:
        out['agree'] = out['agree_imm'] = out['slot_rf'] = np.nan
    return out


def run_cell(name, cfg, featured_id, reps, duration, warmup, seed=42):
    quiet_logging()
    t0 = time.time()
    runner = SimulationRunner(get_infrastructure())
    exp = ExperimentConfig(simulation_duration=duration, num_replications=reps,
                           operational_master_seed=seed, collection_interval=1.0)
    results = runner.run_experiment(operational_config=cfg, experiment_config=exp,
                                    scoring_config=ScoringConfig())
    summaries = [summarize(r, warmup, featured_id) for r in results]
    return name, summaries, time.time() - t0
