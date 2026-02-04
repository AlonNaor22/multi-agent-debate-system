# Multi-Agent Debate System

A multi-agent system where AI agents powered by Claude debate any topic. Features a React web UI with real-time streaming, audience voting, and argument scoring.

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Anthropic API key

### 1. Clone and setup
```bash
git clone https://github.com/AlonNaor22/multi-agent-debate-system.git
cd multi-agent-debate-system

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure API key
Create a `.env` file in the root directory:
```
ANTHROPIC_API_KEY=your-api-key-here
```

### 3. Run the app
Open two terminals:

**Terminal 1 - Backend:**
```bash
uvicorn api.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 4. Open the app
Go to **http://localhost:5173** in your browser.

---

## How It Works

The system uses LangChain to orchestrate three separate Claude instances, each with a distinct persona:

- **Pro Agent** — Argues in favor of the topic
- **Con Agent** — Argues against the topic
- **Judge/Moderator** — Evaluates arguments and declares a winner

### Debate Flow

```
Introduction → Opening Statements → Rebuttals → Audience Vote → Closing Statements → Verdict → Scoring
```

Messages stream in real-time like ChatGPT, and you can vote on who's winning mid-debate.

## Features

- **Web UI** — React frontend with chat-style interface
- **Live streaming** — Watch responses appear character-by-character
- **Multiple personality styles** — Passionate, Aggressive, Academic, or Humorous
- **Audience voting** — Vote on who's winning between rounds
- **Argument scoring** — Judge scores each individual argument
- **Color-coded speakers** — PRO (green), CON (red), Judge (yellow), Moderator (blue)

### Personality Styles

| Style | Description |
|-------|-------------|
| **Passionate** | Persuasive, uses rhetorical techniques, acknowledges opponents |
| **Aggressive** | Confrontational, attacks logic directly, never concedes |
| **Academic** | Formal, cites research and data, uses logical frameworks |
| **Humorous** | Witty, uses satire and analogies, entertains while persuading |

## Project Structure

```
├── api/                         # FastAPI backend
│   ├── main.py                  # API entry point
│   ├── routes/
│   │   ├── debates.py           # REST endpoints
│   │   └── websocket.py         # WebSocket streaming
│   ├── schemas/
│   │   └── debate.py            # Pydantic models
│   └── services/
│       └── debate_service.py    # Debate orchestration
│
├── frontend/                    # React app
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/debate/   # UI components
│   │   ├── stores/              # Zustand state
│   │   └── types/               # TypeScript types
│   └── package.json
│
├── src/                         # Core debate logic
│   ├── agents/
│   │   └── base_agent.py        # DebateAgent class
│   ├── prompts.py               # Personality system prompts
│   └── debate_controller.py     # CLI orchestration
│
├── main.py                      # CLI entry point
├── config.py                    # Model settings
└── requirements.txt
```

## CLI Mode (Alternative)

You can also run debates in the terminal without the web UI:

```bash
python main.py
```

## Technologies

- **Backend:** Python, FastAPI, LangChain, Anthropic Claude
- **Frontend:** React, TypeScript, Vite, TailwindCSS, Zustand
- **Real-time:** WebSocket streaming

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/debates` | POST | Create a new debate |
| `/api/config/styles` | GET | Get available personality styles |
| `/ws/debates/{id}` | WS | WebSocket for real-time streaming |
