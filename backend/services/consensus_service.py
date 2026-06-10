"""共识提炼服务"""

import json
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import (
    ConsensusType,
)
from backend.services.llm_service import get_llm_service
from backend.services.discussion_service import DiscussionService


class ConsensusService:
    """共识提炼服务"""

    CONSENSUS_PROMPT = """你是一个讨论分析专家。基于以下圆桌讨论的内容，提炼出共识、分歧和洞见。

讨论主题：{topic}

最近的发言：
{recent_messages}

请分析并以JSON格式返回：
{{
    "consensuses": [
        {{"content": "共识内容", "type": "consensus"}},
        {{"content": "分歧内容", "type": "dissensus"}},
        {{"content": "洞见内容", "type": "insight"}}
    ]
}}

分析要求：
1. 共识(consensus): 各方达成一致的观点
2. 分歧(dissensus): 各方存在争议的观点
3. 洞见(insight): 讨论中产生的新观点或启发

注意：
- 每条内容要简洁有力，控制在50字以内
- 只提取最核心的观点
- 不要重复已经提取过的共识"""

    def __init__(self, db: Session):
        self.db = db
        self.discussion_service = DiscussionService(db)

    def _build_messages_text(self, messages: list[dict], participants: list[dict]) -> str:
        """构建消息文本（带参与者名称）"""
        # 构建participant字典用于O(1)查找
        participant_dict = {p.id: p.name for p in participants}

        return "\n".join([
            f"- {participant_dict.get(m.get('participant_id'), m.get('participant_name', '未知'))}: {m['content']}"
            for m in messages[-10:]  # 只取最近10条
        ])

    def extract_consensus(
        self,
        discussion_id: str,
        topic: str,
        recent_messages: Optional[list[dict]] = None,
    ) -> list[dict]:
        """提取共识和分歧"""

        # 如果没有提供最近消息，从数据库获取
        if recent_messages is None:
            messages = self.discussion_service.get_messages(discussion_id, limit=20)
            recent_messages = [
                {
                    "participant_id": m.participant_id,
                    "content": m.content,
                }
                for m in messages
            ]

        # 如果没有消息，返回空
        if not recent_messages:
            return []

        # 获取参与者列表（一次性查询）
        participants = self.discussion_service.get_participants(discussion_id)

        # 构建消息文本
        messages_text = self._build_messages_text(recent_messages, participants)

        try:
            # 调用LLM提取共识
            llm_service = get_llm_service(temperature=0.3)
            result = llm_service.invoke_json(
                system_prompt="你是一个讨论分析专家。",
                user_prompt=self.CONSENSUS_PROMPT.format(
                    topic=topic,
                    recent_messages=messages_text,
                ),
            )

            # 检查是否有错误
            if "error" in result:
                raise ValueError(f"LLM返回错误: {result['error']}")

            # 提取共识
            consensuses = result.get("consensuses", [])

            # 获取当前轮次（一次性查询）
            discussion = self.discussion_service.get_discussion(discussion_id)
            current_round = discussion.current_round if discussion else 0

            # 批量保存到数据库
            saved_consensuses = []
            for c in consensuses:
                # 验证必需字段
                if "content" not in c:
                    continue  # 跳过无效项

                consensus_type_str = c.get("type", "consensus")
                try:
                    consensus_type = ConsensusType(consensus_type_str)
                except ValueError:
                    consensus_type = ConsensusType.CONSENSUS

                # 添加到列表（不立即commit）
                from backend.models import Consensus as ConsensusModel
                consensus = ConsensusModel(
                    id=str(__import__('uuid').uuid4()),
                    discussion_id=discussion_id,
                    content=c["content"],
                    consensus_type=consensus_type,
                    round_number=current_round,
                )
                self.db.add(consensus)
                saved_consensuses.append({
                    "id": consensus.id,
                    "content": consensus.content,
                    "consensus_type": consensus.consensus_type.value,
                    "round_number": consensus.round_number,
                })

            # 批量提交
            if saved_consensuses:
                self.db.commit()

            return saved_consensuses

        except Exception as e:
            # 回滚本次操作
            self.db.rollback()
            raise ValueError(f"共识提取失败: {str(e)}") from e

    def get_consensuses(self, discussion_id: str) -> list[dict]:
        """获取讨论的所有共识"""
        consensuses = self.discussion_service.get_consensuses(discussion_id)
        return [
            {
                "id": c.id,
                "content": c.content,
                "consensus_type": c.consensus_type.value,
                "round_number": c.round_number,
                "created_at": c.created_at.isoformat(),
            }
            for c in consensuses
        ]
