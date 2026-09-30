# calibration_step1_geography.py
"""
Step 1 of the calibration phase: the geography, as the choice model sees it.

The choice model never sees the map. It sees, for each customer, a list of
10 distances d(R, C). Everything computed later (P(nearest), beta, uplift,
mean leg, restaurant load shares) is a function of that distance matrix and
nothing else. This script builds the matrix and describes it, with no choice
model involved yet.

Terms used below
  catchment of R_j      : the part of the map where R_j is the nearest restaurant
                          (in geometry this region is called R_j's Voronoi cell)
  catchment share of R_j: fraction of the map's area inside that catchment; with
                          uniform customers it is also the fraction of customers
  gap                   : a customer's second-nearest distance minus nearest distance
"""

# %%
%load_ext autoreload 
%autoreload 2

# %% 0. Imports and constants
import sys
import os
# This file lives in <repo root>/study_scripts_new_20260930/, while the package
# delivery_sim/ lives in <repo root>/. Python only finds packages in folders on
# sys.path, so add the repo root: two dirname() steps up from this file.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import numpy as np
import matplotlib.pyplot as plt

from delivery_sim.simulation.configuration import StructuralConfig
from delivery_sim.infrastructure.infrastructure import Infrastructure
from delivery_sim.utils.location_utils import calculate_distance

AREA = 10.0      # km, side of the square service area
N_REST = 10
SEED = 42
GRID_N = 200     # customer grid is GRID_N x GRID_N cell midpoints


# %% 1. Restaurants
infra = Infrastructure(StructuralConfig(AREA, N_REST, 0.5), SEED)
restaurants = infra.get_restaurant_repository().find_all()
ids = [r.restaurant_id for r in restaurants]
R = np.array([r.location for r in restaurants])

# restaurant-to-restaurant distances: who has a close neighbour?
RR = np.linalg.norm(R[:, None, :] - R[None, :, :], axis=2)
np.fill_diagonal(RR, np.inf)

print("Restaurants")
print(f"  {'id':>4}  {'x':>5}  {'y':>5}  {'to edge':>7}  {'closest other':>15}")
for j, rid in enumerate(ids):
    x, y = R[j]
    edge = min(x, y, AREA - x, AREA - y)
    k = RR[j].argmin()
    print(f"  {rid:>4}  {x:5.2f}  {y:5.2f}  {edge:7.2f}  {ids[k]:>5} at {RR[j, k]:4.2f} km")


# %% 2. Customers
# Each grid point is the midpoint of a small square cell of equal area, so a
# plain average over grid points is an average over the service area. That
# matches the simulator, which draws customers uniform(0, AREA) in x and y.
centers = (np.arange(GRID_N) + 0.5) * AREA / GRID_N
gx, gy = np.meshgrid(centers, centers)
C = np.column_stack([gx.ravel(), gy.ravel()])


# %% 3. Distance matrix, D[customer, restaurant]
D = np.linalg.norm(C[:, None, :] - R[None, :, :], axis=2)

# Check it against the simulator's own distance function on sampled points.
check_rng = np.random.RandomState(0)
for c in check_rng.choice(len(C), 200, replace=False):
    for j, r in enumerate(restaurants):
        assert abs(D[c, j] - calculate_distance(r.location, C[c].tolist())) < 1e-9
print("\nDistance matrix agrees with calculate_distance on 200 sampled customers.")


# %% 4. Descriptors
D_sorted = np.sort(D, axis=1)
d_nearest = D_sorted[:, 0]            # leg if the customer always takes the nearest
d_second = D_sorted[:, 1]
gap = d_second - d_nearest            # how contested the nearest restaurant is
d_random = D.mean(axis=1)             # expected leg if the customer picks uniformly
nearest = D.argmin(axis=1)
share = np.bincount(nearest, minlength=N_REST) / len(C)   # catchment share
mean_dist_to = D.mean(axis=0)         # average customer's distance to each restaurant

print("\nCustomer-side distances (averaged over the map)")
print(f"  to nearest restaurant       {d_nearest.mean():.2f} km")
print(f"  to a random restaurant      {d_random.mean():.2f} km")
print(f"  nearest-vs-second gap       mean {gap.mean():.2f} km, "
      f"median {np.median(gap):.2f} km, share under 0.5 km {np.mean(gap < 0.5):.2f}")

print("\nPer restaurant")
print(f"  {'id':>4}  {'catchment share':>15}  {'mean customer distance':>22}")
for j, rid in enumerate(ids):
    print(f"  {rid:>4}  {share[j]:15.3f}  {mean_dist_to[j]:22.2f}")


# %% 5. Is the grid fine enough?
# A grid has no built-in error bar, so check it by refinement: recompute the
# same geometric summaries on a coarser and a finer grid. If they barely move,
# GRID_N is fine enough and the numbers above are not grid artifacts.
def geometry_summary(n):
    c = (np.arange(n) + 0.5) * AREA / n
    x, y = np.meshgrid(c, c)
    pts = np.column_stack([x.ravel(), y.ravel()])
    d = np.linalg.norm(pts[:, None, :] - R[None, :, :], axis=2)
    return d.min(axis=1).mean(), np.bincount(d.argmin(axis=1), minlength=N_REST) / len(pts)

base_near, base_share = geometry_summary(GRID_N)
print(f"\nGrid refinement check (reference: GRID_N = {GRID_N})")
for n in (GRID_N // 2, GRID_N * 2):
    near_n, share_n = geometry_summary(n)
    print(f"  GRID_N = {n:>3}: mean nearest distance differs by {abs(near_n - base_near):.5f} km, "
          f"largest catchment-share difference {np.abs(share_n - base_share).max():.5f}")


# %% 6. Plots
fig, ax = plt.subplots(2, 2, figsize=(12, 11))

a = ax[0, 0]
a.imshow(nearest.reshape(GRID_N, GRID_N), origin="lower", extent=[0, AREA, 0, AREA],
         cmap="tab10", alpha=0.45, interpolation="nearest")
a.scatter(R[:, 0], R[:, 1], c="k", s=25)
for j, rid in enumerate(ids):
    a.annotate(rid, R[j], xytext=(4, 4), textcoords="offset points", fontsize=10)
a.set_title("Catchments: which restaurant is nearest")
a.set_xlabel("km"); a.set_ylabel("km")

a = ax[0, 1]
im = a.imshow(gap.reshape(GRID_N, GRID_N), origin="lower", extent=[0, AREA, 0, AREA],
              cmap="viridis")
a.scatter(R[:, 0], R[:, 1], c="w", s=15)
fig.colorbar(im, ax=a, label="km")
a.set_title("Gap: second-nearest minus nearest distance")

a = ax[1, 0]
bins = np.linspace(0, 12, 49)
a.hist(d_nearest, bins=bins, alpha=0.6, density=True, label="to nearest")
a.hist(d_random, bins=bins, alpha=0.6, density=True, label="to random (mean over 10)")
a.set_title("Customer distance distributions")
a.set_xlabel("km"); a.legend()

a = ax[1, 1]
a.bar(ids, share)
a.axhline(1 / N_REST, ls="--", c="k", lw=1, label="1/N")
a.set_title("Catchment share per restaurant"); a.legend()

fig.tight_layout()
fig.savefig("step1_geography_seed42.png", dpi=130)
print("\nSaved step1_geography_seed42.png")
plt.show()