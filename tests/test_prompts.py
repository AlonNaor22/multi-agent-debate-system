import pytest
from src.prompts import PRO_STYLES, CON_STYLES, JUDGE_AGENT_PROMPT
import config

EXPECTED_STYLES = ["passionate", "aggressive", "academic", "humorous"]


class TestProStyles:
    def test_all_expected_styles_present(self):
        for style in EXPECTED_STYLES:
            assert style in PRO_STYLES, f"PRO style '{style}' is missing"

    def test_no_empty_prompts(self):
        for style, prompt in PRO_STYLES.items():
            assert prompt.strip(), f"PRO style '{style}' prompt is empty"

    def test_prompts_are_substantive(self):
        for style, prompt in PRO_STYLES.items():
            assert len(prompt) > 100, f"PRO style '{style}' prompt is suspiciously short"


class TestConStyles:
    def test_all_expected_styles_present(self):
        for style in EXPECTED_STYLES:
            assert style in CON_STYLES, f"CON style '{style}' is missing"

    def test_no_empty_prompts(self):
        for style, prompt in CON_STYLES.items():
            assert prompt.strip(), f"CON style '{style}' prompt is empty"

    def test_pro_and_con_prompts_differ_per_style(self):
        for style in EXPECTED_STYLES:
            assert PRO_STYLES[style] != CON_STYLES[style], \
                f"PRO and CON are identical for style '{style}'"


class TestJudgePrompt:
    def test_is_non_empty(self):
        assert JUDGE_AGENT_PROMPT.strip()

    def test_mentions_verdict(self):
        assert "verdict" in JUDGE_AGENT_PROMPT.lower()

    def test_mentions_neutrality(self):
        assert any(word in JUDGE_AGENT_PROMPT.lower() for word in ["neutral", "impartial", "fair"])


class TestConfig:
    def test_model_name_is_non_empty_string(self):
        assert isinstance(config.MODEL_NAME, str) and config.MODEL_NAME.strip()

    def test_temperatures_in_valid_range(self):
        assert 0.0 <= config.TEMPERATURE_DEBATERS <= 1.0
        assert 0.0 <= config.TEMPERATURE_JUDGE <= 1.0

    def test_judge_temperature_lower_than_debaters(self):
        assert config.TEMPERATURE_JUDGE < config.TEMPERATURE_DEBATERS

    def test_max_tokens_is_positive(self):
        assert config.MAX_TOKENS > 0

    def test_scoring_max_tokens_has_more_headroom_than_a_single_turn(self):
        assert config.SCORING_MAX_TOKENS > config.MAX_TOKENS

    def test_rebuttal_rounds_at_least_one(self):
        assert config.NUM_REBUTTAL_ROUNDS >= 1

    def test_available_styles_match_prompt_dicts(self):
        for style in config.AVAILABLE_STYLES:
            assert style in PRO_STYLES, f"'{style}' in config but missing from PRO_STYLES"
            assert style in CON_STYLES, f"'{style}' in config but missing from CON_STYLES"

    def test_default_styles_are_valid(self):
        assert config.DEFAULT_PRO_STYLE in config.AVAILABLE_STYLES
        assert config.DEFAULT_CON_STYLE in config.AVAILABLE_STYLES
