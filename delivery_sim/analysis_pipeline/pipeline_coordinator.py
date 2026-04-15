# analysis_pipeline/pipeline_coordinator.py
"""
Phase-based pipeline coordinator for experiment analysis.

Single responsibility: Orchestrate the analysis pipeline through
clearly defined phases, delegating work to specialized processors.
"""

from delivery_sim.utils.logging_system import get_logger
from delivery_sim.analysis_pipeline.data_preparation import prepare_analysis_data
from delivery_sim.analysis_pipeline.replication_processor import ReplicationProcessor
from delivery_sim.analysis_pipeline.experiment_aggregator import ExperimentAggregator
from delivery_sim.analysis_pipeline.confidence_interval_constructor import construct_confidence_intervals
from delivery_sim.analysis_pipeline.metric_configurations import get_metric_configuration


class ExperimentAnalysisPipeline:
    """
    Phase-based orchestrator for end-to-end experiment analysis.
    
    Coordinates four distinct phases:
    Phase 0: Data preparation (warmup filtering)
    Phase 1: Replication-level processing
    Phase 2: Experiment-level aggregation
    Phase 3: Confidence interval construction
    """
    
    def __init__(self, warmup_period, enabled_metric_types, confidence_level=0.95):
        """
        Initialize the analysis pipeline.
        
        Args:
            warmup_period: Duration to exclude from analysis (simulation time units)
            enabled_metric_types: List of metric types to process
            confidence_level: Confidence level for intervals (default: 0.95)
        """
        self.warmup_period = warmup_period
        self.enabled_metric_types = enabled_metric_types
        self.confidence_level = confidence_level
        
        # Initialize phase processors
        self.replication_processor = ReplicationProcessor()
        self.experiment_aggregator = ExperimentAggregator()
        
        self.logger = get_logger("analysis_pipeline.coordinator")
        self.logger.info(f"Pipeline initialized: warmup_period={warmup_period}, "
                        f"confidence_level={confidence_level}, "
                        f"enabled_metrics={enabled_metric_types}")
    
    def analyze_experiment(self, raw_replication_results):
        """
        Transform raw simulation data into comprehensive experiment-level summary.
        
        Clear phase-by-phase processing:
        Phase 0: Data preparation (warmup filtering)
        Phase 1: Replication-level processing
        Phase 2: Experiment-level aggregation
        Phase 3: Confidence interval construction
        Phase 4: Metadata enrichment and finalization
        
        Args:
            raw_replication_results: List of raw simulation results (one per replication)
            
        Returns:
            dict: Complete experiment summary with statistics and confidence intervals
        """
        num_replications = len(raw_replication_results)
        self.logger.info(f"Starting analysis for {num_replications} replications")
        
        # Prepare metric configurations once
        metric_configs = {
            metric_type: get_metric_configuration(metric_type) 
            for metric_type in self.enabled_metric_types
        }
        
        # Phase 0: Prepare analysis data (warmup filtering)
        prepared_analysis_data = self._phase0_prepare_analysis_data(
            raw_replication_results
        )
        
        # Phase 1: Process each replication
        replication_metrics_by_type = self._phase1_process_replications(
            prepared_analysis_data, metric_configs
        )
        
        # Phase 2: Aggregate across replications
        experiment_statistics_by_type = self._phase2_aggregate_experiment(
            replication_metrics_by_type, metric_configs
        )
        
        # Phase 3: Construct confidence intervals
        experiment_results_with_cis = self._phase3_construct_confidence_intervals(
            experiment_statistics_by_type, replication_metrics_by_type, metric_configs
        )
        
        # Phase 4: Finalize with metadata
        return self._phase4_finalize_results(
            num_replications,  # Just pass the count
            experiment_statistics_by_type,
            experiment_results_with_cis,
            replication_metrics_by_type,      # add this
            prepared_analysis_data          # add this too
        )
    
    def _phase0_prepare_analysis_data(self, raw_replication_results):
        """
        Phase 0: Prepare analysis data by filtering warmup period.
        
        Transforms raw simulation results into analysis-ready data by:
        - Extracting repositories from each replication
        - Extracting system snapshots from each replication
        - Applying warmup period filtering
        - Creating analytical populations
        
        Args:
            raw_replication_results: List of raw simulation results (one per replication)
                Each result is a dict with 'repositories' and 'system_snapshots' keys
                
        Returns:
            list: Analysis data objects (one per replication) ready for metric processing
        """
        self.logger.info("Phase 0: Preparing analysis data (warmup filtering)")
        
        prepared_analysis_data = []
        
        for i, raw_replication_result in enumerate(raw_replication_results):
            repositories = raw_replication_result['repositories']
            system_snapshots = raw_replication_result.get('system_snapshots', [])  
            event_records = raw_replication_result.get('event_records', {}) # NEW
            
            analysis_data = prepare_analysis_data(
                repositories, 
                self.warmup_period,
                system_snapshots,  
                event_records   # NEW
            )
            prepared_analysis_data.append(analysis_data)
            
            self.logger.debug(
                f"Prepared analysis data for replication {i+1}/{len(raw_replication_results)}"
            )
        
        self.logger.info(f"Phase 0 complete: Prepared {len(prepared_analysis_data)} replications")
        return prepared_analysis_data
        
    def _phase1_process_replications(self, prepared_analysis_data, metric_configs):
        """
        Phase 1: Transform analysis data into replication-level metrics.
        
        Args:
            prepared_analysis_data: List of warmup-filtered analysis data
            metric_configs: Dict of metric configurations
            
        Returns:
            dict: {metric_type: [rep1_metrics, rep2_metrics, ...]}
        """
        self.logger.info("Phase 1: Processing replication-level metrics")
        
        replication_metrics_by_type = {
            metric_type: [] for metric_type in metric_configs.keys()
        }
        
        for i, analysis_data in enumerate(prepared_analysis_data):
            self.logger.debug(f"Processing replication {i+1}/{len(prepared_analysis_data)}")
            
            for metric_type, metric_config in metric_configs.items():
                processed_metrics = self.replication_processor.process_replication(
                    analysis_data, metric_config
                )
                
                if processed_metrics:
                    replication_metrics_by_type[metric_type].append(processed_metrics)
                    self.logger.debug(f"Processed {metric_type} for replication {i+1}")
                else:
                    self.logger.warning(f"Empty results for {metric_type} in replication {i+1}")
        
        # Log phase summary
        for metric_type, metrics_list in replication_metrics_by_type.items():
            self.logger.info(
                f"Phase 1 complete: {len(metrics_list)} replications for {metric_type}"
            )
        
        return replication_metrics_by_type
    
    def _phase2_aggregate_experiment(self, replication_metrics_by_type, metric_configs):
        """
        Phase 2: Aggregate replication-level metrics into experiment-level statistics.
        
        Args:
            replication_metrics_by_type: Dict of {metric_type: [rep1, rep2, ...]}
            metric_configs: Dict of metric configurations
            
        Returns:
            dict: {metric_type: experiment_statistics}
        """
        self.logger.info("Phase 2: Aggregating across replications")
        
        experiment_statistics_by_type = {}
        
        for metric_type, metric_config in metric_configs.items():
            # Extract metrics for ONE metric type
            metrics_across_replications = replication_metrics_by_type.get(metric_type, [])
            
            if not metrics_across_replications:
                self.logger.warning(f"No metrics for {metric_type}")
                continue
            
            # Aggregate this metric type
            experiment_stats = self.experiment_aggregator.aggregate_experiment(
                metrics_across_replications, metric_config
            )
            
            if experiment_stats:
                experiment_statistics_by_type[metric_type] = experiment_stats
                self.logger.debug(f"Aggregated {metric_type}")
            else:
                self.logger.warning(f"No experiment statistics for {metric_type}")
        
        self.logger.info(f"Phase 2 complete: {len(experiment_statistics_by_type)} metric types")
        return experiment_statistics_by_type
    
    def _phase3_construct_confidence_intervals(self, experiment_statistics_by_type, 
                                            replication_metrics_by_type, metric_configs):
        """
        Phase 3: Add statistical inference (confidence intervals).
        
        Args:
            experiment_statistics_by_type: Dict of {metric_type: statistics}
            replication_metrics_by_type: Dict of {metric_type: [rep1, rep2, ...]}
            metric_configs: Dict of metric configurations
            
        Returns:
            dict: {metric_type: statistics_with_cis}
        """
        self.logger.info("Phase 3: Constructing confidence intervals")
        
        experiment_results_with_cis = {}
        
        # Loop at coordinator level (consistent with Phase 2)
        for metric_type, metric_config in metric_configs.items():
            if metric_type not in experiment_statistics_by_type:
                self.logger.warning(f"No experiment statistics for {metric_type}")
                continue
            
            self.logger.debug(f"Processing CIs for {metric_type}")
            
            # Extract data for ONE metric type
            metric_statistics = experiment_statistics_by_type[metric_type]
            metrics_across_replications = replication_metrics_by_type[metric_type]
            
            # Construct CIs for this metric type (router handles pattern dispatch)
            results_with_cis = construct_confidence_intervals(
                metric_statistics,
                metrics_across_replications,
                metric_config,
                self.confidence_level
            )
            
            experiment_results_with_cis[metric_type] = results_with_cis
            self.logger.debug(f"Constructed CIs for {metric_type}")
        
        self.logger.info("Phase 3 complete: Confidence intervals added")
        return experiment_results_with_cis
    
    def _phase4_finalize_results(self, num_replications, experiment_statistics_by_type,
                                experiment_results_with_cis, replication_metrics_by_type, prepared_analysis_data):
        """
        Phase 4: Add metadata and finalize experiment summary.
        
        Args:
            num_replications: Number of replications analyzed
            experiment_statistics_by_type: Dict of {metric_type: statistics}
            experiment_results_with_cis: Dict of {metric_type: statistics_with_cis}
            
        Returns:
            dict: Complete experiment summary
        """
        self.logger.info("Phase 4: Finalizing experiment summary")
        
        experiment_summary = {
            'num_replications': num_replications,
            'warmup_period': self.warmup_period,
            'confidence_level': self.confidence_level,
            'processed_metric_types': self.enabled_metric_types,
            'experiment_statistics': experiment_statistics_by_type,
            'statistics_with_cis': experiment_results_with_cis,
            'replication_metrics': replication_metrics_by_type,    # add this
            'replication_snapshots': [ad.post_warmup_snapshots for ad in prepared_analysis_data],  #add this too
            'replication_event_records': [ad.post_warmup_event_records for ad in prepared_analysis_data]  # ADD
        }
        
        self.logger.info("Analysis pipeline completed successfully")
        return experiment_summary