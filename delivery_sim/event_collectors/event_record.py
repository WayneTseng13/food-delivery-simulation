# delivery_sim/event_collectors/event_record.py

class EventRecord:
    """
    Single recorded event occurrence.

    Stores timestamp and any event-specific metadata extracted
    at collection time by a concrete collector.
    """

    def __init__(self, timestamp, metadata=None):
        self.timestamp = timestamp
        self.metadata = metadata or {}