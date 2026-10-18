# calibration_step3_boost.py
"""
Step 3 of the calibration phase: the recommendation boost b.

The slotted restaurant gets +b added to its utility, which multiplies its odds
against every other restaurant by k = exp(b). The baseline is k = 2.

Questions answered here:
  - how much does a boost move one customer, and why (cell 3)
  - featured curation: boost the same restaurant R_F for everyone. For each
    possible R_F: how many orders move, and does that cost or save distance (cells 4-5)
  - boost each customer's NEAREST restaurant: this is exactly what the
    operational policy does when no driver is idle (its "queued" branch), so it
    is the offline part of operational curation (cell 6)
  - how the results change with k (cell 7)

The operational policy's other branch (an idle driver exists) depends on driver
positions, which are not in D, so it can only be studied in the simulation.

Terms used below
  baseline share  : restaurant's demand share with no boost (step 2's s_j)
  featured share  : its demand share when it holds the slot for every customer
                    (= the "compliance" the simulation should reproduce)
  uplift          : featured share - baseline share = fraction of ALL orders the
                    boost moves to the slotted restaurant ("redirected orders")
  leg change      : change in the mean restaurant-to-customer leg, km per order
  km per redirect : leg change / uplift = extra km per redirected order
                    (negative = the boost SAVES distance)
"""

# %% 0. Imports and constants
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np
import matplotlib.pyplot as plt

from delivery_sim.simulation.configuration import StructuralConfig
from delivery_sim.infrastructure.infrastructure import Infrastructure

AREA = 10.0
N_REST = 10
SEED = 42
GRID_N = 200
K_BASE = 2.0
K_GRID = [1.5, 2.0, 4.0, 9.0]

# beta for each behavioral label, from step 2 (cell 6 there)
LABEL_BETAS = {"10%": 0.0, "25%": 0.3013, "40%": 0.5737,
               "55%": 0.9358, "70%": 1.5944, "85%": 3.6442}


# %% 1. Layout, grid, D (same as steps 1 and 2)
infra = Infrastructure(StructuralConfig(AREA, N_REST, 0.5), SEED)
restaurants = infra.get_restaurant_repository().find_all()
ids = [r.restaurant_id for r in restaurants]
R = np.array([r.location for r in restaurants])

centers = (np.arange(GRID_N) + 0.5) * AREA / GRID_N
gx, gy = np.meshgrid(centers, centers)
C = np.column_stack([gx.ravel(), gy.ravel()])
D = np.linalg.norm(C[:, None, :] - R[None, :, :], axis=2)
nearest = D.argmin(axis=1)
rows = np.arange(len(C))


# %% 2. Choice probabilities (same function as step 2, now with the boost used)
def choice_probs(D, beta, boost_col=None, b=0.0):
    """
    boost_col: None (no slot), one column index (same restaurant for every
    customer = featured), or an array with one column index per customer
    (a different restaurant per customer, e.g. each one's nearest).
    """
    U = -beta * D
    if boost_col is not None:
        U = U.copy()
        if np.ndim(boost_col) == 0:
            U[:, boost_col] += b
        else:
            U[np.arange(len(D)), boost_col] += b
    U = U - U.max(axis=1, keepdims=True)
    W = np.exp(U)
    return W / W.sum(axis=1, keepdims=True)


# %% 3. One customer: what a boost does
# Adding b to one restaurant's utility multiplies its weight by k = exp(b);
# everyone else's weight is unchanged. If its probability without the boost
# was P, then with the boost it becomes
#     P_boosted = k P / (1 + (k - 1) P)
# so the uplift for that customer is
#     P_boosted - P = (k - 1) P (1 - P) / (1 + (k - 1) P)
# The uplift depends ONLY on P and k: not on distances, beta, or the other
# restaurants directly. They matter only through P.
# It is zero at P = 0 (nobody to move) and at P = 1 (already chosen), and is
# largest at P* = 1 / (1 + sqrt(k)).


def uplift_formula(P, k):
    return (k - 1) * P * (1 - P) / (1 + (k - 1) * P)


# Check the formula against direct computation for every customer on the grid.
beta = LABEL_BETAS["40%"]
P0 = choice_probs(D, beta)
worst = 0.0
for k in K_GRID:
    for j in range(N_REST):
        P1 = choice_probs(D, beta, j, np.log(k))
        worst = max(worst, np.abs((P1[:, j] - P0[:, j]) - uplift_formula(P0[:, j], k)).max())
