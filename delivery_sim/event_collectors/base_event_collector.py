# delivery_sim/event_collectors/base_event_collector.py

from delivery_sim.event_collectors.event_record import EventRecord


class BaseEventCollector:
    """
    Base class for event-driven data collection during simulation.

    Contrast with SystemDataCollector (time-driven, polls at fixed intervals).
    This collector reacts to events as they occur, recording each occurrence
    with timestamp and optional metadata.

    Structural difference from time-based collection:
        Time-based: one trigger (clock interval) -> multiple observations bundled
                    into one snapshot. New metrics added to SystemDataDefinitions.
        Event-based: each event type is its own trigger -> separate record stream
                     per event type. New collectors are separate files.

    Subclasses must define:
        event_type  : the event class to listen for
        extract_metadata(event) : (optional) what to pull from the event beyond timestamp
    """

    event_type = None  # subclass must override

    def __init__(self, event_dispatcher):
        if self.event_type is None:
            raise NotImplementedError("Subclass must define event_type")
        self.records = []
        event_dispatcher.register(self.event_type, self._handle_event)

    def _handle_event(self, event):
        record = EventRecord(
            timestamp=event.timestamp,
            metadata=self.extract_metadata(event)
        )
        self.records.append(record)

    def extract_metadata(self, event):
        """
        Override to extract event-specific metadata.
        Default implementation records no metadata beyond timestamp.
        """
        return {}

    def get_records(self):
        """Return all recorded EventRecord objects."""
        return list(self.records)

    def get_timestamps(self):
        """Convenience method: return timestamps only."""
        return [r.timestamp for r in self.records]