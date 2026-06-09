from enum import Enum


class DebatePhase(str, Enum):
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
    PRO = "PRO"
    CON = "CON"
    MODERATOR = "MODERATOR"
    JUDGE = "JUDGE"
    AUDIENCE = "AUDIENCE"
    SCORING = "SCORING"
