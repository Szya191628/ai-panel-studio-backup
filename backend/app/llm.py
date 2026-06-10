"""LLM API integration (mimo-v2.5-pro).

Handles guest generation, speech generation, finding extraction,
and summary generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# Color palette for experts
EXPERT_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Purple
    "#85C1E9",  # Sky
]


async def call_llm(
    messages: list[dict[str, str]],
    temperature: float = 0.8,
    max_tokens: int = 1000,
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """Call LLM API with messages."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    if stream:
        return _stream_response(headers, payload)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _stream_response(
    headers: dict[str, str],
    payload: dict[str, Any],
) -> AsyncIterator[str]:
    """Stream response from LLM API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def generate_guests(
    topic: str,
    expert_count: int = 4,
) -> dict[str, Any]:
    """Generate host and expert profiles for a topic."""

    prompt = f"""你是一个专业的节目策划人。现在需要为一场关于"{topic}"的圆桌讨论节目配置嘉宾阵容。

请生成 1 位主持人和 {expert_count} 位专家嘉宾。

要求：
1. 主持人：中立客观，善于引导讨论，有丰富的主持经验
2. 专家：来自不同领域、持有不同立场和观点，能够产生有价值的碰撞
3. 每位专家的立场要明确且有差异性
4. 姓名要像真实的人名

请严格按以下 JSON 格式返回，不要有任何其他文字：

{{
    "host": {{
        "name": "姓名",
        "job_title": "职业",
        "title": "头衔",
        "stance": "立场描述"
    }},
    "experts": [
        {{
            "name": "姓名",
            "job_title": "职业",
            "title": "头衔",
            "stance": "立场描述"
        }}
    ]
}}"""

    messages = [
        {"role": "system", "content": "你是专业的节目策划人，擅长为不同话题配置有冲突性和深度的嘉宾阵容。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await call_llm(messages, temperature=0.9)
        # Parse JSON from response
        result = result.strip()
        # Handle markdown code blocks
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1])

        data = json.loads(result)

        # Add colors and avatar seeds
        host = data["host"]
        host["color"] = "#FF6B6B"
        host["avatar_seed"] = f"host_{hash(host['name']) % 10000:04d}"

        for i, expert in enumerate(data["experts"]):
            expert["color"] = EXPERT_COLORS[i % len(EXPERT_COLORS)]
            expert["avatar_seed"] = f"expert_{hash(expert['name']) % 10000:04d}"

        return data

    except Exception as e:
        logger.error(f"Guest generation failed: {e}")
        # Fallback with default guests
        return _default_guests(topic, expert_count)


def _default_guests(topic: str, expert_count: int) -> dict[str, Any]:
    """Fallback default guests when API fails."""
    host = {
        "name": "张明",
        "job_title": "节目主持人",
        "title": "资深媒体人",
        "stance": "中立客观",
        "color": "#FF6B6B",
        "avatar_seed": "host_0001",
    }

    experts = []
    default_names = [
        ("李研究员", "AI 研究员", "首席科学家", "技术乐观派"),
        ("王架构师", "软件架构师", "技术总监", "实用主义者"),
        ("陈教授", "大学教授", "博士生导师", "学术审慎派"),
        ("赵产品经理", "产品经理", "产品VP", "用户导向派"),
        ("刘创业者", "科技创业者", "CEO", "创新激进派"),
    ]

    for i in range(min(expert_count, len(default_names))):
        name, job, title, stance = default_names[i]
        experts.append({
            "name": name,
            "job_title": job,
            "title": title,
            "stance": stance,
            "color": EXPERT_COLORS[i % len(EXPERT_COLORS)],
            "avatar_seed": f"expert_{i:04d}",
        })

    return {"host": host, "experts": experts}


async def generate_speech(
    topic: str,
    participant: dict[str, Any],
    transcript: list[dict[str, Any]],
    round_num: int,
    is_host: bool = False,
) -> str:
    """Generate a speech for a participant."""

    # Build transcript context
    transcript_text = ""
    for t in transcript[-10:]:  # Last 10 speeches
        transcript_text += f"{t['name']}（{t['job_title']}）：{t['content']}\n"

    if is_host:
        prompt = f"""你是圆桌讨论的主持人，话题是"{topic}"。

