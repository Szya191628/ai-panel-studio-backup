# AI Panel Studio - 思考过程可视化

## 问题分析

需求文档指出的核心问题：
> "AI输出通常以最终结论呈现，缺乏'思考过程'和'观点演化'的实时感与沉浸感"

## 解决方案

### 1. 思考过程三阶段

```
阶段1: 思考 (Thinking)
  ↓ AI 分析当前讨论情况
阶段2: 草稿 (Draft)
  ↓ AI 形成初步观点
阶段3: 发言 (Speech)
  ↓ AI 完善并输出最终发言
```

### 2. 技术实现

#### 后端 - LLM 调用

```python
async def generate_speech_with_thinking(...) -> AsyncIterator[dict]:
    """生成带思考过程的发言"""

    prompt = """
    请按以下步骤输出：
    步骤1：分析当前讨论的关键点（用"思考："开头）
    步骤2：形成你的初步观点（用"草稿："开头）
    步骤3：完善并输出最终发言（用"发言："开头）
    """

    async for chunk in call_llm(messages, stream=True):
        if "思考：" in content:
            yield {"type": "thinking", "content": ...}
        elif "草稿：" in content:
            yield {"type": "draft", "content": ...}
        elif "发言：" in content:
            yield {"type": "complete", "content": ...}
```

#### SSE 事件

```python
# 思考过程事件
await sse_manager.publish_thinking(discussion_id, participant_id, content)
await sse_manager.publish_draft(discussion_id, participant_id, content)
await sse_manager.publish_speech_evolution(discussion_id, participant_id, stage, content)
```

#### 前端展示

```tsx
{thinkingProcess && thinkingProcess.stage !== 'final' && (
  <div className="thinking-process-panel">
    <div className="thinking-header">
      <span className="thinking-icon">🧠</span>
      <span className="thinking-label">
        {participant.name} 正在思考...
      </span>
    </div>
    <div className="thinking-content">
      {thinkingProcess.stage === 'thinking' && (
        <div className="thinking-stage">
          <span className="stage-badge thinking">分析中</span>
          <p className="stage-text">{thinkingProcess.content}</p>
        </div>
      )}
      {thinkingProcess.stage === 'draft' && (
        <div className="thinking-stage">
          <span className="stage-badge draft">草稿</span>
          <p className="stage-text">{thinkingProcess.content}</p>
        </div>
      )}
    </div>
  </div>
)}
```

## 用户体验流程

### 场景：专家发言

1. **开始**
   - 专家状态变为"准备中"
   - 显示思考过程面板

2. **思考阶段**
   ```
   🧠 李AI 正在思考...
   [分析中] 当前讨论中，王强支持现场办公，张华支持远程办公...
   ```

3. **草稿阶段**
   ```
   🧠 李AI 正在思考...
   [草稿] 我认为两种模式各有优势，需要根据行业特点选择...
   ```

4. **发言阶段**
   - 思考过程面板消失
   - 发言内容显示在 Transcript 中
   - 专家状态变回"待机"

## 视觉设计

### 思考过程面板

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 李AI 正在思考...                                    [×]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐                                                 │
│  │ 分析中   │ 当前讨论中，王强支持现场办公，张华支持远程办公，│
│  └─────────│ 双方观点对立但都有道理...                        │
│            └─────────────────────────────────────────────────│
│  ┌─────────┐                                                 │
│  │ 草稿    │ 我认为两种模式各有优势，需要根据行业特点选择。   │
│  └─────────│ 制造业适合现场办公，互联网行业适合远程办公...    │
│            └─────────────────────────────────────────────────│
└─────────────────────────────────────────────────────────────┘
```

### 动画效果

- 面板出现：`fadeIn 0.3s ease`
- 思考图标：`pulse 1.5s infinite`
- 阶段切换：平滑过渡

## 与传统方案对比

| 方案 | 体验 | 沉浸感 |
|------|------|--------|
| 传统方案 | 等待 → 一次性显示结果 | ⭐⭐ |
| 流式输出 | 边生成边显示文字 | ⭐⭐⭐ |
| **思考过程可视化** | 展示思考 → 草稿 → 最终发言 | ⭐⭐⭐⭐⭐ |

## 核心价值

1. **真实感** - 模拟人类思考过程
2. **沉浸感** - 用户"看到" AI 在想什么
3. **教育性** - 了解 AI 如何分析问题
4. **趣味性** - 像观察真人讨论一样

## 后续优化方向

- [ ] 思考过程动画优化
- [ ] 支持中断思考（用户可以跳过）
- [ ] 思考时间显示
- [ ] 思考过程回放