assert worst < 1e-12, worst
print(f"Uplift formula matches direct computation on the grid (largest difference {worst:.1e})")

print("\nPer-customer uplift by baseline probability P")
grid_P = [0.02, 0.1, 0.2, 0.3, 0.414, 0.5, 0.7, 0.9]
print(f"  {'k':>4}  {'peak at P*':>10}  " + "  ".join(f"P={p:<5}" for p in grid_P))
for k in K_GRID:
    print(f"  {k:4.1f}  {1 / (1 + np.sqrt(k)):10.3f}  "
          + "  ".join(f"{uplift_formula(p, k):7.3f}" for p in grid_P))


# %% 4. Featured curation: every restaurant as R_F, every label
def featured_effects(D, beta, j, k):
    """Effects of putting restaurant j in the slot for every customer."""
    P0 = choice_probs(D, beta)
    P1 = choice_probs(D, beta, j, np.log(k))
    base = P0[:, j].mean()
    feat = P1[:, j].mean()
    leg0 = (P0 * D).sum(axis=1)          # each customer's expected leg, no boost
    leg1 = (P1 * D).sum(axis=1)          # ... with the boost
    up_c = P1[:, j] - P0[:, j]           # each customer's uplift
    dleg_c = leg1 - leg0                 # each customer's leg change
    inside = nearest == j                # customers in j's own catchment
    return {
        "base": base, "feat": feat, "uplift": feat - base,
        "dleg": dleg_c.mean(),
        "km_per": dleg_c.mean() / (feat - base),
        # decomposition by where the redirected orders come from
        # (averaged over ALL customers, so inside + outside = total)
        "up_in": (up_c * inside).mean(), "up_out": (up_c * ~inside).mean(),
        "dleg_in": (dleg_c * inside).mean(), "dleg_out": (dleg_c * ~inside).mean(),
    }


FE = {lab: [featured_effects(D, be, j, K_BASE) for j in range(N_REST)]
      for lab, be in LABEL_BETAS.items()}

print(f"\nFeatured curation, k = {K_BASE:g}: share without -> with the slot (uplift)")
print(f"  {'R_F':>4}  " + "  ".join(f"{lab:>19}" for lab in LABEL_BETAS))
for j, rid in enumerate(ids):
    print(f"  {rid:>4}  " + "  ".join(
        f"{FE[lab][j]['base']:.3f}->{FE[lab][j]['feat']:.3f} ({FE[lab][j]['uplift']:.3f})"
        for lab in LABEL_BETAS))

print(f"\nFeatured curation, k = {K_BASE:g}: extra km per redirected order (negative = saves distance)")
print(f"  {'R_F':>4}  {'catchment':>9}  " + "  ".join(f"{lab:>6}" for lab in LABEL_BETAS))
catchment_share = np.bincount(nearest, minlength=N_REST) / len(C)
for j, rid in enumerate(ids):
    print(f"  {rid:>4}  {catchment_share[j]:9.3f}  "
          + "  ".join(f"{FE[lab][j]['km_per']:+6.2f}" for lab in LABEL_BETAS))


# %% 5. Why the sign differs: where redirected orders come from (at nearest-40%)
# Redirected customers who live INSIDE R_F's catchment are pulled to their own
# nearest restaurant: their leg gets shorter. Those OUTSIDE are pulled away from
# a closer restaurant: their leg gets longer. The net sign depends on the mix.
lab = "40%"
print(f"\nWhere R_F's redirected orders come from, at nearest-{lab}, k = {K_BASE:g}")
print(f"  {'R_F':>4}  {'uplift':>6}  {'share from inside':>17}  "
      f"{'km/redirect inside':>18}  {'km/redirect outside':>19}  {'net':>6}")
for j, rid in enumerate(ids):
    e = FE[lab][j]
    print(f"  {rid:>4}  {e['uplift']:6.3f}  {e['up_in'] / e['uplift']:17.2f}  "
          f"{e['dleg_in'] / e['up_in']:+18.2f}  {e['dleg_out'] / e['up_out']:+19.2f}  "
          f"{e['km_per']:+6.2f}")


