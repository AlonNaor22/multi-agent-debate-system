"""Canonical phase and speaker identifiers shared across the debate system.

These enums are the single vocabulary used by the engine, the CLI, the web
service, and the persisted transcript — and they are mirrored by hand in the
React types (``frontend/src/types/debate.ts``). Both inherit from ``str`` so
each member serialises straight to JSON and compares equal to the plain string
stored on a transcript entry, with no manual ``.value`` juggling at the
boundaries.
"""
from enum import Enum


class DebatePhase(str, Enum):
    """The phases a debate moves through, in running order.

    ``DebateEngine`` walks these from ``INTRODUCTION`` to ``FINISHED`` and emits
    a ``PhaseChange`` at each step; the value is tagged onto every transcript
    entry and drives the web progress bar.
    """
    INTRODUCTION = "introduction"
    OPENING_PRO = "opening_pro"
    OPENING_CON = "opening_con"
    REBUTTAL = "rebuttal"
    CLOSING_PRO = "closing_pro"
    CLOSING_CON = "closing_con"
    VERDICT = "verdict"
    SCORING = "scoring"
    FINISHED = "finished"


class Speaker(str, Enum):
    """Who produced a given transcript entry.

    ``PRO``, ``CON``, ``JUDGE`` and ``MODERATOR`` (the judge during the intro)
    are emitted by the engine as ``Turn`` speakers; ``AUDIENCE`` tags the
    interim vote line and ``SCORING`` the scoreboard. The values double as the
    web UI's per-speaker colour-coding keys.
    """
    PRO = "PRO"
    CON = "CON"
    MODERATOR = "MODERATOR"
    JUDGE = "JUDGE"
    AUDIENCE = "AUDIENCE"
    SCORING = "SCORING"
