# delivery_sim/utils/curation_policy.py
"""
Restaurant selection policies for order arrival.

Policy U (UniformPolicy):
    Selects a restaurant uniformly at random. This is the baseline behavior
    that matches Study 1 and Study 2.

Policy X (ProximityCurationPolicy):
    R-D curation as described in Savelsbergh & Ulmer (2024).
    Ranks restaurants by distance to the nearest idle driver and recommends
    the closest one. Falls back to uniform random when no idle drivers exist
    (R-D signal unavailable).

Usage:
    policy = ProximityCurationPolicy(
        restaurant_repository=repo,
        driver_repository=driver_repo,
        restaurant_selection_stream=rng_stream
    )
    restaurant = policy.select()   # returns a Restaurant object
"""

from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger


class UniformPolicy:
    """
    Policy U: uniform random restaurant selection.

    Baseline behavior — equivalent to the original _select_restaurant_location
    logic extracted into a policy object. Exists so the call site in
    OrderArrivalService is uniform regardless of which policy is active.
    """

    def __init__(self, restaurant_repository, restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.rng = restaurant_selection_stream

    def select(self):
        """
        Select a restaurant uniformly at random.

        Returns:
            Restaurant: the selected restaurant object
        """
        restaurants = self.restaurant_repository.find_all()
        selected = self.rng.choice(restaurants)
        self.logger.debug(
            f"UniformPolicy selected restaurant {selected.restaurant_id}"
        )
        return selected


class ProximityCurationPolicy:
    """
    Policy X: R-D proximity curation (Savelsbergh & Ulmer, 2024).

    When idle drivers exist:
        Ranks all restaurants by their distance to the nearest idle driver.
        Returns the restaurant with the shortest minimum distance.

    When no idle drivers exist:
        R-D signal is unavailable. Falls back to uniform random selection,
        identical to Policy U. Tracks how often this fallback occurs so the
        operating envelope can be characterized across regimes.
    """

    def __init__(self, restaurant_repository, driver_repository,
                 restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.rng = restaurant_selection_stream  # used only for fallback

        # Counters for operating envelope characterization (Research Question 5)
        self._total_selections = 0
        self._fallback_count = 0

    def select(self):
        """
        Select a restaurant using R-D proximity curation.

        Returns:
            Restaurant: the selected restaurant object
        """
        self._total_selections += 1
        idle_drivers = self.driver_repository.find_available_drivers()

        if not idle_drivers:
            # No idle drivers — R-D signal unavailable, fall back to uniform
            self._fallback_count += 1
            restaurants = self.restaurant_repository.find_all()
            selected = self.rng.choice(restaurants)
            self.logger.debug(
                f"ProximityCuration: no idle drivers, fallback to random "
                f"-> restaurant {selected.restaurant_id}"
            )
            return selected

        # Rank restaurants by distance to nearest idle driver
        restaurants = self.restaurant_repository.find_all()
        best_restaurant = None
        best_dist = float('inf')

        for r in restaurants:
            min_dist = min(
                calculate_distance(r.location, d.location)
                for d in idle_drivers
            )
            if min_dist < best_dist:
                best_dist = min_dist
                best_restaurant = r

        self.logger.debug(
            f"ProximityCuration selected restaurant {best_restaurant.restaurant_id} "
            f"(nearest idle driver dist={best_dist:.3f}km, "
            f"idle_drivers={len(idle_drivers)})"
        )
        return best_restaurant

    def get_fallback_rate(self):
        """
        Return fraction of selections that fell back to uniform random.

        This is the R-D signal availability rate complement — it measures
        how often the curation mechanism was actually operative.
        Returns 0.0 if no selections have been made yet.
        """
        if self._total_selections == 0:
            return 0.0
        return self._fallback_count / self._total_selections

    def get_selection_counts(self):
        """
        Return raw counters for external aggregation.

        Returns:
            dict with 'total' and 'fallback' keys
        """
        return {
            'total': self._total_selections,
            'fallback': self._fallback_count
        }