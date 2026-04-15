# delivery_sim/simulation/simulation_runner_redesigned.py
"""
SimulationRunner: Infrastructure-Consuming Runner for Operational Simulation

Redesigned SimulationRunner that accepts pre-built Infrastructure instances and focuses
purely on operational simulation execution. Infrastructure setup is now external,
enabling efficient reuse across multiple experimental configurations.

Key Changes from Original:
- Accepts Infrastructure as constructor input (not created internally)
- Removes infrastructure setup responsibilities
- Focuses on operational simulation execution
- Enables O(1) infrastructure reuse across M configurations
"""

import simpy
from delivery_sim.events.event_dispatcher import EventDispatcher
from delivery_sim.simulation.rng_manager import OperationalRNGManager
from delivery_sim.repositories.order_repository import OrderRepository
from delivery_sim.repositories.driver_repository import DriverRepository
from delivery_sim.repositories.pair_repository import PairRepository
from delivery_sim.repositories.delivery_unit_repository import DeliveryUnitRepository
from delivery_sim.services.order_arrival_service import OrderArrivalService
from delivery_sim.services.driver_arrival_service import DriverArrivalService
from delivery_sim.services.pairing_service import PairingService
from delivery_sim.services.assignment_service import AssignmentService
from delivery_sim.services.delivery_service import DeliveryService
from delivery_sim.services.driver_scheduling_service import DriverSchedulingService
from delivery_sim.utils.id_generator import PrefixedIdGenerator
from delivery_sim.utils.logging_system import get_logger, configure_logging
from delivery_sim.system_data.system_data_definitions import SystemDataDefinitions
from delivery_sim.system_data.system_data_collector import SystemDataCollector
from delivery_sim.system_data.system_snapshot_repository import SystemSnapshotRepository
from delivery_sim.utils.priority_scoring import PriorityScorer
from delivery_sim.event_collectors.collector_registry import EventCollectorRegistry

