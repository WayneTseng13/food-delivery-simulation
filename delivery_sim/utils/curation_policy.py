"""
Curation policies for restaurant recommendation at order-arrival time.

The OrderArrivalService calls a curation policy's select(customer_location) to
obtain a restaurant recommendation, which the customer then accepts or rejects
according to their choice model.

Policy U (no curation) is NOT a class here. It is represented by
config.curation_policy is None, handled directly in OrderArrivalService: no
recommendation is produced (no restaurant is slotted).

This module was reduced for the featuring chapter. The earlier state-adaptive
family (X', X'') with the edge-manufacture branch lives on a previous git branch;
that investigation concluded edge-manufacture adds no operational value, so the
pure-operational policy survives here only as single_immediate + single_queued,
which is exactly CurationPolicy in 'operational' mode.

The blend(tau) mode was retired with the move to an explicit customer choice
model. Under that model the customer applies their own proximity gate to any
recommendation (compliance is endogenous and distance-dependent), so a
platform-side tau tolerance on operational currency no longer has independent
meaning: far featured restaurants are declined by the customer's own preference,
and the residual operational cost of featuring is an externality to MEASURE (the
penalty below), not a threshold to SET. What survives is a single binary choice
of which restaurant, if any, gets the recommendation slot.

The single policy class covers two modes, set explicitly by
config.curation_policy (NOT inferred from parameter values):

    'operational'  Always recommend the operational optimum R_op
                   (single_immediate + single_queued). featured_restaurant_id is
                   ignored.
    'featured'     Policy F. Always recommend the featured restaurant R_F.

'featured' requires featured_restaurant_id; a missing one is an error, not a
silent fallback to operational mode.
"""

from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger


