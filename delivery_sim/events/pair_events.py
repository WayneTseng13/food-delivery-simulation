# delivery_sim/events/pair_events.py
"""
Pair-related events.

Under assignment-time bundling (mechanism iii) pairing is no longer an
arrival-time event. Pairs are created at dispatch, inside the assignment step.
The two arrival-time pairing-outcome events have therefore been removed:

  - PairCreatedEvent   : previously emitted by PairingService.form_pair and
                         consumed by AssignmentService.handle_pair_created to
                         trigger assignment for a freshly formed pair. Under
                         (iii) the pair is formed and assigned in the same call,
                         so there is nothing to announce and no subscriber.

  - PairingFailedEvent : previously emitted when an arriving order found no
                         pairing candidate, to route it back into assignment as
                         a single. Under (iii) an order flows straight to
                         assignment; there is no interception to repair.

Retained:

  - PairStateChangedEvent : live. Dispatched by Pair.transition_to on every
                            state change (CREATED -> ASSIGNED -> COMPLETED),
                            including the zero-duration CREATED -> ASSIGNED
                            collapse at dispatch under (iii).

  - PairAssignedEvent / PairCompletedEvent : retained pending verification.
                            These do not appear to be dispatched anywhere (only
                            PairStateChangedEvent is emitted by the Pair entity,
                            and delivery completion emits DeliveryUnitCompletedEvent).
                            If a tree-wide search finds no dispatch or subscribe
                            site, they were already dead under mechanism (ii) and
                            can be removed in a separate housekeeping pass -- that
                            is orthogonal to the (iii) migration.
"""

from delivery_sim.events.base_events import Event


class PairEvent(Event):
    """Base class for all pair-related events."""
    def __init__(self, timestamp, pair_id):
        super().__init__(timestamp)
        self.pair_id = pair_id


class PairAssignedEvent(PairEvent):
    """Event for when a pair is assigned to a driver."""
    def __init__(self, timestamp, pair_id, driver_id, delivery_unit_id):
        super().__init__(timestamp, pair_id)
        self.driver_id = driver_id
        self.delivery_unit_id = delivery_unit_id


class PairCompletedEvent(PairEvent):
    """Event for when both orders in a pair have been delivered."""
    def __init__(self, timestamp, pair_id):
        super().__init__(timestamp, pair_id)


class PairStateChangedEvent(PairEvent):
    """Technical event for tracking all pair state transitions."""
    def __init__(self, timestamp, pair_id, old_state, new_state):
        super().__init__(timestamp, pair_id)
        self.old_state = old_state
        self.new_state = new_state