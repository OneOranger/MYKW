# AI Knowledge Vault - 个人 AI 知识库系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![React](https://img.shields.io/badge/React-18.3+-61dafb.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-3178c6.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**一个功能完备的本地部署个人 AI 知识库系统，支持 RAG 检索、智能对话、自动知识升级**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [系统架构](#-系统架构) • [API 文档](#-api-文档) • [开发指南](#-开发指南)

</div>

---

## 📖 项目简介

AI Knowledge Vault 是一个**本地优先**（Local-First）的个人 AI 知识库系统，结合了先进的 RAG（Retrieval-Augmented Generation）技术、智能记忆管理和自动化知识升级机制。系统能够在离线环境下运行，保护您的隐私，同时提供强大的知识管理和智能问答能力。

### 核心亮点

- 🔒 **本地优先**：所有数据存储在本机，无需云端，保护隐私
- 🧠 **智能记忆**：短期 + 长期记忆机制，支持多轮上下文对话
- 📚 **自动升级**：从对话中自动提取知识点，经审核后入库
- 🔍 **混合检索**：本地知识库未命中时自动联网补充
- 📊 **完整溯源**：每次回答提供详细的引用来源和检索元数据
- ⚙️ **Prompt 工程**：可配置的 Prompt 管理系统

---

## ✨ 功能特性

### 1. 智能对话系统

- **多轮对话**：支持上下文感知的连续对话
- **双记忆机制**：
  - 短期记忆：当前会话上下文
  - 长期记忆：跨会话知识持久化
- **意图识别**：自动区分知识查询、闲聊和任务指令

### 2. 知识库管理

- **多格式支持**：TXT、MD、PDF、DOCX、PPTX、XLSX、CSV
- **批量上传**：支持文件和文件夹上传
- **自动分类**：智能识别知识领域并自动分类
- **去重合并**：自动检测重复知识并智能合并
- **版本管理**：完整的知识文档版本追踪

### 3. RAG 检索增强

- **本地 Embedding**：使用 sentence-transformers 进行文本向量化
- **向量数据库**：LanceDB 高性能向量存储
- **元数据过滤**：支持按领域、标签等多维度过滤
- **引用溯源**：每个回答附带详细的引用来源

### 4. 自动知识升级

当知识库中没有相关内容时：

1. AI 会告知"当前知识库中没有相关知识内容"
2. 结合互联网搜索提供回答
3. 自动提取知识点生成候选文档
4. 用户审核后可一键入库

### 5. Prompt 工程管理

- YAML 配置文件管理
- 支持系统提示词、用户提示词、示例管理
- 版本控制和回归测试

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 对话界面  │  │ 知识管理  │  │ 审核面板  │  │ 元数据展示│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                  Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Knowledge Agent Core                     │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  │  │
│  │  │ Memory  │  │ Retriever│  │  Auto Upgrade       │  │  │
│  │  │ Manager │  │ Engine  │  │  Pipeline           │  │  │
│  │  └─────────┘  └─────────┘  └─────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │LanceDB   │  │ Documents│  │ Memory   │  │  Logs    │   │
│  │VectorDB  │  │ Storage  │  │ Storage  │  │ System   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

#### 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | FastAPI 0.115+ | 高性能异步 API |
| **向量数据库** | LanceDB 0.30+ | 本地向量存储 |
| **Embedding** | sentence-transformers 3.0+ | 文本向量化 |
| **LLM** | OpenAI API (兼容) | 通过代理访问 |
| **文档处理** | pypdf, python-docx, python-pptx, pandas | 多格式解析 |
| **配置管理** | pydantic-settings | 类型安全配置 |

#### 前端

| 组件 | 技术 | 说明 |
|------|------|------|
| **框架** | React 18.3 + TypeScript | 类型安全的 UI |
| **构建工具** | Vite 5.4+ | 快速开发体验 |
| **UI 组件** | shadcn/ui + Radix UI | 现代化组件库 |
| **样式** | Tailwind CSS 3.4+ | 实用优先 CSS |
| **状态管理** | TanStack Query | 数据获取和缓存 |
| **路由** | React Router 6.30+ | 客户端路由 |

---

## 🚀 快速开始

### 前置要求

- **Python** 3.10+
- **Node.js** 18+
- **Git** 2.30+
- **OpenAI API Key**（支持兼容的代理）

### 1. 克隆仓库

```bash
git clone https://github.com/OneOranger/MYKW.git
cd MYKW
```

### 2. 后端启动

```bash
# 进入后端目录
cd ai-konwledge-backend

# 激活虚拟环境 (PowerShell)
.\.venv\Scripts\Activate.ps1
conda deactivate

# 激活虚拟环境 (CMD)
.\.venv\Scripts\activate.bat

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 启动服务
uvicorn aipayment_kb_agent.api.app:app --host 127.0.0.1 --port 8000 --reload
```

后端服务将在 `http://127.0.0.1:8000` 启动，API 文档访问 `http://127.0.0.1:8000/docs`

### 3. 前端启动