class SimulationRunner:
    """
    Infrastructure-consuming runner for operational simulation execution.
    
    Takes a pre-built Infrastructure instance and focuses purely on running
    operational simulation logic. Enables efficient reuse of infrastructure
    across multiple experimental configurations.
    """
    
    def __init__(self, infrastructure):
        """
        Initialize SimulationRunner with pre-built Infrastructure.
        
        Args:
            infrastructure: Pre-built Infrastructure instance with analysis results
        """
        self.logger = get_logger("simulation.runner")
        
        # Validate infrastructure has been analyzed
        if not infrastructure.has_analysis_results():
            raise ValueError("Infrastructure must be analyzed before use in SimulationRunner.")
        
        # Extract ONLY what we actually need from infrastructure
        analysis_results = infrastructure.get_analysis_results()
        self.typical_distance = analysis_results['typical_distance']  # Only this!
        
        # Store infrastructure components for reuse
        self.restaurant_repository = infrastructure.get_restaurant_repository()
        self.structural_config = infrastructure.structural_config
        
        self.logger.info(f"SimulationRunner initialized with typical_distance={self.typical_distance:.3f}km")
        
        # Variant components (fresh per configuration/replication)
        self.operational_config = None
        self.experiment_config = None
        self.scoring_config = None
        self.config = None
        self.env = None
        self.event_dispatcher = None
        self.order_repository = None
        self.driver_repository = None
        self.pair_repository = None
        self.delivery_unit_repository = None
        self.operational_rng = None
        self.priority_scorer = None
        self.id_generators = None
        self.services = None
        
        # System data collection components (variant per replication)
        self.system_data_definitions = None
        self.system_data_collector = None
        self.system_snapshot_repository = None

        self.event_collector_registry = None
    
    def run_experiment(self, operational_config, experiment_config, scoring_config=None):
        """
        Execute simulation experiment with multiple replications.
        
        REFACTORED: Now returns replication_results directly, no wrapper dictionary.
        
        Args:
            operational_config: OperationalConfig with arrival rates, pairing rules, etc.
            experiment_config: ExperimentConfig with duration, replications, seed, collection interval
            scoring_config: Optional ScoringConfig for priority scoring (defaults to ScoringConfig())
            
        Returns:
            list: Direct replication results list (no wrapper dictionary)
        """
        from delivery_sim.simulation.configuration import ScoringConfig
        
        # Store configurations for use across replications
        self.operational_config = operational_config
        self.experiment_config = experiment_config
        self.scoring_config = scoring_config or ScoringConfig()
        
        # Create flat config for service access (only what services actually need)
        self.config = self._create_service_config()
        
        self.logger.info(f"Starting experiment with {experiment_config.num_replications} replications")
        
        # ===== RUN MULTIPLE REPLICATIONS =====
        replication_results = []
        
        for replication in range(experiment_config.num_replications):
            self.logger.info(f"Starting replication {replication + 1}/{experiment_config.num_replications}")
            
            # Initialize fresh components for this replication
            self._initialize_variant_components(replication)
            
            # Run this replication
            replication_result = self._run_single_replication()
            replication_results.append(replication_result)
            
            self.logger.info(f"Completed replication {replication + 1}")
        
        # ===== RETURN SIMPLIFIED RESULTS =====
        self.logger.info(f"Experiment completed: {len(replication_results)} replications")
        return replication_results  # ✅ Direct return, no wrapper dictionary
    
    def _create_service_config(self):
        """
        Create simple config object that provides flat access to parameters services need.
        
        Much simpler than SimulationConfig - just combines the configs services actually use.
        """
        from delivery_sim.simulation.configuration import FlatConfig
        
        return FlatConfig(
            self.structural_config,                 
            self.operational_config,                
            self.experiment_config,                 
            None,                                  
            self.scoring_config                    
        )
    

    
    def _initialize_variant_components(self, replication_number):
        """
        Initialize fresh components for a single replication.
        
        Uses provided infrastructure but creates fresh operational components.
        """
        self.logger.debug(f"Initializing variant components for replication {replication_number}...")
        
        # 1. Create fresh ID generators for this replication
        self._create_id_generators()
        
        # 2. Create fresh simulation environment
        self.env = simpy.Environment()
        self.event_dispatcher = EventDispatcher()
        
        # 3. Create fresh operational RNG (different seed per replication)
        operational_master_seed = self.config.operational_master_seed  # CHANGED
        self.operational_rng = OperationalRNGManager(operational_master_seed, replication_number)  # CHANGED
        
        # Log sample seeds to verify replication independence
        sample_seeds = self.operational_rng.get_sample_stream_seeds()
        self.logger.debug(f"Replication {replication_number} RNG streams: {sample_seeds}")
        
        # 4. Create fresh entity repositories (except restaurants - reuse from infrastructure)
        self.order_repository = OrderRepository()
        self.driver_repository = DriverRepository()
        self.pair_repository = PairRepository()
        self.delivery_unit_repository = DeliveryUnitRepository()
        
        # 5. Create priority scorer
        self.priority_scorer = PriorityScorer(
            scoring_config=self.scoring_config,
            typical_distance=self.typical_distance,  # Direct access to only what we need
            env=self.env
        )
        # 6. Create services (connect infrastructure to variant environment)
        self._create_services()
        
        # 7. Initialize system data collection infrastructure
        self._initialize_system_data_collection()

        # 8. Initialize event collection infrastructure       ← ADD THIS
        self._initialize_event_collection()

        self.logger.debug(f"Variant components initialized for replication {replication_number}")
    
    def _create_id_generators(self):
        """Create ID generators for entities that reset per replication."""
        self.logger.debug("Creating ID generators...")
        
        self.id_generators = {
            'order': PrefixedIdGenerator('O', 1),      # Generates: O1, O2, O3, ...
            'driver': PrefixedIdGenerator('D', 1),     # Generates: D1, D2, D3, ...
            # Restaurant IDs are handled in infrastructure - no generator needed
        }
    
    def _create_services(self):
        """Create services that connect infrastructure to variant environment."""
        self.logger.debug("Creating services...")
        
        # Create core services
        services = {
            'order_arrival': OrderArrivalService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                order_repository=self.order_repository,
                restaurant_repository=self.restaurant_repository,  # Reuse from infrastructure!
                config=self.config,
                id_generator=self.id_generators['order'],
                operational_rng_manager=self.operational_rng
            ),
            
            'driver_arrival': DriverArrivalService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                driver_repository=self.driver_repository,
                config=self.config,
                id_generator=self.id_generators['driver'],
                operational_rng_manager=self.operational_rng
            ),
            
            'driver_scheduling': DriverSchedulingService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                driver_repository=self.driver_repository
            ),
            
            'assignment': AssignmentService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                order_repository=self.order_repository,
                driver_repository=self.driver_repository,
                pair_repository=self.pair_repository,
                delivery_unit_repository=self.delivery_unit_repository,
                priority_scorer=self.priority_scorer,  # Uses infrastructure analysis!
                config=self.config
            ),
            
            'delivery': DeliveryService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                driver_repository=self.driver_repository,
                order_repository=self.order_repository,
                pair_repository=self.pair_repository,
                delivery_unit_repository=self.delivery_unit_repository,
                restaurant_repository=self.restaurant_repository,  # Reuse from infrastructure!
                config=self.config
            )
        }
        
        # Create pairing service if enabled
        if self.config.pairing_enabled:
            services['pairing'] = PairingService(
                env=self.env,
                event_dispatcher=self.event_dispatcher,
                order_repository=self.order_repository,
                pair_repository=self.pair_repository,
                config=self.config
            )
        
        # Store services for easy access
        self.services = services
        
        # Log services created
        pairing_status = "with pairing" if self.config.pairing_enabled else "without pairing"
        self.logger.info(f"Initialized {len(services)} services {pairing_status}")
    
    def _initialize_system_data_collection(self):
        """Initialize system data collection for warmup analysis."""
        self.logger.debug("Initializing system data collection infrastructure...")
        
        # Create repository for storing snapshots
        self.system_snapshot_repository = SystemSnapshotRepository()
        
        # Create definitions for calculating system metrics
        repositories_dict = {
            'order': self.order_repository,
            'driver': self.driver_repository,
            'pair': self.pair_repository,
            'delivery_unit': self.delivery_unit_repository
        }
        self.system_data_definitions = SystemDataDefinitions(repositories_dict)
        
        # Create collector that will run during simulation
        collection_interval = self.config.collection_interval
        self.system_data_collector = SystemDataCollector(
            env=self.env,
            system_data_definitions=self.system_data_definitions,
            snapshot_repository=self.system_snapshot_repository,
            collection_interval=collection_interval
        )
        
        self.logger.debug(f"System data collection initialized with interval {collection_interval} minutes")
    
    def _initialize_event_collection(self):
        """
        Initialize event-driven data collection for mechanistic analysis.

        Separate from _initialize_system_data_collection() by design:
            - System data collection: time-driven, SimPy process, polls state at intervals
            - Event collection: event-driven, reacts to dispatched events as they occur

        Adding new event collectors requires only changes to EventCollectorRegistry.
        This method never needs to change.
        """
        self.logger.debug("Initializing event collection infrastructure...")
        self.event_collector_registry = EventCollectorRegistry(self.event_dispatcher)
        self.logger.debug("Event collection initialized")

    def _run_single_replication(self):
        """
        Execute single replication and return raw repository data and system snapshots.
        """
        # Run simulation (system data collector runs automatically as SimPy process)
        duration = self.config.simulation_duration
        self.logger.debug(f"Running simulation for {duration} minutes")
        self.env.run(until=duration)
        self.logger.info(f"Simulation completed at time {self.env.now:.2f}")
        
        # Collect repositories
        repositories = {
            'order': self.order_repository,
            'driver': self.driver_repository,
            'pair': self.pair_repository,
            'delivery_unit': self.delivery_unit_repository,
            'restaurant': self.restaurant_repository  # From infrastructure
        }
        
        # Collect system snapshots for warmup analysis
        system_snapshots = self.system_snapshot_repository.get_all_snapshots()
        
        self.logger.debug(f"Collected {len(system_snapshots)} system snapshots for warmup analysis")
        
        # Return enhanced results structure
        return {
            'repositories': repositories,
            'system_snapshots': system_snapshots,
            'event_records': self.event_collector_registry.get_all_records()
        }