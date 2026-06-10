# 核心 Prompt 记录文档

> 本文档记录了使用 Claude Code + Deepseek V4 Pro 开发 AI Panel Studio 过程中最核心的 25 段 Prompt。
> 每段 Prompt 均标注了对应的开发范式阶段（SDD/DDD/TDD/E2E），并附有简要说明。

---

## 阶段一：SDD（Schema-Driven Development，契约/模型驱动）

### Prompt 1 - 业务需求分析

```
请根据以下业务需求，分析"AI圆桌讨论"系统的核心实体和关系：
- 用户输入话题，系统生成主持人+专家阵容
- 支持多轮讨论，每轮有发言记录
- 需要追踪共识和分歧
- 支持多讨论并行

请输出：核心实体列表、实体关系、关键业务规则。
```

**说明**：这是项目的起点，通过结构化的需求分析，让AI理解业务全貌，为后续数据建模奠定基础。

---

### Prompt 2 - 数据库 Schema 设计

```
请设计 SQLite 数据库 Schema，包含以下表：
1. discussions - 讨论表（id, topic, status, current_round, max_rounds, summary）
2. participants - 参与者表（id, discussion_id, name, role, title, stance, color）
3. speeches - 发言表（id, discussion_id, participant_id, content, round_number, speech_type）
4. findings - 共识/分歧表（id, discussion_id, content, finding_type, round_number）

要求：
- 使用 PRAGMA user_version 管理版本迁移
- 包含外键约束和级联删除
- 输出完整的 CREATE TABLE 语句
```

**说明**：精确定义数据库结构，这是 SDD 的核心——先定义数据契约，再实现业务逻辑。

---

### Prompt 3 - Dataclass 数据模型

```
请为上述数据库表设计对应的 Python dataclass 数据模型：
- Discussion, Participant, Speech, Finding, ConvergenceRecord, GuestProfile
- 使用 @dataclass 装饰器
- 包含类型注解
- 提供 from_dict() 类方法用于从数据库行构造
- 零外部依赖，仅使用 Python 标准库
```

**说明**：定义轻量级数据模型，与 ORM 解耦，便于单元测试和快速原型开发。

---

### Prompt 4 - Pydantic Schema 定义

```
请设计 Pydantic v2 Schema，定义 API 请求/响应契约：
- CreateDiscussionRequest: 创建讨论请求（topic, expert_count, max_rounds）
- DiscussionResponse: 讨论详情响应
- ParticipantResponse: 参与者响应
- SpeechResponse: 发言响应
- SSEEvent: SSE 事件格式

包含字段校验：长度限制、范围限制、默认值。
```

**说明**：API 契约是前后端协作的桥梁，Pydantic Schema 提供了运行时的数据校验能力。

---

### Prompt 5 - API 接口设计

```
请设计 RESTful API 接口，遵循以下规范：

讨论管理：
- POST /api/discussions - 创建讨论
- GET /api/discussions - 讨论列表
- GET /api/discussions/{id} - 讨论详情
- POST /api/discussions/{id}/confirm - 确认阵容并启动
- POST /api/discussions/{id}/end - 结束讨论

嘉宾生成：
- POST /api/guests/generate - 生成嘉宾阵容

SSE 流：
- GET /api/discussions/{id}/events - SSE 事件流

请输出 OpenAPI 格式的接口定义。
```

**说明**：清晰的 API 设计是前后端并行开发的前提，也是 SDD 阶段的关键产出。

---

## 阶段二：DDD（Design-Driven Development，设计驱动）

### Prompt 6 - 演播厅 UI 设计规范

```
请设计"AI圆桌演播厅"的视觉规范：

色彩系统（CSS变量）：
- --bg-primary: 深蓝色背景 #0a0e1a
- --accent-cyan: 青色强调 #00d4ff
- --accent-amber: 琥珀色 #ffb800
- --glass-bg: 玻璃态背景 rgba(255,255,255,0.05)

视觉效果：
- 噪点纹理叠加
- 环境光晕效果
- 玻璃拟态（backdrop-filter: blur）
- ON AIR 闪烁标识

布局：深色主题，模拟电视演播厅氛围。
```

