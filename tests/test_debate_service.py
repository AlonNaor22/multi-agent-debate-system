"""Tests for the DebateService — session management and the streaming
run_debate event generator, with the LLM mocked (see conftest fixtures).

These are async tests; pytest-asyncio runs them on an event loop (asyncio_mode
is set to ``auto`` in pytest.ini).
"""
import asyncio
from contextlib import suppress
from datetime import timedelta
from unittest.mock import patch

import pytest

from api import db
from api.services.debate_service import DebateService, SessionLimitExceeded
from api.schemas.debate import WSMessageType, DebatePhase
from config import SESSION_TTL_SECONDS


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

    def test_create_debate_defers_agent_construction(self, mock_build_agents):
        # Deferring build_agents out of __init__ is what stops orphan POSTs from
        # holding open ChatAnthropic clients: no agents until run_debate runs.
        svc = DebateService()
        session = svc.create_debate("T", "passionate", "passionate")
        assert mock_build_agents.call_count == 0
        assert session.pro_agent is None
        assert session.con_agent is None
        assert session.judge_agent is None
        assert session.started is False


# ---------------------------------------------------------------------------
# Deferred agent construction + started flag (memory-leak fix)
# ---------------------------------------------------------------------------

class TestDeferredAgents:
    async def test_run_debate_builds_agents_and_marks_started(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            await _drain(svc, session)
        # Agents were constructed lazily, exactly once, when the debate ran.
        assert mock_build_agents.call_count == 1
        assert session.started is True


# ---------------------------------------------------------------------------
# MAX_LIVE_SESSIONS cap
# ---------------------------------------------------------------------------

class TestSessionCap:
    def test_create_beyond_cap_raises(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.MAX_LIVE_SESSIONS", 2):
            svc.create_debate("T", "passionate", "passionate")
            svc.create_debate("T", "passionate", "passionate")
            with pytest.raises(SessionLimitExceeded):
                svc.create_debate("T", "passionate", "passionate")
        # The rejected session was not stored.
        assert len(svc.sessions) == 2

    def test_cap_sweeps_expired_orphans_before_rejecting(self, mock_build_agents):
        # A backlog of expired orphans must not wrongly reject a fresh request:
        # create_debate sweeps first, freeing room under the cap.
        svc = DebateService()
        with patch("api.services.debate_service.MAX_LIVE_SESSIONS", 2):
            a = svc.create_debate("T", "passionate", "passionate")
            b = svc.create_debate("T", "passionate", "passionate")
            # Age both existing sessions past the TTL.
            old = db.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS + 1)
            a.created_at = b.created_at = old
            # At the cap, but the two are reclaimable — this should succeed.
            fresh = svc.create_debate("T", "passionate", "passionate")
        assert fresh.debate_id in svc.sessions
        assert a.debate_id not in svc.sessions
        assert b.debate_id not in svc.sessions
        assert len(svc.sessions) == 1


# ---------------------------------------------------------------------------
# TTL sweeper
# ---------------------------------------------------------------------------

class TestSessionSweeper:
    def test_orphans_swept_past_ttl(self, mock_build_agents):
        # Creating N debates without a socket must not retain them past the TTL.
        svc = DebateService()
        sessions = [
            svc.create_debate("T", "passionate", "passionate") for _ in range(5)
        ]
        old = db.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS + 1)
        for s in sessions:
            s.created_at = old

        evicted = svc.sweep_expired_sessions()
        assert evicted == 5
        assert svc.sessions == {}

    def test_fresh_orphans_not_swept(self, mock_build_agents):
        svc = DebateService()
        for _ in range(3):
            svc.create_debate("T", "passionate", "passionate")
        assert svc.sweep_expired_sessions() == 0
        assert len(svc.sessions) == 3

    def test_started_session_never_swept_even_when_old(self, mock_build_agents):
        # A live debate (started by a socket) outlives the TTL — it must NOT be
        # reclaimed out from under run_debate; its cleanup is run_debate's finally.
        svc = DebateService()
        session = svc.create_debate("T", "passionate", "passionate")
        session.started = True
        session.created_at = db.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS + 1)

        assert svc.sweep_expired_sessions() == 0
        assert session.debate_id in svc.sessions

    async def test_sweeper_loop_reclaims_orphans_over_time(self, mock_build_agents):
        svc = DebateService()
        session = svc.create_debate("T", "passionate", "passionate")
        session.created_at = db.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS + 1)

        task = asyncio.create_task(svc.run_session_sweeper(interval=0.01))
        try:
            # Give the loop a few ticks to run at least one sweep.
            for _ in range(50):
                await asyncio.sleep(0.01)
                if not svc.sessions:
                    break
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        assert svc.sessions == {}


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

        # 1 intro + 2 openings + 2*2 rebuttals + 2 closings + verdict = 10 streamed turns
        # (scoring is a structured ARGUMENT_SCORES event, not a streamed turn).
        assert types.count(WSMessageType.MESSAGE_COMPLETE) == 10
        assert types.count(WSMessageType.ARGUMENT_SCORES) == 1
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

    async def test_vote_recorded_in_transcript_and_structured_scores_set(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            events = await _drain(svc, session, vote="CON")

        complete = next(e for e in events if e["type"] == WSMessageType.DEBATE_COMPLETE)
        transcript = complete["data"]["transcript"]
        audience = [e for e in transcript if e["speaker"] == "AUDIENCE"]
        assert audience and "CON" in audience[0]["content"]

        # argument_scores is now a serialized DebateScores (dict), with computed averages.
        scores = complete["data"]["argument_scores"]
        assert scores["winner"] == "PRO"
        assert scores["pro_average"] == 8.0
        assert scores["con_average"] == 6.0
        assert [a["score"] for a in scores["pro_arguments"]] == [8]

    async def test_argument_scores_event_emitted_during_scoring(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            events = await _drain(svc, session)

        scores_event = next(e for e in events if e["type"] == WSMessageType.ARGUMENT_SCORES)
        assert scores_event["data"]["scores"]["winner"] == "PRO"

    async def test_session_evicted_after_completion(self, mock_build_agents):
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            await _drain(svc, session)
        assert svc.get_session(session.debate_id) is None

    async def test_run_debate_blocks_for_vote_then_records_it(self, mock_build_agents):
        # run_debate no longer self-times-out at the audience vote: it blocks
        # until a vote is submitted, then records it. The single authoritative
        # timeout now lives in the WebSocket route (which submits TIE on a silent
        # client — see tests/test_routes.py). Here we prove the block-until-submit
        # contract directly: without a vote the generator parks and does not
        # advance; submitting one (TIE, as the route does on timeout) unblocks it.
        svc = DebateService()
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            session = svc.create_debate("T", "passionate", "passionate")
            gen = svc.run_debate(session)

            # Drive the generator up to the vote prompt.
            async for event in gen:
                if event["type"] == WSMessageType.VOTE_REQUIRED:
                    break

            # With no vote submitted, the generator parks on vote_event and does
            # not advance to VOTE_RECEIVED.
            advance = asyncio.ensure_future(gen.__anext__())
            await asyncio.sleep(0.05)
            assert not advance.done()

            # Submitting the vote unblocks it and the value is recorded verbatim.
            svc.submit_vote(session.debate_id, "TIE")
            received = await advance
            assert received["type"] == WSMessageType.VOTE_RECEIVED
            assert received["data"]["vote"] == "TIE"

            # Drain the remainder so the session is cleaned up.
            async for _ in gen:
                pass

        assert svc.get_session(session.debate_id) is None


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