# %% 6. Boost each customer's nearest (operational policy, queued branch)
def boost_nearest_effects(D, beta, k):
    P0 = choice_probs(D, beta)
    P1 = choice_probs(D, beta, nearest, np.log(k))
    uplift = (P1[rows, nearest] - P0[rows, nearest]).mean()
    dleg = ((P1 - P0) * D).sum(axis=1).mean()
    return uplift, dleg


print(f"\nBoost each customer's nearest, k = {K_BASE:g}")
print(f"  {'label':>6}  {'P(nearest) -> boosted':>21}  {'uplift':>6}  {'leg change km':>13}")
for lab, be in LABEL_BETAS.items():
    up, dleg = boost_nearest_effects(D, be, K_BASE)
    pn = choice_probs(D, be)[rows, nearest].mean()
    print(f"  {lab:>6}  {pn:10.3f} -> {pn + up:.3f}  {up:6.3f}  {dleg:+13.3f}")


# %% 7. Sensitivity to k
print("\nBoost-nearest uplift by k (largest per row marked *)")
print(f"  {'k':>4}  " + "  ".join(f"{lab:>6}" for lab in LABEL_BETAS))
for k in K_GRID:
    ups = [boost_nearest_effects(D, be, k)[0] for be in LABEL_BETAS.values()]
    top = int(np.argmax(ups))
    print(f"  {k:4.1f}  " + "  ".join(
        f"{u:5.3f}{'*' if i == top else ' '}" for i, u in enumerate(ups)))

print("\nFeatured km per redirected order at nearest-40%, by k")
print(f"  {'R_F':>4}  " + "  ".join(f"k={k:<4g}" for k in K_GRID))
for j, rid in enumerate(ids):
    print(f"  {rid:>4}  " + "  ".join(
        f"{featured_effects(D, LABEL_BETAS['40%'], j, k)['km_per']:+6.2f}" for k in K_GRID))


# %% 8. Plots
beta_curve = np.linspace(0, 4, 81)
fig, ax = plt.subplots(2, 2, figsize=(13, 11))

a = ax[0, 0]
p = np.linspace(0, 1, 201)
for k in K_GRID:
    line, = a.plot(p, uplift_formula(p, k), label=f"k = {k:g}")
    ps = 1 / (1 + np.sqrt(k))
    a.plot(ps, uplift_formula(ps, k), "o", c=line.get_color())
a.set_xlabel("customer's probability of the slotted restaurant, no boost (P)")
a.set_ylabel("uplift for that customer")
a.set_title("One customer: uplift vs P (dots = peak P*)"); a.legend()

a = ax[0, 1]
for j, rid in enumerate(ids):
    a.plot(beta_curve, [featured_effects(D, be, j, K_BASE)["uplift"] for be in beta_curve], label=rid)
for be in list(LABEL_BETAS.values())[1:]:
    a.axvline(be, c="tab:red", lw=0.6, alpha=0.5)
a.set_xlabel("beta (1/km)"); a.set_ylabel("uplift (fraction of all orders)")
a.set_title(f"Featured uplift for each R_F, k = {K_BASE:g}"); a.legend(ncol=2, fontsize=8)

a = ax[1, 0]
for j, rid in enumerate(ids):
    a.plot(beta_curve, [featured_effects(D, be, j, K_BASE)["km_per"] for be in beta_curve], label=rid)
for be in list(LABEL_BETAS.values())[1:]:
    a.axvline(be, c="tab:red", lw=0.6, alpha=0.5)
a.axhline(0, c="k", lw=1)
a.set_xlabel("beta (1/km)"); a.set_ylabel("km")
a.set_title("Featured: extra km per redirected order (below 0 = saves distance)")
a.legend(ncol=2, fontsize=8)

a = ax[1, 1]
for k in K_GRID:
    a.plot(beta_curve, [boost_nearest_effects(D, be, k)[0] for be in beta_curve], label=f"k = {k:g}")
for be in list(LABEL_BETAS.values())[1:]:
    a.axvline(be, c="tab:red", lw=0.6, alpha=0.5)
a.set_xlabel("beta (1/km)"); a.set_ylabel("uplift (fraction of all orders)")
a.set_title("Boost each customer's nearest: uplift by k"); a.legend()

fig.tight_layout()
fig.savefig("step3_boost_seed42.png", dpi=130)
print("\nSaved step3_boost_seed42.png")
plt.show()