**说明**：DDD 的核心是用设计驱动开发，演播厅的视觉风格是产品的核心差异化要素。

---

### Prompt 7 - 根布局组件

```
请实现 Next.js 14 的根布局 (layout.tsx)：

要求：
- 使用 App Router
- 加载 Google Fonts（Barlow Condensed, DM Sans, JetBrains Mono）
- 语言设为 zh-CN
- 包含顶部导航栏：品牌标识 "AI Panel Studio" + "ON AIR" 状态指示
- 深色主题，应用 globals.css 样式
- 响应式布局
```

**说明**：布局是页面的骨架，需要在早期确定，后续所有页面都基于此布局扩展。

---

### Prompt 8 - 首页设计与实现

```
请实现首页 (page.tsx)：

功能区域：
1. 快速创建区：
   - 话题输入框（placeholder: "输入讨论话题..."）
   - 嘉宾人数选择器（2-8人，默认4）
   - 讨论轮次选择器（1-20轮，默认3）
   - 5个预设快捷话题标签

2. 讨论列表区：
   - 卡片式展示所有讨论
   - 状态徽章（筹备中/进行中/已结束）
   - 参与者数量、轮次、共识度
   - 点击进入演播厅

样式：演播厅深色主题，卡片玻璃态效果。
```

**说明**：首页是用户的第一印象，需要兼顾功能性和视觉冲击力。

---

### Prompt 9 - 演播厅页面核心布局

```
请实现演播厅页面 (studio/[id]/page.tsx) 的核心布局：

区域划分（不依赖页面滚动，各区域独立滚动）：
1. 顶部控制栏：ON AIR 标识、话题标题、轮次信息、共识度进度条、自动运行/结束按钮
2. 左侧参与者面板：头像、姓名、职业、状态徽章（待机/准备中/发言中）
3. 中间主区域：
   - 思考过程面板（分析中/草稿阶段）
   - 讨论记录面板（发言列表，带头像、颜色标识、LIVE 流式标记）
4. 右侧面板：共识与分歧列表
5. 结束遮罩层：讨论结束时显示总结

响应式：超宽屏4列、桌面3列、平板2列、手机1列。
```

**说明**：演播厅是产品的核心页面，布局设计直接影响用户体验的沉浸感。

---

### Prompt 10 - 发言气泡组件

```
请设计发言气泡组件的样式：

- 每个发言人使用专属颜色标识
- 左侧显示头像（DiceBear API 生成）
- 右侧显示发言内容
- 支持流式显示：逐字出现，带光标闪烁动画
- LIVE 标记：流式播放时显示红色 "LIVE" 徽章
- 区分发言人类型：
  - 主持人：金色边框
  - 专家：各自专属颜色

CSS动画：
- @keyframes typing-cursor: 光标闪烁
- @keyframes speech-appear: 发言出现动画
```

**说明**：发言气泡是讨论内容的主要载体，流式显示增强了实时感和沉浸感。

---

### Prompt 11 - 参与者状态小窗

```
请设计参与者状态小窗组件：

每个参与者显示：
- 头像（DiceBear personas 风格）
- 姓名 + 职业/Title
- 状态徽章：待机(灰色) / 准备中(黄色) / 发言中(绿色)
- 思考摘要（当状态为"准备中"时显示）
- 发言意图指示器：反驳(红) / 补充(蓝) / 追问(紫) / 赞同(绿)

布局：网格排列，自适应容器宽度。
动画：状态切换时有过渡效果。
```

**说明**：状态小窗让用户能实时感知每个 Agent 的运行状态，增强"观看直播"的体验。

---

### Prompt 12 - 共识与分歧面板

