import anthropic
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

import config
from src.agents.base_agent import AgentError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(name="Pro", role="arguing FOR", system_prompt="Be persuasive."):
    """Build a DebateAgent with the LLM chain fully mocked."""
    with patch("src.agents.base_agent.ChatAnthropic"), \
         patch("src.agents.base_agent.ChatPromptTemplate"):
        from src.agents.base_agent import DebateAgent
        agent = DebateAgent(name=name, role=role, system_prompt=system_prompt)
    return agent


async def _aiter(items):
    """Yield items as an async iterator — stand-in for chain.astream(...)."""
    for item in items:
        yield item


async def _aiter_then_raise(items, exc):
    """Yield items, then raise — a stream that fails partway through."""
    for item in items:
        yield item
    raise exc


# ---------------------------------------------------------------------------
# DebateAgent construction
# ---------------------------------------------------------------------------

class TestDebateAgentConstruct:
    def test_name_and_role_stored(self):
        agent = _make_agent(name="Judge", role="moderator")
        assert agent.name == "Judge"
        assert agent.role == "moderator"

    def test_chain_is_built(self):
        agent = _make_agent()
        assert agent.chain is not None

    def test_default_temperature_accepted(self):
        with patch("src.agents.base_agent.ChatAnthropic") as mock_llm, \
             patch("src.agents.base_agent.ChatPromptTemplate"):
            from src.agents.base_agent import DebateAgent
            DebateAgent(name="X", role="Y", system_prompt="Z")
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["temperature"] == 0.7

    def test_custom_temperature_passed_to_llm(self):
        with patch("src.agents.base_agent.ChatAnthropic") as mock_llm, \
             patch("src.agents.base_agent.ChatPromptTemplate"):
            from src.agents.base_agent import DebateAgent
            DebateAgent(name="X", role="Y", system_prompt="Z", temperature=0.1)
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["temperature"] == 0.1

    def test_configures_timeout_and_retries(self):
        with patch("src.agents.base_agent.ChatAnthropic") as mock_llm, \
             patch("src.agents.base_agent.ChatPromptTemplate"):
            from src.agents.base_agent import DebateAgent
            DebateAgent(name="X", role="Y", system_prompt="Z")
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["timeout"] == config.REQUEST_TIMEOUT
            assert call_kwargs["max_retries"] == config.MAX_RETRIES


# ---------------------------------------------------------------------------
# DebateAgent.respond
# ---------------------------------------------------------------------------

class TestDebateAgentRespond:
    def test_returns_content_string(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = "My argument."
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = mock_response

        result = agent.respond("some context", "some instruction")

        assert result == "My argument."

    def test_passes_correct_keys_to_chain(self):
        agent = _make_agent(name="Pro", role="FOR")
        mock_response = MagicMock()
        mock_response.content = "response"
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = mock_response

        agent.respond("ctx", "instr")

        call_kwargs = agent.chain.invoke.call_args[0][0]
        assert call_kwargs["debate_context"] == "ctx"
        assert call_kwargs["instruction"] == "instr"
        assert call_kwargs["name"] == "Pro"
        assert call_kwargs["role"] == "FOR"


# ---------------------------------------------------------------------------
# DebateAgent.astream_respond (native async streaming)
# ---------------------------------------------------------------------------

class TestDebateAgentAstreamRespond:
    @pytest.mark.asyncio
    async def test_yields_non_empty_chunks(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter(
            [MagicMock(content="Hello "), MagicMock(content="world"), MagicMock(content="")]
        )

        result = [chunk async for chunk in agent.astream_respond("ctx", "instr")]

        assert result == ["Hello ", "world"]  # empty chunk filtered

    @pytest.mark.asyncio
    async def test_empty_chunks_skipped(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter([MagicMock(content="")])

        result = [chunk async for chunk in agent.astream_respond("ctx", "instr")]

        assert result == []


# ---------------------------------------------------------------------------
# build_agents factory
# ---------------------------------------------------------------------------

class TestBuildAgents:
    def test_returns_three_agents(self):
        with patch("src.agents.base_agent.ChatAnthropic"), \
             patch("src.agents.base_agent.ChatPromptTemplate"):
            from src.agents.base_agent import build_agents
            pro, con, judge = build_agents("passionate", "passionate")
        assert pro.name == "Pro"
        assert con.name == "Con"
        assert judge.name == "Judge"

    def test_different_styles_accepted(self):
        with patch("src.agents.base_agent.ChatAnthropic"), \
             patch("src.agents.base_agent.ChatPromptTemplate"):
            from src.agents.base_agent import build_agents
            pro, con, judge = build_agents("aggressive", "academic")
        assert pro.name == "Pro"
        assert con.name == "Con"


# ---------------------------------------------------------------------------
# Failure paths — transient API errors become AgentError
# ---------------------------------------------------------------------------

class TestRespondFailure:
    def test_anthropic_error_becomes_agent_error(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.invoke.side_effect = anthropic.AnthropicError("api down")

        with pytest.raises(AgentError):
            agent.respond("ctx", "instr")

    def test_original_exception_is_chained(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        original = anthropic.AnthropicError("api down")
        agent.chain.invoke.side_effect = original

        with pytest.raises(AgentError) as exc_info:
            agent.respond("ctx", "instr")

        # `raise ... from e` preserves the cause for server-side logging.
        assert exc_info.value.__cause__ is original

    def test_non_anthropic_errors_propagate_unwrapped(self):
        """A genuine bug (not an API failure) is not masked as an AgentError."""
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.invoke.side_effect = ValueError("programming error")

        with pytest.raises(ValueError):
            agent.respond("ctx", "instr")


class TestAstreamRespondFailure:
    @pytest.mark.asyncio
    async def test_anthropic_error_becomes_agent_error(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter_then_raise(
            [], anthropic.AnthropicError("api down")
        )

        with pytest.raises(AgentError):
            [chunk async for chunk in agent.astream_respond("ctx", "instr")]

    @pytest.mark.asyncio
    async def test_failure_after_partial_stream(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter_then_raise(
            [MagicMock(content="partial ")], anthropic.AnthropicError("dropped mid-stream")
        )

        collected = []
        with pytest.raises(AgentError):
            async for chunk in agent.astream_respond("ctx", "instr"):
                collected.append(chunk)

        # The chunk yielded before the failure was delivered; then AgentError.
        assert collected == ["partial "]
