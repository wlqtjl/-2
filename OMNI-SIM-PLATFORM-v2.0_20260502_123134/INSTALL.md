# OMNI-SIM PLATFORM v2.0 - 安装包说明

## 📦 安装包内容

```
游戏平台2.0/
├── README.md                      # 项目文档
├── .gitignore                     # Git忽略文件
│
├── install.sh                     # macOS/Linux 安装脚本
├── install.bat                    # Windows 安装脚本
├── start.sh                       # macOS/Linux 启动脚本
├── start.bat                      # Windows 启动脚本
│
├── backend/                       # 后端服务
│   ├── requirements.txt          # Python依赖
│   ├── main.py                   # 应用入口
│   ├── game_training.db          # SQLite数据库（已有示例数据）
│   ├── .env.example              # 配置文件示例
│   ├── apps/                     # 应用模块
│   │   ├── ai/                  # AI模块
│   │   ├── api/                 # API路由
│   │   └── core/                # 核心模块
│   └── schemas/                  # 数据模型
│
└── frontend/                      # 前端应用
    └── apps/web/                # Web前端
        ├── package.json          # Node依赖
        └── src/                 # 源代码
```

---

## 🚀 快速开始

### 方式一：一键安装（推荐）

#### macOS/Linux

```bash
chmod +x install.sh
./install.sh
./start.sh
```

#### Windows

```cmd
install.bat
start.bat
```

### 方式二：手动安装

#### 1. 后端安装

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate.bat  # Windows

pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 2. 前端安装

```bash
cd frontend/apps/web
npm install
npm run dev
```

---

## 📋 使用说明

### 访问应用

- **前端**: http://localhost:3002
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

### 测试账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | admin@example.com | （请通过种子脚本创建） |
| 讲师 | instructor@example.com | （请自行设置） |
| 学员 | learner@example.com | （请自行设置） |

---

## 🔧 配置说明

### 环境变量配置

编辑 `backend/.env` 文件：

```env
# AI配置（可选）
DEEPSEEK_API_KEY=your_api_key
QIANWEN_API_KEY=your_api_key
CLAUDE_API_KEY=your_api_key

# 数据库配置
USE_SQLITE=true
```

### 前端配置

编辑 `frontend/apps/web/src/api/index.ts`：

```typescript
const API_BASE_URL = 'http://localhost:8000';
```

---

## 📊 数据库

项目使用SQLite数据库，位置：`backend/game_training.db`

数据库已包含示例数据：
- 3个测试用户
- 3个示例课程
- 多个关卡和题目

### 数据库备份

```bash
# 备份数据库
cp backend/game_training.db backend/game_training.db.backup

# 恢复数据库
cp backend/game_training.db.backup backend/game_training.db
```

---

## 🤖 AI功能

### 支持的文档格式

- DOCX (Word文档)
- PDF
- PPTX (PowerPoint)
- TXT (纯文本)

### AI模型

默认使用fallback生成，如需真实AI：

1. 获取API Key
2. 配置到 `backend/.env`
3. 重启后端服务

---

## 🛠️ 故障排查

### 问题1：服务启动失败

```bash
# 检查端口占用
lsof -ti:3002,8000  # macOS/Linux
netstat -ano | findstr ":3002"  # Windows

# 检查后端日志
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 问题2：前端无法连接后端

1. 确认后端服务正常运行
2. 访问 http://localhost:8000/docs
3. 检查API地址配置

### 问题3：依赖安装失败

```bash
# 升级pip
pip install --upgrade pip

# 重新安装
cd backend
pip install -r requirements.txt
```

---

## 📚 开发说明

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

---

## 🎯 下一步

1. ✅ 安装完成后，访问 http://localhost:3002
2. ✅ 使用测试账号登录
3. ✅ 体验游戏化学习
4. ✅ 尝试上传培训文档生成关卡
5. ✅ 查看学习数据和分析报告

---

## 📞 技术支持

如有问题，请：
1. 查看 README.md
2. 访问 http://localhost:8000/docs
3. 检查项目目录下的示例数据

---

## 📄 版本信息

- **版本**: v2.0.0
- **发布日期**: 2024-05
- **状态**: 开发版（含示例数据）
