"""LLM服务 - 统一的大模型调用封装"""

import json
import re
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from backend.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# 预编译正则表达式
_JSON_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*([\s\S]*?)```', re.IGNORECASE)


class LLMService:
    """LLM服务类"""

    def __init__(self, temperature: float = 0.7, streaming: bool = False):
        self.temperature = temperature
        self.streaming = streaming
        self._client = None

    @property
    def client(self) -> ChatOpenAI:
        """懒加载LLM客户端"""
        if self._client is None:
            self._client = ChatOpenAI(
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=self.temperature,
                streaming=self.streaming,
            )
        return self._client

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM获取响应"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self.client.invoke(messages)
        return response.content

    def invoke_with_history(
        self,
        system_prompt: str,
        history: list[dict],
        user_prompt: Optional[str] = None,
    ) -> str:
        """带历史消息的LLM调用"""
        messages = [SystemMessage(content=system_prompt)]

        for msg in history:
            role = msg.get("role", "user")
            content = msg["content"]
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        if user_prompt:
            messages.append(HumanMessage(content=user_prompt))

        response = self.client.invoke(messages)
        return response.content

    def invoke_json(self, system_prompt: str, user_prompt: str) -> dict:
        """调用LLM并解析JSON响应"""
        response_text = self.invoke(system_prompt, user_prompt)

        # 尝试提取JSON
        try:
            # 尝试直接解析
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试提取代码块中的JSON
            json_match = _JSON_BLOCK_PATTERN.search(response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 返回原始文本作为错误
            return {"error": "无法解析JSON响应", "raw": response_text}


# 全局单例缓存（按temperature+streaming组合）
_llm_service_cache: dict[tuple[float, bool], LLMService] = {}


def get_llm_service(temperature: float = 0.7, streaming: bool = False) -> LLMService:
    """获取LLM服务单例"""
    cache_key = (temperature, streaming)
    if cache_key not in _llm_service_cache:
        _llm_service_cache[cache_key] = LLMService(
            temperature=temperature,
            streaming=streaming,
        )
    return _llm_service_cache[cache_key]
