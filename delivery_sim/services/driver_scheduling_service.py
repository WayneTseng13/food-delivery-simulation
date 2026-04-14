from delivery_sim.entities.states import DriverState
from delivery_sim.events.driver_events import DriverLoggedInEvent, DriverAvailableForAssignmentEvent, DriverLoggedOutEvent
from delivery_sim.events.delivery_unit_events import DeliveryUnitCompletedEvent
from delivery_sim.utils.logging_system import get_logger

class DriverSchedulingService:
    def __init__(self, env, event_dispatcher, driver_repository):
        """Initialize the driver scheduling service with its dependencies."""
        # Get a logger instance specific to this component
        self.logger = get_logger("services.driver_scheduling")
        
        # Store dependencies
        self.env = env
        self.event_dispatcher = event_dispatcher
        self.driver_repository = driver_repository
        
        # Log service initialization
        self.logger.info(f"[t={self.env.now:.2f}] DriverSchedulingService initialized")
        
        # Register for relevant events
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for DriverLoggedInEvent")
        self.event_dispatcher.register(DriverLoggedInEvent, self.handle_driver_login)
        
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Registering handler for DeliveryUnitCompletedEvent")
        self.event_dispatcher.register(DeliveryUnitCompletedEvent, self.handle_delivery_completed)
        
    
    # ===== Event Handlers (Entry Points) =====
    
    def handle_driver_login(self, event):
        """
        Handler for DriverLoggedInEvent. Validates driver and schedules logout if valid.
        
        This handler implements the Entry-Point Validation Pattern by validating
        entities before passing them to operations.
        
        Args:
            event: The DriverLoggedInEvent
        """
        # Log event handling
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling DriverLoggedInEvent for driver {event.driver_id}")
        
        # Extract identifiers from event
        driver_id = event.driver_id
        intended_logout_time = event.timestamp + event.service_duration
        
        # Validate driver exists
        driver = self.driver_repository.find_by_id(driver_id)
        if not driver:
            self.logger.validation(f"[t={self.env.now:.2f}] Driver {driver_id} not found, cannot schedule logout")
            return
        
        # Pass validated information to operation
        self.schedule_driver_logout(driver_id, intended_logout_time)
        self.logger.debug(f"[t={self.env.now:.2f}] Scheduled logout for driver {driver_id} at time {intended_logout_time:.2f}")
        
        # Driver is freshly available — signal availability same as post-delivery return
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DriverAvailableForAssignmentEvent for driver {driver_id} (login)")
        self.event_dispatcher.dispatch(DriverAvailableForAssignmentEvent(
            timestamp=event.timestamp,
            driver_id=driver_id
        ))


    def handle_delivery_completed(self, event):
        """
        Handler for DeliveryUnitCompletedEvent. Validates driver and checks logout conditions.
        
        Args:
            event: The DeliveryUnitCompletedEvent
        """
        # Log event handling
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Handling DeliveryUnitCompletedEvent for unit {event.delivery_unit_id} by driver {event.driver_id}")
        
        # Extract identifiers from event
        driver_id = event.driver_id
        timestamp = event.timestamp
        
        # Validate driver exists
        driver = self.driver_repository.find_by_id(driver_id)
        if not driver:
            self.logger.validation(f"[t={self.env.now:.2f}] Driver {driver_id} not found, cannot check logout conditions")
            return
        
        # Pass validated entity to operation
        self.evaluate_driver_availability_after_delivery(driver, event.timestamp)
      
    # ===== Operations (Business Logic) =====
    
    def schedule_driver_logout(self, driver_id, intended_logout_time):
        """
        Schedule a logout attempt for when the driver's intended time arrives.
        
        Args:
            driver_id: ID of the driver to schedule logout for
            intended_logout_time: When the driver intends to log out
        """
        self.logger.info(f"[t={self.env.now:.2f}] Scheduling logout for driver {driver_id} at time {intended_logout_time:.2f}")
        self.env.process(self._driver_logout_process(driver_id, intended_logout_time))
    
    def evaluate_driver_availability_after_delivery(self, driver, current_time):
        """Operation: Determine if driver should log out or become available for assignment."""
        if current_time >= driver.intended_logout_time:
            # Driver is overdue - execute immediate logout
            self.execute_driver_logout(driver, current_time, "overdue")
        else:
            # Driver is eligible for assignment - notify assignment service
            self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} available for new assignments")
            
            # Add the missing simulation_event log
            self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DriverAvailableForAssignmentEvent for driver {driver.driver_id}")
            self.event_dispatcher.dispatch(DriverAvailableForAssignmentEvent(
                timestamp=current_time,
                driver_id=driver.driver_id
            ))

    def evaluate_scheduled_logout(self, driver_id, current_time):
        """Operation: Evaluate what to do when a driver's intended logout time arrives."""
        # Validate driver exists (following light handler pattern even in operations)
        driver = self.driver_repository.find_by_id(driver_id)
        if not driver:
            self.logger.validation(f"[t={self.env.now:.2f}] Driver {driver_id} not found during scheduled logout evaluation")
            return
        
        # Check driver state and take appropriate action
        if driver.state == DriverState.AVAILABLE:
            # Driver is idle - log them out immediately
            self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} is available at intended logout time, executing logout")
            self.execute_driver_logout(driver, current_time, "scheduled")
            
        else: # driver.state == DriverState.DELIVERING
            # Driver is busy - note this but don't interrupt their delivery
            self.logger.info(f"[t={self.env.now:.2f}] Driver {driver.driver_id} is delivering at intended logout time, logout deferred until delivery completion")
            

    def execute_driver_logout(self, driver, timestamp, logout_reason):
        """Operation: Execute the logout procedure (shared by different logout paths)."""
        self.logger.info(f"[t={self.env.now:.2f}] Logging out driver {driver.driver_id} ({logout_reason})")
        driver.transition_to(DriverState.OFFLINE, self.event_dispatcher, self.env)
        
        # Add the missing simulation_event log
        self.logger.simulation_event(f"[t={self.env.now:.2f}] Dispatching DriverLoggedOutEvent for driver {driver.driver_id}")
        self.event_dispatcher.dispatch(DriverLoggedOutEvent(
            timestamp=timestamp,
            driver_id=driver.driver_id,
            final_location=driver.location,
            login_time=driver.login_time
        ))

    # SimPy process (internal method)
    def _driver_logout_process(self, driver_id, intended_logout_time):
        """SimPy process that waits until intended logout time and evaluates driver state."""
        self.logger.debug(f"[t={self.env.now:.2f}] Started logout monitoring process for driver {driver_id}")
        
        # Wait until the intended logout time arrives
        time_until_logout = intended_logout_time - self.env.now
        if time_until_logout > 0:
            self.logger.debug(f"[t={self.env.now:.2f}] Waiting {time_until_logout:.2f} minutes until driver {driver_id}'s logout time")
            yield self.env.timeout(time_until_logout)
        
        # When intended logout time arrives, evaluate what to do
        self.logger.debug(f"[t={self.env.now:.2f}] Driver {driver_id}'s intended logout time reached")
        self.evaluate_scheduled_logout(driver_id, self.env.now)

