# User Story 1 快速启动指南

## 🎯 目标

验证User Story 1完整功能：上传PDF → PyMuPDF加载 → 全文解析 → JSON结果验证

## ⚡ 快速开始（3步）

### 1️⃣ 安装依赖

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 2️⃣ 运行集成测试

```bash
# 自动启动服务器并运行测试
./run_integration_test.sh
```

### 3️⃣ 查看结果

看到以下输出即为成功：
```
✓ ALL TESTS PASSED - User Story 1 is functional!
```

## 📋 详细步骤

### 选项A: 自动化测试（推荐）

一键运行：
```bash
./run_integration_test.sh
```

脚本自动执行：
- ✅ 检查/启动后端服务器
- ✅ 创建测试PDF文件
- ✅ 执行完整测试流程
- ✅ 验证结果和性能
- ✅ 清理测试数据

### 选项B: 手动测试

**终端1 - 启动后端**
```bash
cd backend
python -m src.main
```

**终端2 - 运行测试**
```bash
cd backend
python tests/test_integration_us1.py
```

## 🧪 测试内容

测试会执行以下操作：

1. **健康检查** - 验证API服务可用
2. **创建测试PDF** - 自动生成包含文本的PDF文件
3. **上传文档** - POST /api/v1/documents
4. **加载文档** - POST /api/v1/processing/load (PyMuPDF)
5. **解析文档** - POST /api/v1/processing/parse (full_text)
6. **验证结果** - 检查JSON文件完整性
7. **性能测试** - 验证处理时间 < 3分钟

## ✅ 成功标准

- [x] 所有API调用返回200状态码
- [x] 文档上传成功（ID生成）
- [x] PyMuPDF加载完成（result_id生成）
- [x] 全文解析完成（content提取）
- [x] JSON结果文件存在且有效
- [x] 处理时间 < 180秒
- [x] 内容非空且包含预期文本

## 🐛 故障排除

### 问题: "Cannot connect to API server"

**解决方案：**
```bash
# 启动后端服务器
cd backend
python -m src.main
```

### 问题: "ModuleNotFoundError"

**解决方案：**
```bash
# 安装依赖
cd backend
pip install -r requirements.txt
```

### 问题: "Permission denied"

**解决方案：**
```bash
# 给脚本添加执行权限
chmod +x run_integration_test.sh
```

### 问题: 端口8000被占用

**解决方案：**
```bash
# 查找占用进程
lsof -i :8000

# 杀掉进程
kill -9 <PID>
```

## 📊 测试输出示例

```
============================================================
User Story 1 - Integration Test
============================================================

[10:30:15] [INFO] Checking API health...
[10:30:15] [INFO] ✓ API server is healthy
[10:30:15] [INFO] ✓ Test PDF exists: backend/tests/fixtures/sample.pdf

=== STEP 1: Upload Document ===
[10:30:15] [INFO] ✓ Document uploaded successfully
[10:30:15] [INFO]   - ID: 1
[10:30:15] [INFO]   - Filename: test_document.pdf
[10:30:15] [INFO]   - Size: 2048 bytes

=== STEP 2: Load with PyMuPDF ===
[10:30:16] [INFO] ✓ Document loaded successfully
[10:30:16] [INFO]   - Result ID: 1
[10:30:16] [INFO]   - Provider: pymupdf

=== STEP 3: Parse Document (full_text) ===
[10:30:16] [INFO] ✓ Document parsed successfully
[10:30:16] [INFO]   - Result ID: 2

=== STEP 4: Verify JSON Results ===
[10:30:16] [INFO] ✓ Retrieved result details
[10:30:16] [INFO] ✓ Result file exists
[10:30:16] [INFO] ✓ Result JSON is valid
[10:30:16] [INFO] ✓ Content extracted successfully

=== Performance Verification ===
[10:30:16] [INFO] Total processing time: 1.23s
[10:30:16] [INFO] ✓ Performance meets SC-001 (< 3 min)

=== Cleanup ===
[10:30:16] [INFO] ✓ Deleted test document: 1

============================================================
[10:30:16] [SUCCESS] ✓ ALL TESTS PASSED - User Story 1 is functional!
============================================================
```

## 🔍 手动验证（可选）

启动服务器后，访问：

1. **API文档**: http://localhost:8000/docs
2. **健康检查**: http://localhost:8000/health

手动测试上传：
```bash
# 上传文档
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@sample.pdf"

# 查看文档列表
curl "http://localhost:8000/api/v1/documents"
```

## 📁 相关文件

```
spec-demo/
├── run_integration_test.sh          # 自动化测试脚本
├── TEST_US1.md                       # 详细测试文档
├── QUICKSTART_US1.md                 # 本文件
├── backend/
│   ├── tests/
│   │   ├── test_integration_us1.py  # 集成测试脚本
│   │   └── fixtures/
│   │       └── sample.pdf            # 自动生成
│   ├── storage/
│   │   ├── uploads/                  # 上传的文档
│   │   └── results/                  # 处理结果JSON
│   └── src/
│       └── main.py                   # 后端入口
└── specs/
    └── 001-document-processing/
        └── tasks.md                  # 任务清单（T058✅）
```

## 📈 下一步

User Story 1 测试通过后：

1. **启动前端验证UI** 
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   访问: http://localhost:5173

2. **继续User Story 2** - 文档分块和向量嵌入
3. **继续User Story 3** - 向量索引和搜索
4. **继续User Story 4** - 智能文本生成

## 💡 提示

- 使用 `--no-cleanup` 保留测试数据用于调试
- 查看 `logs/backend.log` 了解详细日志
- 所有处理结果保存在 `backend/storage/results/`
- 测试会自动创建PDF，无需手动准备

---

**状态**: ✅ User Story 1 实施完成  
**任务**: T058 集成测试  
**测试覆盖**: SC-001 (性能), SC-008 (数据完整性)
