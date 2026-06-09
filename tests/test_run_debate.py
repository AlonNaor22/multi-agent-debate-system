"""Tests for DebateController.run_debate and edge cases."""
import pytest
from unittest.mock import MagicMock, patch
from src.debate_controller import DebateController
from src.debate_enums import DebatePhase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(response="Agent response."):
    agent = MagicMock()
    agent.respond.return_value = response
    return agent


@pytest.fixture
def agents():
    return _make_agent(), _make_agent(), _make_agent()


@pytest.fixture
def controller(agents):
    pro, con, judge = agents
    return DebateController(
        topic="Should AI be regulated?",
        pro_agent=pro,
        con_agent=con,
        judge_agent=judge,
    )


# ---------------------------------------------------------------------------
# argument_scores initialised before run_debate
# ---------------------------------------------------------------------------

class TestArgumentScoresInit:
    def test_exists_before_run(self, controller):
        assert hasattr(controller, "argument_scores")
        assert controller.argument_scores is None


# ---------------------------------------------------------------------------
# run_debate — full flow with mocked agents and input()
# ---------------------------------------------------------------------------

class TestRunDebate:
    def _run(self, controller):
        with patch("builtins.input", return_value="1"), \
             patch.object(controller.console, "print"):
            return controller.run_debate()

    def test_returns_transcript(self, controller):
        transcript = self._run(controller)
        assert isinstance(transcript, list)
        assert len(transcript) > 0

    def test_transcript_contains_all_speakers(self, controller):
        transcript = self._run(controller)
        speakers = {e["speaker"] for e in transcript}
        assert "MODERATOR" in speakers
        assert "PRO" in speakers
        assert "CON" in speakers
        assert "JUDGE" in speakers
        assert "AUDIENCE" in speakers
        assert "SCORING" in speakers

    def test_phase_sequence_correct(self, controller):
        self._run(controller)
        phases = [e["phase"] for e in controller.transcript]
        # Introduction must come first
        assert phases[0] == DebatePhase.INTRODUCTION.value
        # The last entry (SCORING) is recorded while phase==FINISHED; all
        # entries before it should use a debate-active phase
        assert phases[-1] == DebatePhase.FINISHED.value
        assert DebatePhase.VERDICT.value in phases

    def test_phase_ends_as_finished(self, controller):
        self._run(controller)
        assert controller.phase == DebatePhase.FINISHED

    def test_argument_scores_set_after_run(self, controller):
        self._run(controller)
        assert controller.argument_scores is not None

    def test_all_agents_called(self, controller, agents):
        pro, con, judge = agents
        self._run(controller)
        assert pro.respond.called
        assert con.respond.called
        assert judge.respond.called

    def test_rebuttal_rounds_match_config(self, controller, agents):
        pro, con, judge = agents
        with patch("src.debate_controller.NUM_REBUTTAL_ROUNDS", 3), \
             patch("builtins.input", return_value="1"), \
             patch.object(controller.console, "print"):
            controller.run_debate()
        # Pro is called: 1 (opening) + 3 (rebuttals) + 1 (closing) = 5 debate calls
        # plus judge intro + verdict + scoring = 3 judge calls; con same as pro
        assert pro.respond.call_count == 5
        assert con.respond.call_count == 5


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_topic_still_runs(self):
        controller = DebateController(
            topic="",
            pro_agent=_make_agent(),
            con_agent=_make_agent(),
            judge_agent=_make_agent(),
        )
        with patch("builtins.input", return_value="3"), \
             patch.object(controller.console, "print"):
            transcript = controller.run_debate()
        assert isinstance(transcript, list)

    def test_invalid_vote_defaults_to_tie(self, controller):
        with patch("builtins.input", return_value="99"), \
             patch.object(controller.console, "print"):
            controller.run_debate()
        audience_entry = next(e for e in controller.transcript if e["speaker"] == "AUDIENCE")
        assert "TIE" in audience_entry["content"]

    def test_transcript_preserved_after_error_in_scoring(self, controller, agents):
        """If scoring raises after the verdict, the rest of the transcript is intact."""
        pro, con, judge = agents
        call_count = [0]
        original = judge.respond

        def respond_with_late_error(*a, **kw):
            call_count[0] += 1
            if call_count[0] >= 3:  # intro + verdict pass; scoring fails
                raise RuntimeError("LLM failure")
            return "response"

        judge.respond = respond_with_late_error

        with patch("builtins.input", return_value="1"), \
             patch.object(controller.console, "print"), \
             pytest.raises(RuntimeError):
            controller.run_debate()

        # Transcript up to the failure is still intact
        speakers = [e["speaker"] for e in controller.transcript]
        assert "MODERATOR" in speakers
        assert "PRO" in speakers