class CurationPolicy:
    """
    Operational or business (featured) curation over an optional single featured
    restaurant R_F.

    Operational optimum R_op (state-dependent)
    ------------------------------------------
        single_immediate (>=1 idle driver):  R_op = argmin (R-D + R-C)
        single_queued    (no idle driver):   R_op = argmin R-C = R_nearest

    where R-D is distance to the nearest idle driver and R-C is the delivery leg.
    These two rules are the surviving X'' policy verbatim.

    Featuring penalty (the operational externality of featuring)
    ------------------------------------------------------------
        c(R) = d(R, nearest idle driver) + d(R, C)   if an idle driver exists
        c(R) = d(R, C)                               otherwise

        penalty = c(R_F) - c(R_op)   >= 0 by construction (R_op = argmin c)

    This is the extra knowable operational travel the shared fleet absorbs when
    the platform places R_F instead of the operational optimum. It is measured
    and stamped on every featured arrival, but it does NOT gate the
    recommendation -- featured mode always recommends R_F. Whether a given
    customer actually TAKES R_F is decided downstream by the customer's own
    choice model (proximity-sensitive compliance), not by any platform-side
    tolerance. penalty is in the state-dependent operational currency, NOT the
    R-C detour d(R_F,C) - d(R_nearest,C): in the immediate branch R_op need not
    be R_nearest (they coincide only when the R-C optimum also wins once R-D is
    added), so that detour can go negative and is unsafe as a cost benchmark.

    Mode
    ----
    self.mode in {'operational', 'featured'} comes straight from
    config.curation_policy. Intent is explicit, not inferred from whether a
    featured id happens to be set. 'operational' ignores featuring entirely and
    slots R_op; 'featured' always slots R_F. (Policy U -- no slot at all -- is
    config.curation_policy is None, handled in OrderArrivalService, not here.)

    Queue-blindness
    ---------------
    Reads only the customer location, the idle-driver set, and the fixed layout.
    Never consults the pending-order pool. Curation is myopic w.r.t. the queue by
    construction.

    RNG neutrality
    --------------
    select() consumes no random numbers. It only names which restaurant is
    slotted (R_op or R_F); the customer's selection draw happens downstream in
    OrderArrivalService on its seeded operational stream(s). Because the stream
    position does not move inside select(), the same CRN stream is shared across
    policies at a given arrival index -- recommendations may diverge, but the
    random draw that resolves the customer's choice is common (arrival-side
    paired comparison preserved).

    Returns
    -------
    tuple: (Restaurant, curation_result, penalty)

        curation_result:
            'operational_immediate' / 'operational_queued'   R_op recommended
            'featured_immediate'    / 'featured_queued'       R_F recommended
        Prefix = which restaurant was slotted, suffix = branch. Branch mix reads
        off the suffix.

        penalty:
            mode 'operational'  -> None  (no featuring; no penalty defined)
            mode 'featured'     -> float >= 0, the operational externality of
                                   featuring c(R_F) - c(R_op): the extra knowable
                                   travel the fleet absorbs to place R_F instead
                                   of the operational optimum. Stamped on every
                                   featured arrival as instrumentation for the
                                   featuring-cost analysis; never gated.
    """

    _VALID_MODES = {'operational', 'featured'}

    def __init__(self, restaurant_repository, driver_repository, config,
                 featured_restaurant_id=None):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.config = config

        self.mode = config.curation_policy
        if self.mode not in self._VALID_MODES:
            raise ValueError(
                f"CurationPolicy got curation_policy={self.mode!r}; "
                f"expected one of {self._VALID_MODES}. "
                f"(Policy U is curation_policy=None and is not handled by this "
                f"class.)")

        self.featured_restaurant_id = featured_restaurant_id

        if self.mode == 'featured':
            # Featured mode is meaningless without a target.
            if featured_restaurant_id is None:
                raise ValueError(
                    f"curation_policy={self.mode!r} requires a "
                    f"featured_restaurant_id, but none was given. Featuring "
                    f"nothing is incoherent; use 'operational' for pure X''.")

        self._featured = None  # resolved lazily on first select()

    # ----- operational optimum (surviving X'') -----

    def _select_operational(self, customer_location, idle_drivers):
        """
        R_op = the pure-operational recommendation, and the branch it came from.

        single_immediate: argmin (R-D + R-C) over all restaurants.
        single_queued:    argmin R-C over all restaurants (R_nearest).

        Both are the argmin of _cost_of under the current information set, so
        _cost_of(R_op) is the minimum cost and penalty >= 0 for any R_F.

        Returns (R_op, branch) where branch is 'immediate' or 'queued'.
        """
        restaurants = self.restaurant_repository.find_all()
        best = None
        best_cost = float('inf')
        for r in restaurants:
            cost = self._cost_of(r, customer_location, idle_drivers)
            if cost < best_cost:
                best_cost = cost
                best = r
        branch = 'immediate' if idle_drivers else 'queued'
        return best, branch

    def _cost_of(self, restaurant, customer_location, idle_drivers):
        """
        Expected knowable operational travel to serve this arrival from
        `restaurant`, under current information. Its argmin over all restaurants
        is exactly R_op, so penalty = c(R_F) - c(R_op) >= 0.
        """
        r_c = calculate_distance(restaurant.location, customer_location)
        if idle_drivers:
            r_d = min(
                calculate_distance(restaurant.location, d.location)
                for d in idle_drivers
            )
            return r_d + r_c
        return r_c

    # ----- featured restaurant resolution -----

    def _get_featured(self):
        if self._featured is None:
            for r in self.restaurant_repository.find_all():
                if r.restaurant_id == self.featured_restaurant_id:
                    self._featured = r
                    break
            if self._featured is None:
                known = [r.restaurant_id
                         for r in self.restaurant_repository.find_all()]
                raise ValueError(
                    f"featured_restaurant_id {self.featured_restaurant_id!r} not "
                    f"found. Known restaurant ids: {known}")
        return self._featured

    # ----- main entry point -----

    def select(self, customer_location):
        idle_drivers = self.driver_repository.find_available_drivers()
        r_op, branch = self._select_operational(customer_location, idle_drivers)

        # Operational mode (X''): slot R_op, no featuring, no penalty.
        if self.mode == 'operational':
            self.logger.debug(
                f"operational_{branch}: restaurant {r_op.restaurant_id}")
            return r_op, 'operational_' + branch, None

        # Featured mode (F): always slot R_F. penalty is measured and stamped,
        # never used to gate the recommendation.
        r_f = self._get_featured()

        # Identity short-circuit: featuring is free when R_F already is R_op.
        # Comparing ids (not costs) guarantees an exact 0.0 penalty and keeps the
        # measured externality clean of float noise in two summed cost paths.
        if r_f.restaurant_id == r_op.restaurant_id:
            penalty = 0.0
        else:
            penalty = (self._cost_of(r_f, customer_location, idle_drivers)
                       - self._cost_of(r_op, customer_location, idle_drivers))
            if penalty < 0.0:
                # r_op is the argmin of the same cost function; a genuine negative
                # is impossible. Only float underflow in the immediate branch (two
                # separately-summed sqrt paths) can produce a tiny negative. Clamp
                # it so the stamped externality never reads spuriously below zero.
                assert penalty > -1e-9, (
                    f"Negative featuring penalty {penalty!r} in branch "
                    f"{branch!r}: _cost_of disagrees with the operational argmin.")
                penalty = 0.0

        self.logger.debug(
            f"featured_{branch}: restaurant {r_f.restaurant_id} "
            f"(penalty={penalty:.3f})")
        return r_f, 'featured_' + branch, penalty