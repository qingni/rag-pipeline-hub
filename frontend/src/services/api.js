/**
 * API client configuration
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any request modifications here (e.g., auth tokens)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // Handle errors globally
    const errorMessage = error.response?.data?.error?.message || error.message || 'Unknown error occurred'
    console.error('API Error:', errorMessage)
    
    // Return structured error
    return Promise.reject({
      code: error.response?.data?.error?.code || 'UNKNOWN_ERROR',
      message: errorMessage,
      details: error.response?.data?.error?.details || {},
      status: error.response?.status
    })
  }
)

export default apiClient
