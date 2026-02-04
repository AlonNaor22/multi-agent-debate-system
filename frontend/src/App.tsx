import { useState, useCallback, useRef } from 'react';
import { useDebateStore } from './stores/debateStore';
import { DebateSetup, DebateChat } from './components/debate';

type Vote = 'PRO' | 'CON' | 'TIE';

function App() {
  const {
    isDebating,
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
  } = useDebateStore();
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

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
        throw new Error('Failed to create debate');
      }

      const data = await response.json();
      const newDebateId = data.debate_id;

      // Connect WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/debates/${newDebateId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsLoading(false);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWSMessage(message, topic, proStyle, conStyle);
      };

      ws.onerror = () => {
        setError('WebSocket connection failed');
        setIsLoading(false);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setIsLoading(false);
    }
  }, [setError]);

  const handleWSMessage = useCallback((
    message: { type: string; debate_id: string; data: Record<string, unknown> },
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
        setPhase(data.phase as 'introduction' | 'opening_pro' | 'opening_con' | 'rebuttal' | 'closing_pro' | 'closing_con' | 'verdict' | 'scoring' | 'finished');
        break;

      case 'message_start':
        startStreaming(data.speaker as 'PRO' | 'CON' | 'MODERATOR' | 'JUDGE' | 'AUDIENCE' | 'SCORING');
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

      case 'debate_complete':
        endDebate();
        break;

      case 'error':
        setError(data.message as string);
        break;
    }
  }, [startDebate, setPhase, startStreaming, appendStreamingChunk, finishStreaming, setIsWaitingForVote, addMessage, endDebate, setError]);

  const handleVote = useCallback((vote: Vote) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'vote', vote }));
      setIsWaitingForVote(false);
    }
  }, [setIsWaitingForVote]);

  const handleNewDebate = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    reset();
  }, [reset]);

  // Show setup page if not debating and phase is not finished
  // Show chat if debating OR if debate has finished (so user can review)
  const showChat = isDebating || currentPhase === 'finished';

  return (
    <div className="min-h-screen bg-gray-100">
      {showChat ? (
        <DebateChat onVote={handleVote} onNewDebate={handleNewDebate} />
      ) : (
        <DebateSetup onStart={handleStart} isLoading={isLoading} />
      )}
    </div>
  );
}

export default App;
