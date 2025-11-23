"""Data Pipeline Package - Phase 2.4

High-performance async data pipeline for real-time market data integration.
Supports multi-exchange data ingestion, event processing, and database persistence.

Modules:
    async_pipeline: Core async queue and pipeline orchestrator
    db_inserter: Bulk database operations and persistence layer
    exchange_connector: Multi-exchange API integration (Binance, Bitget, Bybit, MEXC, OKX, Phemex)
    universal_feeder: Universal data feed aggregator from multiple sources

Author: Development Team
Date: 2024
Version: 2.4.0
"""

import logging
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from async_pipeline import AsyncPipeline, AsyncQueue, DataEvent, EventType, ProcessingStatus

__version__ = "2.4.0"
__author__ = "Development Team"
__all__ = [
    "AsyncPipeline",
    "AsyncQueue",
    "DataEvent",
    "EventType",
    "ProcessingStatus",
    "initialize_pipeline",
    "get_logger",
]

# Configure module-level logger
logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for data pipeline modules.
    
    Args:
        name: Logger name (typically __name__ of calling module)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Data pipeline initialized")
    """
    return logging.getLogger(name)


def initialize_pipeline(
    num_workers: int = 4,
    batch_size: int = 100,
    max_queue_size: int = 10000,
    retry_count: int = 3,
    timeout_seconds: float = 30.0,
    enable_metrics: bool = True,
) -> "AsyncPipeline":
    """
    Initialize and configure the async data pipeline.
    
    This is a convenience function for common pipeline setup patterns.
    Configures the pipeline with production-grade defaults optimized for
    real-time market data ingestion from multiple exchanges.
    
    Args:
        num_workers: Number of async workers in the pipeline (default: 4)
        batch_size: Number of events to batch before processing (default: 100)
        max_queue_size: Maximum queue size before applying backpressure (default: 10000)
        retry_count: Maximum retry attempts for failed events (default: 3)
        timeout_seconds: Event processing timeout in seconds (default: 30.0)
        enable_metrics: Enable metrics collection and monitoring (default: True)
        
    Returns:
        Configured AsyncPipeline instance ready for use
        
    Raises:
        ValueError: If configuration parameters are invalid
        ImportError: If async_pipeline module is not available
        
    Example:
        >>> pipeline = initialize_pipeline(
        ...     num_workers=8,
        ...     batch_size=200,
        ...     enable_metrics=True
        ... )
        >>> await pipeline.start()
    """
    # Import here to avoid circular imports
    try:
        from .async_pipeline import AsyncPipeline
    except ImportError as e:
        logger.error(f"Failed to import AsyncPipeline: {e}")
        raise ImportError("AsyncPipeline module not found. Ensure async_pipeline.py exists.")
    
    # Validate configuration
    if num_workers < 1:
        raise ValueError(f"num_workers must be >= 1, got {num_workers}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")
    if max_queue_size < batch_size:
        raise ValueError(f"max_queue_size ({max_queue_size}) must be >= batch_size ({batch_size})")
    if retry_count < 0:
        raise ValueError(f"retry_count must be >= 0, got {retry_count}")
    if timeout_seconds <= 0:
        raise ValueError(f"timeout_seconds must be > 0, got {timeout_seconds}")
    
    logger.info(
        f"Initializing AsyncPipeline: workers={num_workers}, batch_size={batch_size}, "
        f"max_queue_size={max_queue_size}, retry_count={retry_count}, "
        f"timeout_seconds={timeout_seconds}, metrics={enable_metrics}"
    )
    
    # Create and configure pipeline
    pipeline = AsyncPipeline(
        num_workers=num_workers,
        batch_size=batch_size,
        max_queue_size=max_queue_size,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        enable_metrics=enable_metrics,
    )
    
    logger.info("AsyncPipeline initialized successfully")
    return pipeline


def get_pipeline_config() -> Dict[str, Any]:
    """
    Get recommended default configuration for production deployment.
    
    Returns production-grade configuration suitable for real-time trading operations
    with multi-exchange data integration. Tune these values based on your specific
    requirements and system resources.
    
    Returns:
        Dictionary with recommended configuration parameters
        
    Example:
        >>> config = get_pipeline_config()
        >>> config['num_workers'] = 8  # Increase for higher throughput
        >>> pipeline = initialize_pipeline(**config)
    """
    return {
        # Worker and concurrency settings
        "num_workers": 4,
        "batch_size": 100,
        "max_queue_size": 10000,
        
        # Retry and resilience settings
        "retry_count": 3,
        "timeout_seconds": 30.0,
        
        # Monitoring and observability
        "enable_metrics": True,
        
        # This config supports:
        # - Real-time market data from Binance, Bitget, Bybit, MEXC, OKX, Phemex
        # - High-frequency event processing (100+ events/sec)
        # - Automatic retry with exponential backoff
        # - Dead-letter queue for failed events
        # - Comprehensive metrics and logging
    }


# Module initialization
logger.debug(f"Data Pipeline Package v{__version__} loaded")
