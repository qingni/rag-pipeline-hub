# Embedding API 配置说明

## 认证架构

本项目的嵌入服务涉及两层认证：

```
前端应用 → [认证层1] → 后端 API → [认证层2] → 外部 Embedding API
         (可选)              (必需)
```

### 认证层1：前端 → 后端（可选，开发环境禁用）

- **环境变量**: `EMBEDDING_CLIENT_API_KEY`
- **用途**: 保护后端 `/api/v1/embedding/*` 端点
- **开发建议**: **留空不设置**，自动禁用认证
- **生产建议**: 设置强密码保护 API

### 认证层2：后端 → 外部 API（必需）

- **环境变量**: `EMBEDDING_API_KEY`
- **用途**: 后端调用 `http://dev.fit-ai.woa.com/api/llmproxy`
- **必需设置**: 向外部 API 提供商获取有效的 API Key

## 配置步骤

### 1. 后端配置 (`backend/.env`)

```bash
# ========== 必需配置 ==========
# 外部 Embedding API 的密钥（联系 API 提供商获取）
EMBEDDING_API_KEY=your-actual-api-key-from-provider

# 外部 API 地址
EMBEDDING_API_BASE_URL=http://dev.fit-ai.woa.com/api/llmproxy

# ========== 可选配置 ==========
# 前端到后端的认证（开发环境建议注释掉）
# EMBEDDING_CLIENT_API_KEY=change-me

# 允许的前端源
FRONTEND_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173
```

### 2. 前端配置 (`frontend/.env`)

**开发环境不需要配置！** 前端代码已自动处理：
- 如果设置了 `VITE_EMBEDDING_API_KEY`，会发送 `X-API-Key` 头
- 如果未设置，正常发送请求（开发模式）

```bash
# 可选：仅在生产环境需要前端认证时设置
# VITE_EMBEDDING_API_KEY=your-client-api-key
```

## 启动服务

### 1. 获取 API Key

**重要**: 你需要联系 `dev.fit-ai.woa.com` 的管理员获取有效的 `EMBEDDING_API_KEY`

### 2. 配置 API Key

```bash
# 编辑 backend/.env
cd backend
vim .env

# 找到这一行并替换为实际的 key
EMBEDDING_API_KEY=your-actual-api-key-from-provider
```

### 3. 重启后端

```bash
# 方式1: 使用启动脚本（推荐）
./start_backend.sh

# 方式2: 手动启动
cd backend
source .venv/bin/activate  # 如果使用虚拟环境
uvicorn src.main:app --reload
```

启动时检查日志输出：
```
✅ Embedding API authentication DISABLED (dev mode)  # 开发模式，前端认证已禁用
```

### 4. 测试

```bash
# 健康检查
curl http://localhost:8000/api/v1/embedding/health

# 应该返回：
{
  "status": "healthy",
  "api_connectivity": true,
  "models_available": ["bge-m3", "qwen3-embedding-8b", ...],
  "authentication": "valid"
}
```

## 常见问题

### Q1: 401 Unauthorized

**原因**: 
- 后端的 `EMBEDDING_API_KEY` 无效或未设置
- 前端意外启用了 `EMBEDDING_CLIENT_API_KEY`

**解决**:
```bash
# 1. 确认后端 .env 中 EMBEDDING_CLIENT_API_KEY 被注释
grep "EMBEDDING_CLIENT_API_KEY" backend/.env
# 应该看到: # EMBEDDING_CLIENT_API_KEY=...

# 2. 确认 EMBEDDING_API_KEY 已设置
grep "EMBEDDING_API_KEY" backend/.env
# 应该看到: EMBEDDING_API_KEY=sk-xxxxx（实际的key）

# 3. 重启后端服务
```

### Q2: [object Object] 错误

已修复！现在会显示清晰的错误消息。如果看到后端返回的详细错误：
- `"Invalid API key"` - 需要更新 `EMBEDDING_API_KEY`
- `"Rate limit exceeded"` - API 调用频率过高，稍后重试
- `"Network timeout"` - 外部 API 响应超时

### Q3: 如何启用生产环境的前端认证？

```bash
# 1. 后端 .env
EMBEDDING_CLIENT_API_KEY=your-strong-secret-key

# 2. 前端 .env
VITE_EMBEDDING_API_KEY=your-strong-secret-key

# 注意：两者必须一致！
```

## 架构说明

### 开发模式（当前配置）
```
浏览器 → FastAPI Backend → External API
         (无认证)          (需要 EMBEDDING_API_KEY)
```

### 生产模式
```
浏览器 → FastAPI Backend → External API
     (需要 X-API-Key)   (需要 EMBEDDING_API_KEY)
```

## 相关文件

- `backend/src/middleware/api_key_middleware.py` - 前端认证中间件
- `backend/src/services/embedding_service.py` - 外部 API 调用
- `frontend/src/services/embeddingService.js` - 前端 API 客户端
- `frontend/src/stores/embedding.js` - Pinia store（错误处理）
