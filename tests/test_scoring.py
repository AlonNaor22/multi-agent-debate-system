"""Tests for the DebateScores schema — computed averages and validation."""
import pytest
from pydantic import ValidationError

from src.scoring import ArgumentScore, DebateScores


def _scores(pro, con, winner="PRO"):
    return DebateScores(
        pro_arguments=[ArgumentScore(summary=f"p{i}", score=s, reason="r") for i, s in enumerate(pro)],
        con_arguments=[ArgumentScore(summary=f"c{i}", score=s, reason="r") for i, s in enumerate(con)],
        winner=winner,
        strongest_argument="x",
        weakest_argument="y",
    )


class TestComputedAverages:
    def test_averages_are_rounded_means(self):
        s = _scores(pro=[8, 6], con=[5, 5, 5])
        assert s.pro_average == 7.0
        assert s.con_average == 5.0

    def test_empty_side_averages_to_zero(self):
        s = _scores(pro=[], con=[7])
        assert s.pro_average == 0.0
        assert s.con_average == 7.0

    def test_averages_serialize_in_model_dump(self):
        d = _scores(pro=[9], con=[3]).model_dump()
        assert d["pro_average"] == 9.0
        assert d["con_average"] == 3.0
        assert d["winner"] == "PRO"


class TestValidation:
    def test_score_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ArgumentScore(summary="x", score=11, reason="r")

    def test_winner_must_be_an_allowed_value(self):
        with pytest.raises(ValidationError):
            _scores(pro=[8], con=[6], winner="MAYBE")

    def test_computed_averages_are_not_required_model_inputs(self):
        # The judge supplies per-argument scores + winner; averages are computed,
        # so they must NOT appear in the structured-output (tool-input) schema.
        required = DebateScores.model_json_schema(mode="validation").get("required", [])
        assert "pro_average" not in required
        assert "con_average" not in required
