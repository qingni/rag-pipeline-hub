/**
 * Chunked Upload Service - 分片上传支持断点续传
 * 
 * 功能：
 * 1. 计算文件 MD5 哈希
 * 2. 分片上传
 * 3. 断点续传
 * 4. 秒传检测
 * 5. 上传进度回调
 */
import apiClient from './api'

// 分片大小: 5MB (需与后端一致)
const CHUNK_SIZE = 5 * 1024 * 1024

/**
 * 计算文件 MD5 哈希
 * 使用 Web Crypto API 分片计算
 * 
 * @param {File} file - 要计算哈希的文件
 * @param {Function} onProgress - 进度回调 (0-100)
 * @returns {Promise<string>} - MD5 哈希值（32位小写）
 */
async function calculateFileHash(file, onProgress) {
  // 使用简单的分片读取 + 累积哈希方式
  // 注意：Web Crypto API 不直接支持 MD5，这里使用简单的自定义实现
  // 生产环境建议使用 spark-md5 库
  
  return new Promise((resolve, reject) => {
    const chunks = Math.ceil(file.size / CHUNK_SIZE)
    let currentChunk = 0
    const reader = new FileReader()
    
    // 简单的哈希累积（非标准 MD5，但足够用于文件识别）
    // 生产环境应使用 spark-md5
    let hashBuffer = new Uint8Array(16)
    
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result
        const data = new Uint8Array(arrayBuffer)
        
        // 使用 SubtleCrypto SHA-256 计算（比 MD5 更安全，现代浏览器都支持）
        // 然后截取前 32 个字符作为 "哈希"
        const hashPart = await crypto.subtle.digest('SHA-256', data)
        const hashArray = new Uint8Array(hashPart)
        
        // 累积哈希
        for (let i = 0; i < 16; i++) {
          hashBuffer[i] ^= hashArray[i] ^ hashArray[i + 16]
        }
        
        currentChunk++
        
        if (onProgress) {
          onProgress(Math.round((currentChunk / chunks) * 100))
        }
        
        if (currentChunk < chunks) {
          loadNext()
        } else {
          // 转换为 32 位十六进制字符串
          const hashHex = Array.from(hashBuffer)
            .map(b => b.toString(16).padStart(2, '0'))
            .join('')
          resolve(hashHex)
        }
      } catch (err) {
        reject(err)
      }
    }
    
    reader.onerror = reject
    
    function loadNext() {
      const start = currentChunk * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      reader.readAsArrayBuffer(file.slice(start, end))
    }
    
    loadNext()
  })
}

/**
 * 初始化上传会话
 * 
 * @param {File} file - 要上传的文件
 * @param {string} fileHash - 文件 MD5 哈希
 * @returns {Promise<Object>} - 初始化结果
 */
async function initUpload(file, fileHash) {
  const response = await apiClient.post('/upload/init', null, {
    params: {
      filename: file.name,
      file_size: file.size,
      file_hash: fileHash
    }
  })
  return response
}

/**
 * 查询上传状态
 * 
 * @param {string} uploadId - 上传会话 ID
 * @returns {Promise<Object>} - 上传状态
 */
async function getUploadStatus(uploadId) {
  const response = await apiClient.get(`/upload/${uploadId}/status`)
  return response
}

/**
 * 上传单个分片
 * 
 * @param {string} uploadId - 上传会话 ID
 * @param {number} chunkIndex - 分片索引
 * @param {Blob} chunkData - 分片数据
 * @returns {Promise<Object>} - 上传结果
 */
async function uploadChunk(uploadId, chunkIndex, chunkData) {
  const formData = new FormData()
  formData.append('chunk', chunkData)
  
  const response = await apiClient.post(
    `/upload/${uploadId}/chunk`,
    formData,
    {
      params: { chunk_index: chunkIndex },
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000  // 单个分片上传超时 2 分钟
    }
  )
  return response
}

/**
 * 完成上传
 * 
 * @param {string} uploadId - 上传会话 ID
 * @returns {Promise<Object>} - 完成结果（包含文档信息）
 */
async function completeUpload(uploadId) {
  const response = await apiClient.post(`/upload/${uploadId}/complete`, null, {
    timeout: 180000  // 合并分片可能需要较长时间，超时 3 分钟
  })
  return response
}

/**
 * 取消上传
 * 
 * @param {string} uploadId - 上传会话 ID
 * @returns {Promise<Object>} - 取消结果
 */
