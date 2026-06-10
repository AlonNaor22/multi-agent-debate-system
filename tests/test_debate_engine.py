"""Tests for the shared DebateEngine — the single source of truth for the
debate flow that both the CLI and the web service consume.

The engine is pure (no LLM, no I/O, no state mutation), so these tests use
plain sentinel objects for the agents and assert the event stream directly.
"""
import pytest

from src.debate_enums import DebatePhase, Speaker
from src.prompts import INSTRUCTION_INTRO, INSTRUCTION_PRO_OPENING
from src.debate_engine import (
    DebateState,
    DebateEngine,
    WordLimits,
    DEFAULT_WORD_LIMITS,
    PhaseChange,
    Turn,
    Vote,
    Score,
    format_audience_vote,
)


PRO_AGENT = "pro-agent"
CON_AGENT = "con-agent"
JUDGE_AGENT = "judge-agent"


def build_engine(rounds=2, word_limits=None, topic="Should AI be regulated?"):
    return DebateEngine(
        topic,
        PRO_AGENT,
        CON_AGENT,
        JUDGE_AGENT,
        num_rebuttal_rounds=rounds,
        word_limits=word_limits,
    )


# ---------------------------------------------------------------------------
# DebateState — the de-duplicated transcript handling
# ---------------------------------------------------------------------------

class TestDebateState:
    def test_starts_empty_in_introduction(self):
        state = DebateState("topic")
        assert state.transcript == []
        assert state.phase == DebatePhase.INTRODUCTION
        assert state.argument_scores is None

    def test_add_to_transcript_tags_current_phase(self):
        state = DebateState("topic")
        state.phase = DebatePhase.VERDICT
        state.add_to_transcript("JUDGE", "the verdict")
        assert state.transcript[0] == {
            "speaker": "JUDGE",
            "content": "the verdict",
            "phase": DebatePhase.VERDICT.value,
        }

    def test_transcript_text_starts_with_topic(self):
        state = DebateState("Is the sky blue?")
        assert state.get_transcript_text().startswith("DEBATE TOPIC: Is the sky blue?")

    def test_transcript_text_formats_speaker_brackets(self):
        state = DebateState("topic")
        state.add_to_transcript("PRO", "my point")
        assert "[PRO]: my point" in state.get_transcript_text()


# ---------------------------------------------------------------------------
# Word limits
# ---------------------------------------------------------------------------

class TestWordLimits:
    def test_default_values_match_web_constants(self):
        assert DEFAULT_WORD_LIMITS == WordLimits(
            intro=150, opening=250, rebuttal=200, closing=200, verdict=300
        )

    def test_suffix_includes_limit_and_separator(self):
        wl = WordLimits()
        assert wl.suffix("intro") == " Keep your introduction concise (under 150 words)."
        assert wl.suffix("verdict") == "\nKeep it thorough but concise (under 300 words)."


# ---------------------------------------------------------------------------
# Engine event stream
# ---------------------------------------------------------------------------

class TestEngineSequence:
    def test_phase_change_order(self):
        phases = [e.phase for e in build_engine().events() if isinstance(e, PhaseChange)]
        assert phases == [
            DebatePhase.INTRODUCTION,
            DebatePhase.OPENING_PRO,
            DebatePhase.OPENING_CON,
            DebatePhase.REBUTTAL,
            DebatePhase.CLOSING_PRO,
            DebatePhase.CLOSING_CON,
            DebatePhase.VERDICT,
            DebatePhase.SCORING,
            DebatePhase.FINISHED,
        ]

    def test_turn_speakers_and_agents(self):
        turns = [e for e in build_engine(rounds=2).events() if isinstance(e, Turn)]
        speakers = [t.speaker for t in turns]
        assert speakers == [
            Speaker.MODERATOR,
            Speaker.PRO, Speaker.CON,            # openings
            Speaker.PRO, Speaker.CON,            # rebuttal round 1
            Speaker.PRO, Speaker.CON,            # rebuttal round 2
            Speaker.PRO, Speaker.CON,            # closings
            Speaker.JUDGE,                       # verdict
        ]
        # Scoring is a Score event, not a streamed Turn (see test below).
        # The judge speaks as moderator and judge; debaters keep their agent.
        by_speaker = {t.speaker: t.agent for t in turns}
        assert by_speaker[Speaker.MODERATOR] is JUDGE_AGENT
        assert by_speaker[Speaker.JUDGE] is JUDGE_AGENT
        assert by_speaker[Speaker.PRO] is PRO_AGENT
        assert by_speaker[Speaker.CON] is CON_AGENT

    def test_scoring_is_a_score_event_run_by_the_judge(self):
        events = list(build_engine().events())
        scores = [e for e in events if isinstance(e, Score)]
        assert len(scores) == 1
        assert scores[0].agent is JUDGE_AGENT
        # Scoring must NOT be streamed as a Turn anymore.
        assert all(not (isinstance(e, Turn) and e.speaker == Speaker.SCORING) for e in events)

    def test_single_vote_between_rebuttals_and_closings(self):
        events = list(build_engine().events())
        votes = [i for i, e in enumerate(events) if isinstance(e, Vote)]
        assert len(votes) == 1
        vote_idx = votes[0]
        # The vote sits after the REBUTTAL phase change and before CLOSING_PRO.
        rebuttal_idx = next(i for i, e in enumerate(events)
                            if isinstance(e, PhaseChange) and e.phase == DebatePhase.REBUTTAL)
        closing_idx = next(i for i, e in enumerate(events)
                           if isinstance(e, PhaseChange) and e.phase == DebatePhase.CLOSING_PRO)
        assert rebuttal_idx < vote_idx < closing_idx

    def test_rebuttal_rounds_scale_with_config(self):
        def rebuttal_turns(rounds):
            return [e for e in build_engine(rounds=rounds).events()
                    if isinstance(e, Turn) and e.label and e.label.startswith("Rebuttal")]
        assert len(rebuttal_turns(1)) == 2   # pro + con, one round
        assert len(rebuttal_turns(3)) == 6   # pro + con, three rounds

    def test_rebuttal_labels_count_up(self):
        labels = [e.label for e in build_engine(rounds=2).events()
                  if isinstance(e, Turn) and e.label and e.label.startswith("Rebuttal")]
        assert labels == ["Rebuttal 1", "Rebuttal 1", "Rebuttal 2", "Rebuttal 2"]


class TestEngineWordLimits:
    def test_no_limits_leaves_instructions_bare(self):
        turns = [e for e in build_engine(word_limits=None).events() if isinstance(e, Turn)]
        intro = turns[0]
        assert intro.instruction == INSTRUCTION_INTRO.format(topic="Should AI be regulated?")
        opening = turns[1]
        assert opening.instruction == INSTRUCTION_PRO_OPENING

    def test_limits_append_per_phase_suffix(self):
        turns = [e for e in build_engine(word_limits=DEFAULT_WORD_LIMITS).events()
                 if isinstance(e, Turn)]
        intro = turns[0]
        assert intro.instruction.endswith(" Keep your introduction concise (under 150 words).")
        assert intro.instruction.startswith(
            INSTRUCTION_INTRO.format(topic="Should AI be regulated?")
        )
        opening = turns[1]
        assert opening.instruction.endswith(" Be persuasive but concise (under 250 words).")


# ---------------------------------------------------------------------------
# Audience vote formatting (shared by CLI and web)
# ---------------------------------------------------------------------------

class TestFormatAudienceVote:
    @pytest.mark.parametrize("side", ["PRO", "CON", "TIE"])
    def test_format(self, side):
        assert format_audience_vote(side) == f"Audience vote: {side} is winning."
