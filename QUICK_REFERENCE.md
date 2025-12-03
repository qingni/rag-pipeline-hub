# 快速参考 - 文档加载功能

## 🚀 核心功能

### 1️⃣ 智能加载器选择

**自动模式** (推荐)
```
上传 PDF → 自动选择 PyMuPDF
上传 DOCX → 自动选择 DOCX
上传 DOC → 自动选择 DOC
上传 TXT/MD → 自动选择 Text
```

**手动模式**
- 可在自动选择后调整
- 适用于特殊需求场景

### 2️⃣ 文档管理

**表格视图优势**
- 📊 紧凑布局 - 一屏显示更多文档
- 🎯 信息清晰 - 所有关键信息一目了然
- ⚡ 操作便捷 - 点击选择，右键删除

**删除文档**
1. 点击文档行右侧"删除"
2. 确认对话框中点击"确认删除"
3. 完成！文档及相关数据已删除

### 3️⃣ 支持的格式

| 格式 | 图标 | 默认加载器 | 说明 |
|-----|------|----------|------|
| PDF | 📄 | pymupdf | 高性能PDF处理 |
| DOCX | 📝 | docx | Word 2007+ |
| DOC | 📝 | doc | 旧版Word |
| TXT | 📃 | text | 纯文本 |
| MD | 📋 | text | Markdown |

## 💡 使用技巧

### 快速加载文档
```
1. 拖拽文件到上传区域
   ↓
2. 等待上传完成
   ↓
3. 自动选中文档并切换加载器
   ↓
4. 点击"开始加载"
```

### 批量管理文档
```
1. 使用表格视图浏览所有文档
   ↓
2. 通过分页查看更多文档
   ↓
3. 点击文档名选中并查看详情
   ↓
4. 不需要的文档直接删除
```

### 处理特殊格式
```
DOC文件加载失败？
→ 安装 antiword: brew install antiword
→ 或转换为 DOCX 格式

预览不清晰？
→ 尝试切换其他加载器
→ PDF 可选: pymupdf, pypdf, unstructured
```

## 🎯 常见问题

### Q: 为什么要自动切换加载器？
**A:** 每种格式都有最优的加载器，自动切换可以：
- 提高加载成功率
- 获得最佳性能
- 减少用户操作

### Q: 删除文档会影响什么？
**A:** 会删除：
- 文档源文件
- 所有处理结果
- 相关JSON数据

不会影响：
- 其他文档
- 系统配置

### Q: 表格视图能否切回卡片视图？
**A:** 当前版本仅支持表格视图。如有需要，可在设置中添加切换选项（待开发）。

### Q: 如何查看文档详情？
**A:** 点击文档行即可在右侧看到：
- 文档预览
- 处理结果
- 相关信息

## 📋 快捷键 (计划中)

| 快捷键 | 功能 |
|-------|------|
| `Ctrl+U` | 打开上传对话框 |
| `↑↓` | 切换选中的文档 |
| `Enter` | 加载选中的文档 |
| `Delete` | 删除选中的文档 |
| `Ctrl+R` | 刷新文档列表 |

## 🔧 高级功能

### API 直接调用

**自动选择加载器**
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id"
  }'
```

**指定加载器**
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "loader_type": "docx"
  }'
```

**查看可用加载器**
```bash
curl http://localhost:8000/loaders
```

**删除文档**
```bash
curl -X DELETE "http://localhost:8000/documents/{document_id}"
```

### Python 示例

```python
from src.services.loading_service import loading_service
from src.storage.database import get_db

# 获取数据库会话
db = next(get_db())

# 自动选择加载器
result = loading_service.load_document(
    db=db,
    document_id="your-document-id"
)

print(f"使用的加载器: {result.provider}")
print(f"加载状态: {result.status}")
```

## 📊 性能指标

| 操作 | 平均时间 | 说明 |
|-----|---------|------|
| 上传文档 (1MB) | < 2秒 | 取决于网络速度 |
| 加载PDF (10页) | < 5秒 | 使用PyMuPDF |
| 加载DOCX (20页) | < 3秒 | 使用python-docx |
| 删除文档 | < 1秒 | 包含相关数据 |
| 列表刷新 | < 1秒 | 20个文档 |

## 🎨 UI状态说明

### 文档状态

| 状态 | 颜色 | 说明 |
|-----|------|------|
| 已上传 | 🔵 蓝色 | 刚上传，未加载 |
| 处理中 | 🟡 黄色 | 正在加载/处理 |
| 就绪 | 🟢 绿色 | 已完成，可使用 |
| 错误 | 🔴 红色 | 处理失败 |

### 交互反馈

| 操作 | 反馈 |
|-----|------|
| 悬停文档行 | 背景变浅灰色 |
| 选中文档 | 背景变蓝色 |
| 加载中 | 显示转圈动画 |
| 删除中 | 按钮显示转圈 |
| 操作成功 | 自动更新列表 |
| 操作失败 | 显示错误提示 |

## 📚 相关资源

- [完整文档](backend/DOCUMENT_LOADERS.md) - 加载器详细说明
- [UI优化说明](UI_OPTIMIZATION_UPDATE.md) - 界面改进详情
- [快速开始](QUICK_START_NEW_LOADERS.md) - 新手指南
- [API文档](http://localhost:8000/docs) - 完整API参考

## 🆘 需要帮助？

1. 查看 [常见问题](backend/DOCUMENT_LOADERS.md#常见问题)
2. 运行测试脚本: `python backend/examples/test_loaders.py`
3. 检查日志: `logs/`
4. 提交 Issue: [GitHub Issues](#)

---

**版本**: 1.1.0  
**最后更新**: 2025-12-03  
**下一个版本**: 批量操作、文档搜索、排序功能
