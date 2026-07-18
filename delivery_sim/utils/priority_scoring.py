# delivery_sim/utils/priority_scoring.py
"""
Priority Scoring System for Food Delivery Assignment Decisions

This module implements a multi-criteria scoring system that evaluates
assignment opportunities based on distance efficiency, throughput optimization,
and fairness considerations.

--- Scalar interface (mechanism iii) ---

The scorer is a pure function of three scalars:

    calculate_priority_score(total_distance, num_orders, wait_time)

It knows nothing about drivers, orders, pairs, options, EntityType, or route
geometry. The caller (AssignmentService) is responsible for computing:

  - total_distance : full travel distance of the candidate assignment, in km.
                     For a solo option: driver -> restaurant -> customer.
                     For a bundle option: driver leg + best pair route, obtained
                     from route_evaluator.evaluate_complete with the driver known.
  - num_orders     : 1 for a solo option, 2 for a bundle option.
  - wait_time      : age of the oldest order in the option (now - earliest arrival),
                     in minutes.

Why scalar. Under arrival-time pairing (mechanism ii) the scorer took (driver,
entity), branched on entity_type, and called evaluate_complete internally to
recover a pair's distance -- duplicating the route evaluation the assignment step
also performed. Under assignment-time bundling the enumeration already computes
each option's distance and sequence against the winning driver, so the scorer
recomputing distance would be pure waste (~250 route evaluations per dispatch).

Collapsing the scorer to three scalars removes the duplicate route call, removes
all EntityType branching (the scorer never needed to know what a Pair is), and
makes the score a provably identical function of the same arguments across both
mechanisms -- the property the (ii)-vs-(iii) comparison depends on.

Configuration is handled by ScoringConfig in configuration.py.
Infrastructure analysis (typical_distance) is handled by infrastructure_analysis.
"""

from delivery_sim.utils.logging_system import get_logger


class PriorityScorer:
    """
    Multi-criteria scorer for assignment opportunities.

    Evaluates a candidate assignment described by three scalars against the
    configured distance / throughput / fairness weights. Absolute normalization
    (no dependence on the other candidates) means an option's score is invariant
    to how many other options are enumerated alongside it.
    """

    def __init__(self, scoring_config, typical_distance, env):
        """
        Initialize scorer with configuration and infrastructure characteristics.

        Args:
            scoring_config: ScoringConfig instance from configuration.py
            typical_distance: Pre-calculated typical distance for this infrastructure
            env: SimPy environment for this replication (retained for logging context)
        """
        self.config = scoring_config
        self.typical_distance = typical_distance
        self.env = env
        self.logger = get_logger("utils.priority_scorer")

        self.logger.debug(
            f"PriorityScorer initialized with typical_distance={typical_distance:.3f}km")

    def calculate_priority_score(self, total_distance, num_orders, wait_time):
        """
        Calculate the priority score for a candidate assignment.

        Args:
            total_distance: Full travel distance of the assignment, in km
            num_orders: Number of orders in the assignment (1 or 2)
            wait_time: Age of the oldest order in the assignment, in minutes

        Returns:
            tuple: (priority_score_0_to_100, components_dictionary)

            The components dictionary carries the sub-scores and the raw inputs so
            the caller can store them on the DeliveryUnit and, for bundle options,
            attach the chosen route sequence before creating the assignment.
        """
        distance_score = self._calculate_distance_score(total_distance)
        throughput_score = self._calculate_throughput_score(num_orders)
        fairness_score = self._calculate_fairness_score(wait_time)

        combined_score = (
            self.config.weight_distance * distance_score +
            self.config.weight_throughput * throughput_score +
            self.config.weight_fairness * fairness_score
        )

        priority_score = combined_score * 100

        self.logger.debug(
            f"[t={self.env.now:.2f}] Priority score: "
            f"distance={distance_score:.3f}, throughput={throughput_score:.3f}, "
            f"fairness={fairness_score:.3f}, combined={priority_score:.2f} "
            f"(total_distance={total_distance:.3f}km, num_orders={num_orders}, "
            f"wait={wait_time:.2f}min)"
        )

        components = {
            "distance_score": distance_score,
            "throughput_score": throughput_score,
            "fairness_score": fairness_score,
            "combined_score_0_1": combined_score,
            "total_distance": total_distance,
            "num_orders": num_orders,
            "assignment_delay_minutes": wait_time
        }

        return priority_score, components

    def _calculate_distance_score(self, total_distance):
        """
        Distance efficiency score via two-step normalization.

        Step 1 (contextualization): normalize by typical distance for this
        geography, so scores are comparable across configurations of different
        scale.

        Step 2 (performance assessment): apply the universal acceptability
        standard max_distance_ratio_multiplier.

        Both steps use only config constants and the infrastructure-derived
        typical_distance -- never the other candidates. This absolute
        normalization is what makes an option's score independent of the size of
        the option set, and therefore comparable across mechanisms.

        Returns:
            float: Distance efficiency score in [0, 1], where
                1.0 = zero distance, 0.5 = one typical distance,
                0.0 = at or beyond max_distance_ratio_multiplier x typical.
        """
        distance_ratio = total_distance / self.typical_distance
        distance_score = max(0, 1 - distance_ratio / self.config.max_distance_ratio_multiplier)
        return distance_score

    def _calculate_throughput_score(self, num_orders):
        """
        Throughput score via direct normalization.

        Throughput is capacity utilization -- how many orders in one trip. It is
        an absolute, discrete measure (drivers carry 1 or 2 orders), so no
        geographical normalization applies.

        Args:
            num_orders: Number of orders in the assignment (1 or 2)

        Returns:
            float: Throughput score in [0, 1], where 1.0 = full capacity (2
                orders) and 0.5 = half capacity (1 order).
        """
        throughput_score = num_orders / self.config.max_orders_per_trip
        return throughput_score

    def _calculate_fairness_score(self, wait_time):
        """
        Fairness (wait-time urgency) score via direct normalization with ceiling.

        Fairness reflects how urgently the assignment is needed, based on how long
        the oldest order has waited. Time is absolute, so no geographical
        normalization applies.

        The caller supplies wait_time as the age of the oldest order in the
        option (now - earliest arrival). For a bundle this is the earliest of the
        two constituent arrivals, so an aged order makes any option containing it
        more urgent rather than being diluted by a fresh companion.

        Args:
            wait_time: Age of the oldest order in the assignment, in minutes

        Returns:
            float: Fairness score in [0, 1], where 0.0 = just arrived and
                1.0 = at or beyond max_acceptable_delay.
        """
        fairness_score = min(1.0, wait_time / self.config.max_acceptable_delay)
        return fairness_score