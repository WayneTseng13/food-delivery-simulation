"""
Choice-aware curation study (minimal version).

Q1  Does choice-awareness matter for operational curation?
    U vs O-greedy vs O-aware, across behavioral beta labels, at two loads.
Q2  What does promotion cost operationally?
    lambda sweep of the unified rule v_j = lambda*m_j - c_j with R_F = R10,
    under both the Delta-V rule (Blend-aware) and the greedy rule
    (Blend-greedy, argmax v_j ignoring choice probabilities), plus F.

All cells use the same operational master seed, so replication i of every
policy sees the same arrival times and customer locations (paired comparison).

Run:  python choice_aware_curation_study.py   -> results/choice_aware_results.pkl
"""
import os
import sys
import pickle
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from choice_aware_common import LABEL_BETAS, make_config, run_cell

REPS = 20
DURATION = 2000
WARMUP = 500
RATIOS = [7.0, 10.0]          # light load / heavy load (from the U load scan)
FEATURED = 'R10'
LAMBDAS = [0.5, 1.0, 2.0, 4.0, 8.0]

Q1_LABELS = ['25%', '40%', '55%', '70%', '85%']
Q2_LABELS = ['40%', '70%']


def build_cells():
    cells = []
    for lab in Q1_LABELS:
        beta = LABEL_BETAS[lab]
        for ratio in RATIOS:
            # U and O-* carry FEATURED as an observation target only (rf_share);
            # it does not enter their decisions (lambda = 0).
            cells.append(((lab, ratio, 'U', 0.0), make_config(ratio, beta, None)))
            cells.append(((lab, ratio, 'O-greedy', 0.0), make_config(ratio, beta, 'operational')))
            cells.append(((lab, ratio, 'O-aware', 0.0), make_config(ratio, beta, 'aware')))
    for lab in Q2_LABELS:
        beta = LABEL_BETAS[lab]
        for ratio in RATIOS:
            cells.append(((lab, ratio, 'F', None),
                          make_config(ratio, beta, 'featured', featured_id=FEATURED)))
            for lam in LAMBDAS:
                cells.append(((lab, ratio, 'Blend-aware', lam),
                              make_config(ratio, beta, 'aware', featured_id=FEATURED, lam=lam)))
                cells.append(((lab, ratio, 'Blend-greedy', lam),
                              make_config(ratio, beta, 'aware', featured_id=FEATURED, lam=lam,
                                          rule='greedy')))
    return cells


if __name__ == '__main__':
    cells = build_cells()
    print(f"{len(cells)} cells x {REPS} reps")
    t0 = time.time()
    args = [(key, cfg, FEATURED, REPS, DURATION, WARMUP) for key, cfg in cells]
    results = {}
    with Pool(2) as pool:
        for i, (key, summaries, dt) in enumerate(pool.starmap(run_cell, args, chunksize=1)):
            results[key] = summaries
    os.makedirs('results', exist_ok=True)
    with open('results/choice_aware_results.pkl', 'wb') as f:
        pickle.dump({'results': results, 'reps': REPS, 'duration': DURATION,
                     'warmup': WARMUP, 'featured': FEATURED}, f)
    print(f"done in {time.time() - t0:.0f}s")
