# delivery_sim/simulation/rng_manager.py
"""
Random Number Generation Management for Food Delivery Simulation

This module manages two separate types of randomness in the delivery simulation:

1. STRUCTURAL RANDOMNESS (StructuralRNGManager):
   - Controls infrastructure generation (restaurant layout)
   - Uses a single 'structural_seed' directly (not derived)
   - Purpose: Create different physical delivery environments
   - Example: structural_seed=42 → one restaurant layout
             structural_seed=123 → different restaurant layout
   
2. OPERATIONAL RANDOMNESS (OperationalRNGManager):
   - Controls operational simulation factors (orders, drivers, service, etc.)
   - Uses 'operational_master_seed' to derive multiple independent RNG streams
   - Purpose: Create different demand/supply patterns in same environment
   - Example: operational_master_seed=100 → derives seeds for:
              * Order arrivals (stream for replication 0, 1, 2, ...)
              * Driver arrivals (stream for replication 0, 1, 2, ...)
              * Service durations (stream for replication 0, 1, 2, ...)
              * Customer locations, driver locations, restaurant selection
              * Each replication gets independent streams for all processes

CRITICAL: These two randomness types are COMPLETELY INDEPENDENT:
- Infrastructure creation uses StructuralRNGManager with structural_seed
- Simulation execution uses OperationalRNGManager with operational_master_seed
- Changing one does NOT affect the other
- Different infrastructures can share same operational_master_seed (and vice versa)

Usage Patterns:
--------------
# Infrastructure study: vary structural_seed, fix operational_master_seed
structural_seeds = [42, 123, 999]  # Test 3 different layouts
for seed in structural_seeds:
    infrastructure = Infrastructure(..., structural_seed=seed)
    runner = SimulationRunner(infrastructure)
    runner.run_experiment(..., operational_master_seed=100)  # Same operational patterns

# Operational study: fix structural_seed, vary operational parameters
infrastructure = Infrastructure(..., structural_seed=42)  # Fixed layout
for load_ratio in [0.5, 0.8, 1.0]:
    config = OperationalConfig(load_ratio=load_ratio)
    runner.run_experiment(config, operational_master_seed=100)  # Can reuse same seed
"""

import numpy as np


class StructuralRNGManager:
    """
    Manages RNG for structural/physical infrastructure generation.
    
    This manager handles restaurant layout generation. It uses a single seed
    directly without derivation, as there's only one structural generation
    event per infrastructure instance.
    
    The structural seed controls ONLY the physical layout of restaurants
    within the delivery area. It has NO effect on operational factors like
    order arrivals, driver arrivals, or service times.
    
    Args:
        structural_seed: Random seed for restaurant position generation.
                        Each unique seed produces a different restaurant layout.
    
    Attributes:
        structural_seed (int): The seed used for this infrastructure
        rng (np.random.RandomState): Random number generator for restaurant positions
    
    Example:
        # Create two different layouts
        manager_a = StructuralRNGManager(structural_seed=42)
        manager_b = StructuralRNGManager(structural_seed=123)
        
        # Same seed → same layout (reproducible)
        manager_c = StructuralRNGManager(structural_seed=42)
        # manager_a and manager_c produce identical restaurant layouts
        
    Note:
        This manager is typically created once per Infrastructure instance
        and reused for any analysis that requires random sampling based on
        the infrastructure (e.g., Monte Carlo distance calculations).
    """
    
    def __init__(self, structural_seed):
        """
        Initialize structural RNG with specified seed.
        
        Args:
            structural_seed: Random seed for infrastructure generation
        """
        self.structural_seed = structural_seed
        self.rng = np.random.RandomState(structural_seed)


