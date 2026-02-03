/**
 * Embedding progress SSE service.
 * 
 * Provides real-time progress updates via Server-Sent Events.
 */

const BASE_URL = '/api/v1/embedding/progress';

/**
 * Create SSE connection for progress updates.
 * @param {string} taskId - Embedding task ID
 * @param {Object} callbacks - Event callbacks
 * @param {Function} callbacks.onProgress - Called on progress update
 * @param {Function} callbacks.onComplete - Called when task completes
 * @param {Function} callbacks.onError - Called on error
 * @returns {EventSource} SSE connection
 */
export const createProgressStream = (taskId, callbacks = {}) => {
  const { onProgress, onComplete, onError } = callbacks;
  
  const eventSource = new EventSource(`${BASE_URL}/stream/${taskId}`);
  
  // Handle progress events
  eventSource.addEventListener('progress', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onProgress) {
        onProgress(data);
      }
    } catch (e) {
      console.error('Failed to parse progress event:', e);
    }
  });
  
  // Handle complete event
  eventSource.addEventListener('complete', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onComplete) {
        onComplete(data);
      }
      eventSource.close();
    } catch (e) {
      console.error('Failed to parse complete event:', e);
    }
  });
  
  // Handle timeout event
  eventSource.addEventListener('timeout', (event) => {
    console.warn('Progress stream timed out');
    if (onError) {
      onError(new Error('Progress tracking timed out'));
    }
    eventSource.close();
  });
  
  // Handle errors
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    if (onError) {
      onError(error);
    }
    // Don't close on error - SSE will reconnect automatically
  };
  
  return eventSource;
};

/**
 * Create SSE connection for batch progress updates.
 * @param {string[]} taskIds - Array of task IDs
 * @param {Object} callbacks - Event callbacks
 * @returns {EventSource} SSE connection
 */
export const createBatchProgressStream = (taskIds, callbacks = {}) => {
  const { onProgress, onComplete, onError } = callbacks;
  
  const idsParam = taskIds.join(',');
  const eventSource = new EventSource(`${BASE_URL}/batch/stream?task_ids=${encodeURIComponent(idsParam)}`);
  
  // Handle individual progress events
  eventSource.addEventListener('progress', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onProgress) {
        onProgress(data);
      }
    } catch (e) {
      console.error('Failed to parse progress event:', e);
    }
  });
  
  // Handle batch complete event
  eventSource.addEventListener('batch_complete', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onComplete) {
        onComplete(data);
      }
      eventSource.close();
    } catch (e) {
      console.error('Failed to parse batch_complete event:', e);
    }
  });
  
  // Handle errors
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    if (onError) {
      onError(error);
    }
  };
  
  return eventSource;
};

/**
 * Get current progress snapshot (non-streaming).
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} Progress data
 */
export const getProgress = async (taskId) => {
  const response = await fetch(`${BASE_URL}/${taskId}`);
  if (!response.ok) {
    throw new Error(`Failed to get progress: ${response.statusText}`);
  }
  return response.json();
};

/**
 * Clear progress data for a completed task.
 * @param {string} taskId - Task ID
 * @returns {Promise<void>}
 */
export const clearProgress = async (taskId) => {
  const response = await fetch(`${BASE_URL}/${taskId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to clear progress: ${response.statusText}`);
  }
};

/**
 * Progress tracker class for managing SSE connections.
 */
export class ProgressTracker {
  constructor() {
    this.connections = new Map();
    this.progressData = new Map();
  }
  
  /**
   * Start tracking a task.
   * @param {string} taskId - Task ID
   * @param {Object} callbacks - Event callbacks
   */
  track(taskId, callbacks = {}) {
    // Close existing connection if any
    this.untrack(taskId);
    
    const onProgress = (data) => {
      this.progressData.set(taskId, data);
      if (callbacks.onProgress) {
        callbacks.onProgress(data);
      }
    };
    
    const onComplete = (data) => {
      this.progressData.set(taskId, { ...this.progressData.get(taskId), ...data, completed: true });
      if (callbacks.onComplete) {
        callbacks.onComplete(data);
      }
      this.connections.delete(taskId);
    };
    
    const onError = (error) => {
      if (callbacks.onError) {
        callbacks.onError(error);
      }
    };
    
    const connection = createProgressStream(taskId, { onProgress, onComplete, onError });
    this.connections.set(taskId, connection);
  }
  
  /**
   * Stop tracking a task.
   * @param {string} taskId - Task ID
   */
  untrack(taskId) {
    const connection = this.connections.get(taskId);
    if (connection) {
      connection.close();
      this.connections.delete(taskId);
    }
  }
  
  /**
   * Get progress data for a task.
   * @param {string} taskId - Task ID
   * @returns {Object|null} Progress data
   */
  getProgress(taskId) {
    return this.progressData.get(taskId) || null;
  }
  
  /**
   * Close all connections.
   */
  closeAll() {
    for (const connection of this.connections.values()) {
      connection.close();
    }
    this.connections.clear();
    this.progressData.clear();
  }
}

// Default tracker instance
let defaultTracker = null;

/**
 * Get default progress tracker.
 * @returns {ProgressTracker}
 */
export const getProgressTracker = () => {
  if (!defaultTracker) {
    defaultTracker = new ProgressTracker();
  }
  return defaultTracker;
};

export default {
  createProgressStream,
  createBatchProgressStream,
  getProgress,
  clearProgress,
  ProgressTracker,
  getProgressTracker,
};
