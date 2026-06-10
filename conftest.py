# Root conftest.py — lets pytest find src/, api/, config.py from the project root,
# and provides shared fixtures for mocking the LLM in web-layer tests.
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def make_mock_agent():
    """Factory for a DebateAgent stand-in — no real LLM, no API key.

    The returned agent's ``astream_respond`` is an async generator that yields a
    couple of canned chunks, or raises ``AgentError`` when ``fail=True`` (to
    exercise the error path). ``respond`` is also stubbed for completeness.
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

        agent.astream_respond = astream_respond
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
