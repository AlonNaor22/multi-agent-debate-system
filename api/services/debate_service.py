import asyncio
import uuid
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

from src.agents.base_agent import DebateAgent
from src.prompts import PRO_STYLES, CON_STYLES, JUDGE_AGENT_PROMPT
from config import TEMPERATURE_DEBATERS, TEMPERATURE_JUDGE, NUM_REBUTTAL_ROUNDS
from api.schemas.debate import DebatePhase, Speaker, WSMessageType

# Load environment variables
load_dotenv()

# Word limits for different response types
WORD_LIMIT_INTRO = 150
WORD_LIMIT_OPENING = 250
WORD_LIMIT_REBUTTAL = 200
WORD_LIMIT_CLOSING = 200
WORD_LIMIT_VERDICT = 300
WORD_LIMIT_SCORING = 400


class DebateSession:
    """Represents an active debate session."""

    def __init__(self, debate_id: str, topic: str, pro_style: str, con_style: str):
        self.debate_id = debate_id
        self.topic = topic
        self.pro_style = pro_style
        self.con_style = con_style
        self.transcript: list[dict] = []
        self.phase = DebatePhase.INTRODUCTION
        self.vote: Optional[str] = None
        self.vote_event = asyncio.Event()
        self.argument_scores: Optional[str] = None

        # Create agents
        self.pro_agent = DebateAgent(
            name="Pro",
            role="arguing FOR the topic",
            system_prompt=PRO_STYLES[pro_style],
            temperature=TEMPERATURE_DEBATERS
        )

        self.con_agent = DebateAgent(
            name="Con",
            role="arguing AGAINST the topic",
            system_prompt=CON_STYLES[con_style],
            temperature=TEMPERATURE_DEBATERS
        )

        self.judge_agent = DebateAgent(
            name="Judge",
            role="moderator and judge",
            system_prompt=JUDGE_AGENT_PROMPT,
            temperature=TEMPERATURE_JUDGE
        )

    def add_to_transcript(self, speaker: str, content: str):
        """Record what was said and by whom."""
        self.transcript.append({
            "speaker": speaker,
            "content": content,
            "phase": self.phase.value
        })

    def get_transcript_text(self) -> str:
        """Build the full debate transcript as a string."""
        text = f"DEBATE TOPIC: {self.topic}\n\n"
        for entry in self.transcript:
            text += f"[{entry['speaker']}]: {entry['content']}\n\n"
        return text


