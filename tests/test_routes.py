"""Tests for the API routes via FastAPI's TestClient — the REST endpoints and
the WebSocket debate flow — with the LLM mocked (see conftest fixtures)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    # The app's lifespan refuses to start without a key; the real LLM is mocked,
    # so any non-empty value works.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def _drive_ws(ws, *, vote="PRO"):
    """Receive WebSocket messages until the debate completes or errors,
    auto-answering the vote prompt. Returns the list of messages."""
    messages = []
    while True:
        msg = ws.receive_json()
        messages.append(msg)
        if msg["type"] == "vote_required" and vote is not None:
            ws.send_json({"type": "vote", "vote": vote})
        if msg["type"] in ("debate_complete", "error"):
            break
    return messages


# ---------------------------------------------------------------------------
# Startup: AVAILABLE_STYLES / PRO_STYLES / CON_STYLES consistency
# ---------------------------------------------------------------------------

class TestLifespanStyleValidation:
    """A style config mismatch must fail fast at startup (SystemExit), not
    surface later as a raw KeyError / 500 mid-request — see the lifespan
    docstring in api/main.py.
    """

    async def test_lifespan_exits_when_a_style_has_no_matching_prompt(self, monkeypatch):
        import api.main as api_main

        monkeypatch.setattr(api_main, "AVAILABLE_STYLES", ["passionate", "sarcastic"])
        with pytest.raises(SystemExit):
            async with api_main.lifespan(api_main.app):
                pytest.fail("lifespan should not yield when style config is invalid")

    async def test_lifespan_starts_when_styles_are_valid(self, monkeypatch):
        import api.main as api_main

        monkeypatch.setattr(api_main, "AVAILABLE_STYLES", ["passionate", "academic"])
        async with api_main.lifespan(api_main.app):
            pass  # reaching here means startup succeeded


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

class TestStylesEndpoint:
    def test_lists_available_styles_with_descriptions(self, client):
        resp = client.get("/api/config/styles")
        assert resp.status_code == 200
        styles = resp.json()["styles"]
        names = [s["name"] for s in styles]
        assert {"passionate", "aggressive", "academic", "humorous"} <= set(names)
        assert all(s["description"] for s in styles)


class TestCreateDebate:
    def test_happy_path(self, client, mock_build_agents):
        resp = client.post("/api/debates", json={
            "topic": "Should AI be regulated?",
            "pro_style": "passionate",
            "con_style": "academic",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == "Should AI be regulated?"
        assert data["pro_style"] == "passionate"
        assert data["con_style"] == "academic"
        assert data["debate_id"]

    def test_invalid_pro_style_returns_400(self, client):
        resp = client.post("/api/debates", json={
            "topic": "T", "pro_style": "bogus", "con_style": "passionate",
        })
        assert resp.status_code == 400

    def test_invalid_con_style_returns_400(self, client):
        resp = client.post("/api/debates", json={
            "topic": "T", "pro_style": "passionate", "con_style": "bogus",
        })
        assert resp.status_code == 400

    def test_blank_topic_returns_422(self, client):
        resp = client.post("/api/debates", json={
            "topic": "   ", "pro_style": "passionate", "con_style": "passionate",
        })
        assert resp.status_code == 422

    def test_missing_topic_returns_422(self, client):
        resp = client.post("/api/debates", json={
            "pro_style": "passionate", "con_style": "passionate",
        })
        assert resp.status_code == 422

    def test_over_live_session_cap_returns_429(self, client, mock_build_agents):
        # With the cap set to 1, the first create succeeds and the second — still
        # live because no socket drove it — is rejected with 429.
        body = {"topic": "T", "pro_style": "passionate", "con_style": "passionate"}
        with patch("api.services.debate_service.MAX_LIVE_SESSIONS", 1):
            first = client.post("/api/debates", json=body)
            second = client.post("/api/debates", json=body)
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["detail"]


# ---------------------------------------------------------------------------
# WebSocket flow
# ---------------------------------------------------------------------------

class TestWebSocket:
    def test_unknown_debate_id_gets_error_and_closes(self, client):
        with client.websocket_connect("/ws/debates/does-not-exist") as ws:
            msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "not found" in msg["data"]["message"].lower()

    def test_happy_path_streams_full_debate(self, client, mock_build_agents):
        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            debate_id = client.post("/api/debates", json={
                "topic": "T", "pro_style": "passionate", "con_style": "passionate",
            }).json()["debate_id"]

            with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
                messages = _drive_ws(ws, vote="PRO")

        types = [m["type"] for m in messages]
        assert types[0] == "debate_started"
        assert types[-1] == "debate_complete"
        assert "vote_required" in types
        assert "vote_received" in types
        assert "argument_scores" in types
        assert "error" not in types
        # Token-by-token streaming reaches the client.
        assert "message_chunk" in types

        # The structured scoreboard reaches the client.
        scores = next(m for m in messages if m["type"] == "argument_scores")["data"]["scores"]
        assert scores["winner"] in ("PRO", "CON", "TIE")
        assert "pro_average" in scores and "con_average" in scores

    def test_silent_client_vote_times_out_to_tie_and_evicts_session(self, client, mock_build_agents):
        # A client that receives the vote prompt and never votes must not hang
        # the debate: the route's VOTE_TIMEOUT_SECONDS bound records a TIE, the
        # debate completes, and the session is fully evicted (no leak). A short
        # timeout keeps the test fast.
        from api.services.debate_service import debate_service

        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1), \
             patch("api.routes.websocket.VOTE_TIMEOUT_SECONDS", 0.1):
            debate_id = client.post("/api/debates", json={
                "topic": "T", "pro_style": "passionate", "con_style": "passionate",
            }).json()["debate_id"]

            with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
                # vote=None → connect, receive vote_required, never send a vote.
                messages = _drive_ws(ws, vote=None)

        types = [m["type"] for m in messages]
        assert "vote_required" in types
        assert types[-1] == "debate_complete"

        received = next(m for m in messages if m["type"] == "vote_received")
        assert received["data"]["vote"] == "TIE"

        # The session was reclaimed by run_debate's cleanup — nothing leaks.
        assert debate_service.get_session(debate_id) is None

    def test_second_connect_to_live_debate_is_rejected(self, client, mock_build_agents):
        # A second WebSocket for an in-flight debate must be refused (error event
        # + closed socket) and must never run a second run_debate over the shared
        # session — the live transcript stays untouched.
        from api.services.debate_service import debate_service

        with patch("api.services.debate_service.NUM_REBUTTAL_ROUNDS", 1):
            debate_id = client.post("/api/debates", json={
                "topic": "T", "pro_style": "passionate", "con_style": "passionate",
            }).json()["debate_id"]

            with client.websocket_connect(f"/ws/debates/{debate_id}") as ws1:
                # Drive the first connection until it parks at the audience vote —
                # the debate is now live (started=True, still in the registry).
                msg = ws1.receive_json()
                while msg["type"] != "vote_required":
                    msg = ws1.receive_json()

                live = debate_service.get_session(debate_id)
                assert live is not None and live.started is True
                transcript_before = list(live.transcript)

                # A second connect for the same live debate is rejected outright.
                with client.websocket_connect(f"/ws/debates/{debate_id}") as ws2:
                    rejected = ws2.receive_json()
                assert rejected["type"] == "error"
                assert "already running" in rejected["data"]["message"].lower()

                # The rejected connection never ran run_debate, so the live
                # transcript is untouched (no interleaved/duplicated appends).
                assert live.transcript == transcript_before

                # The first debate still finishes cleanly over its own socket.
                ws1.send_json({"type": "vote", "vote": "PRO"})
                types = [msg["type"]]
                while types[-1] not in ("debate_complete", "error"):
                    types.append(ws1.receive_json()["type"])

        assert types[-1] == "debate_complete"
        # The single (first) runner evicted the session on completion — no leak,
        # and no double-eviction from a second runner.
        assert debate_service.get_session(debate_id) is None

    def test_error_path_emits_clean_error_event(self, client, make_mock_agent):
        def factory(pro_style, con_style):
            return make_mock_agent("PRO", fail=True), make_mock_agent("CON"), make_mock_agent("JUDGE")

        with patch("api.services.debate_service.build_agents", side_effect=factory):
            debate_id = client.post("/api/debates", json={
                "topic": "T", "pro_style": "passionate", "con_style": "passionate",
            }).json()["debate_id"]

            with client.websocket_connect(f"/ws/debates/{debate_id}") as ws:
                messages = _drive_ws(ws)

        assert messages[-1]["type"] == "error"
        assert "temporarily unavailable" in messages[-1]["data"]["message"].lower()
        assert all(m["type"] != "debate_complete" for m in messages)
