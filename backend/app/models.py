"""Data models for AI Panel Studio.

Pure dataclasses with zero external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Discussion:
    id: str
    topic: str
    status: str = "assembling"  # assembling/active/concluded/cancelled
    max_rounds: int = 5
    current_round: int = 0
    host_profile: Optional[dict[str, Any]] = None
    created_at: int = 0
    concluded_at: Optional[int] = None
    conclusion: Optional[str] = None
    convergence_score: Optional[float] = None


@dataclass
class Participant:
    id: str
    discussion_id: str
    name: str
    job_title: str = ""
    title: str = ""
    stance: str = ""
    color: str = "#4A90D9"
    avatar_seed: str = ""
    status: str = "standby"  # standby/preparing/speaking
    thinking_summary: str = ""
    is_host: bool = False


@dataclass
class Speech:
    id: int
    discussion_id: str
    participant_id: str
    round: int
    content: str
    speech_type: str = "statement"  # statement/question/rebuttal/summary
    reply_to: Optional[int] = None
    created_at: int = 0


@dataclass
class Finding:
    id: int
    discussion_id: str
    type: str  # consensus/disagreement/new_point
    content: str
    round: int
    related_speeches: list[int] = field(default_factory=list)


@dataclass
class ConvergenceRecord:
    discussion_id: str
    round: int
    score: float
    consensus_count: int = 0
    disagreement_count: int = 0


# Guest generation response model
@dataclass
class GuestProfile:
    name: str
    job_title: str
    title: str
    stance: str
    color: str
    avatar_seed: str


@dataclass
class GuestGenerationResult:
    host: GuestProfile
    experts: list[GuestProfile]
