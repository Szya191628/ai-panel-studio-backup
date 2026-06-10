"""智能体层单元测试"""

import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "D:/ai-panel-studio")

from backend.agents.state import AgentState, create_agent_state
from backend.agents.prompts import PromptManager
from backend.agents.llm import create_llm, build_message_history
from backend.agents.routing import route_after_moderator, route_after_expert, increment_round
from backend.agents.graph import RoundTableGraph


# ==================== 状态测试 ====================

class TestAgentState:
    """智能体状态测试"""

    def test_create_agent_state(self):
        """测试创建初始状态"""
        participants = [
            {"id": "mod1", "name": "主持人", "role": "moderator", "title": "资深主持人", "stance": "中立"},
            {"id": "exp1", "name": "专家1", "role": "expert", "title": "领域专家", "stance": "支持"},
        ]

        state = create_agent_state(
            discussion_id="test-disc-1",
            topic="AI与教育",
            participants=participants,
            max_rounds=5,
        )

        assert state["discussion_id"] == "test-disc-1"
        assert state["topic"] == "AI与教育"
        assert state["participants"] == participants
        assert state["max_rounds"] == 5
        assert state["current_round"] == 0
        assert state["current_speaker_index"] == 0
        assert state["messages"] == []
        assert state["consensuses"] == []
        assert state["phase"] == "setup"
        assert state["error"] == ""

    def test_create_agent_state_defaults(self):
        """测试默认参数"""
        state = create_agent_state(
            discussion_id="test",
            topic="测试",
            participants=[],
        )

        assert state["max_rounds"] == 5


# ==================== Prompt测试 ====================

class TestPromptManager:
    """Prompt管理器测试"""

    def test_get_moderator_prompt(self):
        """测试获取主持人提示词"""
        participants = [
            {"name": "专家1", "title": "AI研究员", "stance": "支持AI"},
            {"name": "专家2", "title": "教育家", "stance": "关注人文"},
        ]

        prompt = PromptManager.get_moderator_prompt(
            topic="AI与教育",
            current_round=1,
            max_rounds=5,
            participants=participants,
        )

        assert "AI与教育" in prompt
        assert "1" in prompt
        assert "5" in prompt
        assert "专家1" in prompt
        assert "专家2" in prompt

    def test_get_expert_prompt(self):
        """测试获取专家提示词"""
        expert = {
            "name": "张教授",
            "title": "AI研究员",
            "stance": "支持AI发展",
        }

        prompt = PromptManager.get_expert_prompt(
            expert=expert,
            topic="AI与教育",
            current_round=1,
            max_rounds=5,
        )

        assert "张教授" in prompt
        assert "AI研究员" in prompt
        assert "支持AI发展" in prompt
        assert "AI与教育" in prompt

    def test_get_summary_prompt(self):
        """测试获取总结提示词"""
        participants = [
            {"name": "专家1", "title": "AI研究员", "stance": "支持AI"},
        ]

        prompt = PromptManager.get_summary_prompt(
            topic="AI与教育",
            current_round=5,
            participants=participants,
        )

        assert "AI与教育" in prompt
        assert "5" in prompt

    def test_get_consensus_prompt(self):
        """测试获取共识提炼提示词"""
        recent_messages = [
            {"participant_name": "专家1", "content": "AI能提高效率"},
            {"participant_name": "专家2", "content": "但需要关注伦理"},
        ]

        prompt = PromptManager.get_consensus_prompt(
            topic="AI与教育",
            recent_messages=recent_messages,
        )

        assert "AI与教育" in prompt
        assert "AI能提高效率" in prompt


# ==================== LLM工具测试 ====================

class TestLLMUtils:
    """LLM工具测试"""

    def test_build_message_history(self):
        """测试构建消息历史"""
        participants = [
            {"id": "mod1", "name": "主持人", "role": "moderator"},
            {"id": "exp1", "name": "专家1", "role": "expert"},
        ]

        messages = [
            {"participant_id": "mod1", "content": "开场白"},
            {"participant_id": "exp1", "content": "专家观点"},
        ]

        result = build_message_history(messages, participants, max_messages=10)

        assert len(result) == 2
        assert "主持人" in result[0].content
        assert "开场白" in result[0].content
        assert "专家1" in result[1].content

    def test_build_message_history_truncation(self):
        """测试消息历史截断"""
        participants = [{"id": "exp1", "name": "专家", "role": "expert"}]
        messages = [{"participant_id": "exp1", "content": f"消息{i}"} for i in range(20)]

        result = build_message_history(messages, participants, max_messages=5)

        assert len(result) == 5
        assert "消息15" in result[0].content  # 最近5条从15开始


# ==================== 路由测试 ====================

