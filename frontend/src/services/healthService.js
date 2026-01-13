/**
 * Health check service
 */
import apiClient from './api'

const healthService = {
  /**
   * Get system health status
   */
  async getHealth() {
    return apiClient.get('/health')
  }
}

export default healthService