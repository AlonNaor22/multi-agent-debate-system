"""The shared debate engine — single source of truth for the debate flow.

Before this module existed, the entire phase sequence (intro → openings →
rebuttals → vote → closings → verdict → scoring) plus ``add_to_transcript`` and
``get_transcript_text`` were reimplemented in BOTH the synchronous CLI
(``src/debate_controller.py``) and the streaming web service
(``api/services/debate_service.py``). The two copies had already drifted — only
the web path enforced per-phase word limits.

The design here splits the problem into three small, reusable pieces:

* :class:`DebateState` — owns the transcript and current phase, and is the one
  place ``add_to_transcript`` / ``get_transcript_text`` live. Both the CLI
  controller and the web session subclass it.
* :class:`DebateEngine` — a generator that *yields* the debate as a stream of
  :class:`PhaseChange`, :class:`Turn` and :class:`Vote` events. It contains the
  phase ordering and the turn instructions but does NOT call the LLM or touch
  any state. This is the single source of truth for "what happens next".
* The consumers — they iterate the engine's events and decide *how* to execute
  each one: the CLI runs the agent synchronously and prints with Rich; the web
  service streams the agent token-by-token over a WebSocket. Only the execution
  and rendering differ; the flow is shared.

Keeping the engine free of I/O and state mutation is what lets the same sequence
drive a blocking CLI and an async streaming service without either path being
able to silently diverge from the other again.
"""
from dataclasses import dataclass
from typing import Optional, Union

from src.debate_enums import DebatePhase, Speaker
from src.agents.base_agent import DebateAgent
from src.prompts import (
    INSTRUCTION_INTRO,
    INSTRUCTION_PRO_OPENING,
    INSTRUCTION_CON_OPENING,
    INSTRUCTION_REBUTTAL,
    INSTRUCTION_CLOSING,
    INSTRUCTION_VERDICT,
    INSTRUCTION_SCORING,
)
from src.scoring import DebateScores


# ---------------------------------------------------------------------------
# Shared debate state
# ---------------------------------------------------------------------------

class DebateState:
    """Holds the running transcript and the current phase of a debate.

    Both ``DebateController`` (CLI) and ``DebateSession`` (web) subclass this so
    that the transcript format — what an agent sees as ``debate_context`` and
    what gets saved/streamed — is defined exactly once.
    """

    def __init__(self, topic: str):
        self.topic = topic
        self.transcript: list[dict] = []
        self.phase: DebatePhase = DebatePhase.INTRODUCTION
        self.argument_scores: Optional[DebateScores] = None

    def add_to_transcript(self, speaker: str, content: str) -> None:
        """Record what was said and by whom, tagged with the current phase."""
        self.transcript.append({
            "speaker": speaker,
            "content": content,
            "phase": self.phase.value,
        })

    def get_transcript_text(self) -> str:
        """Build the full debate transcript as a string.

        This is what gets passed to each agent as ``debate_context``. Every
        agent sees the FULL history — that is how they know what the other
        agents said and can respond to it.
        """
        text = f"DEBATE TOPIC: {self.topic}\n\n"
        for entry in self.transcript:
            text += f"[{entry['speaker']}]: {entry['content']}\n\n"
        return text


def format_audience_vote(side: str) -> str:
    """Render the audience-vote transcript line. Shared so the CLI and web
    service record the vote identically."""
    return f"Audience vote: {side} is winning."


# ---------------------------------------------------------------------------
# Per-phase word limits (used by the streaming web path)
# ---------------------------------------------------------------------------

# Each phase appends a short "keep it under N words" nudge to the instruction.
# The wording and separator differ per phase, so they are templated here once.
_LIMIT_TEMPLATES = {
    "intro":    " Keep your introduction concise (under {n} words).",
    "opening":  " Be persuasive but concise (under {n} words).",
    "rebuttal": " Be focused and concise (under {n} words).",
    "closing":  " Be impactful but concise (under {n} words).",
    "verdict":  "\nKeep it thorough but concise (under {n} words).",
}


@dataclass(frozen=True)
class WordLimits:
    """Per-phase response word limits appended to turn instructions.

    The streaming web path uses these to keep responses snappy on screen; the
    CLI passes ``word_limits=None`` to the engine and gets the bare
    instructions. Values are env-tunable defaults matching the original
    web-service constants.
    """
    intro: int = 150
    opening: int = 250
    rebuttal: int = 200
    closing: int = 200
    verdict: int = 300

    def suffix(self, kind: str) -> str:
        """Return the instruction suffix for a given phase ``kind``."""
        return _LIMIT_TEMPLATES[kind].format(n=getattr(self, kind))


# The defaults the web service has always used.
DEFAULT_WORD_LIMITS = WordLimits()


