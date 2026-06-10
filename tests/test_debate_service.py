"""Tests for the DebateService — session management and the streaming
run_debate event generator, with the LLM mocked (see conftest fixtures).

These are async tests; pytest-asyncio runs them on an event loop (asyncio_mode
is set to ``auto`` in pytest.ini).
"""
from unittest.mock import patch

import pytest

from api.services.debate_service import DebateService
from api.schemas.debate import WSMessageType, DebatePhase


# ---------------------------------------------------------------------------
# Session management (synchronous)
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def test_create_debate_returns_populated_session(self, mock_build_agents):
        svc = DebateService()
        session = svc.create_debate("Should AI be regulated?", "passionate", "academic")
        assert session.topic == "Should AI be regulated?"
        assert session.pro_style == "passionate"
        assert session.con_style == "academic"
        assert session.debate_id
        assert session.phase == DebatePhase.INTRODUCTION
        assert session.transcript == []

    def test_create_debate_stores_session(self, mock_build_agents):
        svc = DebateService()
        session = svc.create_debate("T", "passionate", "passionate")
        assert svc.get_session(session.debate_id) is session

    def test_create_debate_ids_are_unique(self, mock_build_agents):
        svc = DebateService()
        a = svc.create_debate("T", "passionate", "passionate")
        b = svc.create_debate("T", "passionate", "passionate")
        assert a.debate_id != b.debate_id

    def test_get_session_unknown_id_returns_none(self):
        assert DebateService().get_session("does-not-exist") is None

    def test_submit_vote_sets_vote_and_event(self, mock_build_agents):
        svc = DebateService()
        session = svc.create_debate("T", "passionate", "passionate")
        assert not session.vote_event.is_set()
        svc.submit_vote(session.debate_id, "PRO")
        assert session.vote == "PRO"
        assert session.vote_event.is_set()

    def test_submit_vote_unknown_id_is_noop(self):
        # Should not raise even when the session doesn't exist.
        DebateService().submit_vote("nope", "PRO")


# ---------------------------------------------------------------------------
# run_debate — the streaming event sequence
# ---------------------------------------------------------------------------

async def _drain(svc, session, *, vote="PRO"):
    """Run a debate to completion, auto-submitting a vote when asked."""
    events = []
    async for event in svc.run_debate(session):
        events.append(event)
        if event["type"] == WSMessageType.VOTE_REQUIRED and vote is not None:
            svc.submit_vote(session.debate_id, vote)
    return events


class TestRunDebateHappyPath:
    async def test_full_event_sequence(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 2):
            session = svc.create_debate("T", "passionate", "passionate")
            events = await _drain(svc, session)

        types = [e["type"] for e in events]
        assert types[0] == WSMessageType.DEBATE_STARTED
        assert types[-1] == WSMessageType.DEBATE_COMPLETE

        # Phase changes, in order (the frontend progress bar depends on these).
        phases = [e["data"]["phase"] for e in events if e["type"] == WSMessageType.PHASE_CHANGE]
        assert phases == [
            "introduction", "opening_pro", "opening_con", "rebuttal",
            "closing_pro", "closing_con", "verdict", "scoring", "finished",
        ]

        # 1 intro + 2 openings + 2*2 rebuttals + 2 closings + verdict + scoring = 11 turns
        assert types.count(WSMessageType.MESSAGE_COMPLETE) == 11
        assert types.count(WSMessageType.VOTE_REQUIRED) == 1
        assert types.count(WSMessageType.VOTE_RECEIVED) == 1

    async def test_chunks_reassemble_into_message_content(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            events = await _drain(svc, session)

        # First completed message is the moderator intro, streamed from the
        # JUDGE mock agent's two chunks ("JUDGE-a " + "JUDGE-b").
        first = next(e for e in events if e["type"] == WSMessageType.MESSAGE_COMPLETE)
        assert first["data"]["speaker"] == "MODERATOR"
        assert first["data"]["content"] == "JUDGE-a JUDGE-b"

    async def test_vote_recorded_in_transcript_and_scores_set(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            events = await _drain(svc, session, vote="CON")

        complete = next(e for e in events if e["type"] == WSMessageType.DEBATE_COMPLETE)
        transcript = complete["data"]["transcript"]
        audience = [e for e in transcript if e["speaker"] == "AUDIENCE"]
        assert audience and "CON" in audience[0]["content"]
        assert complete["data"]["argument_scores"] == "JUDGE-a JUDGE-b"

    async def test_session_evicted_after_completion(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            await _drain(svc, session)
        assert svc.get_session(session.debate_id) is None

    async def test_vote_timeout_defaults_to_tie(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1), \
             patch("api.services.debate_service.VOTE_TIMEOUT_SECONDS", 0.05):
            session = svc.create_debate("T", "passionate", "passionate")
            # vote=None → never submit a vote, so the wait times out.
            events = await _drain(svc, session, vote=None)

        received = next(e for e in events if e["type"] == WSMessageType.VOTE_RECEIVED)
        assert received["data"]["vote"] == "TIE"


class TestRunDebateErrorPath:
    async def test_agent_failure_yields_clean_error_event(self, make_mock_agent):
        # PRO fails on its opening statement (after the intro streams fine).
        def factory(pro_style, con_style):
            return make_mock_agent("PRO", fail=True), make_mock_agent("CON"), make_mock_agent("JUDGE")

        with patch("api.services.debate_service.build_agents", side_effect=factory):
            svc = DebateService()
            session = svc.create_debate("T", "passionate", "passionate")
            events = [e async for e in svc.run_debate(session)]

        types = [e["type"] for e in events]
        assert WSMessageType.ERROR in types
        assert WSMessageType.DEBATE_COMPLETE not in types

        error = next(e for e in events if e["type"] == WSMessageType.ERROR)
        msg = error["data"]["message"]
        assert "temporarily unavailable" in msg.lower()
        # No raw exception text / internal detail leaks to the client.
        assert "AgentError" not in msg and "unavailable while" not in msg

    async def test_session_evicted_even_on_error(self, make_mock_agent):
        def factory(pro_style, con_style):
            return make_mock_agent("PRO", fail=True), make_mock_agent("CON"), make_mock_agent("JUDGE")

        with patch("api.services.debate_service.build_agents", side_effect=factory):
            svc = DebateService()
            session = svc.create_debate("T", "passionate", "passionate")
            [e async for e in svc.run_debate(session)]
        assert svc.get_session(session.debate_id) is None
