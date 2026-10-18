# calibration_step2_choice_probabilities.py
"""
Step 2 of the calibration phase: from distances to choice probabilities.

Step 1 built D, the customer x restaurant distance matrix. Here the choice
model is applied to D, with no boost yet (no curation):

    P_j(c) = exp(-beta * D[c, j]) / sum_k exp(-beta * D[c, k])

and everything that follows from it:
  - what probabilities look like for individual customers
  - the map-wide P(nearest) as a function of beta
  - inverting that function: which beta gives "X% pick their nearest"
  - what each beta implies: mean delivery leg and restaurant demand shares

Terms used below
  P(nearest)      : probability a customer picks their nearest restaurant;
                    "map-wide" means averaged over all customers on the grid
  behavioral label: a target value of map-wide P(nearest), e.g. "nearest-40%"
  mean leg        : expected restaurant-to-customer distance, averaged over the map
  demand share s_j: fraction of all orders that go to restaurant j
                    (the action plan wrote this as lambda_j; renamed here because
                    lambda conventionally means an arrival RATE)
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
from delivery_sim.utils.customer_choice_model import CustomerChoiceModel

AREA = 10.0
N_REST = 10
SEED = 42
GRID_N = 200
TARGETS = [0.10, 0.25, 0.40, 0.55, 0.70, 0.85]   # behavioral labels for the beta sweep


# %% 1. Layout, customer grid, distance matrix (same as step 1)
infra = Infrastructure(StructuralConfig(AREA, N_REST, 0.5), SEED)
restaurants = infra.get_restaurant_repository().find_all()
ids = [r.restaurant_id for r in restaurants]
R = np.array([r.location for r in restaurants])


def build_grid(n):
    centers = (np.arange(n) + 0.5) * AREA / n
    gx, gy = np.meshgrid(centers, centers)
    return np.column_stack([gx.ravel(), gy.ravel()])


def distance_matrix(C):
    return np.linalg.norm(C[:, None, :] - R[None, :, :], axis=2)


C = build_grid(GRID_N)
D = distance_matrix(C)
nearest = D.argmin(axis=1)
catchment_share = np.bincount(nearest, minlength=N_REST) / len(C)
print(f"Grid: {len(C)} customers x {N_REST} restaurants")


# %% 2. Choice probabilities for every customer at once
def choice_probs(D, beta, boost_col=None, b=0.0):
    """
    Softmax over each row of D. Returns a matrix the same shape as D whose
    row c is customer c's probability of choosing each restaurant.

    boost_col is the column index of the slotted restaurant (None = no slot).
    Not used in this step; included so the check in cell 3 covers it too.
    """
    U = -beta * D                       # utility of each restaurant for each customer
    if boost_col is not None:
        U = U.copy()
        U[:, boost_col] += b
    U = U - U.max(axis=1, keepdims=True)    # stops exp() under/overflowing; cancels below
    W = np.exp(U)
    return W / W.sum(axis=1, keepdims=True)


# %% 3. Check: is this the simulator's own choice model?
# CustomerChoiceModel.choice_probabilities is what the simulation calls on every
# order. It consumes no randomness, so selection_stream can be None here.
check_rng = np.random.RandomState(0)
sample = check_rng.choice(len(C), 300, replace=False)
worst = 0.0
for beta in (0.0, 0.5737, 3.6442):
    for boost_id, b in ((None, 0.0), ("R10", np.log(2))):
        model = CustomerChoiceModel(beta, b, None)
        col = None if boost_id is None else ids.index(boost_id)
        P = choice_probs(D[sample], beta, col, b)
        for i, c in enumerate(sample):
            sim = model.choice_probabilities(C[c].tolist(), restaurants, boost_id)
            worst = max(worst, np.abs(P[i] - np.array(sim)).max())
assert worst < 1e-12, worst
print(f"choice_probs matches CustomerChoiceModel (largest difference {worst:.1e})")


# %% 4. Anatomy: four individual customers
# Hand-picked to show different situations:
#   A deep inside R7's catchment, nearest is far ahead of the rest (large gap)
#   B on the R9 / R10 boundary, two restaurants almost tied (gap ~ 0)
#   C in the R3 / R8 corner, a near-duplicate pair (gap capped at 0.38 km)
#   D next to R6, but R4 is almost as close (the shadowing pair)
examples = {"A": [8.8, 1.2], "B": [3.7, 4.1], "C": [1.2, 1.2], "D": [0.4, 9.2]}
show_betas = [0.0, 0.3, 0.6, 1.0, 1.6, 3.6]

for name, loc in examples.items():
    d = distance_matrix(np.array([loc]))[0]
    order = np.argsort(d)
    j1, j2 = order[0], order[1]
    gap = d[j2] - d[j1]
    print(f"\nCustomer {name} at {loc}: nearest {ids[j1]} {d[j1]:.2f} km, "
          f"second {ids[j2]} {d[j2]:.2f} km, gap {gap:.2f} km")
    print(f"  {'beta':>5}  {'P(nearest)':>10}  {'P(second)':>9}  {'P(other 8)':>10}"
          f"  {'P1/P2':>6}  {'exp(beta*gap)':>13}")
    for beta in show_betas:
        p = choice_probs(d[None, :], beta)[0]
        print(f"  {beta:5.1f}  {p[j1]:10.3f}  {p[j2]:9.3f}  {1 - p[j1] - p[j2]:10.3f}"
              f"  {p[j1] / p[j2]:6.3g}  {np.exp(beta * gap):13.3g}")
# The last two columns are always equal: the odds between any two restaurants
# depend only on their distance difference, never on the other restaurants.


# %% 5. Map-wide P(nearest) as a function of beta
def p_nearest_map(D, nearest, beta):
    P = choice_probs(D, beta)
    return P[np.arange(len(D)), nearest].mean()


beta_curve = np.linspace(0, 6, 121)
pn_curve = np.array([p_nearest_map(D, nearest, be) for be in beta_curve])

# For every single customer, P(nearest) = 1 / (1 + sum over others of
# exp(-beta * (d_other - d_nearest))), and each term shrinks as beta grows.
# So P(nearest) rises with beta for every customer, and so does its average.
assert np.all(np.diff(pn_curve) > 0)
print(f"\nMap-wide P(nearest): {pn_curve[0]:.3f} at beta = 0, "
      f"{pn_curve[-1]:.3f} at beta = {beta_curve[-1]:.0f}; strictly increasing")


# %% 6. Inversion: which beta gives each behavioral label?
def invert(D, nearest, target, lo=0.0, hi=50.0, iters=100):
    """
    Bisection. P(nearest) rises with beta (cell 5), so if P at the midpoint is
    below target the answer is above the midpoint, otherwise below. Each step
    halves the bracket; 100 steps is far beyond float precision.
    """
    for _ in range(iters):
        mid = (lo + hi) / 2
        if p_nearest_map(D, nearest, mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# At beta = 0 every restaurant has probability 1/N, so P(nearest) is exactly
# 1/N = 0.10. The first label needs no search.
assert abs(p_nearest_map(D, nearest, 0.0) - 1 / N_REST) < 1e-12
betas = {0.10: 0.0}
for t in TARGETS[1:]:
    betas[t] = invert(D, nearest, t)

# Grid refinement: same beta, coarser and finer grid; P(nearest) should barely move.
refine = {}
for n in (GRID_N // 2, GRID_N * 2):
    Dn = distance_matrix(build_grid(n))
    refine[n] = [p_nearest_map(Dn, Dn.argmin(axis=1), be) for be in betas.values()]

print("\nBehavioral label -> beta")
print(f"  {'label':>12}  {'beta (1/km)':>11}  {'P(nearest) on grid':>18}"
      f"  {'diff at N=100':>13}  {'diff at N=400':>13}")
for i, (t, be) in enumerate(betas.items()):
    pn = p_nearest_map(D, nearest, be)
    print(f"  {'nearest-' + str(int(round(t * 100))) + '%':>12}  {be:11.4f}  {pn:18.6f}"
          f"  {abs(refine[GRID_N // 2][i] - pn):13.1e}  {abs(refine[GRID_N * 2][i] - pn):13.1e}")


# %% 7. What each label implies: mean leg and demand shares
d_nearest_mean = D.min(axis=1).mean()      # beta = infinity limit of the mean leg
d_random_mean = D.mean()                    # beta = 0 value of the mean leg


def mean_leg(D, beta):
    return (choice_probs(D, beta) * D).sum(axis=1).mean()


def demand_shares(D, beta):
    return choice_probs(D, beta).mean(axis=0)


leg_curve = np.array([mean_leg(D, be) for be in beta_curve])
share_curve = np.array([demand_shares(D, be) for be in beta_curve])

print(f"\nMean leg: {d_random_mean:.2f} km at beta = 0, falls toward {d_nearest_mean:.2f} km")
print(f"  {'label':>12}  {'mean leg':>8}  " + "  ".join(f"{rid:>5}" for rid in ids))
for t, be in betas.items():
    s = demand_shares(D, be)
    print(f"  {'nearest-' + str(int(round(t * 100))) + '%':>12}  {mean_leg(D, be):8.2f}  "
          + "  ".join(f"{x:5.3f}" for x in s))
print(f"  {'catchment':>12}  {d_nearest_mean:8.2f}  "
      + "  ".join(f"{x:5.3f}" for x in catchment_share))


# %% 8. Plots
fig, ax = plt.subplots(2, 2, figsize=(13, 11))
label_betas = [be for t, be in betas.items() if t > 0.10]

a = ax[0, 0]
a.plot(beta_curve, pn_curve, c="k")
for t, be in betas.items():
    a.plot(be, t, "o", c="tab:red")
    a.annotate(f"{int(round(t * 100))}%", (be, t), xytext=(6, -10), textcoords="offset points")
a.axhline(1 / N_REST, ls="--", c="grey", lw=1)
a.set_xlabel("beta (1/km)"); a.set_ylabel("map-wide P(nearest)")
a.set_title("P(nearest) vs beta, with the behavioral labels")

a = ax[0, 1]
be_show = betas[0.40]
P = choice_probs(D, be_show)
pn_map = P[np.arange(len(C)), nearest].reshape(GRID_N, GRID_N)
im = a.imshow(pn_map, origin="lower", extent=[0, AREA, 0, AREA], cmap="magma", vmin=0, vmax=1)
a.scatter(R[:, 0], R[:, 1], c="w", s=15)
fig.colorbar(im, ax=a, label="P(nearest)")
a.set_title(f"Each customer's P(nearest) at nearest-40% (beta = {be_show:.2f})")

a = ax[1, 0]
a.plot(beta_curve, leg_curve, c="k")
a.axhline(d_random_mean, ls="--", c="grey", lw=1, label="beta = 0 (random restaurant)")
a.axhline(d_nearest_mean, ls=":", c="grey", lw=1, label="beta = inf (nearest restaurant)")
for be in label_betas:
    a.axvline(be, c="tab:red", lw=0.6, alpha=0.5)
a.set_xlabel("beta (1/km)"); a.set_ylabel("km")
a.set_title("Mean restaurant-to-customer leg"); a.legend()

a = ax[1, 1]
for j, rid in enumerate(ids):
    line, = a.plot(beta_curve, share_curve[:, j], label=rid)
    a.plot(beta_curve[-1] + 0.15, catchment_share[j], "<", c=line.get_color())
for be in label_betas:
    a.axvline(be, c="tab:red", lw=0.6, alpha=0.5)
a.axhline(1 / N_REST, ls="--", c="grey", lw=1)
a.set_xlabel("beta (1/km)"); a.set_ylabel("demand share")
a.set_title("Demand shares s_j(beta); arrows = catchment shares (beta = inf)")
a.legend(ncol=2, fontsize=8, loc="lower right", bbox_to_anchor=(1, 0.06))

fig.tight_layout()
fig.savefig("step2_choice_probabilities_seed42.png", dpi=130)
print("\nSaved step2_choice_probabilities_seed42.png")
plt.show()