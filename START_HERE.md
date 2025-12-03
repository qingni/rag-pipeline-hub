# 🎯 START HERE - 快速启动

## 🚀 启动服务（2步）

### 后端 - 终端1
```bash
./start_backend.sh
```
✅ 访问: http://localhost:8000/docs

### 前端 - 终端2  
```bash
./start_frontend.sh
```
✅ 访问: http://localhost:5173

---

## 📖 或者手动启动

### 后端
```bash
cd backend
pip install -r requirements.txt    # 仅首次
python -m src.main
```

### 前端
```bash
cd frontend
npm install                         # 仅首次
npm run dev
```

---

## ✅ 验证服务

```bash
# 检查后端
curl http://localhost:8000/health

# 检查前端
open http://localhost:5173
```

---

## 🧪 运行测试

```bash
./run_integration_test.sh
```

---

## 📚 更多帮助

- **完整启动指南**: [`STARTUP_GUIDE.md`](STARTUP_GUIDE.md)
- **快速上手**: [`QUICKSTART_US1.md`](QUICKSTART_US1.md)
- **测试指南**: [`TEST_US1.md`](TEST_US1.md)
- **文档索引**: [`US1_INDEX.md`](US1_INDEX.md)

---

## ❓ 遇到问题？

1. 检查Python版本: `python --version` (需要 3.11+)
2. 检查Node版本: `node --version` (需要 18+)
3. 查看 [`STARTUP_GUIDE.md`](STARTUP_GUIDE.md) 的常见问题部分
4. 检查端口占用: `lsof -i :8000` 和 `lsof -i :5173`

---

**最常见错误**:
- ❌ 依赖未安装 → 运行 `pip install -r requirements.txt` 和 `npm install`
- ❌ 端口被占用 → 修改 `.env` 中的 `PORT` 配置
- ❌ 权限问题 → 运行 `chmod +x *.sh`
