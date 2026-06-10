from typing import Generator
import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from config import MODEL_NAME, MAX_TOKENS, REQUEST_TIMEOUT, MAX_RETRIES


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
        )

        # 2. THE PROMPT TEMPLATE - This defines HOW the agent thinks.
        #    The system message gives the agent its persona/personality.
        #    The human message provides context and instructions each turn.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", (
                "Current debate transcript:\n{debate_context}\n\n"
                "Your instruction for this turn:\n{instruction}\n\n"
                "Respond in character as {name}, the {role} in this debate."
            ))
        ])

        # 3. THE CHAIN - This connects the prompt template to the LLM.
        #    The "|" operator (pipe) is LangChain's way of saying:
        #    "Take the output of the left side and feed it to the right side"
        #    So: filled prompt template -> sent to Claude -> response
        self.chain = self.prompt | self.llm

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

        return response.content

    def stream_respond(self, debate_context: str, instruction: str) -> Generator[str, None, None]:
        """Stream a response chunk by chunk for real-time display.

        Raises :class:`AgentError` if the Anthropic API fails mid-stream, so the
        web layer can emit a clean error event instead of a raw traceback.
        """
        try:
            for chunk in self.chain.stream({
                "debate_context": debate_context,
                "instruction": instruction,
                "name": self.name,
                "role": self.role
            }):
                if chunk.content:
                    yield chunk.content
        except anthropic.AnthropicError as e:
            raise AgentError(
                f"The AI service was unavailable while {self.name} was responding."
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
