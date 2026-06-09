import pytest
from unittest.mock import MagicMock, patch, PropertyMock


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
# DebateAgent.stream_respond
# ---------------------------------------------------------------------------

class TestDebateAgentStreamRespond:
    def test_yields_non_empty_chunks(self):
        agent = _make_agent()
        chunks = [MagicMock(content="Hello "), MagicMock(content="world"), MagicMock(content="")]
        agent.chain = MagicMock()
        agent.chain.stream.return_value = iter(chunks)

        result = list(agent.stream_respond("ctx", "instr"))

        assert result == ["Hello ", "world"]  # empty chunk filtered

    def test_empty_chunks_skipped(self):
        agent = _make_agent()
        agent.chain = MagicMock()
        agent.chain.stream.return_value = iter([MagicMock(content="")])

        result = list(agent.stream_respond("ctx", "instr"))

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