当前讨论进展：
{transcript_text}

你是主持人 {participant['name']}。请根据讨论进展，做以下之一：
1. 如果是第1轮：做开场白，介绍话题和嘉宾
2. 如果讨论热烈：引导深入，追问关键观点
3. 如果有分歧：引导双方阐述
4. 如果讨论接近尾声：做简短总结

请用1-2句话发言，自然、专业、有引导性。直接返回发言内容，不要有其他文字。"""
    else:
        prompt = f"""你正在参与一场关于"{topic}"的圆桌讨论。

你的身份：{participant['name']}，{participant['job_title']}，{participant['title']}
你的立场：{participant['stance']}

当前讨论进展：
{transcript_text}

现在轮到你发言。请根据你的立场和讨论进展：
1. 表达你的观点
2. 回应或反驳其他嘉宾的观点
3. 补充新的视角

请用1-2句话发言，有深度、有立场、有碰撞感。直接返回发言内容，不要有其他文字。"""

    messages = [
        {"role": "system", "content": "你是一个有深度、有立场的讨论参与者。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await call_llm(messages, temperature=0.85)
        return result.strip()
    except Exception as e:
        logger.error(f"Speech generation failed: {e}")
        return f"我认为{topic}这个问题值得深入思考。"


async def generate_speech_stream(
    topic: str,
    participant: dict[str, Any],
    transcript: list[dict[str, Any]],
    round_num: int,
    is_host: bool = False,
) -> AsyncIterator[str]:
    """Generate a speech with streaming."""
    transcript_text = ""
    for t in transcript[-10:]:
        transcript_text += f"{t['name']}（{t['job_title']}）：{t['content']}\n"

    if is_host:
        prompt = f"""你是圆桌讨论的主持人，话题是"{topic}"。

当前讨论进展：
{transcript_text}

你是主持人 {participant['name']}。请根据讨论进展做1-2句发言。直接返回发言内容。"""
    else:
        prompt = f"""你正在参与关于"{topic}"的圆桌讨论。

你的身份：{participant['name']}，{participant['job_title']}，{participant['title']}
你的立场：{participant['stance']}

当前讨论进展：
{transcript_text}

请根据你的立场做1-2句发言。直接返回发言内容。"""

    messages = [
        {"role": "system", "content": "你是一个有深度、有立场的讨论参与者。"},
        {"role": "user", "content": prompt},
    ]

    async for chunk in await call_llm(messages, temperature=0.85, stream=True):
        yield chunk


async def extract_findings(
    topic: str,
    speeches: list[dict[str, Any]],
    round_num: int,
) -> list[dict[str, Any]]:
    """Extract consensus and disagreement from speeches."""

    speeches_text = ""
    for s in speeches:
        speeches_text += f"{s['name']}（{s['job_title']}）：{s['content']}\n"

    prompt = f"""分析以下关于"{topic}"的第{round_num}轮讨论，提取共识点和分歧点。

讨论内容：
{speeches_text}

请返回 JSON 格式：
{{
    "findings": [
        {{
            "type": "consensus",
            "content": "共识点描述"
        }},
        {{
            "type": "disagreement",
            "content": "分歧点描述"
        }}
    ]
}}

要求：
1. 只提取明确表达的共识和分歧
2. 每个点用一句话概括
3. 不要捏造不存在的观点"""

    messages = [
        {"role": "system", "content": "你是讨论分析专家，擅长提取观点中的共识和分歧。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await call_llm(messages, temperature=0.3)
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1])
        data = json.loads(result)
        return data.get("findings", [])
    except Exception as e:
        logger.error(f"Finding extraction failed: {e}")
        return []


async def generate_summary(
    topic: str,
    transcript: list[dict[str, Any]],
    consensus: list[str],
    disagreements: list[str],
) -> str:
    """Generate a discussion summary."""

    transcript_text = ""
    for t in transcript[-20:]:
        transcript_text += f"{t['name']}（{t['job_title']}）：{t['content']}\n"

    consensus_text = "\n".join(f"- {c}" for c in consensus) if consensus else "暂无明确共识"
    disagreement_text = "\n".join(f"- {d}" for d in disagreements) if disagreements else "暂无明显分歧"

    prompt = f"""你是圆桌讨论的主持人，请为以下讨论做总结。

