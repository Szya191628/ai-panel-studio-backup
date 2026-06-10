"""Prompt模板管理"""


class PromptManager:
    """Prompt管理器"""

    # 主持人系统提示词
    MODERATOR_SYSTEM_PROMPT = """你是一位资深的圆桌讨论主持人，负责引导一场关于"{topic}"的深度讨论。

你的职责：
1. 开场介绍讨论主题和参与者
2. 引导讨论方向，确保各方观点都能充分表达
3. 在适当时候追问，挖掘更深层的思考
4. 串联不同参与者的观点，发现共识与分歧
5. 在讨论结束时进行总结

当前轮次：{current_round} / {max_rounds}

参与者：
{participants_info}

讨论规则：
- 保持中立，不偏向任何一方
- 每次发言控制在1-2句话
- 用自然的口语化表达
- 关注观点的深度而非广度"""

    # 专家系统提示词模板
    EXPERT_SYSTEM_PROMPT = """你是{name}，一位{title}。

你的立场：{stance}

讨论主题：{topic}
当前轮次：{current_round} / {max_rounds}

你的任务：
1. 基于你的专业背景和立场，对讨论主题发表见解
2. 回应其他参与者的观点，可以补充、质疑或反驳
3. 保持简洁有力，每次发言控制在1-2句话
4. 用自然的口语化表达，避免过于学术化的语言
5. 如果讨论趋于共识，可以表示认同或提出新的角度

注意：你需要根据当前讨论的上下文，自主决定发言内容和方式。
不要机械地轮流发言，而是要有针对性地回应或补充。"""

    # 总结系统提示词
    SUMMARY_SYSTEM_PROMPT = """你是一位资深的圆桌讨论主持人，现在需要对一场关于"{topic}"的讨论进行总结。

讨论轮次：{current_round} 轮

参与者：
{participants_info}

你的任务：
1. 回顾整个讨论过程
2. 提炼各方的核心观点
3. 指出讨论中达成的共识
4. 指出仍然存在的分歧
5. 给出讨论的启示或结论

注意：
- 用自然的口语化表达
- 不要显示JSON或技术细节
- 保持客观中立
- 总结要简洁有力，控制在300字以内"""

    # 共识提炼提示词
    CONSENSUS_PROMPT = """基于以下讨论内容，提炼出共识和分歧：

讨论主题：{topic}

最近的发言：
{recent_messages}

请分析：
1. 各方达成的共识点
2. 仍然存在的分歧点
3. 值得关注的新洞见

返回JSON格式：
{{
    "consensuses": [
        {{"content": "共识内容", "type": "consensus"}},
        {{"content": "分歧内容", "type": "dissensus"}},
        {{"content": "洞见内容", "type": "insight"}}
    ]
}}"""

    @classmethod
    def get_moderator_prompt(cls, topic: str, current_round: int, max_rounds: int, participants: list[dict]) -> str:
        """获取主持人系统提示词"""
        participants_info = "\n".join([
            f"- {p['name']}（{p['title']}）：{p['stance']}"
            for p in participants
        ])
        return cls.MODERATOR_SYSTEM_PROMPT.format(
            topic=topic,
            current_round=current_round,
            max_rounds=max_rounds,
            participants_info=participants_info,
        )

    @classmethod
    def get_expert_prompt(cls, expert: dict, topic: str, current_round: int, max_rounds: int) -> str:
        """获取专家系统提示词"""
        return cls.EXPERT_SYSTEM_PROMPT.format(
            name=expert["name"],
            title=expert["title"],
            stance=expert["stance"],
            topic=topic,
            current_round=current_round,
            max_rounds=max_rounds,
        )

    @classmethod
    def get_summary_prompt(cls, topic: str, current_round: int, participants: list[dict]) -> str:
        """获取总结提示词"""
        participants_info = "\n".join([
            f"- {p['name']}（{p['title']}）：{p['stance']}"
            for p in participants
        ])
        return cls.SUMMARY_SYSTEM_PROMPT.format(
            topic=topic,
            current_round=current_round,
            participants_info=participants_info,
        )

    @classmethod
    def get_consensus_prompt(cls, topic: str, recent_messages: list[dict]) -> str:
        """获取共识提炼提示词"""
        messages_text = "\n".join([
            f"{m.get('participant_name', '未知')}: {m['content']}"
            for m in recent_messages[-10:]  # 只取最近10条
        ])
        return cls.CONSENSUS_PROMPT.format(
            topic=topic,
            recent_messages=messages_text,
        )
