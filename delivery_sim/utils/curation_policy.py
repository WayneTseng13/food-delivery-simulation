"""
Curation policies for restaurant recommendation at order-arrival time.

The OrderArrivalService calls a curation policy's select(customer_location) to
obtain a restaurant recommendation, which the customer then accepts (with
probability p) or rejects.

Policy U (no curation) is NOT a class here. It is represented by
config.curation_policy is None, handled directly in OrderArrivalService: no
recommendation is produced and the customer samples a restaurant uniformly.

This module was reduced for the featuring/blended-curation chapter. The earlier
state-adaptive family (X', X'') with the edge-manufacture branch lives on the
previous git branch; that investigation concluded edge-manufacture adds no
operational value, so the pure-operational policy survives here only as
single_immediate + single_queued, which is exactly BlendedCurationPolicy in
'operational' mode.

The single policy class covers three modes, set explicitly by
config.curation_policy (NOT inferred from parameter values):

    'operational'  X''. Always recommend the operational optimum R_op.
                   featured_restaurant_id / tau are ignored.
    'blended'      Blend(tau). Recommend R_F when the operational penalty is
                   affordable (<= tau), else R_op.
    'featured'     Policy F. Always recommend R_F. Equivalent to 'blended' with
                   tau = inf, but named explicitly so a study row reads as F
                   rather than as a blend with a magic tau.

'blended' and 'featured' require featured_restaurant_id; a missing one is an
error, not a silent fallback to operational mode.
"""

from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger


