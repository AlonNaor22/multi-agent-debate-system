import os
import sys
import json
from dotenv import load_dotenv
from src.agents.base_agent import build_agents, AgentError
from src.debate_controller import DebateController
from config import AVAILABLE_STYLES, DEFAULT_PRO_STYLE, DEFAULT_CON_STYLE

# Load the API key from .env file into environment variables
load_dotenv()


def main():
    """CLI entry point: collect topic/styles, run a full debate, optionally save transcript."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    print("=" * 60)
    print("        MULTI-AGENT DEBATE SYSTEM")
    print("=" * 60)

    topic = input("\nEnter debate topic (or press Enter for default): ").strip()
    if not topic:
        topic = "Should artificial intelligence be regulated by governments?"

    # Let user pick personality styles
    print(f"\nAvailable debater styles: {', '.join(AVAILABLE_STYLES)}")
    pro_style = input(f"Choose PRO style (Enter for '{DEFAULT_PRO_STYLE}'): ").strip().lower()
    if pro_style not in AVAILABLE_STYLES:
        pro_style = DEFAULT_PRO_STYLE

    con_style = input(f"Choose CON style (Enter for '{DEFAULT_CON_STYLE}'): ").strip().lower()
    if con_style not in AVAILABLE_STYLES:
        con_style = DEFAULT_CON_STYLE

    print(f"\nStarting debate on: {topic}")
    print(f"PRO style: {pro_style} | CON style: {con_style}")
    print("-" * 60)

    # Create 3 agents — same model, different personas via system prompts
    pro_agent, con_agent, judge_agent = build_agents(pro_style, con_style)

    # The controller orchestrates the agents
    controller = DebateController(topic, pro_agent, con_agent, judge_agent)
    try:
        controller.run_debate()
    except AgentError as e:
        print("\n" + "=" * 60)
        print(f"The debate was interrupted: {e}")
        print("This is usually temporary — check your connection and API key,")
        print("then run the debate again.")
        sys.exit(1)

    # Offer to save the transcript
    print("\n" + "=" * 60)
    save = input("Save transcript? (y/n): ").strip().lower()
    if save == "y":
        os.makedirs("output", exist_ok=True)
        format_choice = input("Format — (m)arkdown, (j)son, or (b)oth? [m]: ").strip().lower()
        base_name = f"debate_{topic[:30].replace(' ', '_')}"

        if format_choice in ("m", "b", ""):
            md_path = f"output/{base_name}.md"
            try:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(controller.get_transcript_text())
                print(f"Saved Markdown to {md_path}")
            except OSError as e:
                print(f"Failed to save Markdown: {e}")

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
                print(f"Saved JSON to {json_path}")
            except OSError as e:
                print(f"Failed to save JSON: {e}")


if __name__ == "__main__":
    main()
