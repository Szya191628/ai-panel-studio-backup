"""SSE (Server-Sent Events) management.

Reference: agent-roundtable's WebPublisher patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages SSE connections for discussions."""

    def __init__(self):
        # discussion_id -> list of queues
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, discussion_id: str) -> asyncio.Queue:
        """Subscribe to a discussion's events."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if discussion_id not in self._subscribers:
                self._subscribers[discussion_id] = []
            self._subscribers[discussion_id].append(queue)
        return queue

    async def unsubscribe(self, discussion_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from a discussion's events."""
        async with self._lock:
            if discussion_id in self._subscribers:
                try:
                    self._subscribers[discussion_id].remove(queue)
                except ValueError:
                    pass
                if not self._subscribers[discussion_id]:
                    del self._subscribers[discussion_id]

    async def publish(
        self,
        discussion_id: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Publish an event to all subscribers."""
        message = {
            "event": event,
            "data": data,
            "timestamp": int(time.time()),
        }

        async with self._lock:
            queues = self._subscribers.get(discussion_id, [])

        for queue in queues:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Failed to publish to queue: {e}")

    async def publish_init(
        self,
        discussion_id: str,
        data: dict[str, Any],
    ) -> None:
        """Publish initial state."""
        await self.publish(discussion_id, "init", data)

    async def publish_speech_start(
        self,
        discussion_id: str,
        participant_id: str,
        name: str,
        job_title: str,
        round_num: int,
        color: str,
    ) -> None:
        """Publish speech start event."""
        await self.publish(discussion_id, "speech_start", {
            "participant_id": participant_id,
            "name": name,
            "job_title": job_title,
            "round": round_num,
            "color": color,
        })

    async def publish_speech_token(
        self,
        discussion_id: str,
        speech_id: int,
        content: str,
        seq: int,
    ) -> None:
        """Publish speech token (streaming)."""
        await self.publish(discussion_id, "speech_token", {
            "speech_id": speech_id,
            "content": content,
            "seq": seq,
        })

    async def publish_speech_end(
        self,
        discussion_id: str,
        speech_id: int,
        total_tokens: int,
    ) -> None:
        """Publish speech end event."""
        await self.publish(discussion_id, "speech_end", {
            "speech_id": speech_id,
            "total_tokens": total_tokens,
        })

    async def publish_speech(
        self,
        discussion_id: str,
        speech_data: dict[str, Any],
    ) -> None:
        """Publish complete speech."""
        await self.publish(discussion_id, "speech", speech_data)

    async def publish_finding(
        self,
        discussion_id: str,
        finding_type: str,
        content: str,
        round_num: int,
    ) -> None:
        """Publish a finding (consensus/disagreement)."""
        await self.publish(discussion_id, "finding_update", {
            "type": finding_type,
            "content": content,
            "round": round_num,
        })

    async def publish_round_summary(
        self,
        discussion_id: str,
        round_num: int,
        convergence: Optional[float],
        consensus: list[str],
        disagreements: list[str],
    ) -> None:
        """Publish round summary."""
        await self.publish(discussion_id, "round_summary", {
            "round": round_num,
            "convergence": convergence,
            "consensus": consensus,
            "disagreements": disagreements,
        })

    async def publish_status_change(
        self,
        discussion_id: str,
        status: str,
        conclusion: Optional[str] = None,
    ) -> None:
        """Publish status change."""
        data: dict[str, Any] = {"status": status}
        if conclusion:
            data["conclusion"] = conclusion
        await self.publish(discussion_id, "status_change", data)

    async def publish_participant_status(
        self,
        discussion_id: str,
        participant_id: str,
        status: str,
        thinking_summary: str = "",
    ) -> None:
        """Publish participant status update."""
        await self.publish(discussion_id, "participant_status", {
            "participant_id": participant_id,
            "status": status,
            "thinking_summary": thinking_summary,
        })

    async def publish_thinking(
        self,
        discussion_id: str,
        participant_id: str,
        thinking_content: str,
    ) -> None:
        """Publish thinking process event."""
        await self.publish(discussion_id, "thinking", {
            "participant_id": participant_id,
            "content": thinking_content,
        })

    async def publish_draft(
        self,
        discussion_id: str,
        participant_id: str,
        draft_content: str,
    ) -> None:
        """Publish draft content event."""
        await self.publish(discussion_id, "draft", {
            "participant_id": participant_id,
            "content": draft_content,
        })

    async def publish_speech_evolution(
        self,
        discussion_id: str,
        participant_id: str,
        stage: str,  # "thinking", "draft", "final"
        content: str,
    ) -> None:
        """Publish speech evolution event (观点演化)."""
        await self.publish(discussion_id, "speech_evolution", {
            "participant_id": participant_id,
            "stage": stage,
            "content": content,
        })

    async def publish_error(
        self,
        discussion_id: str,
        error: str,
    ) -> None:
        """Publish error event."""
        await self.publish(discussion_id, "error", {"error": error})


# Global SSE manager instance
sse_manager = SSEManager()