class BlendedCurationPolicy:
    """
    Blended business/operational curation over an optional single featured
    restaurant R_F.

    Operational optimum R_op (state-dependent)
    ------------------------------------------
        single_immediate (>=1 idle driver):  R_op = argmin (R-D + R-C)
        single_queued    (no idle driver):   R_op = argmin R-C = R_nearest

    where R-D is distance to the nearest idle driver and R-C is the delivery leg.
    These two rules are the surviving X'' policy verbatim.

    Featuring penalty (the operational cost of featuring)
    -----------------------------------------------------
        c(R) = d(R, nearest idle driver) + d(R, C)   if an idle driver exists
        c(R) = d(R, C)                               otherwise

        penalty = c(R_F) - c(R_op)   >= 0 by construction (R_op = argmin c)

    Recommend R_F iff penalty <= tau. So tau is the maximum operational travel,
    in km, the platform will spend to place R_F instead of the operational
    optimum. penalty is measured in the state-dependent operational currency, NOT
    as the R-C detour d(R_F,C) - d(R_nearest,C): in the immediate branch R_op is
    not R_nearest, so the R-C detour can go negative and is unsuitable as a gate.

    Mode
    ----
    self.mode in {'operational', 'blended', 'featured'} comes straight from
    config.curation_policy. Intent is explicit, not inferred from whether a
    featured id or tau happens to be set. 'operational' ignores featuring
    entirely; 'featured' is 'blended' with tau fixed at +inf.

    Queue-blindness
    ---------------
    Reads only the customer location, the idle-driver set, and the fixed layout.
    Never consults the pending-order pool. Curation is myopic w.r.t. the queue by
    construction.

    RNG neutrality
    --------------
    select() consumes no random numbers under any mode. It always returns a
    recommendation, so the caller fires the compliance draw exactly once per
    arrival and the rejection draw exactly once per rejection -- identical stream
    consumption across the whole tau sweep. Recommendations diverge across tau,
    but the compliance coin at a given arrival index does not, so accept/reject
    outcomes are common across the sweep (arrival-side paired comparison).

    Returns
    -------
    tuple: (Restaurant, curation_result, penalty)

        curation_result:
            'operational_immediate' / 'operational_queued'   R_op recommended
            'featured_immediate'    / 'featured_queued'       R_F recommended
        Prefix = fire decision, suffix = branch. Fire rate and branch mix both
        read off this one field.

        penalty:
            mode 'operational'  -> None  (no featuring decision was made)
            mode 'blended'/'featured' -> float, the penalty, recorded whether or
                                    not featuring fired. On 'operational_*' rows
                                    (blended, declined) it is the penalty that was
                                    declined; on 'featured_*' rows it is the
                                    penalty paid. A single run therefore yields
                                    the whole penalty distribution over arrivals,
                                    from which fire_rate(tau') = P(penalty <=
                                    tau') can be read for every tau'.
    """

    _VALID_MODES = {'operational', 'blended', 'featured'}

    def __init__(self, restaurant_repository, driver_repository, config,
                 featured_restaurant_id=None, tau=None):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.config = config

        self.mode = config.curation_policy
        if self.mode not in self._VALID_MODES:
            raise ValueError(
                f"BlendedCurationPolicy got curation_policy={self.mode!r}; "
                f"expected one of {self._VALID_MODES}. "
                f"(Policy U is curation_policy=None and is not handled by this "
                f"class.)")

        self.featured_restaurant_id = featured_restaurant_id

        if self.mode == 'operational':
            # Featuring is inert. Do not require an id or tau; ignore both.
            self.tau = None
        else:
            # 'blended' or 'featured' -- a featured restaurant is mandatory.
            if featured_restaurant_id is None:
                raise ValueError(
                    f"curation_policy={self.mode!r} requires a "
                    f"featured_restaurant_id, but none was given. Featuring "
                    f"nothing is incoherent; use 'operational' for pure X''.")
            if self.mode == 'featured':
                # Policy F: always feature. tau is fixed at +inf regardless of
                # any value passed (a finite tau here would be a blend, not F).
                self.tau = float('inf')
            else:  # 'blended'
                if tau is None or tau < 0.0:
                    raise ValueError(
                        f"curation_policy='blended' requires a non-negative tau "
                        f"(or inf); got {tau!r}.")
                self.tau = float(tau)

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

    def select(self, customer_location=None):
        idle_drivers = self.driver_repository.find_available_drivers()
        r_op, branch = self._select_operational(customer_location, idle_drivers)

        # Pure operational mode (X''): no featuring, no penalty.
        if self.mode == 'operational':
            self.logger.debug(
                f"Blended[operational] operational_{branch}: "
                f"restaurant {r_op.restaurant_id}")
            return r_op, 'operational_' + branch, None

        # Featuring modes ('blended' / 'featured').
        r_f = self._get_featured()

        # Identity short-circuit: featuring is free when R_F already is R_op.
        # Comparing ids (not costs) guarantees an exact 0.0 penalty and keeps the
        # tau=0 == X'' identity immune to float noise in two summed cost paths.
        if r_f.restaurant_id == r_op.restaurant_id:
            penalty = 0.0
        else:
            penalty = (self._cost_of(r_f, customer_location, idle_drivers)
                       - self._cost_of(r_op, customer_location, idle_drivers))
            if penalty < 0.0:
                # r_op is the argmin of the same cost function; a genuine negative
                # is impossible. Only float underflow in the immediate branch
                # (two separately-summed sqrt paths) can produce a tiny negative.
                # Clamp it -- a -1e-16 penalty flipping the tau=0 fire decision is
                # exactly what would break the bit-identical-to-X'' check.
                assert penalty > -1e-9, (
                    f"Negative featuring penalty {penalty!r} in branch "
                    f"{branch!r}: _cost_of disagrees with the operational argmin.")
                penalty = 0.0

        if penalty <= self.tau:
            self.logger.debug(
                f"Blended featured_{branch}: restaurant {r_f.restaurant_id} "
                f"(penalty={penalty:.3f} <= tau={self.tau})")
            return r_f, 'featured_' + branch, penalty

        self.logger.debug(
            f"Blended operational_{branch}: restaurant {r_op.restaurant_id} "
            f"(declined; penalty={penalty:.3f} > tau={self.tau})")
        return r_op, 'operational_' + branch, penalty