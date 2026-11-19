"""
Analysis of load_dependent_promotion_study.py.

For each ratio:
    x = extra R_F orders, pp of all orders (policy share - paired U share)
    y = fulfillment cost of promotion, min (policy - paired O-aware, i.e. lambda = 0)
The fixed-lambda arms trace the reference frontier. Each state-dependent arm is
compared with the frontier linearly interpolated at the arm's mean x, replication
by replication (same seeds), giving a paired difference with a 95% t-interval.
Negative difference = the state-dependent arm buys the same promotion more cheaply.
"""
import os
import pickle
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results')
blob = pickle.load(open(os.path.join(OUT, 'load_dependent_results.pkl'), 'rb'))
R = blob['results']

BLUE, ORANGE, INK, INK2, GRID = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 13, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': GRID, 'axes.edgecolor': INK2})


def arr(key, m):
    return np.array([s[m] for s in R[key]])


def ci(x):
    return x.mean(), stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))


ratios = sorted({k[0] for k in R})
lines = []
fig, axes = plt.subplots(1, len(ratios), figsize=(7 * len(ratios), 5.2))
for ax, ratio in zip(np.atleast_1d(axes), ratios):
    ku = (ratio, 'U', None, None)
    k0 = (ratio, 'fixed', 0.0, 0.0)
    u_share = arr(ku, 'rf_share')
    base = arr(k0, 'fulfil')
    base_assign = arr(k0, 'assign')

    def xy(key):
        return (arr(key, 'rf_share') - u_share) * 100, arr(key, 'fulfil') - base

    fixed = sorted([k for k in R if k[0] == ratio and k[1] == 'fixed'], key=lambda k: k[2])
    fx = np.array([xy(k)[0].mean() for k in fixed])
    fy_reps = np.array([xy(k)[1] for k in fixed])            # (n_fixed, reps)
    lines.append(f"\nratio {ratio:g}: O-aware fulfillment {base.mean():.2f} min, "
                 f"U R10 share {u_share.mean()*100:.1f}%, idle driver at arrival "
                 f"{arr(k0, 'imm_rate').mean()*100:.0f}% of orders")
    lines.append(f"  {'arm':<22}{'slot R10 slack/busy':>20}{'extra pp':>10}{'cost min':>16}"
                 f"{'frontier':>10}{'vs frontier (paired)':>24}{'d assign':>10}")
    for k, x_, yr in zip(fixed, fx, fy_reps):
        m, h = ci(yr)
        lines.append(f"  {'fixed λ=' + format(k[2], 'g'):<22}"
                     f"{arr(k, 'slot_rf_imm').mean()*100:>9.0f}% /{arr(k, 'slot_rf_q').mean()*100:>4.0f}%"
                     f"{x_:>+10.2f}{m:>+10.3f}±{h:.3f}")
    ax.errorbar(fx, fy_reps.mean(1), yerr=[ci(y)[1] for y in fy_reps], color=BLUE, lw=2.2,
                marker='o', capsize=3, label='Fixed λ (frontier)')

    for kind, col, mk, name in [('two_level', ORANGE, 's', 'Promote when slack'),
                                ('reverse', INK2, 'v', 'Promote when busy (check)')]:
        arms = sorted([k for k in R if k[0] == ratio and k[1] == kind], key=lambda k: (k[3], k[2]))
        xs, ys, hs = [], [], []
        for k in arms:
            x, y = xy(k)
            xm = x.mean()
            ym, yh = ci(y)
            da, dah = ci(arr(k, 'assign') - base_assign)
            if fx[0] <= xm <= fx[-1]:
                j = min(np.searchsorted(fx, xm), len(fx) - 1)
                j = max(j, 1)
                w = (xm - fx[j - 1]) / (fx[j] - fx[j - 1])
                y_front = fy_reps[j - 1] + w * (fy_reps[j] - fy_reps[j - 1])
                dm, dh = ci(y - y_front)
                comp = f"{dm:>+10.3f}±{dh:.3f}" + (' *' if abs(dm) > dh else '  ')
                front = f"{y_front.mean():>+10.3f}"
            else:
                comp, front = f"{'beyond fixed range':>24}", f"{'--':>10}"
            label = f"{kind} λ={k[2]:g}/{k[3]:g}"
            lines.append(f"  {label:<22}"
                         f"{arr(k, 'slot_rf_imm').mean()*100:>9.0f}% /{arr(k, 'slot_rf_q').mean()*100:>4.0f}%"
                         f"{xm:>+10.2f}{ym:>+10.3f}±{yh:.3f}{front}{comp:>24}{da:>+10.3f}")
            xs.append(xm); ys.append(ym); hs.append(yh)
        ax.errorbar(xs, ys, yerr=hs, fmt=mk, color=col, ms=8, capsize=3, label=name)
    ax.axhline(0, color=INK2, lw=0.8, ls='--')
    ax.set_title(f"Ratio {ratio:g}  (P(nearest) 40%, k = 2, R_F = R10)", loc='left', fontsize=13)
    ax.set_xlabel('Extra R10 orders (pp of all orders, vs. no curation)')
    ax.set_ylabel('Fulfillment cost of promotion (min, vs. λ = 0)')
    ax.legend(frameon=False, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'load_dependent_frontier.png'), dpi=180, facecolor='white')
lines.insert(0, "Load-dependent promotion: λ_slack (idle driver exists) / λ_busy (no idle driver)\n"
                "'vs frontier' = arm cost minus fixed-λ frontier at the same extra pp; "
                "negative = cheaper; * = 95% CI excludes 0")
text = '\n'.join(lines)
open(os.path.join(OUT, 'load_dependent_summary.txt'), 'w').write(text)
print(text)
