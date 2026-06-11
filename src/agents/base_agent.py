import logging
from typing import AsyncGenerator, Optional
import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from config import MODEL_NAME, MAX_TOKENS, REQUEST_TIMEOUT, MAX_RETRIES
from src.scoring import DebateScores

logger = logging.getLogger(__name__)


def _cache_stats(usage_metadata) -> Optional[dict[str, int]]:
    """Pull the prompt-cache counters out of a response's usage metadata.

    LangChain normalises Anthropic's ``cache_read_input_tokens`` /
    ``cache_creation_input_tokens`` into ``usage_metadata['input_token_details']``
    under the keys ``cache_read`` / ``cache_creation``. This returns just those
    two counters plus the uncached ``input_tokens`` (the prefix paid for at full
    price), or ``None`` when no usage metadata is present — e.g. the mocked LLM
    in the tests. Kept pure and side-effect free so the cache accounting can be
    asserted on directly.
    """
    if not isinstance(usage_metadata, dict):
        return None
    details = usage_metadata.get("input_token_details") or {}
    return {
        "cache_read": details.get("cache_read") or 0,
        "cache_creation": details.get("cache_creation") or 0,
        "uncached_input": usage_metadata.get("input_tokens") or 0,
    }


class AgentError(RuntimeError):
    """A debate agent failed to get a response from the LLM.

    Wraps Anthropic API failures (rate limits, overload, timeouts, connection
    errors) in one clear, domain-specific error so callers don't have to know
    about the underlying SDK. The CLI turns this into a friendly message instead
    of crashing mid-debate; the web layer turns it into a clean error event
    rather than leaking a raw traceback to the browser.
    """


