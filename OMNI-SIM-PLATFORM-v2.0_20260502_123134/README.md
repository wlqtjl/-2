# OMNI-SIM PLATFORM v2.0
## 游戏化培训平台

---

## 📋 项目简介

OMNI-SIM PLATFORM v2.0 是一个创新的游戏化培训平台，结合了：
- 3D射击游戏场景
- AI智能文档解析
- 自动题目生成
- 游戏化学习体验

### ✨ 核心特性

| 功能 | 描述 |
|------|------|
| 🎮 3D射击游戏 | 使用Three.js打造的沉浸式游戏场景 |
| 🤖 AI文档解析 | 支持DOCX/PDF/PPT/TEXT文档智能解析 |
| 📝 自动题目生成 | 根据文档内容自动生成培训题目 |
| 🏆 成就系统 | 学习进度可视化，成就收集 |
| 👥 角色管理 | 管理员、讲师、学员三种角色 |
| 📊 学习分析 | 学习数据统计和分析报告 |

---

## 🚀 快速开始

### 系统要求

- **Python**: 3.9 或更高版本
- **Node.js**: 16 或更高版本
- **npm**: 8 或更高版本
- **内存**: 建议 4GB 以上
- **磁盘空间**: 500MB 以上

### 一键安装

#### macOS/Linux

```bash
chmod +x install.sh
./install.sh
```

#### Windows

```cmd
install.bat
```

### 启动服务

#### macOS/Linux

```bash
chmod +x start.sh
./start.sh
```

#### Windows

```cmd
start.bat
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3002 |
| 后端API | http://localhost:8000 |
| 后端文档 | http://localhost:8000/docs |

---

## 👤 测试账号

> 以下仅为示例占位账号，请通过 `/auth/register` 或种子脚本创建真实账号；
> 切勿在公开仓库中提交真实邮箱与密码。

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | admin@example.com | （请自行设置） |
| 讲师 | instructor@example.com | （请自行设置） |
| 学员 | learner@example.com | （请自行设置） |

---

## 📁 项目结构

```
游戏平台2.0/
├── backend/                 # 后端服务
│   ├── apps/
│   │   ├── ai/             # AI模块
│   │   ├── api/            # API路由
│   │   └── core/           # 核心模块
│   ├── main.py             # 应用入口
│   ├── requirements.txt    # Python依赖
│   └── game_training.db    # SQLite数据库
│
├── frontend/               # 前端应用
│   └── apps/
│       └── web/            # Web前端
│           ├── src/
│           │   ├── components/  # React组件
│           │   ├── pages/       # 页面组件
│           │   └── api/         # API客户端
│           └── package.json
│
├── install.sh/bat          # 安装脚本
├── start.sh/bat            # 启动脚本
└── README.md              # 项目文档
```

---

## 🔧 配置说明

### 后端配置 (backend/.env)

```env
# 数据库配置
USE_SQLITE=true

# AI配置
DEEPSEEK_API_KEY=your_api_key
DEFAULT_AI_MODEL=deepseek
```

### 前端配置

前端配置文件位置: `frontend/apps/web/src/api/index.ts`

```typescript
const API_BASE_URL = 'http://localhost:8000';
```

---

## 🎯 使用指南

### 1. 作为管理员

1. 登录管理后台
2. 创建和管理课程
3. 上传培训文档
4. 管理用户账号

### 2. 作为讲师

1. 访问讲师工作台
2. 上传培训文档
3. AI自动生成关卡
4. 查看学员学习进度

### 3. 作为学员

1. 登录学习平台
2. 选择课程
3. 开始游戏闯关
4. 查看学习报告

---

## 🧠 AI功能说明

### 支持的文档格式

| 格式 | 说明 |
|------|------|
| DOCX | Word文档（推荐） |
| PDF | PDF文档 |
| PPTX | PowerPoint演示 |
| TXT | 纯文本文件 |

### AI模型选择

平台支持多种AI模型：

| 模型 | 配置键 |
|------|--------|
| DeepSeek | DEEPSEEK_API_KEY |
| 通义千问 | QIANWEN_API_KEY |
| Claude | CLAUDE_API_KEY |

### 关卡生成流程

```
文档上传 → 内容解析 → 知识点提取 → 题目生成 → 关卡配置 → 完成
```

---

## 🛠️ 开发指南

### 后端开发

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend/apps/web
npm run dev
```

### 数据库操作

项目使用SQLite数据库，位置：`backend/game_training.db`

使用SQLite工具查看数据：

```bash
cd backend
sqlite3 game_training.db
```

常用SQL命令：

```sql
-- 查看所有表
.tables

-- 查看用户
SELECT id, email, full_name, role FROM users;

-- 查看课程
SELECT id, name, status FROM courses;

-- 查看关卡
SELECT id, course_id, name FROM levels;
```

---

## 📊 数据库模型

### 主要数据表

| 表名 | 说明 |
|------|------|
| users | 用户账号 |
| tenants | 租户 |
| courses | 课程 |
| levels | 关卡 |
| questions | 题目 |
| level_attempts | 学习记录 |
| achievements | 成就系统 |

---

## 🔒 安全说明

### 开发环境

- 使用默认测试账号
- 无需配置AI API Key（使用fallback）
- SQLite数据库存储在本地

### 生产环境建议

1. 更换SECRET_KEY
2. 使用PostgreSQL数据库
3. 配置HTTPS
4. 限制API访问频率
5. 添加日志审计

---

## 🐛 常见问题

### Q: 服务启动失败？

A: 检查端口占用情况：

```bash
# macOS/Linux
lsof -ti:3000,8000

# Windows
netstat -ano | findstr ":3000"
```

### Q: AI功能不可用？

A: 配置API Key在 `backend/.env` 文件中

### Q: 数据库数据丢失？

A: 备份 `backend/game_training.db` 文件

### Q: 前端无法访问后端？

A: 检查后端是否正常启动，访问 http://localhost:8000/docs

---

## 📚 技术栈

### 后端

- FastAPI
- SQLAlchemy
- JWT认证
- 多AI模型支持

### 前端

- React 18
- TypeScript
- Vite
- Three.js
- Tailwind CSS

---

## 📄 许可证

© 2024 OMNI-SIM PLATFORM Team

---

## 📞 技术支持

如有问题，请查看：
- 后端API文档: http://localhost:8000/docs
- 项目GitHub: [待添加]

---

## 🎉 更新日志

### v2.0.0 (2024-05)
- ✨ 全新3D射击游戏场景
- 🤖 AI文档解析和关卡生成
- 📊 完整的学习数据分析
- 👥 多角色权限管理
- 🎯 成就系统
