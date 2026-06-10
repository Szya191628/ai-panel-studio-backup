"""Core business logic for AI Panel Studio.

Reference: agent-roundtable's RoundtableCore patterns.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from app.db import PanelDB
from app.llm import (
    extract_findings,
    generate_guests,
    generate_speech,
    generate_speech_stream,
    generate_summary,
)
from app.models import Discussion, Participant
from app.sse import sse_manager

logger = logging.getLogger(__name__)


class PanelCore:
    """High-level operations for AI Panel Studio."""

    def __init__(self, db: PanelDB | None = None):
        self.db = db or PanelDB()

    # ------------------------------------------------------------------
    # Guest generation
    # ------------------------------------------------------------------

    async def generate_guests(
        self,
        topic: str,
        expert_count: int = 4,
    ) -> dict[str, Any]:
        """Generate host and expert profiles."""
        result = await generate_guests(topic, expert_count)
        return {
            "ok": True,
            "host": result["host"],
            "experts": result["experts"],
        }

    # ------------------------------------------------------------------
    # Discussion lifecycle
    # ------------------------------------------------------------------

    async def create_discussion(
        self,
        topic: str,
        host: dict[str, Any],
        experts: list[dict[str, Any]],
        max_rounds: int = 5,
    ) -> dict[str, Any]:
        """Create a new discussion with participants."""
        conn = self.db.connect()
        try:
            # Create discussion
            disc = self.db.create_discussion(conn, topic, host, max_rounds)

            # Add host as participant
            self.db.add_participant(
                conn,
                disc.id,
                name=host["name"],
                job_title=host.get("job_title", ""),
                title=host.get("title", ""),
                stance=host.get("stance", ""),
                color=host.get("color", "#FF6B6B"),
                avatar_seed=host.get("avatar_seed", ""),
                is_host=True,
            )

            # Add experts
            for expert in experts:
                self.db.add_participant(
                    conn,
                    disc.id,
                    name=expert["name"],
                    job_title=expert.get("job_title", ""),
                    title=expert.get("title", ""),
                    stance=expert.get("stance", ""),
                    color=expert.get("color", "#4A90D9"),
                    avatar_seed=expert.get("avatar_seed", ""),
                    is_host=False,
                )

            participants = self.db.get_participants(conn, disc.id)

            return {
                "ok": True,
                "discussion_id": disc.id,
                "topic": disc.topic,
                "status": disc.status,
                "participants_count": len(participants),
                "participants": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "job_title": p.job_title,
                        "title": p.title,
                        "stance": p.stance,
                        "color": p.color,
                        "is_host": p.is_host,
                    }
                    for p in participants
                ],
            }
        finally:
            conn.close()

    async def confirm_and_start(
        self,
        discussion_id: str,
    ) -> dict[str, Any]:
        """Confirm guests and start the discussion."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            if disc.status != "assembling":
                return {"ok": False, "error": f"Discussion is already {disc.status}"}

            # Update status to active
            self.db.update_discussion_status(conn, discussion_id, "active")

            # Start round 1
            conn.execute(
                "UPDATE discussions SET current_round = 1 WHERE id = ?",
                (discussion_id,),
            )
            conn.commit()

            # Publish status change
            await sse_manager.publish_status_change(discussion_id, "active")

            return {
                "ok": True,
                "discussion_id": discussion_id,
                "status": "active",
                "message": "讨论已开始",
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Speech operations
    # ------------------------------------------------------------------

    async def record_speech(
        self,
        discussion_id: str,
        participant_id: str,
        content: str,
        speech_type: str = "statement",
        reply_to: Optional[int] = None,
    ) -> dict[str, Any]:
        """Record a speech."""
        conn = self.db.connect()
        try:
            result = self.db.add_speech(
                conn,
                discussion_id,
                participant_id,
                content,
                speech_type,
                reply_to,
            )

            if "error" in result:
                return {"ok": False, "error": result["error"]}

            # Get participant info
            participants = self.db.get_participants(conn, discussion_id)
            participant = next((p for p in participants if p.id == participant_id), None)

            if participant:
                # Publish speech
                await sse_manager.publish_speech(
                    discussion_id,
                    {
                        "id": result["speech_id"],
                        "participant_id": participant_id,
                        "name": participant.name,
                        "job_title": participant.job_title,
                        "content": content,
                        "round": result["round"],
                        "color": participant.color,
                    },
                )

            # Handle round completion
            if result["round_complete"]:
                await self._handle_round_complete(conn, discussion_id, result["round"])

            # Handle discussion completion
            if result["discussion_complete"]:
                await self._handle_discussion_complete(conn, discussion_id)

            return {
                "ok": True,
                "speech_id": result["speech_id"],
                "round": result["round"],
                "round_complete": result["round_complete"],
                "discussion_complete": result["discussion_complete"],
            }
        finally:
            conn.close()

    async def generate_and_record_speech(
        self,
        discussion_id: str,
        participant_id: str,
    ) -> dict[str, Any]:
        """Generate a speech using AI and record it."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            participants = self.db.get_participants(conn, discussion_id)
            participant = next((p for p in participants if p.id == participant_id), None)
            if not participant:
                return {"ok": False, "error": "Participant not found"}

            # Get transcript
            speeches = self.db.get_speeches(conn, discussion_id)
            transcript = []
            for s in speeches:
                p = next((pp for pp in participants if pp.id == s.participant_id), None)
                if p:
                    transcript.append({
                        "name": p.name,
                        "job_title": p.job_title,
                        "content": s.content,
                    })

            # Update participant status to preparing
            self.db.update_participant_status(conn, participant_id, "preparing", "正在思考...")
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "preparing", "正在思考..."
            )

            # Generate speech
            speech_content = await generate_speech(
                disc.topic,
                {
                    "name": participant.name,
                    "job_title": participant.job_title,
                    "title": participant.title,
                    "stance": participant.stance,
                },
                transcript,
                disc.current_round,
                is_host=participant.is_host,
            )

            # Update status to speaking
            self.db.update_participant_status(conn, participant_id, "speaking", speech_content[:50])
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "speaking", speech_content[:50]
            )

            # Publish speech start
            await sse_manager.publish_speech_start(
                discussion_id,
                participant_id,
                participant.name,
                participant.job_title,
                disc.current_round,
                participant.color,
            )

            # Record speech
            result = await self.record_speech(
                discussion_id,
                participant_id,
                speech_content,
            )

            # Publish speech end
            await sse_manager.publish_speech_end(
                discussion_id,
                result.get("speech_id", 0),
                len(speech_content),
            )

            # Update status back to standby
            self.db.update_participant_status(conn, participant_id, "standby", "")
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "standby", ""
            )

            return result
        finally:
            conn.close()

    async def generate_and_record_speech_stream(
        self,
        discussion_id: str,
        participant_id: str,
    ):
        """Generate a speech with thinking process streaming."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                yield {"type": "error", "data": "Discussion not found"}
                return

            participants = self.db.get_participants(conn, discussion_id)
            participant = next((p for p in participants if p.id == participant_id), None)
            if not participant:
                yield {"type": "error", "data": "Participant not found"}
                return

            # Get transcript
            speeches = self.db.get_speeches(conn, discussion_id)
            transcript = []
            for s in speeches:
                p = next((pp for pp in participants if pp.id == s.participant_id), None)
                if p:
                    transcript.append({
                        "name": p.name,
                        "job_title": p.job_title,
                        "content": s.content,
                    })

            # Update status
            self.db.update_participant_status(conn, participant_id, "preparing", "正在思考...")
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "preparing", "正在思考..."
            )
            yield {"type": "status", "data": {"participant_id": participant_id, "status": "preparing"}}

            # Publish speech start
            await sse_manager.publish_speech_start(
                discussion_id,
                participant_id,
                participant.name,
                participant.job_title,
                disc.current_round,
                participant.color,
            )

            # 使用带思考过程的方法
            final_content = ""
            async for event in generate_speech_with_thinking(
                disc.topic,
                {
                    "name": participant.name,
                    "job_title": participant.job_title,
                    "title": participant.title,
                    "stance": participant.stance,
                },
                transcript,
                disc.current_round,
                is_host=participant.is_host,
            ):
                event_type = event["type"]
                content = event["content"]

                if event_type == "thinking":
                    # 思考阶段
                    await sse_manager.publish_thinking(
                        discussion_id, participant_id, content
                    )
                    await sse_manager.publish_participant_status(
                        discussion_id, participant_id, "preparing", f"思考: {content[:30]}..."
                    )
                    yield {"type": "thinking", "data": {"content": content}}

                elif event_type == "draft":
                    # 草稿阶段
                    await sse_manager.publish_draft(
                        discussion_id, participant_id, content
                    )
                    await sse_manager.publish_participant_status(
                        discussion_id, participant_id, "preparing", f"草稿: {content[:30]}..."
                    )
                    yield {"type": "draft", "data": {"content": content}}

                elif event_type == "speech_draft":
                    # 发言草稿
                    await sse_manager.publish_speech_evolution(
                        discussion_id, participant_id, "draft", content
                    )
                    yield {"type": "speech_draft", "data": {"content": content}}

                elif event_type == "complete":
                    # 最终发言
                    final_content = content
                    await sse_manager.publish_speech_evolution(
                        discussion_id, participant_id, "final", content
                    )
                    yield {"type": "speech_final", "data": {"content": content}}

            # 更新状态为发言中
            self.db.update_participant_status(conn, participant_id, "speaking", final_content[:50])
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "speaking", final_content[:50]
            )

            # Record the complete speech
            result = await self.record_speech(
                discussion_id,
                participant_id,
                final_content,
            )

            # Publish speech end
            await sse_manager.publish_speech_end(
                discussion_id,
                result.get("speech_id", 0),
                len(final_content),
            )

            # Update status back to standby
            self.db.update_participant_status(conn, participant_id, "standby", "")
            await sse_manager.publish_participant_status(
                discussion_id, participant_id, "standby", ""
            )

            yield {"type": "complete", "data": result}

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Discussion operations
    # ------------------------------------------------------------------

    async def get_discussion(
        self,
        discussion_id: str,
    ) -> dict[str, Any]:
        """Get discussion details."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            participants = self.db.get_participants(conn, discussion_id)
            speeches = self.db.get_speeches(conn, discussion_id)
            findings = self.db.get_findings(conn, discussion_id)

            consensus = [f.content for f in findings if f.type == "consensus"]
            disagreements = [f.content for f in findings if f.type == "disagreement"]

            return {
                "ok": True,
                "discussion": {
                    "id": disc.id,
                    "topic": disc.topic,
                    "status": disc.status,
                    "current_round": disc.current_round,
                    "max_rounds": disc.max_rounds,
                    "convergence_score": disc.convergence_score,
                    "created_at": disc.created_at,
                    "conclusion": disc.conclusion,
                },
                "participants": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "job_title": p.job_title,
                        "title": p.title,
                        "stance": p.stance,
                        "color": p.color,
                        "status": p.status,
                        "thinking_summary": p.thinking_summary,
                        "is_host": p.is_host,
                    }
                    for p in participants
                ],
                "speeches": [
                    {
                        "id": s.id,
                        "participant_id": s.participant_id,
                        "round": s.round,
                        "content": s.content,
                        "speech_type": s.speech_type,
                        "created_at": s.created_at,
                    }
                    for s in speeches
                ],
                "findings": {
                    "consensus": consensus,
                    "disagreements": disagreements,
                },
            }
        finally:
            conn.close()

    async def list_discussions(
        self,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List discussions."""
        conn = self.db.connect()
        try:
            discussions = self.db.list_discussions(conn, status, limit)

            # Get participant counts
            result = []
            for disc in discussions:
                participants = self.db.get_participants(conn, disc.id)
                result.append({
                    "id": disc.id,
                    "topic": disc.topic,
                    "status": disc.status,
                    "current_round": disc.current_round,
                    "max_rounds": disc.max_rounds,
                    "participant_count": len(participants),
                    "created_at": disc.created_at,
                    "convergence_score": disc.convergence_score,
                })

            return {
                "ok": True,
                "discussions": result,
                "count": len(result),
            }
        finally:
            conn.close()

    async def get_status(
        self,
        discussion_id: str,
    ) -> dict[str, Any]:
        """Get discussion status."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            participants = self.db.get_participants(conn, discussion_id)
            speeches = self.db.get_speeches(conn, discussion_id)
            findings = self.db.get_findings(conn, discussion_id)

            consensus = [f.content for f in findings if f.type == "consensus"]
            disagreements = [f.content for f in findings if f.type == "disagreement"]

            # Get next speaker
            non_host = [p for p in participants if not p.is_host]
            spoke_this_round = {
                s.participant_id
                for s in speeches
                if s.round == disc.current_round
            }
            next_speaker = None
            for p in non_host:
                if p.id not in spoke_this_round:
                    next_speaker = p.id
                    break

            return {
                "ok": True,
                "discussion_id": disc.id,
                "status": disc.status,
                "current_round": disc.current_round,
                "max_rounds": disc.max_rounds,
                "convergence_score": disc.convergence_score,
                "consensus_points": consensus,
                "disagreement_points": disagreements,
                "speech_count": len(speeches),
                "participant_count": len(participants),
                "next_speaker": next_speaker,
            }
        finally:
            conn.close()

    async def end_discussion(
        self,
        discussion_id: str,
        conclusion: Optional[str] = None,
    ) -> dict[str, Any]:
        """End a discussion."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            if disc.status == "concluded":
                return {"ok": False, "error": "Discussion already concluded"}

            # Generate conclusion if not provided
            if not conclusion:
                participants = self.db.get_participants(conn, discussion_id)
                speeches = self.db.get_speeches(conn, discussion_id)
                findings = self.db.get_findings(conn, discussion_id)

                transcript = []
                for s in speeches:
                    p = next((pp for pp in participants if pp.id == s.participant_id), None)
                    if p:
                        transcript.append({
                            "name": p.name,
                            "job_title": p.job_title,
                            "content": s.content,
                        })

                consensus = [f.content for f in findings if f.type == "consensus"]
                disagreements = [f.content for f in findings if f.type == "disagreement"]

                conclusion = await generate_summary(
                    disc.topic, transcript, consensus, disagreements
                )

            # Conclude
            self.db.conclude_discussion(conn, discussion_id, conclusion)

            # Publish
            await sse_manager.publish_status_change(
                discussion_id, "concluded", conclusion
            )

            return {
                "ok": True,
                "discussion_id": discussion_id,
                "action": "concluded",
                "conclusion": conclusion,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Auto-discussion (orchestration)
    # ------------------------------------------------------------------

    async def run_discussion(
        self,
        discussion_id: str,
        max_rounds: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run a full discussion automatically."""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "Discussion not found"}

            participants = self.db.get_participants(conn, discussion_id)
            host = next((p for p in participants if p.is_host), None)
            experts = [p for p in participants if not p.is_host]

            if not host or not experts:
                return {"ok": False, "error": "Need host and experts"}

            rounds = max_rounds or disc.max_rounds

            # Host opening
            await self.generate_and_record_speech(discussion_id, host.id)

            # Discussion rounds
            for round_num in range(1, rounds + 1):
                # Each expert speaks
                for expert in experts:
                    await self.generate_and_record_speech(discussion_id, expert.id)

                # Extract findings
                speeches = self.db.get_speeches(conn, discussion_id)
                round_speeches = [s for s in speeches if s.round == round_num]
                transcript = []
                for s in round_speeches:
                    p = next((pp for pp in participants if pp.id == s.participant_id), None)
                    if p:
                        transcript.append({
                            "name": p.name,
                            "job_title": p.job_title,
                            "content": s.content,
                        })

                findings = await extract_findings(disc.topic, transcript, round_num)
                for f in findings:
                    self.db.add_finding(
                        conn,
                        discussion_id,
                        f["type"],
                        f["content"],
                        round_num,
                    )
                    await sse_manager.publish_finding(
                        discussion_id, f["type"], f["content"], round_num
                    )

                # Calculate convergence
                convergence = self.db.calculate_convergence(conn, discussion_id, round_num)
                if convergence is not None:
                    await sse_manager.publish_round_summary(
                        discussion_id,
                        round_num,
                        convergence,
                        [f["content"] for f in findings if f["type"] == "consensus"],
                        [f["content"] for f in findings if f["type"] == "disagreement"],
                    )

            # Generate summary
            all_speeches = self.db.get_speeches(conn, discussion_id)
            all_findings = self.db.get_findings(conn, discussion_id)
            transcript = []
            for s in all_speeches:
                p = next((pp for pp in participants if pp.id == s.participant_id), None)
                if p:
                    transcript.append({
                        "name": p.name,
                        "job_title": p.job_title,
                        "content": s.content,
                    })

            consensus = [f.content for f in all_findings if f.type == "consensus"]
            disagreements = [f.content for f in all_findings if f.type == "disagreement"]

            conclusion = await generate_summary(
                disc.topic, transcript, consensus, disagreements
            )

            # Conclude
            self.db.conclude_discussion(conn, discussion_id, conclusion)
            await sse_manager.publish_status_change(
                discussion_id, "concluded", conclusion
            )

            return {
                "ok": True,
                "discussion_id": discussion_id,
                "action": "concluded",
                "conclusion": conclusion,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _handle_round_complete(
        self,
        conn: Any,
        discussion_id: str,
        round_num: int,
    ) -> None:
        """Handle round completion - extract findings."""
        participants = self.db.get_participants(conn, discussion_id)
        speeches = self.db.get_speeches(conn, discussion_id)

        round_speeches = [s for s in speeches if s.round == round_num]
        transcript = []
        for s in round_speeches:
            p = next((pp for pp in participants if pp.id == s.participant_id), None)
            if p:
                transcript.append({
                    "name": p.name,
                    "job_title": p.job_title,
                    "content": s.content,
                })

        disc = self.db.get_discussion(conn, discussion_id)
        if not disc:
            return

        findings = await extract_findings(disc.topic, transcript, round_num)
        for f in findings:
            self.db.add_finding(
                conn,
                discussion_id,
                f["type"],
                f["content"],
                round_num,
            )
            await sse_manager.publish_finding(
                discussion_id, f["type"], f["content"], round_num
            )

        convergence = self.db.calculate_convergence(conn, discussion_id, round_num)
        if convergence is not None:
            await sse_manager.publish_round_summary(
                discussion_id,
                round_num,
                convergence,
                [f["content"] for f in findings if f["type"] == "consensus"],
                [f["content"] for f in findings if f["type"] == "disagreement"],
            )

    async def _handle_discussion_complete(
        self,
        conn: Any,
        discussion_id: str,
    ) -> None:
        """Handle discussion completion - generate summary."""
        participants = self.db.get_participants(conn, discussion_id)
        speeches = self.db.get_speeches(conn, discussion_id)
        findings = self.db.get_findings(conn, discussion_id)
        disc = self.db.get_discussion(conn, discussion_id)

        if not disc:
            return

        transcript = []
        for s in speeches:
            p = next((pp for pp in participants if pp.id == s.participant_id), None)
            if p:
                transcript.append({
                    "name": p.name,
                    "job_title": p.job_title,
                    "content": s.content,
                })

        consensus = [f.content for f in findings if f.type == "consensus"]
        disagreements = [f.content for f in findings if f.type == "disagreement"]

        conclusion = await generate_summary(
            disc.topic, transcript, consensus, disagreements
        )

        self.db.conclude_discussion(conn, discussion_id, conclusion)
        await sse_manager.publish_status_change(
            discussion_id, "concluded", conclusion
        )
