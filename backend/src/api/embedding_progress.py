"""
Embedding progress SSE (Server-Sent Events) API.

Provides real-time progress updates for embedding operations.
"""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..models.embedding_task import EmbeddingProgress


router = APIRouter(prefix="/embedding/progress", tags=["Embedding Progress"])


# In-memory task progress storage (should be replaced with Redis in production)
_task_progress = {}
_task_cancellation = {}  # Track cancellation requests


def update_task_progress(task_id: str, progress: EmbeddingProgress):
    """Update task progress (called by embedding service)."""
    _task_progress[task_id] = progress.to_dict()


def get_task_progress(task_id: str) -> dict:
    """Get current task progress."""
    return _task_progress.get(task_id)


def clear_task_progress(task_id: str):
    """Clear task progress after completion."""
    if task_id in _task_progress:
        del _task_progress[task_id]
    if task_id in _task_cancellation:
        del _task_cancellation[task_id]


def request_task_cancellation(task_id: str) -> bool:
    """
    Request cancellation for a task.
    
    Args:
        task_id: Task ID to cancel
        
    Returns:
        True if cancellation was requested
    """
    if task_id not in _task_progress:
        return False
    
    _task_cancellation[task_id] = True
    
    # Update progress status
    if task_id in _task_progress:
        _task_progress[task_id]['status'] = 'cancelling'
    
    return True


def is_task_cancelled(task_id: str) -> bool:
    """Check if a task has been cancelled."""
    return _task_cancellation.get(task_id, False)


async def progress_event_generator(task_id: str) -> AsyncGenerator[dict, None]:
    """
    Generate progress events for SSE streaming.
    
    Args:
        task_id: Embedding task ID
        
    Yields:
        Progress event dictionaries
    """
    last_progress = None
    retry_count = 0
    max_retries = 300  # 5 minutes at 1 second intervals
    
    while retry_count < max_retries:
        progress = get_task_progress(task_id)
        
        if progress is None:
            # Task not started yet or already completed
            retry_count += 1
            await asyncio.sleep(1)
            continue
        
        # Only send if progress changed
        if progress != last_progress:
            last_progress = progress
            yield {
                "event": "progress",
                "data": json.dumps(progress),
            }
            
            # Check if completed
            status = progress.get('status', '')
            if status in ('completed', 'failed', 'cancelled', 'partial'):
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "status": status,
                        "message": "任务已完成" if status == 'completed' else f"任务状态: {status}",
                    }),
                }
                break
        
        await asyncio.sleep(0.5)  # Poll every 500ms
    
    # Timeout
    if retry_count >= max_retries:
        yield {
            "event": "timeout",
            "data": json.dumps({"message": "Progress tracking timed out"}),
        }


@router.get("/stream/{task_id}")
async def stream_progress(task_id: str):
    """
    Stream embedding progress via Server-Sent Events.
    
    Client can connect to this endpoint to receive real-time progress updates.
    
    Events:
    - progress: Contains current progress data
    - complete: Sent when task is finished
    - timeout: Sent if no progress for 5 minutes
    
    Example client usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/embedding/progress/stream/task-123');
    eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        updateProgressUI(progress);
    };
    eventSource.addEventListener('complete', (event) => {
        eventSource.close();
    });
    ```
    """
    return EventSourceResponse(progress_event_generator(task_id))


@router.get("/{task_id}")
async def get_progress(task_id: str):
    """
    Get current progress for an embedding task.
    
    Returns the latest progress snapshot (non-streaming).
    """
    progress = get_task_progress(task_id)
    
    if progress is None:
        raise HTTPException(
            status_code=404,
            detail=f"Progress not found for task {task_id}"
        )
    
    return progress


@router.delete("/{task_id}")
async def clear_progress(task_id: str):
    """
    Clear progress data for a completed task.
    
    Should be called after client has processed the final result.
    """
    clear_task_progress(task_id)
    return {"message": f"Progress cleared for task {task_id}"}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Request cancellation of an embedding task.
    
    This will signal the embedding service to stop processing.
    The task status will change to 'cancelling' and then 'cancelled'.
    
    Note: Cancellation is best-effort. Some items may still be processed
    if they were already in-flight when cancellation was requested.
    """
    success = request_task_cancellation(task_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found or already completed"
        )
    
    return {
        "message": f"Cancellation requested for task {task_id}",
        "status": "cancelling"
    }


# Batch progress streaming
async def batch_progress_generator(
    task_ids: list,
) -> AsyncGenerator[dict, None]:
    """
    Generate progress events for multiple tasks.
    
    Args:
        task_ids: List of task IDs to track
        
    Yields:
        Progress events for all tasks
    """
    active_tasks = set(task_ids)
    retry_count = 0
    max_retries = 600  # 10 minutes
    
    while active_tasks and retry_count < max_retries:
        completed = set()
        
        for task_id in active_tasks:
            progress = get_task_progress(task_id)
            
            if progress:
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "task_id": task_id,
                        **progress,
                    }),
                }
                
                status = progress.get('status', '')
                if status in ('completed', 'failed', 'cancelled', 'partial'):
                    completed.add(task_id)
        
        active_tasks -= completed
        
        if active_tasks:
            await asyncio.sleep(0.5)
            retry_count += 1
    
    # Final summary
    yield {
        "event": "batch_complete",
        "data": json.dumps({
            "completed_tasks": len(task_ids) - len(active_tasks),
            "total_tasks": len(task_ids),
        }),
    }


@router.get("/batch/stream")
async def stream_batch_progress(
    task_ids: str = Query(..., description="Comma-separated task IDs"),
):
    """
    Stream progress for multiple embedding tasks.
    
    Query params:
    - task_ids: Comma-separated list of task IDs
    
    Events include task_id in the data payload.
    """
    ids = [t.strip() for t in task_ids.split(",") if t.strip()]
    
    if not ids:
        raise HTTPException(
            status_code=400,
            detail="At least one task_id is required"
        )
    
    return EventSourceResponse(batch_progress_generator(ids))
