# delivery_sim/event_collectors/collector_registry.py

from delivery_sim.event_collectors.driver_availability_collector import DriverAvailabilityCollector


class EventCollectorRegistry:
    """
    Central registry for all event-driven collectors.

    Owns the knowledge of which event types are being collected.
    SimulationRunner interacts only with this registry — it never
    needs to know about individual collectors.

    To add a new collector:
        1. Create the collector file in event_collectors/
        2. Import it here and add one entry to self._collectors
        No other files need to change.
    """

    def __init__(self, event_dispatcher):
        self._collectors = {
            'driver_availability': DriverAvailabilityCollector(event_dispatcher),
            # future collectors added here only
        }

    def get_all_records(self):
        """
        Return all collected records keyed by collector name.
        Passed directly into the replication result dict.
        """
        return {
            name: collector.get_records()
            for name, collector in self._collectors.items()
        }