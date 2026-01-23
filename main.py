import os
from dotenv import load_dotenv
from src.agents.base_agent import DebateAgent
from src.debate_controller import DebateController
from src.prompts import PRO_AGENT_PROMPT, CON_AGENT_PROMPT, JUDGE_AGENT_PROMPT
from config import TEMPERATURE_DEBATERS, TEMPERATURE_JUDGE

# Load the API key from .env file into environment variables
load_dotenv()


def main():
    print("=" * 60)
    print("        MULTI-AGENT DEBATE SYSTEM")
    print("=" * 60)

    topic = input("\nEnter debate topic (or press Enter for default): ").strip()
    if not topic:
        topic = "Should artificial intelligence be regulated by governments?"

    print(f"\nStarting debate on: {topic}")
    print("-" * 60)

    # Create 3 agents — same model, different personas
    pro_agent = DebateAgent(
        name="Pro",
        role="arguing FOR the topic",
        system_prompt=PRO_AGENT_PROMPT,
        temperature=TEMPERATURE_DEBATERS
    )

    con_agent = DebateAgent(
        name="Con",
        role="arguing AGAINST the topic",
        system_prompt=CON_AGENT_PROMPT,
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
        filename = f"output/debate_{topic[:30].replace(' ', '_')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(controller.get_transcript_text())
        print(f"Saved to {filename}")


if __name__ == "__main__":
    main()
