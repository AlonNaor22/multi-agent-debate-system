import logging

import anthropic
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import config
from src.agents.base_agent import AgentError, _cache_stats
from conftest import sample_scores


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


def _real_prompt_agent(name="Pro", role="arguing FOR the topic", system_prompt="You are the PRO debater."):
    """Build a DebateAgent with a REAL prompt template (only the LLM mocked).

    The fully-mocked ``_make_agent`` stubs out ``ChatPromptTemplate``, so it
    can't see the actual prompt structure. This leaves the template real so the
    ``cache_control`` breakpoints can be asserted on.
    """
    with patch("src.agents.base_agent.ChatAnthropic"):
        from src.agents.base_agent import DebateAgent
        return DebateAgent(name=name, role=role, system_prompt=system_prompt)


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
    async def test_yields_non_empty_chunks(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter(
            [MagicMock(content="Hello "), MagicMock(content="world"), MagicMock(content="")]
        )

        result = [chunk async for chunk in agent.astream_respond("ctx", "instr")]

        assert result == ["Hello ", "world"]  # empty chunk filtered

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
    async def test_anthropic_error_becomes_agent_error(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.astream.side_effect = lambda payload: _aiter_then_raise(
            [], anthropic.AnthropicError("api down")
        )

        with pytest.raises(AgentError):
            [chunk async for chunk in agent.astream_respond("ctx", "instr")]

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


# ---------------------------------------------------------------------------
# Structured scoring (with_structured_output)
# ---------------------------------------------------------------------------

def _judge_with_scoring_chain(chain):
    """Build a mocked judge whose `prompt | structured_llm` yields `chain`."""
    agent = _make_agent(name="Judge", role="judge")
    agent.prompt.__or__.return_value = chain  # prompt | llm.with_structured_output(...)
    return agent


class TestScoreArguments:
    def test_returns_structured_scores(self):
        sample = sample_scores()
        chain = MagicMock()
        chain.invoke.return_value = sample
        agent = _judge_with_scoring_chain(chain)

        assert agent.score_arguments("ctx", "instr") is sample

    def test_anthropic_error_becomes_agent_error(self):
        chain = MagicMock()
        chain.invoke.side_effect = anthropic.AnthropicError("scoring down")
        agent = _judge_with_scoring_chain(chain)

        with pytest.raises(AgentError):
            agent.score_arguments("ctx", "instr")


class TestAscoreArguments:
    async def test_returns_structured_scores(self):
        sample = sample_scores()
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=sample)
        agent = _judge_with_scoring_chain(chain)

        result = await agent.ascore_arguments("ctx", "instr")
        assert result is sample

    async def test_anthropic_error_becomes_agent_error(self):
        chain = MagicMock()
        chain.ainvoke = AsyncMock(side_effect=anthropic.AnthropicError("scoring down"))
        agent = _judge_with_scoring_chain(chain)

        with pytest.raises(AgentError):
            await agent.ascore_arguments("ctx", "instr")


# ---------------------------------------------------------------------------
# Prompt caching — cache_control breakpoints on the stable prefix
# ---------------------------------------------------------------------------

class TestPromptCaching:
    """The persona and the transcript prefix carry Anthropic cache breakpoints;
    the volatile per-turn instruction (deliberately) does not."""

    def _formatted(self, system_prompt="You are the PRO debater."):
        """Render the real prompt to concrete messages for inspection."""
        agent = _real_prompt_agent(system_prompt=system_prompt)
        return agent.prompt.format_messages(
            debate_context="[Pro]: AI helps people.\n",
            instruction="Rebut the Con side.",
            name="Pro",
            role="arguing FOR the topic",
        )

    def test_system_persona_is_cached(self):
        system_msg, _ = self._formatted("PERSONA TEXT")
        block = system_msg.content[0]
        assert block["text"] == "PERSONA TEXT"
        assert block["cache_control"] == {"type": "ephemeral"}

    def test_transcript_prefix_is_cached(self):
        _, human_msg = self._formatted()
        transcript_block = human_msg.content[0]
        assert transcript_block["cache_control"] == {"type": "ephemeral"}
        # The growing transcript is templated into the cached block.
        assert "[Pro]: AI helps people." in transcript_block["text"]

    def test_instruction_is_after_the_breakpoint_and_uncached(self):
        _, human_msg = self._formatted()
        instruction_block = human_msg.content[1]
        assert "cache_control" not in instruction_block
        # The volatile parts land in the uncached trailing block.
        assert "Rebut the Con side." in instruction_block["text"]
        assert "Pro" in instruction_block["text"]
        assert "arguing FOR the topic" in instruction_block["text"]

    def test_at_most_four_breakpoints(self):
        # Anthropic allows at most 4 cache_control breakpoints per request; we
        # use exactly 2 (persona + transcript).
        messages = self._formatted()
        breakpoints = [
            block
            for msg in messages
            for block in msg.content
            if isinstance(block, dict) and "cache_control" in block
        ]
        assert len(breakpoints) == 2


# ---------------------------------------------------------------------------
# Cache accounting — reading the counters out of usage metadata
# ---------------------------------------------------------------------------

class TestCacheStats:
    def test_none_when_no_usage_metadata(self):
        assert _cache_stats(None) is None
        assert _cache_stats(MagicMock()) is None  # mocked LLM in other tests

    def test_extracts_counters_from_usage_metadata(self):
        usage = {
            "input_tokens": 40,
            "output_tokens": 120,
            "total_tokens": 2160,
            "input_token_details": {"cache_read": 2000, "cache_creation": 0},
        }
        assert _cache_stats(usage) == {
            "cache_read": 2000,
            "cache_creation": 0,
            "uncached_input": 40,
        }

    def test_missing_details_default_to_zero(self):
        assert _cache_stats({"input_tokens": 10}) == {
            "cache_read": 0,
            "cache_creation": 0,
            "uncached_input": 10,
        }


class TestCacheUsageLogging:
    """`respond`/`astream_respond` surface the cache counters so a real run can
    confirm the prefix is being served from cache."""

    def test_respond_logs_cache_reads(self, caplog):
        agent = _make_agent(name="Pro")
        response = MagicMock()
        response.content = "argued"
        response.usage_metadata = {
            "input_tokens": 30,
            "input_token_details": {"cache_read": 1500, "cache_creation": 0},
        }
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = response

        with caplog.at_level(logging.INFO, logger="src.agents.base_agent"):
            agent.respond("ctx", "instr")

        assert "Pro prompt cache" in caplog.text
        assert "read=1500" in caplog.text

    def test_respond_without_usage_metadata_is_silent(self, caplog):
        agent = _make_agent()
        response = MagicMock()
        response.content = "x"
        response.usage_metadata = None
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = response

        with caplog.at_level(logging.INFO, logger="src.agents.base_agent"):
            agent.respond("ctx", "instr")

        assert "prompt cache" not in caplog.text