class TestRouting:
    """路由逻辑测试"""

    def _create_state(self, **kwargs) -> AgentState:
        """创建测试状态"""
        default_state = {
            "discussion_id": "test",
            "topic": "测试",
            "current_round": 0,
            "max_rounds": 5,
            "participants": [
                {"id": "mod1", "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立"},
                {"id": "exp1", "name": "专家1", "role": "expert", "title": "专家", "stance": "支持"},
                {"id": "exp2", "name": "专家2", "role": "expert", "title": "专家", "stance": "反对"},
            ],
            "current_speaker_index": 0,
            "messages": [],
            "consensuses": [],
            "phase": "debating",
            "error": "",
        }
        default_state.update(kwargs)
        return default_state

    def test_route_after_moderator_first_expert(self):
        """测试主持人后路由到第一个专家"""
        state = self._create_state()
        assert route_after_moderator(state) == "expert_0"

    def test_route_after_moderator_summarizing(self):
        """测试主持人后路由到总结"""
        state = self._create_state(phase="summarizing")
        assert route_after_moderator(state) == "summarizer"

    def test_route_after_moderator_error(self):
        """测试主持人后路由到错误处理"""
        state = self._create_state(error="测试错误")
        assert route_after_moderator(state) == "error_handler"

    def test_route_after_expert_next_expert(self):
        """测试专家后路由到下一个专家"""
        state = self._create_state(current_speaker_index=1)
        assert route_after_expert(state) == "expert_1"

    def test_route_after_expert_to_moderator(self):
        """测试专家后路由到主持人（轮次递增）"""
        state = self._create_state(current_speaker_index=2)
        assert route_after_expert(state) == "moderator"

    def test_route_after_expert_error(self):
        """测试专家后路由到错误处理"""
        state = self._create_state(error="测试错误")
        assert route_after_expert(state) == "error_handler"

    def test_increment_round(self):
        """测试轮次递增"""
        state = self._create_state(current_round=2, current_speaker_index=2)
        result = increment_round(state)

        assert result["current_round"] == 3
        assert result["current_speaker_index"] == 0


# ==================== 图测试 ====================

class TestRoundTableGraph:
    """圆桌讨论图测试"""

    def _create_participants(self) -> list[dict]:
        """创建测试参与者"""
        return [
            {"id": "mod1", "name": "主持人", "role": "moderator", "title": "资深主持人", "stance": "中立"},
            {"id": "exp1", "name": "专家1", "role": "expert", "title": "AI研究员", "stance": "支持AI"},
            {"id": "exp2", "name": "专家2", "role": "expert", "title": "教育家", "stance": "关注人文"},
        ]

    def test_graph_creation(self):
        """测试图创建"""
        participants = self._create_participants()
        graph = RoundTableGraph(participants, max_rounds=3)

        assert graph.participants == participants
        assert graph.max_rounds == 3
        assert len(graph.experts) == 2
        assert graph.moderator is not None

    def test_graph_creation_without_moderator(self):
        """测试没有主持人时创建图"""
        participants = [
            {"id": "exp1", "name": "专家1", "role": "expert", "title": "专家", "stance": "支持"},
        ]

        with pytest.raises(ValueError, match="必须包含一个主持人"):
            RoundTableGraph(participants)

    def test_graph_creation_without_experts(self):
        """测试没有专家时创建图"""
        participants = [
            {"id": "mod1", "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立"},
        ]

        with pytest.raises(ValueError, match="必须包含至少一个专家"):
            RoundTableGraph(participants)

    @patch('backend.agents.nodes.moderator.create_llm')
    @patch('backend.agents.nodes.expert.create_llm')
    @patch('backend.agents.nodes.summarizer.create_llm')
    def test_graph_invoke(self, mock_summarizer_llm, mock_expert_llm, mock_moderator_llm):
        """测试图执行"""
        # Mock LLM responses
        mock_moderator_response = MagicMock()
        mock_moderator_response.content = "大家好，欢迎参加本次讨论"
        mock_moderator_llm.return_value.invoke.return_value = mock_moderator_response

        mock_expert_response = MagicMock()
        mock_expert_response.content = "我认为AI很有前景"
        mock_expert_llm.return_value.invoke.return_value = mock_expert_response

        mock_summarizer_response = MagicMock()
        mock_summarizer_response.content = "本次讨论总结..."
        mock_summarizer_llm.return_value.invoke.return_value = mock_summarizer_response

        participants = self._create_participants()
        graph = RoundTableGraph(participants, max_rounds=1)

        result = graph.invoke(
            discussion_id="test-disc",
            topic="AI与教育",
        )

        assert "messages" in result
        assert "phase" in result

    def test_graph_stream(self):
        """测试图流式执行"""
        participants = self._create_participants()
        graph = RoundTableGraph(participants, max_rounds=1)

        # 注意：实际流式测试需要mock LLM
        # 这里只测试图的创建和基本结构
        assert graph.graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
