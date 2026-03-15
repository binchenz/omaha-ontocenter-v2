# 本地启动指南（无需 Docker）

## 前置条件

- Python 3.9+
- Node.js 16+
- npm 或 yarn

## 快速启动

### 1. 初始化数据库

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter_v2/backend
python init_db.py
```

预期输出：
```
Creating database tables...
✅ Database initialized successfully!
Database file: omaha.db
```

### 2. 启动后端（终端 1）

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter_v2/backend
./start_backend.sh
```

或手动启动：
```bash
cd /Users/wangfushuaiqi/omaha_ontocenter_v2/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端将运行在：http://localhost:8000
API 文档：http://localhost:8000/docs

### 3. 启动前端（终端 2）

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter_v2/frontend
./start_frontend.sh
```

或手动启动：
```bash
cd /Users/wangfushuaiqi/omaha_ontocenter_v2/frontend
npm install  # 首次运行
npm run dev
```

前端将运行在：http://localhost:5173 或 http://localhost:3000

### 4. 访问应用

打开浏览器访问：http://localhost:5173

## 测试流程

1. **注册用户**
   - 访问 http://localhost:5173
   - 点击"注册"
   - 填写用户名、邮箱、密码

2. **登录**
   - 使用注册的账号登录

3. **创建项目**
   - 点击"新建项目"
   - 填写项目名称和描述
   - 配置数据源（可选）

4. **测试 API**
   - 访问 http://localhost:8000/docs
   - 测试各个 API 端点

## 配置说明

当前使用 SQLite 数据库（`backend/omaha.db`），无需安装 PostgreSQL。

如果需要使用 PostgreSQL：
1. 启动 PostgreSQL 服务
2. 创建数据库：`createdb omaha_db`
3. 修改 `.env` 中的 `DATABASE_URL`

## 停止服务

在各个终端按 `Ctrl+C` 停止服务。

## 故障排除

### 后端启动失败

**问题：** 缺少依赖
```bash
cd backend
pip install --user -r requirements.txt
```

**问题：** 端口被占用
```bash
# 查找占用 8000 端口的进程
lsof -i :8000
# 杀死进程
kill -9 <PID>
```

### 前端启动失败

**问题：** 缺少依赖
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**问题：** 端口被占用
前端会自动使用下一个可用端口（5173, 5174, ...）

### 数据库问题

**重置数据库：**
```bash
cd backend
rm omaha.db
python init_db.py
```

## 开发模式特性

- ✅ 后端热重载（修改代码自动重启）
- ✅ 前端热重载（修改代码自动刷新）
- ✅ SQLite 数据库（无需额外服务）
- ✅ API 文档自动生成
- ✅ CORS 已配置

## 生产部署

生产环境建议使用 Docker Compose：
```bash
docker-compose up -d
```
