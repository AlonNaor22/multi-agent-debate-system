import os
import sys
import json
from dotenv import load_dotenv
from src.agents.base_agent import build_agents, AgentError
from src.debate_controller import DebateController
from config import AVAILABLE_STYLES, DEFAULT_PRO_STYLE, DEFAULT_CON_STYLE
from messages import (
    API_KEY_MISSING,
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


def main():
    """CLI entry point: collect topic/styles, run a full debate, optionally save transcript."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(API_KEY_MISSING)
        sys.exit(1)

    print("=" * 60)
    print(f"        {CLI_BANNER}")
    print("=" * 60)

    topic = input(CLI_TOPIC_PROMPT).strip()
    if not topic:
        topic = DEFAULT_TOPIC

    # Let user pick personality styles
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

    # Create 3 agents — same model, different personas via system prompts
    pro_agent, con_agent, judge_agent = build_agents(pro_style, con_style)

    # The controller orchestrates the agents
    controller = DebateController(topic, pro_agent, con_agent, judge_agent)
    try:
        controller.run_debate()
    except AgentError as e:
        print("\n" + "=" * 60)
        print(CLI_INTERRUPTED.format(error=e))
        print(CLI_INTERRUPTED_HINT)
        sys.exit(1)

    # Offer to save the transcript
    print("\n" + "=" * 60)
    save = input(CLI_SAVE_PROMPT).strip().lower()
    if save == "y":
        os.makedirs("output", exist_ok=True)
        format_choice = input(CLI_FORMAT_PROMPT).strip().lower()
        base_name = f"debate_{topic[:30].replace(' ', '_')}"

        if format_choice in ("m", "b", ""):
            md_path = f"output/{base_name}.md"
            try:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(controller.get_transcript_text())
                print(CLI_SAVED_MARKDOWN.format(path=md_path))
            except OSError as e:
                print(CLI_SAVE_MARKDOWN_FAILED.format(error=e))

        if format_choice in ("j", "b"):
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
            except OSError as e:
                print(CLI_SAVE_JSON_FAILED.format(error=e))


if __name__ == "__main__":
    main()
