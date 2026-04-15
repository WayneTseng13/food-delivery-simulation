# delivery_sim/event_collectors/driver_availability_collector.py

from delivery_sim.event_collectors.base_event_collector import BaseEventCollector
from delivery_sim.events.driver_events import DriverAvailableForAssignmentEvent


class DriverAvailabilityCollector(BaseEventCollector):
    """
    Records all DriverAvailableForAssignmentEvent occurrences during simulation.

    Captures both availability sources:
        - Fresh driver login (dispatched by DriverSchedulingService.handle_driver_login)
        - Post-delivery return (dispatched by evaluate_driver_availability_after_delivery)

    Primary use: measuring driver availability event rate as a function of simulation
    time. This rate is the mechanistic quantity underlying the performance gap between
    configurations — baseline generates these events at roughly twice the rate of
    2x baseline, directly explaining why queued orders wait less.
    """

    event_type = DriverAvailableForAssignmentEvent

    def extract_metadata(self, event):
        return {'driver_id': event.driver_id}