class OperationalRNGManager:
    """
    Manages RNG for operational simulation execution.
    
    This manager derives multiple independent RNG streams from a master seed
    to support multiple replications and different operational processes
    (orders, drivers, service, customers, assignments).
    
    The operational master seed controls ONLY the operational randomness
    (order arrivals, driver arrivals, service durations, customer locations).
    It has NO effect on infrastructure layout (restaurant positions).
    
    Stream Architecture:
    -------------------
    - Each replication gets independent streams for all processes
    - Stream seeds are derived deterministically from operational_master_seed
    - Same master seed + num_replications → identical stream sequence (reproducible)
    - Large offsets (10000 per replication) ensure mathematical independence
    
    Stream Types:
    ------------
    - order_arrivals: Poisson process for order generation timing
    - driver_arrivals: Poisson process for driver login timing
    - service_duration: Truncated normal for food preparation times
    - customer_locations: Uniform sampling for delivery destinations
    - driver_initial_locations: Uniform sampling for driver starting positions
    - restaurant_selection: Random selection for order restaurant assignment

    
    Args:
        operational_master_seed: Master seed for deriving all operational RNG streams.
        replication_number: Replication index (0, 1, 2, ...) for stream separation.
    
    Attributes:
        operational_master_seed (int): The master seed for this operational RNG
        replication_number (int): Which replication this manager serves
        stream_seeds (dict): Mapping of process names to their derived seeds
        streams (dict): Mapping of process names to their RandomState objects
    
    Example:
        # Create managers for 3 replications
        rep0 = OperationalRNGManager(operational_master_seed=100, replication_number=0)
        rep1 = OperationalRNGManager(operational_master_seed=100, replication_number=1)
        rep2 = OperationalRNGManager(operational_master_seed=100, replication_number=2)
        
        # Each replication has independent streams:
        # rep0: order_seed=101, driver_seed=102, service_seed=103, ...
        # rep1: order_seed=10001, driver_seed=10002, service_seed=10003, ...
        # rep2: order_seed=20001, driver_seed=20002, service_seed=20003, ...
        
        # Same master seed → reproducible replication sequence
        rep0_copy = OperationalRNGManager(operational_master_seed=100, replication_number=0)
        # rep0 and rep0_copy produce identical operational patterns
        
    Note:
        This manager is created fresh for each simulation replication.
        Different replications of the same configuration use the same
        operational_master_seed but different replication_numbers.
    """
    
    def __init__(self, operational_master_seed, replication_number=0):
        """
        Initialize operational RNG with independent streams.
        
        Args:
            operational_master_seed: Base seed for deriving all operational streams
            replication_number: Replication index for stream separation (default: 0)
        """
        self.operational_master_seed = operational_master_seed
        self.replication_number = replication_number
        
        # Create independent streams for each random process
        # Uses large offsets (10000) to ensure mathematical independence
        base_offset = replication_number * 10000
        
        # Store both streams and their seeds for transparency and debugging
        self.stream_seeds = {
            'order_arrivals': operational_master_seed + base_offset + 1,
            'driver_arrivals': operational_master_seed + base_offset + 2,
            'service_duration': operational_master_seed + base_offset + 3,
            'customer_locations': operational_master_seed + base_offset + 4,
            'driver_initial_locations': operational_master_seed + base_offset + 5,
            'restaurant_selection': operational_master_seed + base_offset + 6,

        }
        
        # Create RandomState objects for each stream
        self.streams = {
            name: np.random.RandomState(seed) 
            for name, seed in self.stream_seeds.items()
        }
    
    def get_stream(self, process_name):
        """
        Get the random stream for a specific operational process.
        
        Services should request their dedicated stream at initialization
        and use it throughout the simulation for their random needs.
        
        Args:
            process_name: Name of the random process (e.g., 'order_arrivals')
            
        Returns:
            np.random.RandomState: The process-specific random stream
            
        Raises:
            ValueError: If process name is not recognized
            
        Example:
            rng_manager = OperationalRNGManager(100, 0)
            order_stream = rng_manager.get_stream('order_arrivals')
            inter_arrival = order_stream.exponential(scale=1.0)
        """
        if process_name not in self.streams:
            available_streams = ', '.join(self.streams.keys())
            raise ValueError(
                f"Unknown process: {process_name}. "
                f"Available streams: {available_streams}"
            )
        
        return self.streams[process_name]
    
    def get_sample_stream_seeds(self):
        """
        Return sample stream seeds for verification and logging.
        
        Returns subset of stream seeds to verify replication independence
        without cluttering logs with all stream details.
        
        Returns:
            dict: Sample of stream seeds (order and driver arrivals)
        """
        return {
            'order_arrivals': self.stream_seeds['order_arrivals'],
            'driver_arrivals': self.stream_seeds['driver_arrivals']
        }
    
    def get_all_stream_seeds(self):
        """
        Return all stream seeds for debugging purposes.
        
        Returns:
            dict: Complete mapping of process names to their seeds
        """
        return self.stream_seeds.copy()
    
    def get_available_streams(self):
        """
        Get list of available stream names.
        
        Returns:
            list: Names of all available RNG streams
        """
        return list(self.streams.keys())