import { useState, useCallback, useRef } from 'react';
import { useDebateStore } from './stores/debateStore';
import { DebateSetup, DebateChat, PastDebates } from './components/debate';
import { strings } from './constants/strings';
import type { DebateScores, DebatePhase, Speaker, WSMessage, Vote } from './types/debate';

function App() {
  const {
    isDebating,
    error,
    reset,
    setError,
    startDebate,
    setPhase,
    setIsWaitingForVote,
    endDebate,
    phase: currentPhase,
    startStreaming,
    appendStreamingChunk,
    finishStreaming,
    addMessage,
    setScores,
  } = useDebateStore();
  const [isLoading, setIsLoading] = useState(false);
  const [view, setView] = useState<'setup' | 'history'>('setup');
  const wsRef = useRef<WebSocket | null>(null);

  // Defined before handleStart so it can be a stable dependency of it. Every
  // dependency below is a Zustand action (stable identity), so this callback
  // never changes — but listing them keeps react-hooks/exhaustive-deps honest.
  const handleWSMessage = useCallback((
    message: WSMessage,
    topic: string,
    proStyle: string,
    conStyle: string
  ) => {
    const { type, data } = message;

    switch (type) {
      case 'debate_started':
        startDebate(message.debate_id, topic, proStyle, conStyle);
        break;

      case 'phase_change':
        setPhase(data.phase as DebatePhase);
        break;

      case 'message_start':
        startStreaming(data.speaker as Speaker);
        break;

      case 'message_chunk':
        appendStreamingChunk(data.chunk as string);
        break;

      case 'message_complete':
        finishStreaming(data.label as string | undefined);
        break;

      case 'vote_required':
        setIsWaitingForVote(true);
        break;

      case 'vote_received': {
        const store = useDebateStore.getState();
        setIsWaitingForVote(false);
        addMessage({
          speaker: 'AUDIENCE',
          content: data.message as string,
          phase: store.phase || 'rebuttal',
        });
        break;
      }

      case 'argument_scores':
        setScores(data.scores as DebateScores);
        break;

      case 'debate_complete':
        endDebate();
        break;

      case 'error':
        setError(data.message as string);
        break;
    }
  }, [startDebate, setPhase, startStreaming, appendStreamingChunk, finishStreaming, setIsWaitingForVote, addMessage, setScores, endDebate, setError]);

  const handleStart = useCallback(async (topic: string, proStyle: string, conStyle: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // Create debate via REST API
      const response = await fetch('/api/debates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          pro_style: proStyle,
          con_style: conStyle,
        }),
      });

      if (!response.ok) {
        throw new Error(strings.errors.createDebate);
      }

      const data = await response.json();
      const newDebateId = data.debate_id;

      // Connect WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/debates/${newDebateId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsLoading(false);
      };

      ws.onmessage = (event) => {
        let message: WSMessage;
        try {
          message = JSON.parse(event.data);
        } catch (err) {
          console.error('Failed to parse WebSocket message', err);
          return;
        }
        handleWSMessage(message, topic, proStyle, conStyle);
      };

      ws.onerror = () => {
        setError(strings.errors.websocket);
        setIsLoading(false);
      };

      ws.onclose = () => {
        if (useDebateStore.getState().phase !== 'finished') {
          setError(strings.errors.connectionLost);
          setIsLoading(false);
        }
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : strings.errors.generic);
      setIsLoading(false);
    }
  }, [setError, handleWSMessage]);

  const handleVote = useCallback((vote: Vote) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'vote', vote }));
      setIsWaitingForVote(false);
    }
  }, [setIsWaitingForVote]);

  const handleNewDebate = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    reset();
  }, [reset]);

  // Show setup page if not debating and phase is not finished.
  // Show chat if debating, if the debate has finished (so the user can review),
  // or if an error occurred (so the error banner + "New Debate" reset are shown
  // instead of silently dropping back to setup and losing the message).
  const showChat = isDebating || currentPhase === 'finished' || error !== null;

  return (
    <div className="min-h-screen bg-gray-100">
      {showChat ? (
        <DebateChat onVote={handleVote} onNewDebate={handleNewDebate} />
      ) : view === 'history' ? (
        <PastDebates onBack={() => setView('setup')} />
      ) : (
        <DebateSetup
          onStart={handleStart}
          isLoading={isLoading}
          onViewHistory={() => setView('history')}
        />
      )}
    </div>
  );
}

export default App;