```bash
# 进入前端目录
cd ai-knowledge-vault

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 4. 验证安装

访问前端界面，尝试以下操作：

1. 发送一条消息测试对话功能
2. 上传一个文档测试知识库管理
3. 查看检索元数据和引用来源

---

## 📡 API 文档

### 查询接口

#### 智能对话

```http
POST /api/v1/query?auto_upgrade=true
```

**Request Body:**
```json
{
  "session_id": "session_001",
  "message": "什么是 RAG 技术？",
  "auto_upgrade": true,
  "category": "technical",
  "top_k": 5
}
```

**Response:**
```json
{
  "content": "RAG (Retrieval-Augmented Generation) 是一种...",
  "hits": [
    {
      "id": "doc_001",
      "content": "...",
      "score": 0.92,
      "metadata": {
        "domain": "technical",
        "source": "rag_paper.pdf"
      }
    }
  ],
  "meta": {
    "retrieval_time_ms": 45,
    "total_candidates": 12,
    "source": "knowledge_base"
  },
  "citationOrder": ["doc_001", "doc_003"],
  "upgradeDecision": {
    "needs_upgrade": false
  }
}
```

### 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/admin/upload` | POST | 上传文档 |
| `/api/v1/admin/import/sync-raw` | POST | 扫描并导入新文档 |
| `/api/v1/admin/documents` | GET | 获取文档列表 |
| `/api/v1/admin/vectorstore/stats` | GET | 向量库统计信息 |
| `/api/v1/admin/upgrade/pending` | GET | 待审核知识列表 |
| `/api/v1/admin/upgrade/review/{id}` | POST | 审核知识候选 |

### 升级接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/upgrade/review` | GET | 获取待审核列表 |
| `/api/v1/upgrade/review/{id}` | POST | 审核操作 |
| `/api/v1/upgrade/trigger` | POST | 手动触发升级 |

完整 API 文档请参考 [API Spec](ai-konwledge-backend/docs/api_spec.md)

---

## 📂 项目结构

```
MYKW/
├── ai-knowledge-vault/              # 前端项目
│   ├── src/
│   │   ├── components/              # React 组件
│   │   │   ├── atlas/               # 核心业务组件
│   │   │   └── ui/                  # 基础 UI 组件
│   │   ├── lib/                     # 工具库和 API 客户端
│   │   ├── pages/                   # 页面组件
│   │   └── hooks/                   # 自定义 Hooks
│   ├── public/                      # 静态资源
│   └── package.json
│
├── ai-konwledge-backend/            # 后端项目
│   ├── src/aipayment_kb_agent/
│   │   ├── api/                     # FastAPI 路由
│   │   ├── core/                    # 核心 Agent 逻辑
│   │   ├── memory/                  # 记忆管理系统
│   │   ├── knowledge/               # RAG 知识库
│   │   ├── knowledge_ingestion/     # 知识自动摄入管道
│   │   ├── prompts/                 # Prompt 配置管理
│   │   ├── models/                  # Pydantic 数据模型
│   │   ├── tools/                   # 外部工具（如网络搜索）
│   │   └── utils/                   # 工具函数
│   ├── data/                        # 数据存储
│   │   ├── documents/               # 文档存储
│   │   ├── vectorstores/            # 向量数据库
│   │   └── models/                  # 本地模型
│   ├── docs/                        # 项目文档
│   ├── tests/                       # 测试用例
│   └── pyproject.toml
│
└── README.md
```

---

## ⚙️ 配置说明

### 环境变量

创建 `ai-konwledge-backend/.env` 文件：

```env
# OpenAI API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.gptsapi.net/v1
OPENAI_MODEL=gpt-4

# 服务配置
HOST=127.0.0.1
PORT=8000
DEBUG=true

# 知识库配置
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTORSTORE_PATH=data/vectorstores
TOP_K=5
SIMILARITY_THRESHOLD=0.7

# 自动升级配置
AUTO_UPGRADE_ENABLED=true
AUTO_UPGRADE_THRESHOLD=0.6
```

详细配置请参考 [.env.example](ai-konwledge-backend/.env.example)

---

## 🔧 开发指南

### 后端开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
ruff check . --fix
ruff format .

# 类型检查
mypy src/
```

### 前端开发

```bash
# 运行测试
npm run test

# 代码检查
npm run lint

# 构建生产版本
npm run build
```

### 添加新依赖

**后端：**
```bash
pip install new_package
pip freeze > requirements.txt
```

**前端：**
```bash
npm install new_package
```

---

## 📊 数据存储

### 文档存储

```
data/documents/
├── raw/                    # 原始上传文档
├── processed/              # 处理后的文档
└── auto_ingested/          # 自动升级生成的文档
    ├── pending/            # 待审核
    └── reviewed/           # 已审核
```

### 向量数据库

使用 LanceDB 存储知识向量：

```
data/vectorstores/
├── knowledge_chunks.lance/ # 向量数据
└── ingestion_manifest.json # 入库清单
```

### 记忆系统

```
data/
├── short_memory.json       # 短期记忆（会话级）
└── long_memory.json        # 长期记忆（持久化）
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

---

## 📝 日志系统

系统提供详细的日志记录：

- **请求级日志**：每个 API 请求的完整记录
- **节点级日志**：Agent 执行每个步骤的详细日志
- **性能日志**：检索时间、模型推理时间等

日志文件位置：`ai-konwledge-backend/logs/app.log`

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](ai-konwledge-backend/LICENSE) 文件了解详情

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [LanceDB](https://lancedb.com/) - 本地向量数据库
- [sentence-transformers](https://www.sbert.net/) - 文本嵌入模型
- [React](https://react.dev/) - 用户界面库
- [shadcn/ui](https://ui.shadcn.com/) - 精美的 UI 组件

---

## 📧 联系方式

- **作者**：OneOranger
- **项目主页**：https://github.com/OneOranger/MYKW
- **问题反馈**：https://github.com/OneOranger/MYKW/issues

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by OneOranger

</div>
