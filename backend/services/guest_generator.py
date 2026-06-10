"""嘉宾生成服务"""

import json
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import (
    Discussion,
    Participant,
    DiscussionStatus,
    ParticipantRole,
    AgentPhase,
)
from backend.services.llm_service import get_llm_service
from backend.services.discussion_service import DiscussionService


class GuestGeneratorService:
    """嘉宾生成服务"""

    # 预定义的颜色池
    COLORS = [
        "#E74C3C",  # 红色
        "#2ECC71",  # 绿色
        "#F39C12",  # 橙色
        "#9B59B6",  # 紫色
        "#1ABC9C",  # 青色
        "#E67E22",  # 深橙
        "#3498DB",  # 蓝色
        "#2C3E50",  # 深灰蓝
    ]

    GUEST_GENERATION_PROMPT = """你是一个圆桌讨论策划专家。根据给定的讨论话题，生成一组有深度、有对立观点的专家嘉宾阵容。

讨论话题：{topic}
需要生成的专家人数：{expert_count}人

要求：
1. 每位专家需要有明确的职业/Title和专业背景
2. 每位专家需要有清晰的立场和观点倾向
3. 专家之间应该有观点对立或互补，确保讨论有深度碰撞
4. 主持人应该是中立的引导者

请以JSON格式返回：
{{
    "moderator": {{
        "name": "主持人姓名",
        "title": "职业/Title",
        "stance": "立场描述"
    }},
    "experts": [
        {{
            "name": "专家姓名",
            "title": "职业/Title",
            "stance": "立场描述"
        }}
    ]
}}

注意：
- 姓名可以是中文或英文，但要有真实感
- Title要专业、具体
- 立场要鲜明，有对立面
- 不要使用真实的历史人物姓名"""

    REQUIRED_EXPERT_KEYS = {"name", "title", "stance"}

    def __init__(self, db: Session):
        self.db = db
        self.discussion_service = DiscussionService(db)

    def _validate_expert_data(self, expert_data: dict, index: int) -> None:
        """验证专家数据包含必需字段"""
        missing_keys = self.REQUIRED_EXPERT_KEYS - set(expert_data.keys())
        if missing_keys:
            raise ValueError(f"专家{index+1}数据缺少必需字段: {', '.join(missing_keys)}")

    def generate_guests(
        self,
        discussion_id: str,
        topic: str,
        expert_count: int = 4,
    ) -> dict:
        """生成嘉宾阵容"""

        # 保存原始状态用于回滚
        discussion = self.discussion_service.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        original_status = discussion.status

        # 更新讨论状态为生成中
        self.discussion_service.update_discussion_status(
            discussion_id,
            DiscussionStatus.GENERATING,
        )

        try:
            # 调用LLM生成嘉宾
            llm_service = get_llm_service(temperature=0.8)
            result = llm_service.invoke_json(
                system_prompt="你是一个圆桌讨论策划专家。",
                user_prompt=self.GUEST_GENERATION_PROMPT.format(
                    topic=topic,
                    expert_count=expert_count,
                ),
            )

            # 检查是否有错误
            if "error" in result:
                raise ValueError(f"LLM返回错误: {result['error']}")

            # 验证返回格式
            if "moderator" not in result or "experts" not in result:
                raise ValueError("LLM返回格式不正确")

            # 验证主持人数据
            moderator_data = result["moderator"]
            for key in ["name", "title", "stance"]:
                if key not in moderator_data:
                    raise ValueError(f"主持人数据缺少必需字段: {key}")

            # 验证专家数量
            if len(result["experts"]) < expert_count:
                raise ValueError(f"LLM返回的专家数量不足: {len(result['experts'])} < {expert_count}")

            # 验证每个专家的数据
            for i, expert_data in enumerate(result["experts"][:expert_count]):
                self._validate_expert_data(expert_data, i)

            # 创建主持人
            moderator = self.discussion_service.create_participant(
                discussion_id=discussion_id,
                name=moderator_data["name"],
                role=ParticipantRole.MODERATOR,
                title=moderator_data["title"],
                stance=moderator_data["stance"],
                color=self.COLORS[0],
            )

            # 创建专家
            experts = []
            for i, expert_data in enumerate(result["experts"][:expert_count]):
                expert = self.discussion_service.create_participant(
                    discussion_id=discussion_id,
                    name=expert_data["name"],
                    role=ParticipantRole.EXPERT,
                    title=expert_data["title"],
                    stance=expert_data["stance"],
                    color=self.COLORS[(i + 1) % len(self.COLORS)],
                )
                experts.append(expert)

            # 更新讨论状态为确认中
            self.discussion_service.update_discussion_status(
                discussion_id,
                DiscussionStatus.CONFIRMING,
            )

            # 更新专家人数
            discussion.expert_count = expert_count
            self.db.commit()

            return {
                "moderator": moderator,
                "experts": experts,
            }

        except Exception as e:
            # 回滚状态到原始状态
            try:
                self.discussion_service.update_discussion_status(
                    discussion_id,
                    original_status,
                )
            except Exception:
                pass  # 回滚失败时忽略

            # 保留原始异常链
            raise ValueError(f"生成嘉宾失败: {str(e)}") from e

    def regenerate_guests(
        self,
        discussion_id: str,
        topic: str,
        expert_count: int = 4,
    ) -> dict:
        """重新生成嘉宾阵容"""

        # 删除现有参与者
        participants = self.discussion_service.get_participants(discussion_id)
        for p in participants:
            self.db.delete(p)
        self.db.commit()

        # 重新生成
        return self.generate_guests(discussion_id, topic, expert_count)
