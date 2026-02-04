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

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.MODERATOR.value}
        }

        intro = await asyncio.to_thread(
            session.judge_agent.respond,
            "",
            f"Introduce the debate topic: '{session.topic}'. Welcome the debaters and explain the format briefly."
        )
        session.add_to_transcript("MODERATOR", intro)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.MODERATOR.value, "content": intro}
        }

        # --- PHASE 2: Opening Statements ---
        session.phase = DebatePhase.OPENING_PRO
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.PRO.value}
        }

        pro_opening = await asyncio.to_thread(
            session.pro_agent.respond,
            session.get_transcript_text(),
            "Deliver your opening statement. Present your 3 strongest arguments FOR the topic."
        )
        session.add_to_transcript("PRO", pro_opening)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.PRO.value, "content": pro_opening, "label": "Opening Statement"}
        }

        session.phase = DebatePhase.OPENING_CON
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.CON.value}
        }

        con_opening = await asyncio.to_thread(
            session.con_agent.respond,
            session.get_transcript_text(),
            "Deliver your opening statement. Present your 3 strongest arguments AGAINST the topic."
        )
        session.add_to_transcript("CON", con_opening)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.CON.value, "content": con_opening, "label": "Opening Statement"}
        }

        # --- PHASE 3: Rebuttal Rounds ---
        session.phase = DebatePhase.REBUTTAL
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        for round_num in range(1, NUM_REBUTTAL_ROUNDS + 1):
            yield {
                "type": WSMessageType.MESSAGE_START,
                "debate_id": session.debate_id,
                "data": {"speaker": Speaker.PRO.value}
            }

            pro_rebuttal = await asyncio.to_thread(
                session.pro_agent.respond,
                session.get_transcript_text(),
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. Counter their points and strengthen your position."
            )
            session.add_to_transcript("PRO", pro_rebuttal)

            yield {
                "type": WSMessageType.MESSAGE_COMPLETE,
                "debate_id": session.debate_id,
                "data": {"speaker": Speaker.PRO.value, "content": pro_rebuttal, "label": f"Rebuttal {round_num}"}
            }

            yield {
                "type": WSMessageType.MESSAGE_START,
                "debate_id": session.debate_id,
                "data": {"speaker": Speaker.CON.value}
            }

            con_rebuttal = await asyncio.to_thread(
                session.con_agent.respond,
                session.get_transcript_text(),
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. Counter their points and strengthen your position."
            )
            session.add_to_transcript("CON", con_rebuttal)

            yield {
                "type": WSMessageType.MESSAGE_COMPLETE,
                "debate_id": session.debate_id,
                "data": {"speaker": Speaker.CON.value, "content": con_rebuttal, "label": f"Rebuttal {round_num}"}
            }

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

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.PRO.value}
        }

        pro_closing = await asyncio.to_thread(
            session.pro_agent.respond,
            session.get_transcript_text(),
            "Deliver your closing statement. Summarize your strongest points and make a final appeal."
        )
        session.add_to_transcript("PRO", pro_closing)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.PRO.value, "content": pro_closing, "label": "Closing Statement"}
        }

        session.phase = DebatePhase.CLOSING_CON
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.CON.value}
        }

        con_closing = await asyncio.to_thread(
            session.con_agent.respond,
            session.get_transcript_text(),
            "Deliver your closing statement. Summarize your strongest points and make a final appeal."
        )
        session.add_to_transcript("CON", con_closing)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.CON.value, "content": con_closing, "label": "Closing Statement"}
        }

        # --- PHASE 5: Judge's Verdict ---
        session.phase = DebatePhase.VERDICT
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.JUDGE.value}
        }

        verdict = await asyncio.to_thread(
            session.judge_agent.respond,
            session.get_transcript_text(),
            "Deliver your final verdict. Include:\n"
            "1. Summary of strongest arguments from each side\n"
            "2. Weaknesses or missed opportunities from each side\n"
            "3. Your reasoning for the decision\n"
            "4. Scores for each debater (1-10)\n"
            "5. Declaration of winner (or tie)"
        )
        session.add_to_transcript("JUDGE", verdict)

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.JUDGE.value, "content": verdict, "label": "Final Verdict"}
        }

        # --- PHASE 6: Scoring ---
        session.phase = DebatePhase.SCORING
        yield {
            "type": WSMessageType.PHASE_CHANGE,
            "debate_id": session.debate_id,
            "data": {"phase": session.phase.value}
        }

        yield {
            "type": WSMessageType.MESSAGE_START,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.SCORING.value}
        }

        scoring_instruction = (
            "Analyze the debate transcript and score EACH distinct argument made by both sides.\n"
            "Format your response as:\n\n"
            "PRO ARGUMENTS:\n"
            "1. [Argument summary] — Score: X/10 — Reason: [why this score]\n"
            "2. ...\n\n"
            "CON ARGUMENTS:\n"
            "1. [Argument summary] — Score: X/10 — Reason: [why this score]\n"
            "2. ...\n\n"
            "OVERALL:\n"
            "- Pro total average: X/10\n"
            "- Con total average: X/10\n"
            "- Strongest single argument: [which one and why]\n"
            "- Weakest single argument: [which one and why]"
        )

        scores = await asyncio.to_thread(
            session.judge_agent.respond,
            session.get_transcript_text(),
            scoring_instruction
        )
        session.add_to_transcript("SCORING", scores)
        session.argument_scores = scores

        yield {
            "type": WSMessageType.MESSAGE_COMPLETE,
            "debate_id": session.debate_id,
            "data": {"speaker": Speaker.SCORING.value, "content": scores, "label": "Argument Scores"}
        }

        # --- Finished ---
        session.phase = DebatePhase.FINISHED
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