```
请设计共识与分歧展示面板：

布局：
- 左右分栏或上下排列
- 共识区：绿色主题，列表展示共识点
- 分歧区：红色主题，列表展示分歧点

每条共识/分歧：
- 圆形标记 + 内容文本
- 来源轮次标注
- 新增项有高亮动画

底部：讨论总结（主持人生成的自然语言总结）

样式：玻璃态卡片，与演播厅主题一致。
```

**说明**：共识与分歧是讨论的核心产出，需要清晰直观地展示给用户。

---

## 阶段三：后端核心功能实现

### Prompt 13 - SSE 事件管理器

```
请实现 SSE 事件管理器 (sse.py)：

SSEManager 类：
- subscribe(discussion_id) -> asyncio.Queue: 为讨论创建订阅队列
- publish(discussion_id, event): 向所有订阅者推送事件
- 支持的事件类型：
  - init: 初始化数据
  - speech_start / speech_token / speech_end: 流式发言
  - thinking / draft: 思考过程
  - finding_update: 共识/分歧更新
  - round_summary: 轮次总结
  - status_change: 状态变更
  - participant_status: 参与者状态
  - error / ping: 错误和心跳

使用 asyncio.Queue 实现发布-订阅模式，每个讨论独立维护订阅队列列表。
```

**说明**：SSE 是实时通信的核心，发布-订阅模式保证了多讨论并行时的事件隔离。

---

### Prompt 14 - 数据库操作层

```
请实现数据库操作层 (db.py) - PanelDB 类：

核心方法：
- create_discussion(topic, expert_count, max_rounds) -> Discussion
- get_discussion(discussion_id) -> Discussion
- add_participant(discussion_id, name, role, title, stance, color) -> Participant
- record_speech(discussion_id, participant_id, content, round_number, speech_type) -> Speech
- add_finding(discussion_id, content, finding_type, round_number) -> Finding
- update_discussion_status(discussion_id, status)
- get_current_round_speeches(discussion_id, round_number) -> List[Speech]

特性：
- 使用原生 sqlite3，显式事务控制 (BEGIN IMMEDIATE/COMMIT/ROLLBACK)
- WAL 模式提升并发性能
- 自动轮次推进：检测每轮发言是否完成
```

**说明**：数据库层是数据持久化的基础，显式事务控制保证了数据一致性。

---

### Prompt 15 - LLM API 调用封装

```
请实现 LLM API 调用封装 (llm.py)：

核心函数：
1. generate_guests(topic, expert_count) -> dict
   - 生成主持人+专家阵容
   - 包含 fallback 默认嘉宾（当 LLM 调用失败时）

2. generate_speech(participant, transcript, round_number) -> str
   - 生成单条发言
   - 区分主持人和专家的 prompt

3. generate_speech_with_thinking(participant, transcript) -> AsyncGenerator
   - 带思考过程的流式发言
   - 三阶段：thinking -> draft -> speech

4. extract_findings(speeches) -> dict
   - 从发言中提取共识和分歧

5. generate_summary(transcript) -> str
   - 生成讨论总结

使用 httpx 异步调用 OpenAI 兼容 API。
```

**说明**：LLM 封装层是 AI 能力的核心，需要处理好错误恢复和流式输出。

---

### Prompt 16 - 业务逻辑核心

```
请实现业务逻辑核心 (core.py) - PanelCore 类：

编排讨论生命周期：
1. generate_guests(topic, expert_count) -> List[GuestProfile]
   - 调用 LLM 生成嘉宾

2. create_discussion(topic, guests) -> Discussion
   - 创建讨论并添加参与者

3. confirm_and_start(discussion_id) -> Discussion
   - 确认阵容，状态变为 active

4. generate_and_record_speech(discussion_id, participant_id) -> Speech
   - 调用 LLM 生成发言并记录

5. generate_and_record_speech_stream(discussion_id, participant_id) -> AsyncGenerator
   - 带思考过程的流式发言

6. run_discussion(discussion_id)
   - 自动运行完整讨论
   - 流程：主持人开场 -> 专家轮流发言 -> 提取共识 -> 计算收敛度 -> 生成总结
```

