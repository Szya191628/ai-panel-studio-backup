# AI Panel Studio

AI 圆桌讨论 Web App MVP —— 让任何人都能瞬间召集一支"虚拟智库"，围绕任意议题展开深度碰撞。

## 功能特性

- 🎙️ **AI 嘉宾生成**：输入话题，AI 自动生成主持人+专家阵容
- 🎬 **演播厅模式**：实时观看 AI 驱动的圆桌讨论
- 👥 **专家状态小窗**：实时显示每个 Agent 的运行状态
- 💡 **实时共识与分歧**：讨论中持续提炼共识点和分歧点
- 📝 **实时 Transcript**：彩色区分发言人，实时记录讨论
- 📊 **收敛度追踪**：量化讨论进展

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + Vite + TypeScript |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 实时通信 | SSE (Server-Sent Events) |
| LLM | Deepseek V4 Pro |

## 项目结构

```
ai-panel-studio/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── config.py          # 配置管理
│   │   ├── schema.py          # 数据库 Schema
│   │   ├── models.py          # 数据模型
│   │   ├── db.py              # 数据库操作
│   │   ├── core.py            # 业务逻辑
│   │   ├── llm.py             # Deepseek API 调用
│   │   ├── sse.py             # SSE 事件管理
│   │   └── routes/            # API 路由
│   ├── tests/                 # 测试代码
│   └── requirements.txt       # Python 依赖
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API 服务
│   │   └── styles/            # 样式
│   └── package.json           # Node 依赖
├── docs/                       # 文档
│   ├── schema.md              # 数据库 Schema
│   └── API.md                 # API 文档
└── data/                       # 数据
    └── seeds.json             # 样例数据
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Deepseek API Key

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DEEPSEEK_API_KEY=your_api_key_here

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 访问应用

打开浏览器访问 http://localhost:3000

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | Deepseek API 密钥 | 必填 |
| `DEEPSEEK_BASE_URL` | API 基础 URL | https://api.deepseek.com |
| `DEEPSEEK_MODEL` | 模型名称 | deepseek-chat |
| `DATABASE_PATH` | 数据库路径 | ./data/panel_studio.db |
| `PORT` | 后端端口 | 8000 |

## API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/guests/generate` | AI 生成嘉宾阵容 |
| POST | `/api/discussions` | 创建讨论 |
| GET | `/api/discussions` | 获取讨论列表 |
| GET | `/api/discussions/{id}` | 获取讨论详情 |
| POST | `/api/discussions/{id}/confirm` | 确认阵容并开始 |
| POST | `/api/discussions/{id}/speak` | 记录发言 |
| POST | `/api/discussions/{id}/run` | 自动运行讨论 |
| GET | `/api/discussions/{id}/events` | SSE 实时事件流 |
| POST | `/api/discussions/{id}/end` | 结束讨论 |

## 开发范式

本项目遵循 SDD + DDD + TDD 开发范式：

### Phase 1: SDD（契约/模型驱动）
- 数据库 Schema 设计（docs/schema.md）
- API 接口契约定义（docs/API.md）
- 数据模型与类型定义

### Phase 2: DDD（设计驱动）
- UI/UX 设计（演播厅布局）
- 前端组件架构
- 状态管理方案

### Phase 3: TDD（测试驱动）
- 单元测试（backend/tests/）
- 核心逻辑实现
- 集成测试

### Phase 4: E2E（端到端测试）
- 系统联调
- 样例数据
- 质量闭环

## 核心架构

### 参考 agent-roundtable 的设计模式

1. **文件级 IPC**：discussion.json + 原子写入
2. **SSE 事件流**：speech_start/token/end 流式推送
3. **事务控制**：BEGIN IMMEDIATE / COMMIT / ROLLBACK
4. **收敛度计算**：consensus / (consensus + disagreement)

### 数据流

```
用户输入话题 → AI生成嘉宾 → 确认阵容 → 开始讨论
     ↓
主持人开场 → 专家轮流发言 → 提取共识分歧 → 计算收敛度
     ↓
达到轮次上限 → AI生成总结 → 结束讨论
```

## 样例数据

包含 5 个预设讨论话题：
1. "AI 会取代程序员吗？" - 技术专家 4 人
2. "远程办公 vs 现场办公" - 管理专家 3 人
3. "新能源汽车的未来" - 行业专家 5 人
4. "教育改革方向" - 教育专家 4 人
5. "数字货币的前景" - 金融专家 4 人

## 后续改进方向

- [ ] 用户认证系统
- [ ] 讨论回放功能
- [ ] 更多 LLM 模型支持
- [ ] 嘉宾头像生成
- [ ] 讨论导出（Markdown/PDF）
- [ ] 移动端适配优化

## 许可证

MIT
