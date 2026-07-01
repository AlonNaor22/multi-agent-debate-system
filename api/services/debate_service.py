import asyncio
import logging
import uuid
from datetime import timedelta
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv

from src.agents.base_agent import DebateAgent, AgentError, build_agents
from src.debate_engine import (
    DebateState,
    DebateEngine,
    PhaseChange,
    Turn,
    Vote,
    Score,
    DEFAULT_WORD_LIMITS,
    format_audience_vote,
)
from config import (
    NUM_REBUTTAL_ROUNDS,
    MAX_LIVE_SESSIONS,
    SESSION_TTL_SECONDS,
    SESSION_SWEEP_INTERVAL_SECONDS,
)
from api import db
from api.services.debate_repository import save_completed_debate
from api.schemas.debate import Speaker, WSMessageType
from messages import VOTE_PROMPT, AI_SERVICE_UNAVAILABLE

load_dotenv()

logger = logging.getLogger(__name__)

# How long to wait for the audience vote before defaulting to a tie.
VOTE_TIMEOUT_SECONDS = 300


class DebateSession(DebateState):
    """Represents an active debate session.

    Inherits the transcript and phase handling from :class:`DebateState`, and
    adds the web-specific bits: an id, the chosen styles, and the audience-vote
    synchronisation primitives. The debate flow itself comes from the shared
    :class:`DebateEngine` — see :meth:`DebateService.run_debate`.
    """

    def __init__(self, debate_id: str, topic: str, pro_style: str, con_style: str):
        super().__init__(topic)
        self.debate_id = debate_id
        self.pro_style = pro_style
        self.con_style = con_style
        self.created_at = db.utcnow()
        self.vote: Optional[str] = None
        self.vote_event = asyncio.Event()
        # ``started`` flips to True the moment a WebSocket drives this session via
        # ``run_debate`` (see below). A session that is created via POST but never
        # connected stays ``started=False`` and is reclaimed by the TTL sweeper.
        self.started = False
        # Agents are built lazily in ``run_debate`` (``ensure_agents``), not here:
        # constructing the three ``ChatAnthropic`` clients up-front for a session
        # that may never be driven by a socket is exactly what leaked memory.
        self.pro_agent: Optional[DebateAgent] = None
        self.con_agent: Optional[DebateAgent] = None
        self.judge_agent: Optional[DebateAgent] = None

    def ensure_agents(self) -> None:
        """Build the Pro/Con/Judge agents on first use (idempotent)."""
        if self.pro_agent is None:
            self.pro_agent, self.con_agent, self.judge_agent = build_agents(
                self.pro_style, self.con_style
            )


class SessionLimitExceeded(Exception):
    """Raised by :meth:`DebateService.create_debate` when the live-session cap
    (``MAX_LIVE_SESSIONS``) is reached. The REST route turns this into HTTP 429."""


