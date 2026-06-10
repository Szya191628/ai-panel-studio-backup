"""Database operations layer.

Wraps SQLite with explicit transaction control.
Reference: agent-roundtable's RoundtableDB patterns.
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional

from app.config import DATABASE_PATH
from app.models import (
    ConvergenceRecord,
    Discussion,
    Finding,
    Participant,
    Speech,
)
from app.schema import get_connection


class PanelDB:
    """Database operations for AI Panel Studio."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DATABASE_PATH

    def connect(self) -> sqlite3.Connection:
        """Get a new database connection."""
        return get_connection(self.db_path)

    # ------------------------------------------------------------------
    # Discussion operations
    # ------------------------------------------------------------------

    def create_discussion(
        self,
        conn: sqlite3.Connection,
        topic: str,
        host_profile: dict[str, Any],
        max_rounds: int = 5,
    ) -> Discussion:
        """Create a new discussion."""
        import secrets
        disc_id = f"disc_{secrets.token_urlsafe(12)}"
        now = int(time.time())

        conn.execute(
            """INSERT INTO discussions (id, topic, status, max_rounds, host_profile, created_at)
               VALUES (?, ?, 'assembling', ?, ?, ?)""",
            (disc_id, topic, max_rounds, json.dumps(host_profile), now),
        )
        conn.commit()

        return Discussion(
            id=disc_id,
            topic=topic,
            status="assembling",
            max_rounds=max_rounds,
            host_profile=host_profile,
            created_at=now,
        )

    def get_discussion(
        self, conn: sqlite3.Connection, discussion_id: str
    ) -> Optional[Discussion]:
        """Get a discussion by ID."""
        row = conn.execute(
            "SELECT * FROM discussions WHERE id = ?", (discussion_id,)
        ).fetchone()
        if not row:
            return None
        return Discussion(
            id=row["id"],
            topic=row["topic"],
            status=row["status"],
            max_rounds=row["max_rounds"],
            current_round=row["current_round"],
            host_profile=json.loads(row["host_profile"]) if row["host_profile"] else None,
            created_at=row["created_at"],
            concluded_at=row["concluded_at"],
            conclusion=row["conclusion"],
            convergence_score=row["convergence_score"],
        )

    def list_discussions(
        self,
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[Discussion]:
        """List discussions with optional status filter."""
        if status:
            rows = conn.execute(
                "SELECT * FROM discussions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM discussions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            Discussion(
                id=r["id"],
                topic=r["topic"],
                status=r["status"],
                max_rounds=r["max_rounds"],
                current_round=r["current_round"],
                host_profile=json.loads(r["host_profile"]) if r["host_profile"] else None,
                created_at=r["created_at"],
                concluded_at=r["concluded_at"],
                conclusion=r["conclusion"],
                convergence_score=r["convergence_score"],
            )
            for r in rows
        ]

    def update_discussion_status(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        status: str,
    ) -> bool:
        """Update discussion status."""
        conn.execute(
            "UPDATE discussions SET status = ? WHERE id = ?",
            (status, discussion_id),
        )
        conn.commit()
        return True

    def conclude_discussion(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        conclusion: Optional[str] = None,
    ) -> bool:
        """Conclude a discussion."""
        now = int(time.time())
        conn.execute(
            """UPDATE discussions
               SET status = 'concluded', concluded_at = ?, conclusion = ?
               WHERE id = ?""",
            (now, conclusion, discussion_id),
        )
        conn.commit()
        return True

    def advance_round(
        self, conn: sqlite3.Connection, discussion_id: str
    ) -> dict[str, Any]:
        """Advance to the next round."""
        disc = self.get_discussion(conn, discussion_id)
        if not disc:
            return {"error": "Discussion not found"}

        new_round = disc.current_round + 1
        discussion_complete = new_round > disc.max_rounds

        if discussion_complete:
            self.conclude_discussion(conn, discussion_id)
            return {
                "new_round": new_round,
                "discussion_complete": True,
            }

        conn.execute(
            "UPDATE discussions SET current_round = ? WHERE id = ?",
            (new_round, discussion_id),
        )
        conn.commit()
        return {
            "new_round": new_round,
            "discussion_complete": False,
        }

    # ------------------------------------------------------------------
    # Participant operations
    # ------------------------------------------------------------------

    def add_participant(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        name: str,
        job_title: str = "",
        title: str = "",
        stance: str = "",
        color: str = "#4A90D9",
        avatar_seed: str = "",
        is_host: bool = False,
    ) -> Participant:
        """Add a participant to a discussion."""
        import secrets
        part_id = f"part_{secrets.token_urlsafe(12)}"

        conn.execute(
            """INSERT INTO participants
               (id, discussion_id, name, job_title, title, stance, color, avatar_seed, is_host)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (part_id, discussion_id, name, job_title, title, stance, color, avatar_seed, int(is_host)),
        )
        conn.commit()

        return Participant(
            id=part_id,
            discussion_id=discussion_id,
            name=name,
            job_title=job_title,
            title=title,
            stance=stance,
            color=color,
            avatar_seed=avatar_seed,
            is_host=is_host,
        )

    def get_participants(
        self, conn: sqlite3.Connection, discussion_id: str
    ) -> list[Participant]:
        """Get all participants for a discussion."""
        rows = conn.execute(
            "SELECT * FROM participants WHERE discussion_id = ? ORDER BY is_host DESC, rowid",
            (discussion_id,),
        ).fetchall()
        return [
            Participant(
                id=r["id"],
                discussion_id=r["discussion_id"],
                name=r["name"],
                job_title=r["job_title"] or "",
                title=r["title"] or "",
                stance=r["stance"] or "",
                color=r["color"] or "#4A90D9",
                avatar_seed=r["avatar_seed"] or "",
                status=r["status"] or "standby",
                thinking_summary=r["thinking_summary"] or "",
                is_host=bool(r["is_host"]),
            )
            for r in rows
        ]

    def update_participant_status(
        self,
        conn: sqlite3.Connection,
        participant_id: str,
        status: str,
        thinking_summary: str = "",
    ) -> bool:
        """Update participant status and thinking summary."""
        conn.execute(
            """UPDATE participants
               SET status = ?, thinking_summary = ?
               WHERE id = ?""",
            (status, thinking_summary, participant_id),
        )
        conn.commit()
        return True

    # ------------------------------------------------------------------
    # Speech operations
    # ------------------------------------------------------------------

    def add_speech(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        participant_id: str,
        content: str,
        speech_type: str = "statement",
        reply_to: Optional[int] = None,
    ) -> dict[str, Any]:
        """Record a speech and check round progression."""
        now = int(time.time())

        # Get current round
        disc = self.get_discussion(conn, discussion_id)
        if not disc:
            return {"error": "Discussion not found"}

        current_round = disc.current_round

        conn.execute(
            """INSERT INTO speeches
               (discussion_id, participant_id, round, content, speech_type, reply_to, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (discussion_id, participant_id, current_round, content, speech_type, reply_to, now),
        )
        speech_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Check if round is complete (all non-host participants have spoken)
        participants = self.get_participants(conn, discussion_id)
        non_host = [p for p in participants if not p.is_host]
        spoke_this_round = conn.execute(
            """SELECT DISTINCT participant_id FROM speeches
               WHERE discussion_id = ? AND round = ?""",
            (discussion_id, current_round),
        ).fetchall()
        spoke_ids = {r["participant_id"] for r in spoke_this_round}

        round_complete = all(p.id in spoke_ids for p in non_host)

        # Auto-advance round if complete
        discussion_complete = False
        if round_complete:
            result = self.advance_round(conn, discussion_id)
            discussion_complete = result.get("discussion_complete", False)

        conn.commit()

        return {
            "speech_id": speech_id,
            "round": current_round,
            "round_complete": round_complete,
            "discussion_complete": discussion_complete,
        }

    def get_speeches(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        since_round: Optional[int] = None,
    ) -> list[Speech]:
        """Get speeches for a discussion."""
        if since_round is not None:
            rows = conn.execute(
                """SELECT * FROM speeches
                   WHERE discussion_id = ? AND round >= ?
                   ORDER BY round, created_at""",
                (discussion_id, since_round),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM speeches
                   WHERE discussion_id = ?
                   ORDER BY round, created_at""",
                (discussion_id,),
            ).fetchall()
        return [
            Speech(
                id=r["id"],
                discussion_id=r["discussion_id"],
                participant_id=r["participant_id"],
                round=r["round"],
                content=r["content"],
                speech_type=r["speech_type"] or "statement",
                reply_to=r["reply_to"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Finding operations
    # ------------------------------------------------------------------

    def add_finding(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        finding_type: str,
        content: str,
        round_num: int,
        related_speeches: Optional[list[int]] = None,
    ) -> Finding:
        """Add a consensus/disagreement finding."""
        conn.execute(
            """INSERT INTO findings (discussion_id, type, content, round, related_speeches)
               VALUES (?, ?, ?, ?, ?)""",
            (discussion_id, finding_type, content, round_num,
             json.dumps(related_speeches) if related_speeches else None),
        )
        finding_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

        return Finding(
            id=finding_id,
            discussion_id=discussion_id,
            type=finding_type,
            content=content,
            round=round_num,
            related_speeches=related_speeches or [],
        )

    def get_findings(
        self, conn: sqlite3.Connection, discussion_id: str
    ) -> list[Finding]:
        """Get all findings for a discussion."""
        rows = conn.execute(
            "SELECT * FROM findings WHERE discussion_id = ? ORDER BY round, id",
            (discussion_id,),
        ).fetchall()
        return [
            Finding(
                id=r["id"],
                discussion_id=r["discussion_id"],
                type=r["type"],
                content=r["content"],
                round=r["round"],
                related_speeches=json.loads(r["related_speeches"]) if r["related_speeches"] else [],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Convergence operations
    # ------------------------------------------------------------------

    def calculate_convergence(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        round_num: int,
    ) -> Optional[float]:
        """Calculate convergence score for a round.

        Score = consensus / (consensus + disagreement)
        """
        findings = conn.execute(
            """SELECT type, COUNT(*) as cnt FROM findings
               WHERE discussion_id = ? AND round = ?
               GROUP BY type""",
            (discussion_id, round_num),
        ).fetchall()

        counts = {r["type"]: r["cnt"] for r in findings}
        consensus = counts.get("consensus", 0)
        disagreement = counts.get("disagreement", 0)

        if consensus + disagreement == 0:
            return None

        score = consensus / (consensus + disagreement)

        # Record history
        conn.execute(
            """INSERT OR REPLACE INTO convergence_history
               (discussion_id, round, score, consensus_count, disagreement_count)
               VALUES (?, ?, ?, ?, ?)""",
            (discussion_id, round_num, score, consensus, disagreement),
        )
        conn.commit()

        return score

    def get_convergence_history(
        self, conn: sqlite3.Connection, discussion_id: str
    ) -> list[ConvergenceRecord]:
        """Get convergence history for a discussion."""
        rows = conn.execute(
            """SELECT * FROM convergence_history
               WHERE discussion_id = ?
               ORDER BY round""",
            (discussion_id,),
        ).fetchall()
        return [
            ConvergenceRecord(
                discussion_id=r["discussion_id"],
                round=r["round"],
                score=r["score"],
                consensus_count=r["consensus_count"],
                disagreement_count=r["disagreement_count"],
            )
            for r in rows
        ]
