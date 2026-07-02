import os
import sys
import json
from dotenv import load_dotenv
from src.agents.base_agent import build_agents, AgentError
from src.debate_controller import DebateController
from src.prompts import validate_styles, StyleConfigError
from config import AVAILABLE_STYLES, DEFAULT_PRO_STYLE, DEFAULT_CON_STYLE
from messages import (
    API_KEY_MISSING,
    STYLE_CONFIG_INVALID,
    CLI_BANNER,
    CLI_TOPIC_PROMPT,
    DEFAULT_TOPIC,
    CLI_AVAILABLE_STYLES,
    CLI_PRO_STYLE_PROMPT,
    CLI_CON_STYLE_PROMPT,
    CLI_STARTING_ON,
    CLI_STYLE_SUMMARY,
    CLI_INTERRUPTED,
    CLI_INTERRUPTED_HINT,
    CLI_SAVE_PROMPT,
    CLI_FORMAT_PROMPT,
    CLI_SAVED_MARKDOWN,
    CLI_SAVE_MARKDOWN_FAILED,
    CLI_SAVED_JSON,
    CLI_SAVE_JSON_FAILED,
)

# Load the API key from .env file into environment variables
load_dotenv()


def _require_api_key() -> None:
    """Exit early with a clear message if the Anthropic API key isn't set."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(API_KEY_MISSING)
        sys.exit(1)


def _require_valid_style_config() -> None:
    """Exit early if AVAILABLE_STYLES has an entry with no matching prompt.

    Catches a misconfigured env override before the user picks a style that
    would otherwise raise deep inside ``build_agents`` mid-setup.
    """
    try:
        validate_styles(AVAILABLE_STYLES)
    except StyleConfigError as error:
        print(STYLE_CONFIG_INVALID.format(error=error))
        sys.exit(1)


def _prompt_for_setup() -> tuple[str, str, str]:
    """Print the banner and collect the topic and each side's style from stdin.

    Pressing Enter (or entering an unknown style) falls back to the defaults.
    Returns ``(topic, pro_style, con_style)``.
    """
    print("=" * 60)
    print(f"        {CLI_BANNER}")
    print("=" * 60)

    topic = input(CLI_TOPIC_PROMPT).strip()
    if not topic:
        topic = DEFAULT_TOPIC

    print(CLI_AVAILABLE_STYLES.format(styles=", ".join(AVAILABLE_STYLES)))
    pro_style = input(CLI_PRO_STYLE_PROMPT.format(default=DEFAULT_PRO_STYLE)).strip().lower()
    if pro_style not in AVAILABLE_STYLES:
        pro_style = DEFAULT_PRO_STYLE

    con_style = input(CLI_CON_STYLE_PROMPT.format(default=DEFAULT_CON_STYLE)).strip().lower()
    if con_style not in AVAILABLE_STYLES:
        con_style = DEFAULT_CON_STYLE

    print(CLI_STARTING_ON.format(topic=topic))
    print(CLI_STYLE_SUMMARY.format(pro_style=pro_style, con_style=con_style))
    print("-" * 60)
    return topic, pro_style, con_style


def _run_debate(topic: str, pro_style: str, con_style: str) -> DebateController:
    """Build the three agents, run the debate, and return the finished controller.

    Exits with a friendly message if a transient LLM failure interrupts it.
    """
    # Same model, different personas via system prompts.
    pro_agent, con_agent, judge_agent = build_agents(pro_style, con_style)
    controller = DebateController(topic, pro_agent, con_agent, judge_agent)
    try:
        controller.run_debate()
    except AgentError as error:
        print("\n" + "=" * 60)
        print(CLI_INTERRUPTED.format(error=error))
        print(CLI_INTERRUPTED_HINT)
        sys.exit(1)
    return controller


def _offer_to_save(controller: DebateController, topic: str, pro_style: str, con_style: str) -> None:
    """Ask whether to save the transcript and write the chosen format(s)."""
    print("\n" + "=" * 60)
    if input(CLI_SAVE_PROMPT).strip().lower() != "y":
        return

    os.makedirs("output", exist_ok=True)
    format_choice = input(CLI_FORMAT_PROMPT).strip().lower()
    base_name = f"debate_{topic[:30].replace(' ', '_')}"

    if format_choice in ("m", "b", ""):
        _write_markdown(controller, base_name)
    if format_choice in ("j", "b"):
        _write_json(controller, topic, pro_style, con_style, base_name)


def _write_markdown(controller: DebateController, base_name: str) -> None:
    """Write the transcript as Markdown, reporting success or an OS error."""
    md_path = f"output/{base_name}.md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(controller.get_transcript_text())
        print(CLI_SAVED_MARKDOWN.format(path=md_path))
    except OSError as error:
        print(CLI_SAVE_MARKDOWN_FAILED.format(error=error))


def _write_json(
    controller: DebateController, topic: str, pro_style: str, con_style: str, base_name: str
) -> None:
    """Write the full debate (setup + transcript + scores) as JSON."""
    json_path = f"output/{base_name}.json"
    debate_data = {
        "topic": topic,
        "pro_style": pro_style,
        "con_style": con_style,
        "transcript": controller.transcript,
        "argument_scores": (
            controller.argument_scores.model_dump()
            if controller.argument_scores else None
        ),
    }
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(debate_data, f, indent=2, ensure_ascii=False)
        print(CLI_SAVED_JSON.format(path=json_path))
    except OSError as error:
        print(CLI_SAVE_JSON_FAILED.format(error=error))


def main():
    """CLI entry point: collect setup, run a full debate, then optionally save it."""
    _require_api_key()
    _require_valid_style_config()
    topic, pro_style, con_style = _prompt_for_setup()
    controller = _run_debate(topic, pro_style, con_style)
    _offer_to_save(controller, topic, pro_style, con_style)


if __name__ == "__main__":
    main()
