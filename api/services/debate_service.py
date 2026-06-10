import asyncio
import logging
import queue
import threading
import uuid
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from src.agents.base_agent import DebateAgent, AgentError, build_agents
from src.debate_engine import (
    DebateState,
    DebateEngine,
    PhaseChange,
    Turn,
    Vote,
    DEFAULT_WORD_LIMITS,
    format_audience_vote,
)
from config import NUM_REBUTTAL_ROUNDS
from api.schemas.debate import Speaker, WSMessageType

# Load environment variables
load_dotenv()

# Streaming / timing constants
VOTE_TIMEOUT_SECONDS = 300
STREAM_QUEUE_TIMEOUT = 0.1
STREAM_POLL_INTERVAL = 0.05


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
        self.vote: Optional[str] = None
        self.vote_event = asyncio.Event()

        # Create agents
        self.pro_agent, self.con_agent, self.judge_agent = build_agents(pro_style, con_style)


class DebateService:
    """Service for managing debate sessions."""

    def __init__(self):
        self.sessions: dict[str, DebateSession] = {}

    def create_debate(self, topic: str, pro_style: str, con_style: str) -> DebateSession:
        """Create a new debate session."""
        debate_id = str(uuid.uuid4())
        session = DebateSession(debate_id, topic, pro_style, con_style)
        self.sessions[debate_id] = session
        logger.info("Debate created: id=%s topic=%r", debate_id, topic)
        return session

    def get_session(self, debate_id: str) -> Optional[DebateSession]:
        """Get an existing debate session."""
        return self.sessions.get(debate_id)

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
        """Stream an agent's response chunk by chunk."""
        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": speaker.value}
        }

        full_content = ""

        def stream_generator():
            return agent.stream_respond(session.get_transcript_text(), instruction)

        chunk_queue: queue.Queue = queue.Queue()
        done_event = threading.Event()
        worker_error: list[BaseException] = []

        def stream_worker():
            # Runs in a background thread. Capture any failure (e.g. AgentError
            # from a transient API error) so it can be re-raised on the async
            # side — an unhandled exception here would otherwise die silently in
            # the thread and leave the message looking like it ended normally.
            try:
                for chunk in stream_generator():
                    chunk_queue.put(chunk)
            except BaseException as e:  # noqa: BLE001 - re-raised below
                worker_error.append(e)
            finally:
                done_event.set()

        thread = threading.Thread(target=stream_worker)
        thread.start()

        while not done_event.is_set() or not chunk_queue.empty():
            try:
                chunk = chunk_queue.get(timeout=STREAM_QUEUE_TIMEOUT)
                full_content += chunk
                yield {
                    "type": WSMessageType.MESSAGE_CHUNK,
                    "debate_id": session.debate_id,
                    "data": {"speaker": speaker.value, "chunk": chunk}
                }
            except queue.Empty:
                await asyncio.sleep(STREAM_POLL_INTERVAL)

        thread.join()

        # Surface a streaming failure to run_debate, which turns it into a clean
        # error event. Don't record a partial turn or send MESSAGE_COMPLETE.
        if worker_error:
            raise worker_error[0]

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
        logger.info("Debate started: id=%s", session.debate_id)

        # Yield debate started
        yield {
            "type": WSMessageType.DEBATE_STARTED,
            "debate_id": session.debate_id,
            "data": {
                "topic": session.topic,
                "pro_style": session.pro_style,
                "con_style": session.con_style
            }
        }

        engine = DebateEngine(
            session.topic,
            session.pro_agent,
            session.con_agent,
            session.judge_agent,
            num_rebuttal_rounds=NUM_REBUTTAL_ROUNDS,
            word_limits=DEFAULT_WORD_LIMITS,
        )

        try:
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
                    if event.speaker == Speaker.SCORING:
                        session.argument_scores = session.transcript[-1]["content"]

                elif isinstance(event, Vote):
                    yield {
                        "type": WSMessageType.VOTE_REQUIRED,
                        "debate_id": session.debate_id,
                        "data": {"message": "Who is winning so far?"}
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

            # Debate finished — the engine's final PhaseChange already moved the
            # session to FINISHED (and emitted the phase_change above).
            yield {
                "type": WSMessageType.DEBATE_COMPLETE,
                "debate_id": session.debate_id,
                "data": {
                    "transcript": session.transcript,
                    "argument_scores": session.argument_scores
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
                "data": {"message": "The AI service is temporarily unavailable. Please try again."}
            }

        finally:
            # Clean up the session to prevent unbounded memory growth, whether
            # the debate completed or errored out. Note: this store is
            # per-process — it does not survive across multiple uvicorn workers;
            # run with a single worker or use a shared store.
            self.sessions.pop(session.debate_id, None)
            logger.info("Session evicted: id=%s", session.debate_id)


# Global instance
debate_service = DebateService()
