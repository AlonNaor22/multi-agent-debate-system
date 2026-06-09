# Multi-Agent Debate System — Frontend

React + TypeScript single-page application that streams a live AI debate over WebSocket.

## Stack

| Layer | Library |
|-------|---------|
| UI framework | React 19 |
| Language | TypeScript |
| Build tool | Vite 7 |
| Styling | Tailwind CSS v4 |
| State management | Zustand 5 |

## Dev commands

```bash
npm install       # install deps
npm run dev       # start dev server at http://localhost:5173
npm run build     # type-check + production build → dist/
npm run lint      # ESLint
npm run preview   # preview the production build locally
```

## Folder structure

```
src/
  components/debate/   debate UI components (setup, chat, progress, voting)
  stores/              Zustand store (debate state + streaming actions)
  types/               shared TypeScript interfaces (DebatePhase, Speaker, …)
  App.tsx              root component — WebSocket connection lives here
  main.tsx             React entry point
```

## Environment

The dev server proxies `/api` and `/ws` to the backend. The proxy target defaults to `http://localhost:8000` and can be overridden with the `VITE_PROXY_TARGET` environment variable (set automatically in Docker Compose).
