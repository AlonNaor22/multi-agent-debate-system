"""Typed schema for the judge's argument scoring.

The judge used to return its per-argument scores as a free-text blob. This
module defines a structured schema instead, which the judge fills via the
Anthropic structured-output API (LangChain's ``with_structured_output``). The
result is plumbed through the engine, the WebSocket events, and the React UI as
a real scoreboard rather than a wall of text.

The model supplies the per-argument scores, the winner, and the
strongest/weakest picks; the per-side averages are computed in code (a
``computed_field``, so they still serialize) — more reliable than asking the
model to do the arithmetic.
"""
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class ArgumentScore(BaseModel):
    """One scored argument from the debate."""
    summary: str = Field(description="A one-line summary of the argument.")
    score: int = Field(ge=1, le=10, description="Quality score from 1 (weak) to 10 (strong).")
    reason: str = Field(description="A brief justification for the score.")


class DebateScores(BaseModel):
    """The judge's structured scoring of a whole debate."""
    pro_arguments: list[ArgumentScore] = Field(
        description="Each distinct argument the PRO side made, scored."
    )
    con_arguments: list[ArgumentScore] = Field(
        description="Each distinct argument the CON side made, scored."
    )
    winner: Literal["PRO", "CON", "TIE"] = Field(
        description="The side that argued most effectively overall."
    )
    strongest_argument: str = Field(
        description="The single strongest argument in the debate, and why."
    )
    weakest_argument: str = Field(
        description="The single weakest argument in the debate, and why."
    )

    @computed_field  # serialized into model_dump(); not asked of the model
    @property
    def pro_average(self) -> float:
        return _average(self.pro_arguments)

    @computed_field
    @property
    def con_average(self) -> float:
        return _average(self.con_arguments)


def _average(arguments: list[ArgumentScore]) -> float:
    if not arguments:
        return 0.0
    return round(sum(a.score for a in arguments) / len(arguments), 1)