话题：{topic}

讨论要点：
{transcript_text}

共识点：
{consensus_text}

分歧点：
{disagreement_text}

请用自然语言做总结，包括：
1. 讨论的核心议题
2. 各方的主要观点
3. 达成的共识
4. 存在的分歧
5. 值得进一步思考的方向

请用主持人收尾的口吻，200字左右。"""

    messages = [
        {"role": "system", "content": "你是专业的讨论总结者。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await call_llm(messages, temperature=0.7)
        return result.strip()
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return f"关于{topic}的讨论到此结束，感谢各位嘉宾的精彩分享。"


async def generate_speech_with_thinking(
    topic: str,
    participant: dict[str, Any],
    transcript: list[dict[str, Any]],
    round_num: int,
    is_host: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Generate a speech with visible thinking process.

    Yields events:
    - {"type": "thinking", "content": "正在分析..."}
    - {"type": "draft", "content": "部分草稿..."}
    - {"type": "complete", "content": "最终发言"}
    """
    # Build transcript context
    transcript_text = ""
    for t in transcript[-10:]:
        transcript_text += f"{t['name']}（{t['job_title']}）：{t['content']}\n"

    # 思考过程提示
    thinking_prompt = f"""你正在参与一场关于"{topic}"的圆桌讨论。

你的身份：{participant['name']}，{participant['job_title']}，{participant['title']}
你的立场：{participant['stance']}

当前讨论进展：
{transcript_text}

现在请你思考如何发言。请按以下步骤输出：

步骤1：分析当前讨论的关键点（用"思考："开头）
步骤2：形成你的初步观点（用"草稿："开头）
步骤3：完善并输出最终发言（用"发言："开头）

请严格按照这个格式输出，每步一行。"""

    if is_host:
        thinking_prompt = f"""你是圆桌讨论的主持人，话题是"{topic}"。

当前讨论进展：
{transcript_text}

你是主持人 {participant['name']}。请思考如何引导讨论。

请按以下步骤输出：

步骤1：分析当前讨论状态（用"思考："开头）
步骤2：形成引导策略（用"草稿："开头）
步骤3：输出最终发言（用"发言："开头）

请严格按照这个格式输出，每步一行。"""

    messages = [
        {"role": "system", "content": "你是有深度的讨论参与者，会先思考再发言。"},
        {"role": "user", "content": thinking_prompt},
    ]

    try:
        # 流式调用 LLM
        full_content = ""
        async for chunk in await call_llm(messages, temperature=0.85, stream=True):
            full_content += chunk
            # 解析内容，判断阶段
            if "思考：" in full_content and "草稿：" not in full_content:
                # 思考阶段
                thinking_part = full_content.split("思考：")[-1]
                yield {"type": "thinking", "content": thinking_part.strip()}
            elif "草稿：" in full_content and "发言：" not in full_content:
                # 草稿阶段
                draft_part = full_content.split("草稿：")[-1]
                yield {"type": "draft", "content": draft_part.strip()}
            elif "发言：" in full_content:
                # 发言阶段
                speech_part = full_content.split("发言：")[-1]
                yield {"type": "speech_draft", "content": speech_part.strip()}

        # 提取最终发言
        if "发言：" in full_content:
            final_speech = full_content.split("发言：")[-1].strip()
        elif "草稿：" in full_content:
            final_speech = full_content.split("草稿：")[-1].strip()
        else:
            final_speech = full_content.strip()

        # 清理格式
        final_speech = final_speech.replace("思考：", "").replace("草稿：", "").replace("发言：", "")
        final_speech = final_speech.split("\n")[0].strip()  # 取第一行

        yield {"type": "complete", "content": final_speech}

    except Exception as e:
        logger.error(f"Speech generation failed: {e}")
        yield {"type": "complete", "content": f"我认为{topic}这个问题值得深入思考。"}
