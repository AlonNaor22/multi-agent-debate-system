# Multi-Agent Debate System

A multi-agent system where three AI agents powered by Claude debate a given topic. One agent argues **for** a position, another argues **against**, and a third acts as a **judge/moderator** who guides the debate and delivers a final verdict.

## How It Works

The system uses LangChain to orchestrate three separate Claude instances, each with a distinct persona defined by system prompts:

- **Pro Agent** — Passionate, persuasive. Argues in favor of the topic.
- **Con Agent** — Skeptical, analytical. Argues against the topic.
- **Judge/Moderator** — Neutral, thorough. Evaluates arguments and declares a winner.

### Debate Flow

```
Introduction → Opening Statements → Rebuttal Rounds → Closing Statements → Verdict
```

Each agent receives the full debate transcript as context on every turn, allowing them to directly respond to each other's arguments.

## Project Structure

```
├── main.py                  # Entry point — creates agents and runs debate
├── config.py                # Model settings, temperatures, round count
├── src/
│   ├── agents/
│   │   └── base_agent.py   # DebateAgent class (LangChain chain: prompt | llm)
│   ├── prompts.py           # System prompts defining agent personas
│   └── debate_controller.py # Orchestrates turn-taking and debate phases
├── requirements.txt
└── output/                  # Saved debate transcripts
```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/multi-agent-debate-system.git
   cd multi-agent-debate-system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

## Usage

```bash
python main.py
```

Enter a debate topic when prompted (or press Enter for the default topic). The debate will play out in your terminal with color-coded panels for each speaker.

## Key Concepts

- **LangChain Chains** — Each agent is a `ChatPromptTemplate | ChatAnthropic` chain
- **System Prompts as Personas** — The same model becomes three different agents through prompt engineering
- **Shared Transcript** — Agents communicate indirectly via a shared debate history managed by the controller
- **Orchestration** — The `DebateController` manages turn-taking and phase transitions (state machine pattern)

## Technologies

- Python 3.9+
- LangChain + langchain-anthropic
- Anthropic Claude (claude-sonnet-4-5)
- Rich (terminal formatting)
