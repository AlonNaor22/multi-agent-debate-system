import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from config import NUM_REBUTTAL_ROUNDS
from src.debate_enums import DebatePhase, Speaker
from src.agents.base_agent import DebateAgent
from src.scoring import DebateScores
from src.debate_engine import (
    DebateState,
    DebateEngine,
    PhaseChange,
    Turn,
    Vote,
    Score,
    format_audience_vote,
)
from messages import (
    CLI_VOTE_TITLE,
    CLI_VOTE_PANEL,
    CLI_VOTE_INPUT,
    CLI_VOTE_RECORDED,
    CLI_SCORES_TITLE,
    CLI_SCORES_COL_SIDE,
    CLI_SCORES_COL_ARGUMENT,
    CLI_SCORES_COL_SCORE,
    CLI_SCORES_COL_REASON,
    CLI_SCOREBOARD_TITLE,
    CLI_SCOREBOARD_BODY,
)


class DebateController(DebateState):
    """The synchronous (CLI) orchestrator of the multi-agent system.

    This is NOT an agent itself — it's the "director" that decides WHICH agent
    speaks next, WHAT instruction each receives, and WHAT context each can see.
    That ordering now lives in the shared :class:`DebateEngine`; this class just
    *consumes* the engine's events, running each agent synchronously and
    rendering the result with Rich. The streaming web service consumes the very
    same engine, which is what stops the CLI and web flows from drifting apart.

    The agents don't talk to each other directly — the controller passes the
    shared transcript (inherited from :class:`DebateState`) to each one so they
    can respond to what came before.
    """

    # Rich panel colour per speaker.
    _SPEAKER_STYLES = {
        Speaker.MODERATOR: "blue",
        Speaker.PRO: "green",
        Speaker.CON: "red",
        Speaker.JUDGE: "yellow",
    }

    def __init__(self, topic: str, pro_agent: DebateAgent, con_agent: DebateAgent, judge_agent: DebateAgent):
        super().__init__(topic)
        self.pro = pro_agent
        self.con = con_agent
        self.judge = judge_agent
        self.console = Console()

    def timed_respond(self, agent: DebateAgent, context: str, instruction: str) -> tuple[str, float]:
        """Call agent.respond() and measure how long it takes.

        Returns (response_text, seconds_elapsed).
        This is just a timing wrapper — the chain call is identical.
        """
        start = time.time()
        response = agent.respond(context, instruction)
        elapsed = time.time() - start
        return response, elapsed

    def display_message(self, speaker: str, content: str, style: str, elapsed: Optional[float] = None):
        """Display a message with Rich formatting."""
        subtitle = f"[{elapsed:.1f}s]" if elapsed else None
        self.console.print()
        self.console.print(Panel(
            content,
            title=speaker,
            subtitle=subtitle,
            style=style
        ))

    def _title(self, speaker: Speaker, label: Optional[str]) -> str:
        """Build the Rich panel title for a turn."""
        if label:
            return f"{speaker.value} - {label}"
        return speaker.value

    def run_debate(self):
        """Execute the full debate by consuming the shared DebateEngine.

        ``word_limits=None`` keeps the CLI on the original, unconstrained
        instructions. ``NUM_REBUTTAL_ROUNDS`` is read here (not baked into the
        engine) so tests can patch it on this module.
        """
        engine = DebateEngine(
            self.topic,
            self.pro,
            self.con,
            self.judge,
            num_rebuttal_rounds=NUM_REBUTTAL_ROUNDS,
            word_limits=None,
        )

        for event in engine.events():
            if isinstance(event, PhaseChange):
                self.phase = event.phase
            elif isinstance(event, Turn):
                response, elapsed = self.timed_respond(
                    event.agent, self.get_transcript_text(), event.instruction
                )
                self.add_to_transcript(event.speaker.value, response)
                self.display_message(
                    self._title(event.speaker, event.label),
                    response,
                    self._SPEAKER_STYLES.get(event.speaker, "white"),
                    elapsed,
                )
            elif isinstance(event, Score):
                self.argument_scores = event.agent.score_arguments(
                    self.get_transcript_text(), event.instruction
                )
                self._display_scores(self.argument_scores)
            elif isinstance(event, Vote):
                self._collect_vote()

        return self.transcript

    def _display_scores(self, scores: DebateScores):
        """Render the judge's structured scoreboard as a Rich table."""
        self.console.print()
        table = Table(title=CLI_SCORES_TITLE, title_style="bold magenta")
        table.add_column(CLI_SCORES_COL_SIDE, style="bold")
        table.add_column(CLI_SCORES_COL_ARGUMENT)
        table.add_column(CLI_SCORES_COL_SCORE, justify="right")
        table.add_column(CLI_SCORES_COL_REASON)
        for arg in scores.pro_arguments:
            table.add_row("PRO", arg.summary, f"{arg.score}/10", arg.reason)
        for arg in scores.con_arguments:
            table.add_row("CON", arg.summary, f"{arg.score}/10", arg.reason)
        self.console.print(table)
        self.console.print(Panel(
            CLI_SCOREBOARD_BODY.format(
                pro_average=scores.pro_average,
                con_average=scores.con_average,
                winner=scores.winner,
                strongest=scores.strongest_argument,
                weakest=scores.weakest_argument,
            ),
            title=CLI_SCOREBOARD_TITLE,
            style="magenta",
        ))

    def _collect_vote(self):
        """Prompt the human audience for an interim vote and record it."""
        self.console.print()
        self.console.print(Panel(
            CLI_VOTE_PANEL,
            title=CLI_VOTE_TITLE,
            style="cyan"
        ))
        vote = input(CLI_VOTE_INPUT).strip()
        vote_map = {"1": "PRO", "2": "CON", "3": "TIE"}
        vote_text = format_audience_vote(vote_map.get(vote, "TIE"))
        self.add_to_transcript("AUDIENCE", vote_text)
        self.console.print(CLI_VOTE_RECORDED.format(vote=vote_text))