# ---------------------------------------------------------------------------
# Engine events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhaseChange:
    """The debate has advanced to a new phase. Consumers update their state and
    (on the web) emit a ``phase_change`` message."""
    phase: DebatePhase


@dataclass(frozen=True)
class Turn:
    """One agent needs to respond.

    The consumer runs ``agent`` against the current transcript with
    ``instruction``, records the reply under ``speaker``, and renders it
    (``label`` is the human-facing sub-title, e.g. "Rebuttal 1").
    """
    speaker: Speaker
    agent: DebateAgent
    instruction: str
    label: Optional[str] = None


@dataclass(frozen=True)
class Vote:
    """The audience must vote before the debate continues. The consumer collects
    the verdict (CLI ``input()`` / web WebSocket) and records it."""


@dataclass(frozen=True)
class Score:
    """The judge produces the structured scoreboard for the SCORING phase.

    Unlike a :class:`Turn`, this is not streamed as a chat message — the consumer
    calls the agent's structured-scoring method and renders/sends the typed
    :class:`~src.scoring.DebateScores` result.
    """
    agent: DebateAgent
    instruction: str


DebateEvent = Union[PhaseChange, Turn, Vote, Score]


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class DebateEngine:
    """Yields the debate as an ordered stream of events.

    The engine is intentionally pure: it never calls the LLM, prints, awaits, or
    mutates :class:`DebateState`. It just describes — in order — which phase we
    are in, who speaks next and with what instruction. Consumers execute the
    events however they like (synchronously, streamed, etc.) and own the state.
    """

    def __init__(
        self,
        topic: str,
        pro: DebateAgent,
        con: DebateAgent,
        judge: DebateAgent,
        *,
        num_rebuttal_rounds: int,
        word_limits: Optional[WordLimits] = None,
    ):
        self.topic = topic
        self.pro = pro
        self.con = con
        self.judge = judge
        self.num_rebuttal_rounds = num_rebuttal_rounds
        self.word_limits = word_limits

    def _instruction(self, base: str, kind: str) -> str:
        """Append the per-phase word-limit nudge when word limits are enabled."""
        if self.word_limits is None:
            return base
        return base + self.word_limits.suffix(kind)

    def events(self):
        """Generate the full debate as :class:`DebateEvent` objects, in order."""

        # --- PHASE 1: Introduction (judge acts as moderator) ---
        yield PhaseChange(DebatePhase.INTRODUCTION)
        yield Turn(
            Speaker.MODERATOR,
            self.judge,
            self._instruction(INSTRUCTION_INTRO.format(topic=self.topic), "intro"),
        )

        # --- PHASE 2: Opening statements ---
        yield PhaseChange(DebatePhase.OPENING_PRO)
        yield Turn(
            Speaker.PRO,
            self.pro,
            self._instruction(INSTRUCTION_PRO_OPENING, "opening"),
            "Opening Statement",
        )
        yield PhaseChange(DebatePhase.OPENING_CON)
        yield Turn(
            Speaker.CON,
            self.con,
            self._instruction(INSTRUCTION_CON_OPENING, "opening"),
            "Opening Statement",
        )

        # --- PHASE 3: Rebuttal rounds ---
        yield PhaseChange(DebatePhase.REBUTTAL)
        for round_num in range(1, self.num_rebuttal_rounds + 1):
            instruction = self._instruction(
                INSTRUCTION_REBUTTAL.format(round_num=round_num), "rebuttal"
            )
            label = f"Rebuttal {round_num}"
            # Pro and Con share the same rebuttal instruction this round.
            yield Turn(Speaker.PRO, self.pro, instruction, label)
            yield Turn(Speaker.CON, self.con, instruction, label)

        # --- Audience vote (recorded while still in the REBUTTAL phase) ---
        yield Vote()

        # --- PHASE 4: Closing statements ---
        yield PhaseChange(DebatePhase.CLOSING_PRO)
        yield Turn(
            Speaker.PRO,
            self.pro,
            self._instruction(INSTRUCTION_CLOSING, "closing"),
            "Closing Statement",
        )
        yield PhaseChange(DebatePhase.CLOSING_CON)
        yield Turn(
            Speaker.CON,
            self.con,
            self._instruction(INSTRUCTION_CLOSING, "closing"),
            "Closing Statement",
        )

        # --- PHASE 5: Judge's verdict ---
        yield PhaseChange(DebatePhase.VERDICT)
        yield Turn(
            Speaker.JUDGE,
            self.judge,
            self._instruction(INSTRUCTION_VERDICT, "verdict"),
            "Final Verdict",
        )

        # --- PHASE 6: Argument scoring — the judge returns a typed scoreboard ---
        yield PhaseChange(DebatePhase.SCORING)
        yield Score(self.judge, INSTRUCTION_SCORING)

        # --- Debate over ---
        yield PhaseChange(DebatePhase.FINISHED)
