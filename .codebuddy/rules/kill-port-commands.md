---
description: 
alwaysApply: false
enabled: true
updatedAt: 2025-12-25T08:24:39.867Z
provider: 
---

# 端口释放命令规则

## 常用端口释放命令

当遇到 "Address already in use" 或端口占用错误时，使用以下命令释放端口。

### 释放 8000 端口（后端服务）

```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ 端口8000已释放" || echo "ℹ️ 端口8000没有被占用"
```

### 释放 5173 端口（前端服务）

```bash
lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "✅ 端口5173已释放" || echo "ℹ️ 端口5173没有被占用"
```

### 释放任意端口（通用模板）

```bash
lsof -ti:<PORT> | xargs kill -9 2>/dev/null && echo "✅ 端口<PORT>已释放" || echo "ℹ️ 端口<PORT>没有被占用"
```

### 查看端口占用情况

```bash
# 查看指定端口的占用情况
lsof -i:<PORT>

# 查看所有监听端口
lsof -iTCP -sTCP:LISTEN -n -P

# 查看特定进程的端口占用
ps aux | grep <PROCESS_NAME>
```

### 更温和的终止方式

```bash
# 先尝试正常终止（SIGTERM），失败后再强制终止（SIGKILL）
lsof -ti:<PORT> | xargs kill 2>/dev/null || lsof -ti:<PORT> | xargs kill -9 2>/dev/null
```

### 项目常用端口

| 端口 | 服务 | 释放命令 |
|------|------|----------|
| 8000 | 后端 API | `lsof -ti:8000 \| xargs kill -9 2>/dev/null` |
| 5173 | 前端开发服务器 | `lsof -ti:5173 \| xargs kill -9 2>/dev/null` |

## 使用说明

1. **首选方式**：直接使用上述命令释放端口
2. **检查进程**：如果需要确认是什么进程占用了端口，先用 `lsof -i:<PORT>` 查看
3. **优雅终止**：对于重要服务，建议先尝试 `kill` 而非 `kill -9`
4. **脚本化**：可以将常用端口释放命令添加到项目的启动脚本中

## 注意事项

- `kill -9` 是强制终止，可能导致进程无法正常清理资源
- 确认要终止的进程是否正确，避免误杀其他服务
- 在生产环境使用时要格外小心