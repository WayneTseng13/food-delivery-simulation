"""
Analysis of choice_aware_curation_study.py results.

Q1 table : per (beta label, ratio), policy means and the paired difference
           O-aware minus O-greedy with a 95% t-interval over replications.
Q2 plot  : promotion frontier. x = incremental R_F share (policy minus paired U),
           y = mean fulfillment time; Blend-aware vs Blend-greedy over lambda,
           with F and the lambda = 0 points marked.
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

import sys
SUFFIX = sys.argv[1] if len(sys.argv) > 1 else ''      # e.g. '_k5'
with open(os.path.join(OUT, f'choice_aware_results{SUFFIX}.pkl'), 'rb') as f:
    blob = pickle.load(f)
R = blob['results']


def arr(key, metric):
    return np.array([s[metric] for s in R[key]])


def mean_ci(x):
    x = x[~np.isnan(x)]
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), h


def paired(key_a, key_b, metric):
    return mean_ci(arr(key_a, metric) - arr(key_b, metric))


# ---------------- Q1 ----------------
labels = sorted({k[0] for k in R if k[2] == 'O-aware'}, key=lambda s: int(s[:-1]))
ratios = sorted({k[1] for k in R})
metrics = [('assign', 'Wait to assignment (min)'), ('fulfil', 'Fulfillment (min)'),
           ('leg_km', 'R-C leg (km)'), ('pickup', 'Pickup travel (min)')]

lines = []
lines.append("Q1: O-aware vs O-greedy (paired diff = aware - greedy, mean ± 95% CI half-width, 20 reps)")
hdr = (f"{'beta':>5} {'ratio':>5} | {'U fulfil':>8} {'greedy':>7} {'aware':>7} | "
       f"{'d_fulfil':>14} {'d_assign':>14} {'d_pickup':>14} {'d_leg_km':>14} | "
       f"{'imm':>5} {'agree_imm':>9}")
lines.append(hdr)
lines.append('-' * len(hdr))
q1_rows = []
for ratio in ratios:
    for lab in labels:
        ku, kg, ka = (lab, ratio, 'U', 0.0), (lab, ratio, 'O-greedy', 0.0), (lab, ratio, 'O-aware', 0.0)
        row = dict(label=lab, ratio=ratio)
        for m, _ in metrics:
            row[m + '_U'] = arr(ku, m).mean()
            row[m + '_G'] = arr(kg, m).mean()
            row[m + '_A'] = arr(ka, m).mean()
            row['d_' + m], row['h_' + m] = paired(ka, kg, m)
            row['dU_' + m], row['hU_' + m] = paired(kg, ku, m)
        row['imm'] = arr(ka, 'imm_rate').mean()
        row['agree_imm'] = arr(ka, 'agree_imm').mean()
        q1_rows.append(row)
        f = lambda m: f"{row['d_'+m]:+7.3f}±{row['h_'+m]:.3f}"
        lines.append(f"{lab:>5} {ratio:>5.0f} | {row['fulfil_U']:8.2f} {row['fulfil_G']:7.2f} {row['fulfil_A']:7.2f} | "
                     f"{f('fulfil'):>14} {f('assign'):>14} {f('pickup'):>14} {f('leg_km'):>14} | "
                     f"{row['imm']:5.2f} {row['agree_imm']:9.2f}")
    lines.append('-' * len(hdr))

lines.append("")
lines.append("Q1b: O-greedy vs U (paired diff = greedy - U)")
for r in q1_rows:
    lines.append(f"{r['label']:>5} {r['ratio']:>5.0f} | d_fulfil {r['dU_fulfil']:+7.3f}±{r['hU_fulfil']:.3f}  "
                 f"d_assign {r['dU_assign']:+7.3f}±{r['hU_assign']:.3f}  d_leg {r['dU_leg_km']:+7.3f}±{r['hU_leg_km']:.3f}")

# Q1 figure: fulfillment by beta, three policies, two loads
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=False)
for ax, ratio in zip(axes, ratios):
    rows = [r for r in q1_rows if r['ratio'] == ratio]
    x = np.arange(len(rows))
    for pol, col, lab in [('U', '#9aa0a6', 'U (no curation)'), ('G', '#1f77b4', 'O-greedy'),
                          ('A', '#d62728', 'O-aware (ΔV)')]:
        ax.plot(x, [r['fulfil_' + pol] for r in rows], 'o-', color=col, label=lab)
    ax.set_xticks(x, [r['label'] for r in rows])
    ax.set_xlabel('Customer behavior: P(choose nearest) under no curation')
    ax.set_ylabel('Mean fulfillment time (min)')
    ax.set_title(f"{'Light' if ratio == ratios[0] else 'Heavy'} load (ratio {ratio:.0f})")
    ax.grid(alpha=0.3)
axes[0].legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT, f'q1_fulfillment_by_beta{SUFFIX}.png'), dpi=160)

# Q1 figure: paired difference aware - greedy with CI
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, (m, title) in zip(axes, [('fulfil', 'Fulfillment time (min)'), ('leg_km', 'R-C leg (km)')]):
    for i, (ratio, col) in enumerate(zip(ratios, ['#2ca02c', '#9467bd'])):
        rows = [r for r in q1_rows if r['ratio'] == ratio]
        x = np.arange(len(rows)) + (i - 0.5) * 0.15
        ax.errorbar(x, [r['d_' + m] for r in rows], yerr=[r['h_' + m] for r in rows],
                    fmt='o', color=col, capsize=4, label=f"ratio {ratio:.0f}")
    ax.axhline(0, color='k', lw=0.8)
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.set_xlabel('Customer behavior: P(choose nearest)')
    ax.set_title(f"O-aware − O-greedy: {title}\n(below 0 = aware better; 95% CI)")
    ax.grid(alpha=0.3)
axes[0].legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT, f'q1_paired_diff{SUFFIX}.png'), dpi=160)

# ---------------- Q2 ----------------
q2_labels = sorted({k[0] for k in R if k[2] == 'Blend-aware'}, key=lambda s: int(s[:-1]))
lams = sorted({k[3] for k in R if k[2] == 'Blend-aware'})
lines.append("")
lines.append(f"Q2: promotion frontier, R_F = {blob['featured']}, k = {blob.get('k', 2.0):g}")
lines.append("  incr = R_F share minus paired U share (pp of all orders); d_fulfil = vs paired U (min)")
fig, axes = plt.subplots(len(q2_labels), len(ratios), figsize=(11, 4.2 * len(q2_labels)))
axes = np.atleast_2d(axes)
for i, lab in enumerate(q2_labels):
    for j, ratio in enumerate(ratios):
        ax = axes[i, j]
        ku = (lab, ratio, 'U', 0.0)
        u_share = arr(ku, 'rf_share')
        lines.append(f"  beta {lab}, ratio {ratio:.0f}: U R_F share {u_share.mean()*100:.1f}%, "
                     f"U fulfil {arr(ku, 'fulfil').mean():.2f}")
        for pol, col, k0 in [('Blend-aware', '#d62728', 'O-aware'), ('Blend-greedy', '#1f77b4', 'O-greedy')]:
            xs, ys, xh, yh = [], [], [], []
            for lam in [0.0] + lams:
                key = (lab, ratio, k0, 0.0) if lam == 0.0 else (lab, ratio, pol, lam)
                dx, hx = mean_ci((arr(key, 'rf_share') - u_share) * 100)
                dy, hy = paired(key, ku, 'fulfil')
                xs.append(dx); ys.append(dy); xh.append(hx); yh.append(hy)
                slot = arr(key, 'slot_rf').mean() if lam > 0 else 0.0
                lines.append(f"    {pol:>12} lam={lam:4.1f}: slot R_F {slot*100:5.1f}%  incr {dx:+5.2f}±{hx:.2f}pp  "
                             f"d_fulfil {dy:+6.3f}±{hy:.3f}  d_leg {paired(key, ku, 'leg_km')[0]:+6.3f}")
            ax.errorbar(xs, ys, xerr=xh, yerr=yh, fmt='o-', color=col, capsize=3, label=pol)
            for x, y, lam in zip(xs, ys, [0.0] + lams):
                ax.annotate(f"λ={lam:g}", (x, y), textcoords='offset points', xytext=(4, -10),
                            fontsize=7, color=col)
        kf = (lab, ratio, 'F', None)
        dx, hx = mean_ci((arr(kf, 'rf_share') - u_share) * 100)
        dy, hy = paired(kf, ku, 'fulfil')
        lines.append(f"    {'F':>12}          slot R_F 100.0%  incr {dx:+5.2f}±{hx:.2f}pp  d_fulfil {dy:+6.3f}±{hy:.3f}  "
                     f"d_leg {paired(kf, ku, 'leg_km')[0]:+6.3f}")
        ax.errorbar([dx], [dy], xerr=[hx], yerr=[hy], fmt='s', color='k', capsize=3, label='F (R_F for all)')
        ax.axhline(0, color='gray', lw=0.8, ls='--')
        ax.set_xlabel('Incremental R_F orders (pp of all orders, vs U)')
        ax.set_ylabel('Fulfillment time vs U (min)')
        ax.set_title(f"P(nearest) {lab}, {'light' if ratio == ratios[0] else 'heavy'} load (ratio {ratio:.0f})")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, f'q2_frontier{SUFFIX}.png'), dpi=160)

text = '\n'.join(lines)
with open(os.path.join(OUT, f'choice_aware_summary{SUFFIX}.txt'), 'w') as f:
    f.write(text)
print(text)
