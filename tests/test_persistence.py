"""Tests for debate persistence — the repository, the read endpoints, and the
persist-on-completion behaviour of run_debate. The DB is a throwaway SQLite per
test (see ``conftest._test_db``); the LLM is mocked via the conftest fixtures.
"""
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import db
from api.services import debate_repository
from api.services.debate_service import DebateService
from api.schemas.debate import WSMessageType
from conftest import sample_scores


def _save_kwargs(debate_id="d1", topic="T", winner="PRO", n_transcript=2):
    """Build kwargs for save_completed_debate with a fixed created_at.

    created_at is a literal (not db.utcnow()) so tests can patch db.utcnow to
    control completed_at ordering without the call here consuming the patch.
    """
    return dict(
        debate_id=debate_id,
        topic=topic,
        pro_style="passionate",
        con_style="academic",
        transcript=[{"speaker": "PRO", "content": "x", "phase": "opening_pro"}] * n_transcript,
        argument_scores=sample_scores().model_dump(),
        winner=winner,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from api.main import app
    return TestClient(app)


async def _drain(svc, session, *, vote="PRO"):
    """Run a debate to completion, auto-submitting a vote when asked."""
    events = []
    async for event in svc.run_debate(session):
        events.append(event)
        if event["type"] == WSMessageType.VOTE_REQUIRED and vote is not None:
            svc.submit_vote(session.debate_id, vote)
    return events


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class TestRepository:
    def test_save_then_get_round_trips(self):
        debate_repository.save_completed_debate(**_save_kwargs("abc", topic="Round trip"))
        with db.SessionLocal() as s:
            row = debate_repository.get_debate(s, "abc")
            assert row is not None
            assert row.topic == "Round trip"
            assert row.winner == "PRO"
            assert row.message_count == 2
            assert row.argument_scores["winner"] == "PRO"
            assert row.completed_at is not None

    def test_get_unknown_returns_none(self):
        with db.SessionLocal() as s:
            assert debate_repository.get_debate(s, "nope") is None

    def test_list_returns_all_saved(self):
        debate_repository.save_completed_debate(**_save_kwargs("a", topic="First"))
        debate_repository.save_completed_debate(**_save_kwargs("b", topic="Second"))
        with db.SessionLocal() as s:
            rows = debate_repository.list_debates(s)
            assert {r.topic for r in rows} == {"First", "Second"}

    def test_list_orders_most_recently_completed_first(self, monkeypatch):
        # Control completed_at so ordering is deterministic (no clock-resolution
        # ties on fast/coarse-clock platforms).
        stamps = iter([datetime(2026, 1, 1), datetime(2026, 6, 1)])
        monkeypatch.setattr(db, "utcnow", lambda: next(stamps))
        debate_repository.save_completed_debate(**_save_kwargs("old", topic="Old"))
        debate_repository.save_completed_debate(**_save_kwargs("new", topic="New"))
        with db.SessionLocal() as s:
            rows = debate_repository.list_debates(s)
            assert [r.id for r in rows] == ["new", "old"]

    def test_save_is_idempotent_upsert(self):
        debate_repository.save_completed_debate(**_save_kwargs("dup", topic="Orig"))
        debate_repository.save_completed_debate(**_save_kwargs("dup", topic="Updated"))
        with db.SessionLocal() as s:
            rows = debate_repository.list_debates(s)
            row = debate_repository.get_debate(s, "dup")
            assert len([r for r in rows if r.id == "dup"]) == 1
            assert row.topic == "Updated"


# ---------------------------------------------------------------------------
# Persist-on-completion (run_debate)
# ---------------------------------------------------------------------------

class TestServicePersistence:
    async def test_completed_debate_is_persisted(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("Persist me", "passionate", "academic")
            await _drain(svc, session)

        with db.SessionLocal() as s:
            row = debate_repository.get_debate(s, session.debate_id)
            assert row is not None
            assert row.topic == "Persist me"
            assert row.pro_style == "passionate"
            assert row.con_style == "academic"
            assert row.winner == "PRO"  # from the sample_scores mock
            assert row.argument_scores["winner"] == "PRO"
            # The audience vote is part of the saved transcript.
            assert any(e["speaker"] == "AUDIENCE" for e in row.transcript)

    async def test_failed_debate_is_not_persisted(self, make_mock_agent):
        def factory(pro_style, con_style):
            return make_mock_agent("PRO", fail=True), make_mock_agent("CON"), make_mock_agent("JUDGE")

        with patch("api.services.debate_service.build_agents", side_effect=factory):
            svc = DebateService()
            session = svc.create_debate("T", "passionate", "passionate")
            [e async for e in svc.run_debate(session)]

        with db.SessionLocal() as s:
            assert debate_repository.get_debate(s, session.debate_id) is None


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

class TestHistoryRoutes:
    def test_list_is_empty_with_no_debates(self, client):
        resp = client.get("/api/debates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_summary_without_transcript(self, client):
        debate_repository.save_completed_debate(**_save_kwargs("r1", topic="Saved one"))
        resp = client.get("/api/debates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["id"] == "r1"
        assert item["topic"] == "Saved one"
        assert item["winner"] == "PRO"
        assert item["message_count"] == 2
        # The list payload stays lightweight — no transcript/scores blob.
        assert "transcript" not in item
        assert "argument_scores" not in item

    def test_detail_returns_full_debate(self, client):
        debate_repository.save_completed_debate(**_save_kwargs("r2", topic="Detailed"))
        resp = client.get("/api/debates/r2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "r2"
        assert data["topic"] == "Detailed"
        assert isinstance(data["transcript"], list) and len(data["transcript"]) == 2
        assert data["argument_scores"]["winner"] == "PRO"

    def test_detail_unknown_id_returns_404(self, client):
        resp = client.get("/api/debates/does-not-exist")
        assert resp.status_code == 404

    def test_timestamps_are_serialized_with_utc_designator(self, client):
        # created_at/completed_at are stored tz-naive (SQLite has no timezone
        # column type); the serialized wire value must still carry a UTC
        # designator or the frontend's `new Date(iso)` parses it as local time.
        debate_repository.save_completed_debate(**_save_kwargs("r3", topic="TZ check"))
        item = client.get("/api/debates").json()[0]
        assert item["created_at"].endswith("Z")
        assert item["completed_at"].endswith("Z")

        detail = client.get("/api/debates/r3").json()
        assert detail["created_at"].endswith("Z")
        assert detail["completed_at"].endswith("Z")

    def test_completed_debate_appears_in_history_endpoint(self, client, mock_build_agents):
        # End-to-end: run a debate over the WebSocket, then read it back via REST.
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            debate_id = client.post("/api/debates", json={
                "topic": "End to end", "pro_style": "passionate", "con_style": "passionate",
            }).json()["debate_id"]

            with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
                while True:
                    msg = ws.receive_json()
                    if msg["type"] == "vote_required":
                        ws.send_json({"type": "vote", "vote": "PRO"})
                    if msg["type"] in ("debate_complete", "error"):
                        break

        listing = client.get("/api/debates").json()
        assert any(d["id"] == debate_id and d["topic"] == "End to end" for d in listing)

        detail = client.get(f"/api/debates/{debate_id}")
        assert detail.status_code == 200
        assert detail.json()["argument_scores"]["winner"] in ("PRO", "CON", "TIE")
