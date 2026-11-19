"""
Load-dependent promotion study.

Question: can a platform buy the same number of extra R_F orders at lower fleet
cost by promoting mainly when the fleet has slack (an idle driver exists) and
holding back when orders queue?

Policy: choice-aware Delta-V rule, v_j = lambda * m_j - c_j, where lambda is
    lambda_slack  when an idle driver exists at arrival
    lambda_busy   when no idle driver exists
Fixed-lambda arms (lambda_slack = lambda_busy) trace the reference frontier.
'Reverse' arms (promote mainly when busy) are a mechanism check: they should
do worse than the fixed frontier if the idea is right.

Setting: P(nearest) 40%, k = 2, R_F = R10, ratios 7 (light) and 8 (between our
earlier loads, where both states are common). 40 paired replications per arm.

Run:  python load_dependent_promotion_study.py  -> results/load_dependent_results.pkl
"""
import os
import sys
import pickle
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from choice_aware_common import LABEL_BETAS, make_config, run_cell

REPS = 40
DURATION = 2000
WARMUP = 500
RATIOS = [7.0, 8.0]
FEATURED = 'R10'
BETA = LABEL_BETAS['40%']

FIXED = [1.0, 2.0, 3.0, 4.0, 6.0, 8.0]
TWO_LEVEL = ([(ls, 0.0) for ls in [2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0]]
             + [(ls, 1.0) for ls in [4.0, 8.0, 16.0]])
REVERSE = [(1.0, 4.0), (1.0, 8.0)]


def build_cells():
    cells = []
    for ratio in RATIOS:
        cells.append(((ratio, 'U', None, None), make_config(ratio, BETA, None)))
        cells.append(((ratio, 'fixed', 0.0, 0.0), make_config(ratio, BETA, 'aware')))
        for lam in FIXED:
            cells.append(((ratio, 'fixed', lam, lam),
                          make_config(ratio, BETA, 'aware', featured_id=FEATURED, lam=lam)))
        for kind, pairs in [('two_level', TWO_LEVEL), ('reverse', REVERSE)]:
            for ls, lb in pairs:
                cells.append(((ratio, kind, ls, lb),
                              make_config(ratio, BETA, 'aware', featured_id=FEATURED,
                                          lam=ls, lam_busy=lb)))
    return cells


if __name__ == '__main__':
    cells = build_cells()
    print(f"{len(cells)} cells x {REPS} reps", flush=True)
    t0 = time.time()
    args = [(key, cfg, FEATURED, REPS, DURATION, WARMUP) for key, cfg in cells]
    results = {}
    with Pool(2) as pool:
        for key, summaries, dt in pool.starmap(run_cell, args, chunksize=1):
            results[key] = summaries
    os.makedirs('results', exist_ok=True)
    with open('results/load_dependent_results.pkl', 'wb') as f:
        pickle.dump({'results': results, 'reps': REPS, 'featured': FEATURED, 'beta_label': '40%',
                     'k': 2.0}, f)
    print(f"done in {time.time() - t0:.0f}s", flush=True)
