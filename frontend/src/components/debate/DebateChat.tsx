import { useEffect, useRef } from 'react';
import type { Speaker, Vote } from '../../types/debate';
import { useDebateStore } from '../../stores/debateStore';
import { strings } from '../../constants/strings';
import { DebateMessage } from './DebateMessage';
import { DebateProgress } from './DebateProgress';
import { VotingModal } from './VotingModal';
import { Scoreboard } from './Scoreboard';
import { SpeakerBubble } from './SpeakerBubble';

interface DebateChatProps {
  onVote: (vote: Vote) => void;
  onNewDebate: () => void;
}

export function DebateChat({ onVote, onNewDebate }: DebateChatProps) {
  const {
    topic,
    proStyle,
    conStyle,
    phase,
    messages,
    isWaitingForVote,
    streamingContent,
    streamingSpeaker,
    scores,
    error,
  } = useDebateStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const isFinished = phase === 'finished';

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b shadow-sm p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-xl font-bold text-gray-800 truncate flex-1 mr-4">
              {topic}
            </h1>
            <div className="flex items-center gap-2 text-sm">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded font-medium capitalize">
                PRO: {proStyle}
              </span>
              <span className="text-gray-400">{strings.common.versus}</span>
              <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium capitalize">
                CON: {conStyle}
              </span>
            </div>
          </div>
          <DebateProgress phase={phase} />
        </div>
      </header>

      {/* Error banner — a mid-debate failure is recoverable: surface the message
          here and (via the footer) always offer a way out. Pinned below the
          header so it stays visible regardless of scroll position. */}
      {error && (
        <div role="alert" className="bg-red-50 border-b border-red-200 p-4">
          <div className="max-w-4xl mx-auto">
            <p className="font-semibold text-red-800">{strings.chat.errorTitle}</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <DebateMessage key={index} message={message} />
          ))}

          {/* Show streaming content as it arrives */}
          {streamingSpeaker && (
            <StreamingMessage
              speaker={streamingSpeaker}
              content={streamingContent}
            />
          )}

          {/* Final structured scoreboard from the judge */}
          {scores && <Scoreboard scores={scores} />}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Footer — offer "New Debate" both when the debate finishes normally and
          when it errors out, so an error is never a dead-end. */}
      {(isFinished || error) && (
        <footer className="bg-white border-t p-4">
          <div className="max-w-4xl mx-auto flex justify-center">
            <button
              onClick={onNewDebate}
              className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-colors"
            >
              {strings.chat.newDebate}
            </button>
          </div>
        </footer>
      )}

      {/* Voting Modal */}
      {isWaitingForVote && <VotingModal onVote={onVote} />}
    </div>
  );
}

// Streaming message component - shows content as it's being typed, reusing the
// shared SpeakerBubble chrome with a "typing…" hint and a blinking cursor.
interface StreamingMessageProps {
  speaker: Speaker;
  content: string;
}

function StreamingMessage({ speaker, content }: StreamingMessageProps) {
  return (
    <SpeakerBubble
      speaker={speaker}
      headerExtra={<span className="text-sm text-gray-500 italic">{strings.chat.typing}</span>}
    >
      {content || (
        <span className="inline-flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </span>
      )}
      <span className="animate-pulse">|</span>
    </SpeakerBubble>
  );
}
