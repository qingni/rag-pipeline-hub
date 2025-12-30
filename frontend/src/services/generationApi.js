/**
 * Generation API service
 * 文本生成功能的 API 调用服务
 */

const API_BASE = '/api/v1/generation'

/**
 * 非流式生成文本
 * @param {Object} request - 生成请求
 * @param {string} request.question - 用户问题
 * @param {string} [request.model] - 模型名称
 * @param {number} [request.temperature] - 温度参数
 * @param {number} [request.max_tokens] - 最大输出长度
 * @param {Array} [request.context] - 检索上下文
 * @returns {Promise<Object>} 生成响应
 */
export async function generateText(request) {
  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ...request, stream: false })
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '生成失败')
  }
  
  return response.json()
}

/**
 * 流式生成文本
 * @param {Object} request - 生成请求
 * @param {Function} onChunk - 收到数据块时的回调
 * @param {Function} [onError] - 错误回调
 * @param {Function} [onComplete] - 完成回调
 * @returns {Object} 包含 abort 方法的控制对象
 */
export function generateTextStream(request, onChunk, onError, onComplete) {
  const abortController = new AbortController()
  
  fetch(`${API_BASE}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ...request, stream: true }),
    signal: abortController.signal
  })
    .then(async (response) => {
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || '生成失败')
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          if (onComplete) onComplete()
          break
        }
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              if (onComplete) onComplete()
              return
            }
            try {
              const chunk = JSON.parse(data)
              onChunk(chunk)
            } catch (e) {
              console.warn('Failed to parse SSE data:', data)
            }
          }
        }
      }
    })
    .catch((error) => {
      if (error.name === 'AbortError') {
        console.log('Generation aborted')
        return
      }
      if (onError) onError(error)
    })
  
  return {
    abort: () => abortController.abort()
  }
}

/**
 * 取消生成请求
 * @param {string} requestId - 请求ID
 * @returns {Promise<Object>} 响应
 */
export async function cancelGeneration(requestId) {
  const response = await fetch(`${API_BASE}/cancel/${requestId}`, {
    method: 'POST'
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '取消失败')
  }
  
  return response.json()
}

/**
 * 获取可用模型列表
 * @returns {Promise<Object>} 模型列表响应
 */
export async function getModels() {
  const response = await fetch(`${API_BASE}/models`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '获取模型列表失败')
  }
  
  return response.json()
}

/**
 * 获取生成历史列表
 * @param {Object} params - 查询参数
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.page_size=20] - 每页大小
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise<Object>} 历史列表响应
 */
export async function getHistoryList(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', params.page)
  if (params.page_size) searchParams.set('page_size', params.page_size)
  if (params.status) searchParams.set('status', params.status)
  
  const url = `${API_BASE}/history${searchParams.toString() ? '?' + searchParams.toString() : ''}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '获取历史列表失败')
  }
  
  return response.json()
}

/**
 * 获取生成历史详情
 * @param {number} id - 历史记录ID
 * @returns {Promise<Object>} 历史详情
 */
export async function getHistoryDetail(id) {
  const response = await fetch(`${API_BASE}/history/${id}`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '获取历史详情失败')
  }
  
  return response.json()
}

/**
 * 删除生成历史记录
 * @param {number} id - 历史记录ID
 * @returns {Promise<Object>} 响应
 */
export async function deleteHistory(id) {
  const response = await fetch(`${API_BASE}/history/${id}`, {
    method: 'DELETE'
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '删除失败')
  }
  
  return response.json()
}

/**
 * 清空所有生成历史
 * @returns {Promise<Object>} 响应
 */
export async function clearHistory() {
  const response = await fetch(`${API_BASE}/history/clear`, {
    method: 'DELETE'
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '清空失败')
  }
  
  return response.json()
}

export default {
  generateText,
  generateTextStream,
  cancelGeneration,
  getModels,
  getHistoryList,
  getHistoryDetail,
  deleteHistory,
  clearHistory
}
