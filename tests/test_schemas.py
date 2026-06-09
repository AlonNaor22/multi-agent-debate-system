import pytest
from api.schemas.debate import (
    DebatePhase,
    Speaker,
    WSMessageType,
    DebateCreateRequest,
    WSMessage,
)


class TestDebateCreateRequest:
    def test_defaults_to_passionate_styles(self):
        req = DebateCreateRequest(topic="Test topic")
        assert req.pro_style == "passionate"
        assert req.con_style == "passionate"

    def test_accepts_custom_styles(self):
        req = DebateCreateRequest(topic="Test", pro_style="aggressive", con_style="academic")
        assert req.pro_style == "aggressive"
        assert req.con_style == "academic"

    def test_topic_is_required(self):
        with pytest.raises(Exception):
            DebateCreateRequest()

    def test_topic_is_stored(self):
        req = DebateCreateRequest(topic="AI regulation")
        assert req.topic == "AI regulation"


class TestEnums:
    def test_all_phases_have_string_values(self):
        for phase in DebatePhase:
            assert isinstance(phase.value, str)

    def test_finished_phase_exists(self):
        assert DebatePhase.FINISHED is not None

    def test_all_speakers_have_string_values(self):
        for speaker in Speaker:
            assert isinstance(speaker.value, str)

    def test_pro_and_con_speakers_exist(self):
        assert Speaker.PRO is not None
        assert Speaker.CON is not None
        assert Speaker.JUDGE is not None

    def test_ws_message_types_are_strings(self):
        for msg_type in WSMessageType:
            assert isinstance(msg_type.value, str)


class TestWSMessage:
    def test_constructs_valid_message(self):
        msg = WSMessage(
            type=WSMessageType.PHASE_CHANGE,
            debate_id="abc-123",
            data={"phase": "introduction"},
        )
        assert msg.debate_id == "abc-123"
        assert msg.type == WSMessageType.PHASE_CHANGE
        assert msg.data == {"phase": "introduction"}


