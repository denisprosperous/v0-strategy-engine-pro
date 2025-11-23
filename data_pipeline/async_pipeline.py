"""
Async Data Pipeline - Phase 2.4

Provides high-performance async queue-based data pipeline.
Supports real-time market data ingestion from exchange APIs.
Features: event queuing, bulk processing, database persistence.

Author: Development Team
Date: 2024
Version: 2.4.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Coroutine
from enum import Enum
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event type enumeration."""
    MARKET_DATA = "market_data"
    ORDER_UPDATE = "order_update"
    TRADE_EXECUTION = "trade_execution"
    POSITION_UPDATE = "position_update"
    SIGNAL = "signal"
    ERROR = "error"


class ProcessingStatus(Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class DataEvent:
    """Represents a data event in the pipeline."""
    event_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""
    symbol: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more urgent
    retry_count: int = 0
    max_retries: int = 3
    status: str = ProcessingStatus.PENDING.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "data": self.data,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "status": self.status
        }


class AsyncQueue:
    """
    Priority-based async queue for data events.
    
    Features:
    - Priority queue for event ordering
    - Automatic retry on failure
    - Dead-letter queue for failed events
    - Event deduplication
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize async queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self.dead_letter_queue: List[DataEvent] = []
        self.processed_events = set()
        self.max_size = max_size
    
    async def enqueue(
        self,
        event: DataEvent,
        priority: Optional[int] = None
    ) -> bool:
        """
        Add event to queue.
        
        Args:
            event: DataEvent to queue
            priority: Override event priority
        
        Returns:
            True if enqueued successfully
        """
        try:
            # Deduplication
            if event.event_id in self.processed_events:
                logger.debug(f"Duplicate event ignored: {event.event_id}")
                return False
            
            priority_value = priority or event.priority
            await self.queue.put((priority_value, event.event_id, event))
            logger.debug(f"Event enqueued: {event.event_id}")
            return True
        except asyncio.QueueFull:
            logger.warning("Queue full, moving to backpressure")
            return False
    
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[DataEvent]:
        """
        Get next event from queue.
        
        Args:
            timeout: Wait timeout in seconds
        
        Returns:
            DataEvent if available, None on timeout
        """
        try:
            _, _, event = await asyncio.wait_for(
                self.queue.get(),
                timeout=timeout
            )
            event.status = ProcessingStatus.PROCESSING.value
            return event
        except asyncio.TimeoutError:
            return None
    
    async def mark_processed(self, event_id: str) -> None:
        """
        Mark event as successfully processed.
        
        Args:
            event_id: Event identifier
        """
        self.processed_events.add(event_id)
        logger.debug(f"Event marked processed: {event_id}")
    
    async def mark_failed(self, event: DataEvent) -> None:
        """
        Mark event as failed (move to dead-letter queue if max retries exceeded).
        
        Args:
            event: DataEvent that failed
        """
        event.retry_count += 1
        
        if event.retry_count >= event.max_retries:
            self.dead_letter_queue.append(event)
            logger.warning(f"Event moved to DLQ: {event.event_id}")
        else:
            event.status = ProcessingStatus.RETRYING.value
            await self.enqueue(event)
            logger.debug(f"Event queued for retry: {event.event_id}")
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    def dlq_size(self) -> int:
        """Get dead-letter queue size."""
        return len(self.dead_letter_queue)


class AsyncPipeline:
    """
    High-performance async data pipeline.
    
    Responsibilities:
    - Queue management and coordination
    - Event processing and transformation
    - Error handling and retry logic
    - Batch database operations
    - Metrics and monitoring
    """
    
    def __init__(
        self,
        num_workers: int = 4,
        batch_size: int = 100,
        batch_timeout: float = 5.0
    ):
        """
        Initialize async pipeline.
        
        Args:
            num_workers: Number of async workers
            batch_size: Events per batch
            batch_timeout: Max time to wait before flushing batch
        """
        self.queue = AsyncQueue()
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.processors: Dict[str, Callable] = {}
        self.metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "batches_completed": 0
        }
        self.running = False
    
    def register_processor(
        self,
        event_type: str,
        processor: Callable[[DataEvent], Coroutine]
    ) -> None:
        """
        Register event processor.
        
        Args:
            event_type: Type of event to process
            processor: Async function to process event
        """
        self.processors[event_type] = processor
        logger.info(f"Processor registered for: {event_type}")
    
    async def process_event(self, event: DataEvent) -> bool:
        """
        Process single event.
        
        Args:
            event: DataEvent to process
        
        Returns:
            True if processed successfully
        """
        processor = self.processors.get(event.event_type)
        
        if not processor:
            logger.warning(f"No processor for event type: {event.event_type}")
            return False
        
        try:
            await processor(event)
            event.status = ProcessingStatus.COMPLETED.value
            await self.queue.mark_processed(event.event_id)
            self.metrics["events_processed"] += 1
            return True
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            event.status = ProcessingStatus.FAILED.value
            await self.queue.mark_failed(event)
            self.metrics["events_failed"] += 1
            return False
    
    async def batch_process(
        self,
        events: List[DataEvent],
        processor: Callable
    ) -> int:
        """
        Process batch of events.
        
        Args:
            events: List of DataEvents
            processor: Batch processing function
        
        Returns:
            Number of events processed
        """
        if not events:
            return 0
        
        try:
            result = await processor(events)
            self.metrics["batches_completed"] += 1
            logger.info(f"Batch processed: {len(events)} events")
            return len(events)
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return 0
    
    async def worker(self) -> None:
        """
        Worker coroutine that continuously processes events.
        """
        logger.info("Worker started")
        
        while self.running:
            event = await self.queue.dequeue(timeout=1.0)
            
            if event:
                await self.process_event(event)
            else:
                await asyncio.sleep(0.1)
    
    async def start(self) -> None:
        """
        Start pipeline workers.
        """
        self.running = True
        tasks = [
            asyncio.create_task(self.worker())
            for _ in range(self.num_workers)
        ]
        logger.info(f"Pipeline started with {self.num_workers} workers")
        await asyncio.gather(*tasks)
    
    async def stop(self) -> None:
        """
        Stop pipeline gracefully.
        """
        self.running = False
        logger.info("Pipeline stopping...")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get pipeline metrics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            **self.metrics,
            "queue_size": self.queue.size(),
            "dlq_size": self.queue.dlq_size(),
            "workers": self.num_workers
        }


if __name__ == "__main__":
    async def main():
        pipeline = AsyncPipeline(num_workers=4)
        
        # Register sample processor
        async def market_data_processor(event: DataEvent):
            await asyncio.sleep(0.01)
            logger.info(f"Processing market data: {event.symbol}")
        
        pipeline.register_processor(EventType.MARKET_DATA.value, market_data_processor)
        
        # Create sample events
        for i in range(10):
            event = DataEvent(
                event_id=f"evt_{i}",
                event_type=EventType.MARKET_DATA.value,
                exchange="binance",
                symbol="BTCUSDT",
                data={"price": 50000 + i * 100, "volume": 1000}
            )
            await pipeline.queue.enqueue(event)
        
        print(f"Pipeline metrics: {pipeline.get_metrics()}")
    
    asyncio.run(main())