class DebateAgent:
    """A single LLM-backed participant in the debate (Pro, Con, or Judge).

    Each agent owns its own ChatAnthropic instance and prompt chain so it
    maintains an independent temperature and system persona throughout the
    debate. Agents do not hold conversation history — the controller passes
    the full shared transcript on every turn.
    """

    def __init__(self, name: str, role: str, system_prompt: str, temperature: float = 0.7):
        self.name = name
        self.role = role

        # 1. THE LLM - This is the "brain" of the agent.
        #    ChatAnthropic is a LangChain wrapper around the Anthropic API.
        #    Each agent gets its OWN LLM instance with its own settings.
        self.llm = ChatAnthropic(
            model=MODEL_NAME,
            temperature=temperature,
            max_tokens=MAX_TOKENS,
            # Resilience: bound each request and let the SDK retry transient
            # failures (429 / 5xx / connection errors) with exponential backoff
            # before surfacing an error. Tunable via config / env.
            timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
            # Emit token usage (incl. prompt-cache read/write counts) on the
            # streamed response too, not just the non-streaming one — that's how
            # we confirm caching is actually serving the prefix (see README).
            stream_usage=True,
        )

        # 2. THE PROMPT TEMPLATE - This defines HOW the agent thinks.
        #    The system message gives the agent its persona/personality.
        #    The human message provides context and instructions each turn.
        #
        #    Prompt caching: the persona never changes, and the transcript only
        #    ever grows by appending — so every turn re-sends a large,
        #    byte-identical prefix (persona + the debate so far) followed by a
        #    short, volatile instruction. We drop an Anthropic `cache_control`
        #    breakpoint after the persona and another after the transcript, and
        #    keep the per-turn instruction AFTER both. Each later turn then
        #    re-reads that cached prefix at ~10% of the input price instead of
        #    paying full freight to resend the whole history. `cache_control`
        #    rides on the content block; langchain-anthropic forwards it to the
        #    API. See README -> "Prompt caching".
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", [{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }]),
            ("human", [
                {
                    # Stable, append-only prefix — cached up to this breakpoint.
                    "type": "text",
                    "text": "Current debate transcript:\n{debate_context}",
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    # Volatile per-turn instruction, deliberately placed AFTER the
                    # breakpoint so it never invalidates the cached prefix above.
                    "type": "text",
                    "text": (
                        "Your instruction for this turn:\n{instruction}\n\n"
                        "Respond in character as {name}, the {role} in this debate."
                    ),
                },
            ]),
        ])

        # 3. THE CHAIN - This connects the prompt template to the LLM.
        #    The "|" operator (pipe) is LangChain's way of saying:
        #    "Take the output of the left side and feed it to the right side"
        #    So: filled prompt template -> sent to Claude -> response
        self.chain = self.prompt | self.llm

    def _log_cache_usage(self, usage_metadata) -> None:
        """Log the prompt-cache read/write counts from a response's usage.

        This is the verification hook for the caching above: from the second
        turn on, ``read`` should be non-zero (the persona + prior transcript
        served from cache) while ``uncached_input`` stays small (only the new
        turn is paid for in full). A no-op when usage metadata is absent, so a
        mocked LLM never trips it.
        """
        stats = _cache_stats(usage_metadata)
        if stats is None:
            return
        logger.info(
            "%s prompt cache: read=%d created=%d uncached_input=%d tokens",
            self.name,
            stats["cache_read"],
            stats["cache_creation"],
            stats["uncached_input"],
        )

    def respond(self, debate_context: str, instruction: str) -> str:
        """Generate a response given the current debate state.

        Raises :class:`AgentError` if the Anthropic API fails (after the SDK's
        own retries are exhausted), so callers never see a raw SDK exception.
        """

        # 4. INVOKE - This runs the chain.
        #    We pass in the variables that fill the prompt template.
        #    The chain fills the template, sends it to Claude, returns the response.
        try:
            response = self.chain.invoke({
                "debate_context": debate_context,
                "instruction": instruction,
                "name": self.name,
                "role": self.role
            })
        except anthropic.AnthropicError as e:
            raise AgentError(
                f"The AI service was unavailable while {self.name} was responding."
            ) from e

        self._log_cache_usage(getattr(response, "usage_metadata", None))
        return response.content

    async def astream_respond(self, debate_context: str, instruction: str) -> AsyncGenerator[str, None]:
        """Stream a response chunk by chunk using LangChain's native async streaming.

        This is what the streaming web service consumes. Using ``chain.astream``
        keeps the whole path on the event loop — no background thread bridging a
        blocking iterator, no busy-poll. Raises :class:`AgentError` if the
        Anthropic API fails mid-stream, so the web layer can emit a clean error
        event instead of a raw traceback.
        """
        aggregate = None
        try:
            async for chunk in self.chain.astream({
                "debate_context": debate_context,
                "instruction": instruction,
                "name": self.name,
                "role": self.role
            }):
                # Accumulate the chunks so the usage metadata — which Anthropic
                # sends incrementally across the stream — can be read out as a
                # whole once the stream finishes.
                aggregate = chunk if aggregate is None else aggregate + chunk
                if chunk.content:
                    yield chunk.content
        except anthropic.AnthropicError as e:
            raise AgentError(
                f"The AI service was unavailable while {self.name} was responding."
            ) from e

        self._log_cache_usage(getattr(aggregate, "usage_metadata", None))

    def score_arguments(self, debate_context: str, instruction: str) -> DebateScores:
        """Score the debate's arguments as structured data (synchronous; CLI).

        Uses Anthropic structured outputs (LangChain's ``with_structured_output``)
        so the judge returns a typed :class:`DebateScores` instead of free text.
        Raises :class:`AgentError` if the API fails.
        """
        chain = self.prompt | self.llm.with_structured_output(DebateScores)
        try:
            return chain.invoke({
                "debate_context": debate_context,
                "instruction": instruction,
                "name": self.name,
                "role": self.role,
            })
        except anthropic.AnthropicError as e:
            raise AgentError(
                f"The AI service was unavailable while {self.name} was scoring."
            ) from e

    async def ascore_arguments(self, debate_context: str, instruction: str) -> DebateScores:
        """Async counterpart of :meth:`score_arguments` (used by the web service)."""
        chain = self.prompt | self.llm.with_structured_output(DebateScores)
        try:
            return await chain.ainvoke({
                "debate_context": debate_context,
                "instruction": instruction,
                "name": self.name,
                "role": self.role,
            })
        except anthropic.AnthropicError as e:
            raise AgentError(
                f"The AI service was unavailable while {self.name} was scoring."
            ) from e


def build_agents(pro_style: str, con_style: str) -> tuple["DebateAgent", "DebateAgent", "DebateAgent"]:
    """Return (pro_agent, con_agent, judge_agent) configured for a debate."""
    from src.prompts import PRO_STYLES, CON_STYLES, JUDGE_AGENT_PROMPT
    from config import TEMPERATURE_DEBATERS, TEMPERATURE_JUDGE

    pro = DebateAgent(
        name="Pro",
        role="arguing FOR the topic",
        system_prompt=PRO_STYLES[pro_style],
        temperature=TEMPERATURE_DEBATERS,
    )
    con = DebateAgent(
        name="Con",
        role="arguing AGAINST the topic",
        system_prompt=CON_STYLES[con_style],
        temperature=TEMPERATURE_DEBATERS,
    )
    judge = DebateAgent(
        name="Judge",
        role="moderator and judge",
        system_prompt=JUDGE_AGENT_PROMPT,
        temperature=TEMPERATURE_JUDGE,
    )
    return pro, con, judge
