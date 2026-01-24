# Multi-Agent Debate System

A multi-agent system where three AI agents powered by Claude debate a given topic. One agent argues **for** a position, another argues **against**, and a third acts as a **judge/moderator** who guides the debate and delivers a final verdict.

## How It Works

The system uses LangChain to orchestrate three separate Claude instances, each with a distinct persona defined by system prompts:

- **Pro Agent** — Argues in favor of the topic.
- **Con Agent** — Argues against the topic.
- **Judge/Moderator** — Neutral, thorough. Evaluates arguments and declares a winner.

### Personality Styles

Each debater can be configured with a different personality style:

| Style | Description |
|-------|-------------|
| **Passionate** | Persuasive, uses rhetorical techniques, acknowledges opponents |
| **Aggressive** | Confrontational, attacks logic directly, never concedes |
| **Academic** | Formal, cites research and data, uses logical frameworks |
| **Humorous** | Witty, uses satire and analogies, entertains while persuading |

### Debate Flow

```
Introduction → Opening Statements → Rebuttal Rounds → Audience Vote → Closing Statements → Verdict → Argument Scoring
```

Each agent receives the full debate transcript as context on every turn, allowing them to directly respond to each other's arguments.

## Features

- **Multiple personality styles** — Choose different debate styles for Pro and Con agents
- **Argument strength scoring** — Judge scores each individual argument after the debate
- **Audience participation** — Vote on who's winning between rounds (agents react to it)
- **Timed responses** — See how long each agent takes to respond
- **Dual export** — Save transcripts as Markdown, JSON, or both

## Project Structure

```
├── main.py                  # Entry point — creates agents and runs debate
├── config.py                # Model settings, temperatures, styles, round count
├── src/
│   ├── agents/
│   │   └── base_agent.py   # DebateAgent class (LangChain chain: prompt | llm)
│   ├── prompts.py           # System prompts with multiple personality styles
│   └── debate_controller.py # Orchestrates turn-taking, timing, scoring, and voting
├── requirements.txt
└── output/                  # Saved debate transcripts (Markdown and/or JSON)
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

You'll be prompted to:
1. Enter a debate topic (or press Enter for the default)
2. Choose a personality style for the Pro agent
3. Choose a personality style for the Con agent

The debate plays out in your terminal with color-coded panels, response times, and an audience vote between rounds.

## Key Concepts

- **LangChain Chains** — Each agent is a `ChatPromptTemplate | ChatAnthropic` chain
- **System Prompts as Personas** — The same model becomes different agents through prompt engineering
- **Shared Transcript** — Agents communicate indirectly via a shared debate history managed by the controller
- **Orchestration** — The `DebateController` manages turn-taking and phase transitions (state machine pattern)
- **Chain Reuse** — The same judge chain is invoked multiple times with different instructions (verdict, scoring)

## Technologies

- Python 3.9+
- LangChain + langchain-anthropic
- Anthropic Claude (claude-sonnet-4-5)
- Rich (terminal formatting)