**说明**：业务核心层编排了整个讨论流程，是连接 API 层和底层服务的桥梁。

---

### Prompt 17 - API 路由实现

```
请实现讨论 API 路由 (routes/discussions.py)：

端点：
- POST /api/discussions - 创建讨论
  请求体：{topic, expert_count, max_rounds}
  响应：Discussion 对象

- GET /api/discussions - 讨论列表
  响应：Discussion[] 

- GET /api/discussions/{id} - 讨论详情
  响应：Discussion + participants + speeches

- POST /api/discussions/{id}/confirm - 确认阵容
  响应：Discussion (status: active)

- POST /api/discussions/{id}/auto-run - 自动运行
  异步启动讨论，通过 SSE 推送事件

- GET /api/discussions/{id}/events - SSE 事件流
  返回 StreamingResponse，Content-Type: text/event-stream

使用 FastAPI Router，依赖注入 PanelDB 和 PanelCore。
```

**说明**：API 路由是前后端交互的入口，需要处理好异步操作和错误响应。

---

## 阶段四：TDD（Test-Driven Development，测试驱动）

### Prompt 18 - 数据库单元测试

```
请为 PanelDB 编写单元测试 (test_db.py)：

测试用例：
1. test_create_discussion - 创建讨论
2. test_add_participant - 添加参与者
3. test_record_speech - 记录发言
4. test_add_finding - 添加共识/分歧
5. test_update_status - 更新状态
6. test_auto_round_advance - 自动轮次推进
7. test_convergence_calculation - 收敛度计算

要求：
- 使用 pytest 框架
- 每个测试使用独立的内存数据库 (":memory:")
- 测试前后自动创建/清理数据库
- 覆盖正常流程和边界情况
```

**说明**：TDD 的核心是先写测试再写实现，数据库层是最重要的测试对象。

---

### Prompt 19 - 业务逻辑测试

```
请为 PanelCore 编写单元测试：

测试用例：
1. test_generate_guests - 嘉宾生成（mock LLM 调用）
2. test_create_discussion - 创建讨论流程
3. test_confirm_and_start - 确认阵容流程
4. test_generate_speech - 发言生成（mock LLM）
5. test_extract_findings - 共识提取（mock LLM）
6. test_run_discussion_flow - 完整讨论流程

要求：
- 使用 unittest.mock 或 pytest-mock
- Mock 所有 LLM 调用，返回预设数据
- 验证数据库状态变化
- 验证函数调用次数和参数
```

**说明**：业务逻辑测试需要 Mock 外部依赖（LLM API），确保测试的可重复性。

---

### Prompt 20 - API 接口测试

```
请编写 API 接口测试 (test_api.py)：

使用 FastAPI TestClient 测试：

1. test_health_check - 健康检查端点
2. test_create_discussion - 创建讨论接口
3. test_list_discussions - 讨论列表接口
4. test_get_discussion - 讨论详情接口
5. test_confirm_discussion - 确认阵容接口
6. test_generate_guests - 嘉宾生成接口（mock）
7. test_sse_connection - SSE 连接测试

要求：
- 测试 HTTP 状态码
- 测试响应体结构
- 测试错误场景（404, 422, 500）
- 使用 fixtures 管理测试数据
```

**说明**：API 测试验证了接口的正确性，是前后端联调前的质量保障。

---

### Prompt 21 - Agent 节点测试

```
请为 LangGraph Agent 节点编写测试 (test_agents.py)：

测试用例：
1. test_moderator_opening - 主持人开场节点
2. test_expert_speech - 专家发言节点
3. test_summarizer - 总结节点
4. test_routing_logic - 路由逻辑
5. test_parallel_experts - 并行专家执行

要求：
- Mock LLM 调用
- 验证节点输入输出格式
- 验证状态流转正确性
- 测试错误处理
```

