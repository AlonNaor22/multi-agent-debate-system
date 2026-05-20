import pytest
from unittest.mock import MagicMock
from src.debate_controller import DebateController, DebatePhase


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.respond.return_value = "Test argument text"
    return agent


@pytest.fixture
def controller(mock_agent):
    return DebateController(
        topic="Should AI be regulated?",
        pro_agent=mock_agent,
        con_agent=mock_agent,
        judge_agent=mock_agent,
    )


class TestTranscript:
    def test_empty_on_init(self, controller):
        assert controller.transcript == []

    def test_add_single_entry(self, controller):
        controller.add_to_transcript("PRO", "My first argument")
        assert len(controller.transcript) == 1

    def test_entry_has_speaker_and_content(self, controller):
        controller.add_to_transcript("PRO", "My first argument")
        entry = controller.transcript[0]
        assert entry["speaker"] == "PRO"
        assert entry["content"] == "My first argument"

    def test_entry_records_current_phase(self, controller):
        controller.phase = DebatePhase.OPENING_PRO
        controller.add_to_transcript("PRO", "Opening")
        assert controller.transcript[0]["phase"] == DebatePhase.OPENING_PRO.value

    def test_entries_preserve_insertion_order(self, controller):
        controller.add_to_transcript("PRO", "First")
        controller.add_to_transcript("CON", "Second")
        controller.add_to_transcript("JUDGE", "Third")
        assert [e["speaker"] for e in controller.transcript] == ["PRO", "CON", "JUDGE"]


class TestGetTranscriptText:
    def test_starts_with_topic(self, controller):
        text = controller.get_transcript_text()
        assert text.startswith("DEBATE TOPIC: Should AI be regulated?")

    def test_empty_transcript_has_no_speaker_brackets(self, controller):
        assert "[" not in controller.get_transcript_text()

    def test_formats_entries_with_speaker_brackets(self, controller):
        controller.add_to_transcript("PRO", "First point")
        assert "[PRO]: First point" in controller.get_transcript_text()

    def test_all_entries_appear_in_output(self, controller):
        controller.add_to_transcript("PRO", "For it")
        controller.add_to_transcript("CON", "Against it")
        text = controller.get_transcript_text()
        assert "[PRO]: For it" in text
        assert "[CON]: Against it" in text


class TestTimedRespond:
    def test_returns_response_and_elapsed_time(self, controller, mock_agent):
        response, elapsed = controller.timed_respond(mock_agent, "context", "instruction")
        assert response == "Test argument text"
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_passes_context_and_instruction_to_agent(self, controller, mock_agent):
        controller.timed_respond(mock_agent, "the context", "the instruction")
        mock_agent.respond.assert_called_once_with("the context", "the instruction")


class TestInitialState:
    def test_topic_is_stored(self, controller):
        assert controller.topic == "Should AI be regulated?"

    def test_initial_phase_is_introduction(self, controller):
        assert controller.phase == DebatePhase.INTRODUCTION
