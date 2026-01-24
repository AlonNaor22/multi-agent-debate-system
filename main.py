import os
import json
from dotenv import load_dotenv
from src.agents.base_agent import DebateAgent
from src.debate_controller import DebateController
from src.prompts import PRO_STYLES, CON_STYLES, JUDGE_AGENT_PROMPT
from config import TEMPERATURE_DEBATERS, TEMPERATURE_JUDGE, AVAILABLE_STYLES, DEFAULT_PRO_STYLE, DEFAULT_CON_STYLE

# Load the API key from .env file into environment variables
load_dotenv()


def main():
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
    pro_agent = DebateAgent(
        name="Pro",
        role="arguing FOR the topic",
        system_prompt=PRO_STYLES[pro_style],
        temperature=TEMPERATURE_DEBATERS
    )

    con_agent = DebateAgent(
        name="Con",
        role="arguing AGAINST the topic",
        system_prompt=CON_STYLES[con_style],
        temperature=TEMPERATURE_DEBATERS
    )

    judge_agent = DebateAgent(
        name="Judge",
        role="moderator and judge",
        system_prompt=JUDGE_AGENT_PROMPT,
        temperature=TEMPERATURE_JUDGE
    )

    # The controller orchestrates the agents
    controller = DebateController(topic, pro_agent, con_agent, judge_agent)
    controller.run_debate()

    # Offer to save the transcript
    print("\n" + "=" * 60)
    save = input("Save transcript? (y/n): ").strip().lower()
    if save == "y":
        os.makedirs("output", exist_ok=True)
        format_choice = input("Format — (m)arkdown, (j)son, or (b)oth? [m]: ").strip().lower()
        base_name = f"debate_{topic[:30].replace(' ', '_')}"

        if format_choice in ("m", "b", ""):
            md_path = f"output/{base_name}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(controller.get_transcript_text())
            print(f"Saved Markdown to {md_path}")

        if format_choice in ("j", "b"):
            json_path = f"output/{base_name}.json"
            debate_data = {
                "topic": topic,
                "pro_style": pro_style,
                "con_style": con_style,
                "transcript": controller.transcript,
                "argument_scores": controller.argument_scores
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(debate_data, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON to {json_path}")


if __name__ == "__main__":
    main()
