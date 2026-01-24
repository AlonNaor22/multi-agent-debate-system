import time
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from config import NUM_REBUTTAL_ROUNDS


class DebatePhase(Enum):
    """The debate moves through these phases in order."""
    INTRODUCTION = "introduction"
    OPENING_PRO = "opening_pro"
    OPENING_CON = "opening_con"
    REBUTTAL = "rebuttal"
    CLOSING_PRO = "closing_pro"
    CLOSING_CON = "closing_con"
    VERDICT = "verdict"
    FINISHED = "finished"


class DebateController:
    """
    The orchestrator of the multi-agent system.

    This is NOT an agent itself — it's the "director" that decides:
    - WHICH agent speaks next (turn-taking)
    - WHAT instruction each agent receives
    - WHAT context each agent can see (the transcript so far)

    This is what makes it a MULTI-agent system vs. just 3 separate chatbots.
    The agents don't talk to each other directly — the controller passes
    the shared transcript to each one so they can respond to each other.
    """

    def __init__(self, topic, pro_agent, con_agent, judge_agent):
        self.topic = topic
        self.pro = pro_agent
        self.con = con_agent
        self.judge = judge_agent
        self.transcript = []
        self.phase = DebatePhase.INTRODUCTION
        self.console = Console()

    def add_to_transcript(self, speaker: str, content: str):
        """Record what was said and by whom."""
        self.transcript.append({
            "speaker": speaker,
            "content": content,
            "phase": self.phase.value
        })

    def get_transcript_text(self) -> str:
        """Build the full debate transcript as a string.

        This is what gets passed to each agent as 'debate_context'.
        Every agent sees the FULL history — that's how they know
        what the other agents said and can respond to it.
        """
        text = f"DEBATE TOPIC: {self.topic}\n\n"
        for entry in self.transcript:
            text += f"[{entry['speaker']}]: {entry['content']}\n\n"
        return text

    def timed_respond(self, agent, context: str, instruction: str) -> tuple:
        """Call agent.respond() and measure how long it takes.

        Returns (response_text, seconds_elapsed).
        This is just a timing wrapper — the chain call is identical.
        """
        start = time.time()
        response = agent.respond(context, instruction)
        elapsed = time.time() - start
        return response, elapsed

    def display_message(self, speaker: str, content: str, style: str, elapsed: float = None):
        """Display a message with Rich formatting."""
        subtitle = f"[{elapsed:.1f}s]" if elapsed else None
        self.console.print()
        self.console.print(Panel(
            content,
            title=speaker,
            subtitle=subtitle,
            style=style
        ))

    def run_debate(self):
        """Execute the full debate — this is the main loop."""

        # --- PHASE 1: Introduction ---
        self.phase = DebatePhase.INTRODUCTION
        intro, t = self.timed_respond(
            self.judge, "",
            f"Introduce the debate topic: '{self.topic}'. Welcome the debaters and explain the format briefly."
        )
        self.add_to_transcript("MODERATOR", intro)
        self.display_message("MODERATOR", intro, "blue", t)

        # --- PHASE 2: Opening Statements ---
        self.phase = DebatePhase.OPENING_PRO
        pro_opening, t = self.timed_respond(
            self.pro, self.get_transcript_text(),
            "Deliver your opening statement. Present your 3 strongest arguments FOR the topic."
        )
        self.add_to_transcript("PRO", pro_opening)
        self.display_message("PRO - Opening Statement", pro_opening, "green", t)

        self.phase = DebatePhase.OPENING_CON
        con_opening, t = self.timed_respond(
            self.con, self.get_transcript_text(),
            "Deliver your opening statement. Present your 3 strongest arguments AGAINST the topic."
        )
        self.add_to_transcript("CON", con_opening)
        self.display_message("CON - Opening Statement", con_opening, "red", t)

        # --- PHASE 3: Rebuttal Rounds ---
        self.phase = DebatePhase.REBUTTAL
        for round_num in range(1, NUM_REBUTTAL_ROUNDS + 1):

            pro_rebuttal, t = self.timed_respond(
                self.pro, self.get_transcript_text(),
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. Counter their points and strengthen your position."
            )
            self.add_to_transcript("PRO", pro_rebuttal)
            self.display_message(f"PRO - Rebuttal {round_num}", pro_rebuttal, "green", t)

            con_rebuttal, t = self.timed_respond(
                self.con, self.get_transcript_text(),
                f"Rebuttal round {round_num}: Respond to your opponent's arguments. Counter their points and strengthen your position."
            )
            self.add_to_transcript("CON", con_rebuttal)
            self.display_message(f"CON - Rebuttal {round_num}", con_rebuttal, "red", t)

        # --- Audience Vote (between rebuttals and closing) ---
        self.console.print()
        self.console.print(Panel(
            "Who is winning so far?\n\n"
            "  1 = PRO is winning\n"
            "  2 = CON is winning\n"
            "  3 = It's a tie",
            title="AUDIENCE VOTE",
            style="cyan"
        ))
        vote = input("Your vote (1/2/3): ").strip()
        vote_map = {"1": "PRO", "2": "CON", "3": "TIE"}
        vote_text = f"Audience vote: {vote_map.get(vote, 'TIE')} is winning."
        self.add_to_transcript("AUDIENCE", vote_text)
        self.console.print(f"  Recorded: {vote_text}\n")

        # --- PHASE 4: Closing Statements ---
        self.phase = DebatePhase.CLOSING_PRO
        pro_closing, t = self.timed_respond(
            self.pro, self.get_transcript_text(),
            "Deliver your closing statement. Summarize your strongest points and make a final appeal."
        )
        self.add_to_transcript("PRO", pro_closing)
        self.display_message("PRO - Closing Statement", pro_closing, "green", t)

        self.phase = DebatePhase.CLOSING_CON
        con_closing, t = self.timed_respond(
            self.con, self.get_transcript_text(),
            "Deliver your closing statement. Summarize your strongest points and make a final appeal."
        )
        self.add_to_transcript("CON", con_closing)
        self.display_message("CON - Closing Statement", con_closing, "red", t)

        # --- PHASE 5: Judge's Verdict ---
        self.phase = DebatePhase.VERDICT
        verdict, t = self.timed_respond(
            self.judge, self.get_transcript_text(),
            "Deliver your final verdict. Include:\n"
            "1. Summary of strongest arguments from each side\n"
            "2. Weaknesses or missed opportunities from each side\n"
            "3. Your reasoning for the decision\n"
            "4. Scores for each debater (1-10)\n"
            "5. Declaration of winner (or tie)"
        )
        self.add_to_transcript("JUDGE", verdict)
        self.display_message("JUDGE - Final Verdict", verdict, "yellow", t)

        self.phase = DebatePhase.FINISHED

        # Score individual arguments
        self.argument_scores = self.score_arguments()

        return self.transcript

    def score_arguments(self) -> str:
        """Ask the judge to score individual arguments from the debate.

        This reuses the same judge chain — we just pass a different instruction.
        The chain doesn't know or care that the debate is over; it just processes
        whatever instruction we give it against the transcript context.
        """
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

        scores = self.judge.respond(self.get_transcript_text(), scoring_instruction)
        self.add_to_transcript("SCORING", scores)
        self.display_message("ARGUMENT SCORES", scores, "magenta")
        return scores
