# 文档处理和检索系统 - 前端

Vue 3 前端应用，提供友好的用户界面。

## 快速开始

### 1. 安装依赖

```bash
npm install
# 或
pnpm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

### 3. 启动开发服务器

```bash
npm run dev
# 或
pnpm dev
```

应用将在 `http://localhost:5173` 启动。

### 4. 构建生产版本

```bash
npm run build
# 或
pnpm build
```

## 项目结构

```
frontend/
├── src/
│   ├── main.js              # 应用入口
│   ├── App.vue              # 根组件
│   ├── router/              # 路由配置
│   ├── stores/              # 状态管理 (Pinia)
│   ├── views/               # 页面视图
│   ├── components/          # 可复用组件
│   ├── services/            # API服务
│   └── assets/              # 静态资源
├── public/                  # 公共资源
├── index.html               # HTML模板
├── vite.config.js           # Vite配置
├── tailwind.config.js       # TailwindCSS配置
└── package.json             # 依赖配置
```

## 主要功能

- ✅ 文档上传和管理
- ✅ 文档加载
- ✅ 文档分块
- ✅ 向量嵌入
- ✅ 向量索引
- ✅ 搜索查询
- ✅ 文本生成

## 技术栈

- Vue 3 (Composition API)
- Vue Router 4
- Pinia (状态管理)
- Vite (构建工具)
- TailwindCSS (样式)
- Axios (HTTP客户端)

## 开发工具

```bash
# 代码格式化
npm run format

# 代码检查
npm run lint
```

## 环境要求

- Node.js 18+
- npm 或 pnpm
