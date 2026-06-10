from delivery_sim.utils.location_utils import calculate_distance
from delivery_sim.utils.logging_system import get_logger


class UniformPolicy:
    """
    Policy U: uniform random restaurant selection.

    Baseline behavior — equivalent to the original _select_restaurant_location
    logic extracted into a policy object.
    """

    def __init__(self, restaurant_repository, restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.rng = restaurant_selection_stream

    def select(self):
        """
        Select a restaurant uniformly at random.

        Returns:
            tuple: (Restaurant, None)
                   None signals curation is not applicable for this policy.
        """
        restaurants = self.restaurant_repository.find_all()
        selected = self.rng.choice(restaurants)
        self.logger.debug(f"UniformPolicy selected restaurant {selected.restaurant_id}")
        return selected, None


class ProximityCurationPolicy:
    """
    Policy X: R-D proximity curation (Savelsbergh & Ulmer, 2024).

    When idle drivers exist:
        Ranks all restaurants by their distance to the nearest idle driver.
        Returns the restaurant with the shortest minimum distance.

    When no idle drivers exist:
        R-D signal is unavailable. Falls back to uniform random selection.
    """

    def __init__(self, restaurant_repository, driver_repository,
                 restaurant_selection_stream):
        self.logger = get_logger("utils.curation_policy")
        self.restaurant_repository = restaurant_repository
        self.driver_repository = driver_repository
        self.rng = restaurant_selection_stream

    def select(self):
        """
        Select a restaurant using R-D proximity curation.

        Returns:
            tuple: (Restaurant, curation_result)
                   curation_result is 'curated' when idle drivers existed and
                   proximity selection was applied, or 'fallback' when no idle
                   drivers existed and uniform random was used instead.
        """
        idle_drivers = self.driver_repository.find_available_drivers()

        if not idle_drivers:
            restaurants = self.restaurant_repository.find_all()
            selected = self.rng.choice(restaurants)
            self.logger.debug(
                f"ProximityCuration: no idle drivers, fallback to random "
                f"-> restaurant {selected.restaurant_id}"
            )
            return selected, 'fallback'

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
        return best_restaurant, 'curated'