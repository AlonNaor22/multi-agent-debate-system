# Root conftest.py — lets pytest find src/, api/, config.py from the project root,
# and provides shared fixtures for mocking the LLM in web-layer tests.
import pytest
from unittest.mock import MagicMock, patch

from src.scoring import ArgumentScore, DebateScores


@pytest.fixture(autouse=True)
def _test_db(monkeypatch, tmp_path):
    """Point the persistence layer at a throwaway SQLite file for every test.

    Each test gets its own fresh database (so persistence is exercised for real
    and stays isolated), and nothing ever touches the app's real ``debates.db``.
    The DB layer reads ``engine`` / ``SessionLocal`` as module globals, so
    repointing them here is enough for the app code and the read endpoints.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api import db

    db_path = tmp_path / "test_debates.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(
        db, "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )
    db.init_db()  # reads the patched engine; creates the debates table
    yield
    engine.dispose()


def sample_scores() -> DebateScores:
    """A fixed DebateScores for tests (PRO avg 8.0, CON avg 6.0, PRO wins)."""
    return DebateScores(
        pro_arguments=[ArgumentScore(summary="Pro point", score=8, reason="well argued")],
        con_arguments=[ArgumentScore(summary="Con point", score=6, reason="some merit")],
        winner="PRO",
        strongest_argument="Pro point",
        weakest_argument="Con point",
    )


@pytest.fixture
def make_mock_agent():
    """Factory for a DebateAgent stand-in — no real LLM, no API key.

    ``astream_respond`` is an async generator yielding canned chunks (or raising
    ``AgentError`` when ``fail=True``); ``ascore_arguments`` / ``score_arguments``
    return a fixed :class:`DebateScores`. ``respond`` is stubbed for completeness.
    """
    from src.agents.base_agent import AgentError

    def _make(tag="AGENT", fail=False):
        agent = MagicMock()

        async def astream_respond(debate_context, instruction):
            if fail:
                raise AgentError(f"{tag}: AI service unavailable")
                yield  # unreachable; keeps this an async generator
            yield f"{tag}-a "
            yield f"{tag}-b"

        async def ascore_arguments(debate_context, instruction):
            if fail:
                raise AgentError(f"{tag}: AI service unavailable")
            return sample_scores()

        agent.astream_respond = astream_respond
        agent.ascore_arguments = ascore_arguments
        agent.score_arguments.return_value = sample_scores()
        agent.respond.return_value = f"{tag}-a {tag}-b"
        return agent

    return _make


@pytest.fixture
def mock_build_agents(make_mock_agent):
    """Patch the web layer's ``build_agents`` so debates run on mock agents.

    Yields the patched mock so a test can assert on how it was called.
    """
    def factory(pro_style, con_style):
        return make_mock_agent("PRO"), make_mock_agent("CON"), make_mock_agent("JUDGE")

    with patch("api.services.debate_service.build_agents", side_effect=factory) as m:
        yield m
