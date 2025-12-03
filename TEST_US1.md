# User Story 1 集成测试指南

## 测试目标

验证User Story 1的完整工作流程：
1. **上传PDF文档** - 验证文件上传功能
2. **使用PyMuPDF加载** - 验证文档加载功能  
3. **全文解析** - 验证文档解析功能
4. **JSON结果验证** - 验证结果存储和数据完整性

## 测试覆盖

- ✅ **T058**: 完整工作流程测试
- ✅ **SC-001**: 文档处理时间 < 3分钟
- ✅ **SC-008**: 100% 数据完整性（JSON结果完整性）

## 前置条件

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境

确保 `backend/.env` 文件存在（可从 `.env.example` 复制）：

```bash
cd backend
cp .env.example .env
```

检查配置：
- `UPLOAD_DIR=storage/uploads`
- `RESULTS_DIR=storage/results`
- `DATABASE_URL=sqlite:///./storage/app.db`

## 运行方式

### 方式1: 使用自动化脚本（推荐）

```bash
# 在项目根目录执行
./run_integration_test.sh
```

脚本会自动：
- 检查并启动后端服务器
- 安装测试依赖
- 运行集成测试
- 显示详细的测试结果

选项：
```bash
# 测试后不清理数据（用于调试）
./run_integration_test.sh --no-cleanup
```

### 方式2: 手动运行

#### Step 1: 启动后端服务器

```bash
cd backend
python -m src.main
```

服务器启动后访问: http://localhost:8000/docs

#### Step 2: 运行集成测试

在**新终端窗口**中：

```bash
cd backend
python tests/test_integration_us1.py
```

自定义选项：
```bash
# 指定API地址
python tests/test_integration_us1.py --api-url http://localhost:8000

# 测试后不清理数据
python tests/test_integration_us1.py --no-cleanup
```

## 测试流程详解

### 1. 健康检查
```
[INFO] Checking API health...
✓ API server is healthy
```

### 2. 创建测试PDF
```
[INFO] Creating test PDF file...
✓ Created test PDF: backend/tests/fixtures/sample.pdf
```

测试PDF包含：
- 第1页：标题、介绍、Section 1
- 第2页：主要内容、加载方法列表

### 3. 上传文档
```
=== STEP 1: Upload Document ===
✓ Document uploaded successfully
  - ID: 1
  - Filename: test_document.pdf
  - Size: 1234 bytes
  - Format: pdf
```

调用API: `POST /api/v1/documents`

### 4. 加载文档
```
=== STEP 2: Load with PyMuPDF ===
✓ Document loaded successfully
  - Result ID: 1
  - Provider: pymupdf
  - Status: completed
  - Result Path: results/1_load_1234567890.json
```

调用API: `POST /api/v1/processing/load`

参数:
```json
{
  "document_id": 1,
  "loader_type": "pymupdf"
}
```

### 5. 解析文档
```
=== STEP 3: Parse Document (full_text) ===
✓ Document parsed successfully
  - Result ID: 2
  - Provider: internal
  - Status: completed
  - Result Path: results/1_parse_1234567890.json
```

调用API: `POST /api/v1/processing/parse`

参数:
```json
{
  "document_id": 1,
  "parse_mode": "full_text",
  "include_tables": false
}
```

### 6. 验证结果
```
=== STEP 4: Verify JSON Results ===
✓ Retrieved result details
✓ Result file exists: backend/results/1_parse_1234567890.json
✓ Result JSON is valid
  - Keys: ['content', 'metadata', 'parse_mode']
  - Content length: 512 chars
✓ Content extracted successfully
  - Preview: Test Document for Integration Testing...
```

验证内容：
- JSON文件存在
- JSON格式有效
- 包含必需字段：content, metadata
- 内容非空
- 元数据完整

### 7. 性能验证
```
=== Performance Verification ===
Total processing time: 2.45s
✓ Performance meets SC-001 (< 3 min)
```

### 8. 清理
```
=== Cleanup ===
✓ Deleted test document: 1
```

删除测试文档和相关处理结果。

## 预期结果

### 成功输出
```
============================================================
✓ ALL TESTS PASSED - User Story 1 is functional!
============================================================
```

退出码: `0`

### 失败情况

如果任何步骤失败，会显示：
```
✗ TEST FAILED at step: <step_name>
```

退出码: `1`

常见失败原因：
1. **后端服务器未运行** - 确保 `python -m src.main` 已启动
2. **端口冲突** - 确保8000端口未被占用
3. **依赖缺失** - 运行 `pip install -r requirements.txt`
4. **权限问题** - 确保有storage目录的写权限

## 验证标准

### ✅ 功能验证
- [x] 文档上传成功（50MB以内）
- [x] PyMuPDF加载成功
- [x] 全文解析成功
- [x] JSON结果正确保存
- [x] 结果可以查询和检索

### ✅ 性能验证
- [x] 处理时间 < 3分钟（SC-001）
- [x] 响应码正确（200）
- [x] 无服务器错误

### ✅ 数据完整性验证  
- [x] JSON格式有效
- [x] 必需字段存在（content, metadata）
- [x] 内容非空
- [x] 元数据完整（pages, provider, timestamp等）

## 调试技巧

### 查看后端日志
```bash
tail -f logs/backend.log
```

### 保留测试数据
```bash
# 使用 --no-cleanup 选项
python tests/test_integration_us1.py --no-cleanup
```

然后通过API浏览器查看：
- http://localhost:8000/docs
- GET /api/v1/documents
- GET /api/v1/processing/results/{document_id}

### 手动验证JSON文件
```bash
# 查看处理结果
cat backend/storage/results/1_parse_*.json | jq .

# 检查文件内容
ls -lh backend/storage/results/
```

### 测试单个API端点
```bash
# 健康检查
curl http://localhost:8000/health

# 获取文档列表
curl http://localhost:8000/api/v1/documents

# 查看API文档
open http://localhost:8000/docs
```

## 成功标准

测试通过需要满足：

1. ✅ 所有4个步骤成功完成
2. ✅ 无错误或异常
3. ✅ 处理时间 < 180秒
4. ✅ JSON结果包含有效内容
5. ✅ 退出码为0

## 后续步骤

User Story 1 测试通过后，可以继续：

1. **User Story 2** - 文档分块和向量嵌入（T059-T080）
2. **User Story 3** - 向量索引和搜索（T081-T103）
3. **User Story 4** - 智能文本生成（T104-T121）

## 相关文件

- 测试脚本: `backend/tests/test_integration_us1.py`
- 自动化脚本: `run_integration_test.sh`
- 任务清单: `specs/001-document-processing/tasks.md`
- API文档: http://localhost:8000/docs

## 帮助

如果遇到问题：

1. 检查后端日志: `logs/backend.log`
2. 确认服务器运行: `curl http://localhost:8000/health`
3. 验证依赖安装: `pip list | grep -E "fastapi|pymupdf|sqlalchemy"`
4. 检查Python版本: `python --version` (需要 3.11+)

---

**测试任务**: T058  
**User Story**: US1 - 文档上传和基础处理  
**状态**: ✅ 实施完成，待运行验证