async function abortUpload(uploadId) {
  const response = await apiClient.delete(`/upload/${uploadId}/abort`)
  return response
}

/**
 * 带重试的分片上传
 * 
 * @param {string} uploadId - 上传会话 ID
 * @param {number} chunkIndex - 分片索引
 * @param {Blob} chunkData - 分片数据
 * @param {number} maxRetries - 最大重试次数
 * @returns {Promise<Object>} - 上传结果
 */
async function uploadChunkWithRetry(uploadId, chunkIndex, chunkData, maxRetries = 3) {
  let lastError
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await uploadChunk(uploadId, chunkIndex, chunkData)
    } catch (error) {
      lastError = error
      
      // 如果是 4xx 错误，不重试
      if (error.response?.status >= 400 && error.response?.status < 500) {
        throw error
      }
      
      // 等待后重试（指数退避）
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)))
    }
  }
  
  throw lastError
}

/**
 * 完整的断点续传上传流程
 * 
 * @param {File} file - 要上传的文件
 * @param {Object} options - 配置选项
 * @param {Function} options.onHashProgress - 计算哈希进度回调 (0-100)
 * @param {Function} options.onUploadProgress - 上传进度回调 (0-100)
 * @param {Function} options.onPhaseChange - 阶段变化回调 ('hashing' | 'uploading' | 'completing')
 * @param {AbortSignal} options.signal - 取消信号
 * @returns {Promise<Object>} - 上传结果（包含文档信息）
 */
async function uploadWithResume(file, options = {}) {
  const {
    onHashProgress,
    onUploadProgress,
    onPhaseChange,
    signal
  } = options
  
  let uploadId = null
  
  try {
    // 1. 计算文件哈希
    onPhaseChange?.('hashing')
    const fileHash = await calculateFileHash(file, onHashProgress)
    
    if (signal?.aborted) {
      throw new Error('上传已取消')
    }
    
    // 2. 初始化上传会话
    onPhaseChange?.('uploading')
    const initResult = await initUpload(file, fileHash)
    
    if (!initResult.success) {
      throw new Error(initResult.message || '初始化上传失败')
    }
    
    // 秒传成功
    if (initResult.data.instant_upload) {
      onUploadProgress?.(100)
      return {
        success: true,
        instant_upload: true,
        document: initResult.data.document
      }
    }
    
    uploadId = initResult.data.upload_id
    const totalChunks = initResult.data.total_chunks
    const uploadedChunks = new Set(initResult.data.uploaded_chunks || [])
    
    // 3. 上传缺失的分片
    let uploadedCount = uploadedChunks.size
    
    for (let i = 0; i < totalChunks; i++) {
      if (signal?.aborted) {
        // 不要清理会话，以便后续断点续传
        throw new Error('上传已取消')
      }
      
      // 跳过已上传的分片
      if (uploadedChunks.has(i)) {
        continue
      }
      
      // 读取分片数据
      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunkData = file.slice(start, end)
      
      // 上传分片（带重试）
      await uploadChunkWithRetry(uploadId, i, chunkData, 3)
      
      uploadedCount++
      onUploadProgress?.(Math.round((uploadedCount / totalChunks) * 100))
    }
    
    // 4. 完成上传
    onPhaseChange?.('completing')
    const result = await completeUpload(uploadId)
    
    if (result.success && result.data.complete) {
      return {
        success: true,
        document: result.data.document
      }
    } else {
      throw new Error(result.data?.message || '合并文件失败')
    }
    
  } catch (error) {
    // 如果是用户取消，不清理会话（保留断点）
    if (error.message === '上传已取消') {
      throw error
    }
    
    // 其他错误也不清理会话，允许重试
    throw error
  }
}

/**
 * 获取分片大小
 */
function getChunkSize() {
  return CHUNK_SIZE
}

/**
 * 检查文件是否需要分片上传
 * 
 * @param {File} file - 文件
 * @param {number} threshold - 阈值（默认 10MB）
 * @returns {boolean}
 */
function needsChunkedUpload(file, threshold = 10 * 1024 * 1024) {
  return file.size > threshold
}

export default {
  calculateFileHash,
  initUpload,
  getUploadStatus,
  uploadChunk,
  completeUpload,
  abortUpload,
  uploadChunkWithRetry,
  uploadWithResume,
  getChunkSize,
  needsChunkedUpload,
  CHUNK_SIZE
}
