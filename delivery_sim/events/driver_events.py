from delivery_sim.events.base_events import Event

class DriverEvent(Event):
    """Base class for all driver-related events."""
    
    def __init__(self, timestamp, driver_id):
        """
        Initialize a driver event.
        
        Args:
            timestamp: When this event occurred
            driver_id: ID of the driver this event relates to
        """
        super().__init__(timestamp)
        self.driver_id = driver_id

class DriverLoggedInEvent(DriverEvent):
    """Event for when a driver enters the system."""
    
    def __init__(self, timestamp, driver_id, initial_location, service_duration):
        super().__init__(timestamp, driver_id)
        self.initial_location = initial_location
        self.service_duration = service_duration
        self.intended_logout_time = timestamp + service_duration

class DriverLoggedOutEvent(DriverEvent):
    """Event for when a driver exits the system."""
    
    def __init__(self, timestamp, driver_id, final_location, login_time):
        super().__init__(timestamp, driver_id)
        self.final_location = final_location
        self.login_time = login_time
        self.total_service_time = timestamp - login_time

class DriverStateChangedEvent(DriverEvent):
    """Event for when a driver's state changes."""
    
    def __init__(self, timestamp, driver_id, old_state, new_state):
        """
        Initialize a driver state changed event.
        
        Args:
            timestamp: When this event occurred
            driver_id: ID of the driver whose state changed
            old_state: The state the driver was in before the change
            new_state: The state the driver is in after the change
        """
        super().__init__(timestamp, driver_id)
        self.old_state = old_state
        self.new_state = new_state

class DriverLocationUpdatedEvent(DriverEvent):
    """Event for when a driver's location changes."""
    
    def __init__(self, timestamp, driver_id, old_location, new_location):
        """
        Initialize a driver location updated event.
        
        Args:
            timestamp: When this event occurred
            driver_id: ID of the driver whose location changed
            old_location: The location before the change
            new_location: The location after the change
        """
        super().__init__(timestamp, driver_id)
        self.old_location = old_location
        self.new_location = new_location

class DriverAvailableForAssignmentEvent(Event):
    """
    Event indicating a driver is now available for assignment.

    Dispatched by DriverSchedulingService from two sources:
    - Driver login: fresh driver entering the system with no prior task
    - Post-delivery return: driver completed a delivery and is still
      within their intended service window

    AssignmentService listens exclusively to this event for driver-side
    assignment triggers. DriverLoggedInEvent is not used for assignment.
    """
    def __init__(self, timestamp, driver_id):
        super().__init__(timestamp)
        self.driver_id = driver_id   