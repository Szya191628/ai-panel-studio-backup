"""Database layer tests."""

import pytest
from app.db import PanelDB


class TestDiscussion:
    """Test discussion operations."""

    def test_create_discussion(self, db, conn):
        """Test creating a discussion."""
        host = {"name": "Test Host", "job_title": "Host"}
        disc = db.create_discussion(conn, "Test Topic", host, max_rounds=3)

        assert disc.id.startswith("disc_")
        assert disc.topic == "Test Topic"
        assert disc.status == "assembling"
        assert disc.max_rounds == 3

    def test_get_discussion(self, db, conn):
        """Test getting a discussion."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        result = db.get_discussion(conn, disc.id)
        assert result is not None
        assert result.id == disc.id
        assert result.topic == "Test Topic"

    def test_list_discussions(self, db, conn):
        """Test listing discussions."""
        host = {"name": "Test Host"}
        db.create_discussion(conn, "Topic 1", host)
        db.create_discussion(conn, "Topic 2", host)

        discussions = db.list_discussions(conn)
        assert len(discussions) == 2

    def test_update_status(self, db, conn):
        """Test updating discussion status."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        db.update_discussion_status(conn, disc.id, "active")
        result = db.get_discussion(conn, disc.id)
        assert result.status == "active"

    def test_conclude_discussion(self, db, conn):
        """Test concluding a discussion."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        db.conclude_discussion(conn, disc.id, "Test conclusion")
        result = db.get_discussion(conn, disc.id)
        assert result.status == "concluded"
        assert result.conclusion == "Test conclusion"

    def test_advance_round(self, db, conn):
        """Test advancing rounds."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host, max_rounds=3)

        # Set to round 1 first
        conn.execute("UPDATE discussions SET current_round = 1 WHERE id = ?", (disc.id,))
        conn.commit()

        result = db.advance_round(conn, disc.id)
        assert result["new_round"] == 2
        assert result["discussion_complete"] is False

    def test_advance_beyond_max(self, db, conn):
        """Test advancing beyond max rounds."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host, max_rounds=2)

        # Set to max round
        conn.execute("UPDATE discussions SET current_round = 2 WHERE id = ?", (disc.id,))
        conn.commit()

        result = db.advance_round(conn, disc.id)
        assert result["discussion_complete"] is True


class TestParticipant:
    """Test participant operations."""

    def test_add_participant(self, db, conn):
        """Test adding a participant."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        participant = db.add_participant(
            conn, disc.id, "Expert 1", "Engineer", "Senior", "Pro"
        )

        assert participant.id.startswith("part_")
        assert participant.name == "Expert 1"
        assert participant.job_title == "Engineer"

    def test_get_participants(self, db, conn):
        """Test getting participants."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        db.add_participant(conn, disc.id, "Host", is_host=True)
        db.add_participant(conn, disc.id, "Expert 1")
        db.add_participant(conn, disc.id, "Expert 2")

        participants = db.get_participants(conn, disc.id)
        assert len(participants) == 3
        # Host should be first
        assert participants[0].is_host is True

    def test_update_participant_status(self, db, conn):
        """Test updating participant status."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)
        participant = db.add_participant(conn, disc.id, "Expert 1")

        db.update_participant_status(conn, participant.id, "speaking", "Thinking...")

        participants = db.get_participants(conn, disc.id)
        expert = next(p for p in participants if p.id == participant.id)
        assert expert.status == "speaking"
        assert expert.thinking_summary == "Thinking..."


class TestSpeech:
    """Test speech operations."""

    def test_add_speech(self, db, conn):
        """Test adding a speech."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host, max_rounds=3)
        conn.execute("UPDATE discussions SET current_round = 1 WHERE id = ?", (disc.id,))
        conn.commit()

        expert1 = db.add_participant(conn, disc.id, "Expert 1")
        expert2 = db.add_participant(conn, disc.id, "Expert 2")

        result = db.add_speech(conn, disc.id, expert1.id, "Test speech")

        assert "speech_id" in result
        assert result["round"] == 1
        assert result["round_complete"] is False  # Only 1 of 2 experts spoke

    def test_round_completion(self, db, conn):
        """Test round completion detection."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host, max_rounds=3)
        conn.execute("UPDATE discussions SET current_round = 1 WHERE id = ?", (disc.id,))
        conn.commit()

        expert1 = db.add_participant(conn, disc.id, "Expert 1")
        expert2 = db.add_participant(conn, disc.id, "Expert 2")

        # First speech - not complete
        result1 = db.add_speech(conn, disc.id, expert1.id, "Speech 1")
        assert result1["round_complete"] is False

        # Second speech - round complete
        result2 = db.add_speech(conn, disc.id, expert2.id, "Speech 2")
        assert result2["round_complete"] is True

    def test_get_speeches(self, db, conn):
        """Test getting speeches."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)
        conn.execute("UPDATE discussions SET current_round = 1 WHERE id = ?", (disc.id,))
        conn.commit()

        expert = db.add_participant(conn, disc.id, "Expert 1")
        db.add_speech(conn, disc.id, expert.id, "Speech 1")
        db.add_speech(conn, disc.id, expert.id, "Speech 2")

        speeches = db.get_speeches(conn, disc.id)
        assert len(speeches) == 2


class TestFinding:
    """Test finding operations."""

    def test_add_finding(self, db, conn):
        """Test adding a finding."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        finding = db.add_finding(conn, disc.id, "consensus", "Test consensus", 1)

        assert finding.id > 0
        assert finding.type == "consensus"
        assert finding.content == "Test consensus"

    def test_get_findings(self, db, conn):
        """Test getting findings."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        db.add_finding(conn, disc.id, "consensus", "Consensus 1", 1)
        db.add_finding(conn, disc.id, "disagreement", "Disagreement 1", 1)

        findings = db.get_findings(conn, disc.id)
        assert len(findings) == 2

    def test_convergence_calculation(self, db, conn):
        """Test convergence score calculation."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        db.add_finding(conn, disc.id, "consensus", "C1", 1)
        db.add_finding(conn, disc.id, "consensus", "C2", 1)
        db.add_finding(conn, disc.id, "disagreement", "D1", 1)

        score = db.calculate_convergence(conn, disc.id, 1)
        assert score is not None
        assert abs(score - 0.666) < 0.01  # 2/3

    def test_convergence_no_findings(self, db, conn):
        """Test convergence with no findings."""
        host = {"name": "Test Host"}
        disc = db.create_discussion(conn, "Test Topic", host)

        score = db.calculate_convergence(conn, disc.id, 1)
        assert score is None