class DebateService:
    """Service for managing debate sessions.

    The live-session registry, the ``MAX_LIVE_SESSIONS`` cap, and the TTL sweeper
    are all in-memory and **per-process** — they assume a single uvicorn worker.
    Under multiple workers each process keeps its own registry, so a debate
    created on one worker is invisible (and its cap uncounted) on another; run a
    single worker or move to a shared store.
    """

    def __init__(self):
        self.sessions: dict[str, DebateSession] = {}

    def create_debate(self, topic: str, pro_style: str, con_style: str) -> DebateSession:
        """Create a new debate session.

        Raises :class:`SessionLimitExceeded` if the number of live sessions has
        reached ``MAX_LIVE_SESSIONS``. Expired orphans are swept first so a
        backlog of abandoned sessions doesn't wrongly reject a fresh request.
        """
        self.sweep_expired_sessions()
        if len(self.sessions) >= MAX_LIVE_SESSIONS:
            logger.warning(
                "Debate rejected: live-session cap reached (%d/%d)",
                len(self.sessions), MAX_LIVE_SESSIONS,
            )
            raise SessionLimitExceeded(
                f"Live session cap of {MAX_LIVE_SESSIONS} reached"
            )

        debate_id = str(uuid.uuid4())
        session = DebateSession(debate_id, topic, pro_style, con_style)
        self.sessions[debate_id] = session
        logger.info("Debate created: id=%s topic=%r", debate_id, topic)
        return session

    def get_session(self, debate_id: str) -> Optional[DebateSession]:
        """Get an existing debate session."""
        return self.sessions.get(debate_id)

    def sweep_expired_sessions(self) -> int:
        """Evict orphan sessions and return how many were removed.

        An *orphan* is a session that was created (via ``POST /api/debates``) but
        never driven by a WebSocket (``started is False``) and whose age exceeds
        ``SESSION_TTL_SECONDS``. A live debate is never swept — once a socket
        starts it, ``started`` is True and its cleanup is ``run_debate``'s
        ``finally``. Runs synchronously with no ``await``, so it can't race a
        concurrent create/run on the single-threaded event loop.
        """
        cutoff = db.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS)
        expired = [
            debate_id
            for debate_id, session in self.sessions.items()
            if not session.started and session.created_at < cutoff
        ]
        for debate_id in expired:
            self.sessions.pop(debate_id, None)
        if expired:
            logger.info("Swept %d expired orphan session(s)", len(expired))
        return len(expired)

    async def run_session_sweeper(
        self, interval: float = SESSION_SWEEP_INTERVAL_SECONDS
    ) -> None:
        """Background loop that periodically sweeps expired orphan sessions.

        Started from the app lifespan and cancelled on shutdown. One failing
        iteration is logged and swallowed so the loop keeps running.
        """
        logger.info(
            "Session sweeper started: interval=%ss ttl=%ss",
            interval, SESSION_TTL_SECONDS,
        )
        while True:
            await asyncio.sleep(interval)
            try:
                self.sweep_expired_sessions()
            except Exception:
                logger.exception("Session sweeper iteration failed")

    def submit_vote(self, debate_id: str, vote: str):
        """Submit audience vote for a debate."""
        session = self.sessions.get(debate_id)
        if session:
            session.vote = vote
            session.vote_event.set()

    async def _stream_agent_response(
        self,
        session: DebateSession,
        agent: DebateAgent,
        instruction: str,
        speaker: Speaker,
        label: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """Stream an agent's response chunk by chunk over the WebSocket.

        Consumes the agent's native async stream directly — no background thread,
        no queue, no polling. If the stream raises :class:`AgentError`, it
        propagates to :meth:`run_debate` (which turns it into a clean error
        event); the partial turn is intentionally not recorded and no
        MESSAGE_COMPLETE is sent.
        """
        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": speaker.value}
        }

        full_content = ""
        async for chunk in agent.astream_respond(session.get_transcript_text(), instruction):
            full_content += chunk
            yield {
                "type": WSMessageType.MESSAGE_CHUNK,
                "debate_id": session.debate_id,
                "data": {"speaker": speaker.value, "chunk": chunk}
            }

        session.add_to_transcript(speaker.value, full_content)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": speaker.value, "content": full_content, "label": label}
        }

    async def run_debate(self, session: DebateSession) -> AsyncGenerator[dict, None]:
        """Run a debate and yield events for WebSocket streaming.

        The phase/turn ordering comes from the shared :class:`DebateEngine` (the
        same one the CLI uses); this method only decides *how* to execute each
        event — streaming agent turns token-by-token and waiting for the audience
        vote over the socket. ``DEFAULT_WORD_LIMITS`` keeps the per-phase word
        caps the web UI has always used.
        """
        # Mark the session as driven by a socket so the TTL sweeper leaves it
        # alone — from here on, cleanup is this method's ``finally`` block.
        session.started = True
        logger.info("Debate started: id=%s", session.debate_id)

        yield {
            "type": WSMessageType.DEBATE_STARTED,
            "debate_id": session.debate_id,
            "data": {
                "topic": session.topic,
                "pro_style": session.pro_style,
                "con_style": session.con_style
            }
        }

        try:
            # Build the agents now (deferred from __init__) — a session that never
            # reached this point never constructed any ChatAnthropic clients.
            session.ensure_agents()
            engine = DebateEngine(
                session.topic,
                session.pro_agent,
                session.con_agent,
                session.judge_agent,
                num_rebuttal_rounds=NUM_REBUTTAL_ROUNDS,
                word_limits=DEFAULT_WORD_LIMITS,
            )

            for event in engine.events():
                if isinstance(event, PhaseChange):
                    session.phase = event.phase
                    yield {
                        "type": WSMessageType.PHASE_CHANGE,
                        "debate_id": session.debate_id,
                        "data": {"phase": session.phase.value}
                    }

                elif isinstance(event, Turn):
                    async for ws_event in self._stream_agent_response(
                        session, event.agent, event.instruction, event.speaker, event.label
                    ):
                        yield ws_event

                elif isinstance(event, Score):
                    # The judge returns a typed scoreboard (not a streamed turn).
                    session.argument_scores = await event.agent.ascore_arguments(
                        session.get_transcript_text(), event.instruction
                    )
                    yield {
                        "type": WSMessageType.ARGUMENT_SCORES,
                        "debate_id": session.debate_id,
                        "data": {"scores": session.argument_scores.model_dump()}
                    }

                elif isinstance(event, Vote):
                    yield {
                        "type": WSMessageType.VOTE_REQUIRED,
                        "debate_id": session.debate_id,
                        "data": {"message": VOTE_PROMPT}
                    }

                    # Wait for vote with timeout
                    try:
                        await asyncio.wait_for(session.vote_event.wait(), timeout=VOTE_TIMEOUT_SECONDS)
                    except asyncio.TimeoutError:
                        session.vote = "TIE"

                    vote_text = format_audience_vote(session.vote)
                    session.add_to_transcript("AUDIENCE", vote_text)

                    yield {
                        "type": WSMessageType.VOTE_RECEIVED,
                        "debate_id": session.debate_id,
                        "data": {"vote": session.vote, "message": vote_text}
                    }

            # Debate finished successfully — persist it so it survives a restart
            # and shows up in the "past debates" view. The write runs off the
            # event loop (asyncio.to_thread), and a persistence failure must NOT
            # sink a debate the user already watched, so it's logged, not raised.
            try:
                await asyncio.to_thread(
                    save_completed_debate,
                    debate_id=session.debate_id,
                    topic=session.topic,
                    pro_style=session.pro_style,
                    con_style=session.con_style,
                    transcript=session.transcript,
                    argument_scores=(
                        session.argument_scores.model_dump()
                        if session.argument_scores else None
                    ),
                    winner=(session.argument_scores.winner if session.argument_scores else None),
                    created_at=session.created_at,
                )
                logger.info("Debate persisted: id=%s", session.debate_id)
            except Exception:
                logger.exception("Failed to persist debate id=%s", session.debate_id)

            # Debate finished — the engine's final PhaseChange already moved the
            # session to FINISHED (and emitted the phase_change above).
            yield {
                "type": WSMessageType.DEBATE_COMPLETE,
                "debate_id": session.debate_id,
                "data": {
                    "transcript": session.transcript,
                    "argument_scores": (
                        session.argument_scores.model_dump()
                        if session.argument_scores else None
                    )
                }
            }
            logger.info("Debate complete: id=%s", session.debate_id)

        except AgentError:
            # A transient LLM failure interrupted the debate. Log the detail
            # server-side and send the client a clean, generic error event —
            # never a raw exception string.
            logger.exception("Debate failed (AI service error): id=%s", session.debate_id)
            yield {
                "type": WSMessageType.ERROR,
                "debate_id": session.debate_id,
                "data": {"message": AI_SERVICE_UNAVAILABLE}
            }

        finally:
            # Evict the (started) session now that it's finished or errored. This
            # is the cleanup path for sessions a socket drove; orphans that never
            # started are reclaimed by the TTL sweeper instead. Both stores are
            # per-process (single-worker assumption — see the class docstring).
            self.sessions.pop(session.debate_id, None)
            logger.info("Session evicted: id=%s", session.debate_id)


# Module-level singleton: the one in-memory registry of live sessions, shared by
# the REST and WebSocket routes. Per-process only (single-worker assumption — see
# the DebateService docstring). The app lifespan starts run_session_sweeper on it.
debate_service = DebateService()
