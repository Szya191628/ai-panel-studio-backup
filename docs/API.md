# AI Panel Studio API 文档

## 基础信息

- Base URL: `http://localhost:8000`
- Content-Type: `application/json`
- 认证：无（MVP 阶段）

## API 列表

### 1. 嘉宾生成

#### POST `/api/guests/generate`

根据话题和人数，调用 AI 生成嘉宾阵容。

**请求体**：
```json
{
    "topic": "AI 会取代程序员吗？",
    "expert_count": 4,
    "language": "zh"
}
```

**响应**：
```json
{
    "ok": true,
    "host": {
        "name": "张明",
        "job_title": "科技节目主持人",
        "title": "资深媒体人",
        "stance": "中立客观",
        "color": "#FF6B6B",
        "avatar_seed": "host_001"
    },
    "experts": [
        {
            "name": "李工",
            "job_title": "AI 研究员",
            "title": "首席科学家",
            "stance": "AI 将增强而非取代程序员",
            "color": "#4ECDC4",
            "avatar_seed": "expert_001"
        },
        {
            "name": "王架构",
            "job_title": "软件架构师",
            "title": "技术总监",
            "stance": "AI 是工具，创造力不可替代",
            "color": "#45B7D1",
            "avatar_seed": "expert_002"
        }
    ]
}
```

---

### 2. 创建讨论

#### POST `/api/discussions`

创建新讨论并保存嘉宾信息。

**请求体**：
```json
{
    "topic": "AI 会取代程序员吗？",
    "host": {
        "name": "张明",
        "job_title": "科技节目主持人",
        "title": "资深媒体人",
        "stance": "中立客观",
        "color": "#FF6B6B",
        "avatar_seed": "host_001"
    },
    "experts": [
        {
            "name": "李工",
            "job_title": "AI 研究员",
            "title": "首席科学家",
            "stance": "AI 将增强而非取代程序员",
            "color": "#4ECDC4",
            "avatar_seed": "expert_001"
        }
    ],
    "max_rounds": 5
}
```

**响应**：
```json
{
    "ok": true,
    "discussion_id": "disc_abc123",
    "topic": "AI 会取代程序员吗？",
    "status": "assembling",
    "participants_count": 5
}
```

---

### 3. 获取讨论列表

#### GET `/api/discussions`

**查询参数**：
- `status` (可选): 筛选状态
- `limit` (可选): 返回数量，默认 20

**响应**：
```json
{
    "ok": true,
    "discussions": [
        {
            "id": "disc_abc123",
            "topic": "AI 会取代程序员吗？",
            "status": "active",
            "current_round": 2,
            "max_rounds": 5,
            "participant_count": 5,
            "created_at": 1718000000
        }
    ],
    "count": 1
}
```

---

### 4. 获取讨论详情

#### GET `/api/discussions/{id}`

**响应**：
```json
{
    "ok": true,
    "discussion": {
        "id": "disc_abc123",
        "topic": "AI 会取代程序员吗？",
        "status": "active",
        "current_round": 2,
        "max_rounds": 5,
        "convergence_score": 0.65
    },
    "participants": [...],
    "recent_speeches": [...],
    "findings": {
        "consensus": ["AI 可以提高开发效率"],
        "disagreement": ["AI 是否能理解业务逻辑"]
    }
}
```

---

### 5. 确认阵容并开始讨论

#### POST `/api/discussions/{id}/confirm`

**响应**：
```json
{
    "ok": true,
    "discussion_id": "disc_abc123",
    "status": "active",
    "message": "讨论已开始"
}
```

---

### 6. 记录发言（内部调用）

#### POST `/api/discussions/{id}/speak`

**请求体**：
```json
{
    "participant_id": "part_xyz789",
    "content": "我认为 AI 不会取代程序员...",
    "speech_type": "statement",
    "reply_to": null
}
```

**响应**：
```json
{
    "ok": true,
    "speech_id": 42,
    "round": 2,
    "next_speaker": "part_def456",
    "round_complete": false,
    "discussion_complete": false,
    "convergence_score": null
}
```

---

### 7. 获取讨论状态

#### GET `/api/discussions/{id}/status`

**响应**：
```json
{
    "ok": true,
    "discussion_id": "disc_abc123",
    "status": "active",
    "current_round": 2,
    "max_rounds": 5,
    "convergence_score": 0.65,
    "consensus_points": ["AI 可以提高开发效率"],
    "disagreement_points": ["AI 是否能理解业务逻辑"],
    "speech_count": 8,
    "next_speaker": "part_def456"
}
```

---

### 8. SSE 实时事件流

#### GET `/api/discussions/{id}/events`

**响应**：SSE 流

```
event: init
data: {"topic":"...","participants":[...],"status":"active"}

event: speech_start
data: {"participant_id":"...","name":"李工","round":2}

event: speech_token
data: {"speech_id":42,"content":"我认为","seq":1}

event: speech_token
data: {"speech_id":42,"content":"AI不会","seq":2}

event: speech_end
data: {"speech_id":42,"total_tokens":15}

event: finding_update
data: {"type":"consensus","content":"AI可以提高效率","round":2}

event: round_summary
data: {"round":2,"convergence":0.65,"consensus":[...],"disagreement":[...]}
```

---

### 9. 结束讨论

#### POST `/api/discussions/{id}/end`

**请求体**（可选）：
```json
{
    "conclusion": "经过讨论，大家达成共识..."
}
```

**响应**：
```json
{
    "ok": true,
    "discussion_id": "disc_abc123",
    "action": "concluded",
    "conclusion": "经过讨论，大家达成共识..."
}
```

---

## 错误响应

所有接口错误格式统一：

```json
{
    "ok": false,
    "error": "错误描述",
    "code": "ERROR_CODE"
}
```

常见错误码：
- `NOT_FOUND`: 资源不存在
- `INVALID_INPUT`: 输入参数错误
- `LLM_ERROR`: AI 调用失败
- `INTERNAL_ERROR`: 服务器内部错误
