"""User-facing copy for the backend — CLI text and client-facing API/WebSocket messages.

Collected here (rather than scattered as string literals) so the wording the
end user reads lives in exactly one place, and so a future translation is a
drop-in. ``{name}`` placeholders are filled with ``str.format`` at the call site,
matching the style of ``src/prompts.py``.

Out of scope on purpose: LLM prompt/persona text (``src/prompts.py``), log
messages, transcript content, and internal identifiers / enum values.
"""

# --- Shared (CLI startup and API lifespan) ---
API_KEY_MISSING = "ERROR: ANTHROPIC_API_KEY is not set. Add it to your .env file."
STYLE_CONFIG_INVALID = "ERROR: invalid style configuration: {error}"


# --- CLI: entry point (main.py) ---
CLI_BANNER = "MULTI-AGENT DEBATE SYSTEM"
CLI_TOPIC_PROMPT = "\nEnter debate topic (or press Enter for default): "
DEFAULT_TOPIC = "Should artificial intelligence be regulated by governments?"
CLI_AVAILABLE_STYLES = "\nAvailable debater styles: {styles}"
CLI_PRO_STYLE_PROMPT = "Choose PRO style (Enter for '{default}'): "
CLI_CON_STYLE_PROMPT = "Choose CON style (Enter for '{default}'): "
CLI_STARTING_ON = "\nStarting debate on: {topic}"
CLI_STYLE_SUMMARY = "PRO style: {pro_style} | CON style: {con_style}"
CLI_INTERRUPTED = "The debate was interrupted: {error}"
CLI_INTERRUPTED_HINT = (
    "This is usually temporary — check your connection and API key,\n"
    "then run the debate again."
)
CLI_SAVE_PROMPT = "Save transcript? (y/n): "
CLI_FORMAT_PROMPT = "Format — (m)arkdown, (j)son, or (b)oth? [m]: "
CLI_SAVED_MARKDOWN = "Saved Markdown to {path}"
CLI_SAVE_MARKDOWN_FAILED = "Failed to save Markdown: {error}"
CLI_SAVED_JSON = "Saved JSON to {path}"
CLI_SAVE_JSON_FAILED = "Failed to save JSON: {error}"


# --- CLI: live debate rendering (src/debate_controller.py) ---
CLI_VOTE_TITLE = "AUDIENCE VOTE"
CLI_VOTE_PANEL = (
    "Who is winning so far?\n\n"
    "  1 = PRO is winning\n"
    "  2 = CON is winning\n"
    "  3 = It's a tie"
)
CLI_VOTE_INPUT = "Your vote (1/2/3): "
CLI_VOTE_RECORDED = "  Recorded: {vote}\n"
CLI_SCORES_TITLE = "ARGUMENT SCORES"
CLI_SCORES_COL_SIDE = "Side"
CLI_SCORES_COL_ARGUMENT = "Argument"
CLI_SCORES_COL_SCORE = "Score"
CLI_SCORES_COL_REASON = "Reason"
CLI_SCOREBOARD_TITLE = "SCOREBOARD"
CLI_SCOREBOARD_BODY = (
    "PRO average: {pro_average}/10    CON average: {con_average}/10\n"
    "Winner: {winner}\n\n"
    "Strongest: {strongest}\n"
    "Weakest: {weakest}"
)


# --- API / WebSocket: client-facing messages ---
# Style descriptions shown in the setup UI (GET /api/config/styles).
STYLE_DESCRIPTIONS = {
    "passionate": "Persuasive with logical arguments and rhetorical techniques",
    "aggressive": "Confrontational and relentless, attacks opponent's logic directly",
    "academic": "Formal, research-oriented with citations and structured frameworks",
    "humorous": "Witty with satire, clever analogies, and entertaining delivery",
}
INVALID_STYLE = "Invalid {field}. Must be one of: {styles}"
TOO_MANY_DEBATES = "The server is busy running other debates. Please try again in a moment."
DEBATE_NOT_FOUND = "Debate not found"
DEBATE_SESSION_NOT_FOUND = "Debate session not found"
DEBATE_ALREADY_RUNNING = "This debate is already running in another session."
WS_UNEXPECTED_ERROR = "An unexpected error occurred. Please try again."
VOTE_PROMPT = "Who is winning so far?"
AI_SERVICE_UNAVAILABLE = "The AI service is temporarily unavailable. Please try again."