**说明**：Agent 节点是 AI 编排的核心，测试确保了讨论流程的正确性。

---

## 阶段五：E2E（端到端测试与质量闭环）

### Prompt 22 - E2E 测试脚本

```
请编写端到端测试脚本 (test-demo.py)：

测试流程：
1. 启动后端服务
2. 创建讨论（POST /api/discussions）
3. 生成嘉宾（POST /api/guests/generate）
4. 确认阵容（POST /api/discussions/{id}/confirm）
5. 建立 SSE 连接
6. 启动自动运行
7. 监听 SSE 事件，验证：
   - 事件类型完整性
   - 发言内容非空
   - 共识/分歧已生成
   - 轮次正确推进
8. 等待讨论结束
9. 验证最终状态

要求：
- 使用 httpx 异步客户端
- 包含超时处理
- 输出详细的测试日志
```

**说明**：E2E 测试验证了整个系统的端到端流程，是上线前的最终质量保障。

---

### Prompt 23 - 性能优化

```
请分析并优化以下性能问题：

1. SSE 事件推送延迟
   - 问题：多个客户端订阅同一讨论时，事件推送有延迟
   - 优化：使用 asyncio.gather 并行推送到所有订阅队列

2. LLM 调用阻塞
   - 问题：顺序调用多个专家的 LLM，耗时累积
   - 优化：使用 asyncio.gather 并行调用所有专家

3. 数据库连接
   - 问题：每次请求创建新连接
   - 优化：使用连接池或上下文管理器复用连接

请实现上述优化，并说明性能提升预期。
```

**说明**：性能优化是产品化的关键步骤，并行化是提升用户体验的有效手段。

---

### Prompt 24 - 错误处理与容错

```
请完善错误处理机制：

1. LLM 调用失败
   - 实现 fallback 默认嘉宾（当嘉宾生成失败时）
   - 实现发言重试机制（最多重试 3 次）
   - 记录错误日志

2. SSE 连接断开
   - 客户端自动重连（EventSource 原生支持）
   - 服务端清理断开的订阅队列

3. 数据库异常
   - 事务回滚
   - 返回友好的错误信息

4. 讨论状态异常
   - 防止重复启动
   - 防止在错误状态执行操作

请实现上述错误处理，并编写对应的测试用例。
```

**说明**：健壮的错误处理是生产级软件的必备要素，需要覆盖各种异常场景。

---

### Prompt 25 - 文档与部署

```
请完善项目文档：

1. README.md
   - 项目简介与功能特性
   - 技术选型说明
   - 环境变量配置（LLM API Key, Base URL, Model）
   - 安装与运行指南（前端 + 后端）
   - 主要 API 列表
   - 已完成能力与后续改进方向

2. API.md
   - 所有端点的详细说明
   - 请求/响应示例
   - 错误码说明

3. architecture.md
   - 系统架构图（mermaid）
   - 数据流图
   - 组件关系图

请输出完整的文档内容。
```

**说明**：文档是项目可维护性的保障，也是作业交付的必备材料。

---

## 总结

| 阶段 | Prompt 数量 | 核心产出 |
|------|-------------|----------|
| SDD | 5 | 数据库Schema、数据模型、API契约 |
| DDD | 7 | UI设计规范、页面布局、组件样式 |
| 后端功能 | 5 | SSE管理器、数据库层、LLM封装、业务核心、API路由 |
| TDD | 4 | 单元测试（数据库/业务/API/Agent） |
| E2E | 4 | E2E测试、性能优化、错误处理、文档 |

**关键经验**：
1. **先契约后实现**：SDD阶段的 Schema 设计为后续开发提供了明确的接口规范
2. **设计驱动开发**：DDD阶段的 UI 设计规范确保了视觉一致性
3. **测试保障质量**：TDD阶段的测试用例覆盖了核心业务逻辑
4. **端到端验证**：E2E阶段的测试验证了整个系统的正确性
