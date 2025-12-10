"""Chunking queue manager for concurrent task processing."""
import asyncio
from typing import List, Dict, Any
from datetime import datetime


class ChunkingQueueManager:
    """Manager for chunking task queue with concurrency control."""
    
    def __init__(self, max_concurrent: int = 3):
        """
        Initialize queue manager.
        
        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue()
        self.running_tasks = []
        self.is_running = False
    
    async def add_task(self, task_id: str, priority: int = 0):
        """
        Add task to queue.
        
        Args:
            task_id: Task ID
            priority: Task priority (higher = more urgent)
        """
        await self.queue.put((priority, task_id, datetime.now()))
    
    async def process_queue(self):
        """Process tasks from queue with concurrency control."""
        self.is_running = True
        
        while self.is_running:
            # Wait for available slot
            while len(self.running_tasks) >= self.max_concurrent:
                await asyncio.sleep(0.5)
            
            try:
                # Get next task (with timeout to allow checking is_running)
                priority, task_id, queued_at = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                # Start processing task
                task = asyncio.create_task(self._process_task(task_id))
                self.running_tasks.append(task)
                
                # Clean up completed tasks
                self.running_tasks = [t for t in self.running_tasks if not t.done()]
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Queue processing error: {e}")
    
    async def _process_task(self, task_id: str):
        """
        Process a single task.
        
        Args:
            task_id: Task ID to process
        """
        from ..storage.database import SessionLocal
        from ..services.chunking_service import chunking_service
        
        db = SessionLocal()
        try:
            chunking_service.process_chunking_task(task_id, db)
        except Exception as e:
            print(f"Task {task_id} failed: {e}")
        finally:
            db.close()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Queue status information
        """
        return {
            "queued_tasks": self.queue.qsize(),
            "running_tasks": len([t for t in self.running_tasks if not t.done()]),
            "max_concurrent": self.max_concurrent,
            "is_running": self.is_running
        }
    
    async def stop(self):
        """Stop queue processing."""
        self.is_running = False
        
        # Wait for running tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)


# Global queue manager instance
queue_manager = ChunkingQueueManager(max_concurrent=3)