class DebateService:
    """Service for managing debate sessions."""

    def __init__(self):
        self.sessions: dict[str, DebateSession] = {}

    def create_debate(self, topic: str, pro_style: str, con_style: str) -> DebateSession:
        """Create a new debate session."""
        debate_id = str(uuid.uuid4())
        session = DebateSession(debate_id, topic, pro_style, con_style)
        self.sessions[debate_id] = session
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

        # Run the streaming in a thread and yield chunks
        import queue
        import threading

        chunk_queue: queue.Queue = queue.Queue()
        done_event = threading.Event()

        def stream_worker():
            try:
                for chunk in stream_generator():
                    chunk_queue.put(chunk)
            finally:
                done_event.set()

        thread = threading.Thread(target=stream_worker)
        thread.start()

        while not done_event.is_set() or not chunk_queue.empty():
            try:
                chunk = chunk_queue.get(timeout=0.1)
                full_content += chunk
                yield {
                    "type": WSMessageType.MESSAGE_CHUNK,
                    "debate_id": session.debate_id,
                    "data": {"speaker": speaker.value, "chunk": chunk}
                }
            except queue.Empty:
                await asyncio.sleep(0.05)

        thread.join()

        session.add_to_transcript(speaker.value, full_content)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": speaker.value, "content": full_content, "label": label}
        }

    async def run_debate(self, session: DebateSession) -> AsyncGenerator[dict, None]:
        """Run a debate and yield events for WebSocket streaming."""

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

        # --- PHASE 1: Introduction ---
        session.phase = DebatePhase.INTRODUCTION
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        intro_instruction = (
            f"Introduce the debate topic: '{session.topic}'. "
            f"Welcome the debaters and explain the format briefly. "
            f"Keep your introduction concise (under {WORD_LIMIT_INTRO} words)."
        )
        async for event in self._stream_agent_response(
            session, session.judge_agent, intro_instruction, Speaker.MODERATOR
        ):
            yield event

        # --- PHASE 2: Opening Statements ---
        session.phase = DebatePhase.OPENING_PRO
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        pro_opening_instruction = (
            f"Deliver your opening statement. Present your 3 strongest arguments FOR the topic. "
            f"Be persuasive but concise (under {WORD_LIMIT_OPENING} words)."
        )
        async for event in self._stream_agent_response(
            session, session.pro_agent, pro_opening_instruction, Speaker.PRO, "Opening Statement"
        ):
            yield event

        session.phase = DebatePhase.OPENING_CON
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        con_opening_instruction = (
            f"Deliver your opening statement. Present your 3 strongest arguments AGAINST the topic. "
            f"Be persuasive but concise (under {WORD_LIMIT_OPENING} words)."
        )
        async for event in self._stream_agent_response(
            session, session.con_agent, con_opening_instruction, Speaker.CON, "Opening Statement"
        ):
            yield event

        # --- PHASE 3: Rebuttal Rounds ---
        session.phase = DebatePhase.REBUTTAL
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        for round_num in range(1, NUM_REBUTTAL_ROUNDS + 1):
            pro_rebuttal_instruction = (
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. "
                f"Counter their points and strengthen your position. "
                f"Be focused and concise (under {WORD_LIMIT_REBUTTAL} words)."
            )
            async for event in self._stream_agent_response(
                session, session.pro_agent, pro_rebuttal_instruction, Speaker.PRO, f"Rebuttal {round_num}"
            ):
                yield event

            con_rebuttal_instruction = (
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. "
                f"Counter their points and strengthen your position. "
                f"Be focused and concise (under {WORD_LIMIT_REBUTTAL} words)."
            )
            async for event in self._stream_agent_response(
                session, session.con_agent, con_rebuttal_instruction, Speaker.CON, f"Rebuttal {round_num}"
            ):
                yield event

        # --- Audience Vote ---
        yield {
            "type": WSMessageType.VOTE_REQUIRED,
            "debate_id": session.debate_id,
            "data": {"message": "Who is winning so far?"}
        }

        # Wait for vote with timeout
        try:
            await asyncio.wait_for(session.vote_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            session.vote = "TIE"

        vote_text = f"Audience vote: {session.vote} is winning."
        session.add_to_transcript("AUDIENCE", vote_text)

        yield {
            "type": WSMessageType.VOTE_RECEIVED,
            "debate_id": session.debate_id,
            "data": {"vote": session.vote, "message": vote_text}
        }

        # --- PHASE 4: Closing Statements ---
        session.phase = DebatePhase.CLOSING_PRO
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        pro_closing_instruction = (
            f"Deliver your closing statement. Summarize your strongest points and make a final appeal. "
            f"Be impactful but concise (under {WORD_LIMIT_CLOSING} words)."
        )
        async for event in self._stream_agent_response(
            session, session.pro_agent, pro_closing_instruction, Speaker.PRO, "Closing Statement"
        ):
            yield event

        session.phase = DebatePhase.CLOSING_CON
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        con_closing_instruction = (
            f"Deliver your closing statement. Summarize your strongest points and make a final appeal. "
            f"Be impactful but concise (under {WORD_LIMIT_CLOSING} words)."
        )
        async for event in self._stream_agent_response(
            session, session.con_agent, con_closing_instruction, Speaker.CON, "Closing Statement"
        ):
            yield event

        # --- PHASE 5: Judge's Verdict ---
        session.phase = DebatePhase.VERDICT
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        verdict_instruction = (
            f"Deliver your final verdict. Include:\n"
            f"1. Summary of strongest arguments from each side\n"
            f"2. Weaknesses or missed opportunities from each side\n"
            f"3. Your reasoning for the decision\n"
            f"4. Scores for each debater (1-10)\n"
            f"5. Declaration of winner (or tie)\n"
            f"Keep it thorough but concise (under {WORD_LIMIT_VERDICT} words)."
        )
        async for event in self._stream_agent_response(
            session, session.judge_agent, verdict_instruction, Speaker.JUDGE, "Final Verdict"
        ):
            yield event

        # --- PHASE 6: Scoring ---
        session.phase = DebatePhase.SCORING
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        scoring_instruction = (
            f"Analyze the debate transcript and score EACH distinct argument made by both sides.\n"
            f"Format your response as:\n\n"
            f"PRO ARGUMENTS:\n"
            f"1. [Argument summary] — Score: X/10 — Reason: [brief reason]\n"
            f"2. ...\n\n"
            f"CON ARGUMENTS:\n"
            f"1. [Argument summary] — Score: X/10 — Reason: [brief reason]\n"
            f"2. ...\n\n"
            f"OVERALL:\n"
            f"- Pro total average: X/10\n"
            f"- Con total average: X/10\n"
            f"- Strongest single argument: [which one]\n"
            f"- Weakest single argument: [which one]\n"
            f"Keep it concise (under {WORD_LIMIT_SCORING} words)."
        )
        async for event in self._stream_agent_response(
            session, session.judge_agent, scoring_instruction, Speaker.SCORING, "Argument Scores"
        ):
            yield event
        session.argument_scores = session.transcript[-1]["content"]

        # --- Finished ---
        session.phase = DebatePhase.FINISHED
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.DEBATE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {
                "transcript": session.transcript,
                "argument_scores": session.argument_scores
            }
        }


# Global instance
debate_service = DebateService()
