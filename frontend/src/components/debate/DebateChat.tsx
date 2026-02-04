import { useEffect, useRef } from 'react';
import { useDebateStore } from '../../stores/debateStore';
import { DebateMessage } from './DebateMessage';
import { DebateProgress } from './DebateProgress';
import { VotingModal } from './VotingModal';

interface DebateChatProps {
  onVote: (vote: 'PRO' | 'CON' | 'TIE') => void;
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
              <span className="text-gray-400">vs</span>
              <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium capitalize">
                CON: {conStyle}
              </span>
            </div>
          </div>
          <DebateProgress phase={phase} />
        </div>
      </header>

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

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Footer */}
      {isFinished && (
        <footer className="bg-white border-t p-4">
          <div className="max-w-4xl mx-auto flex justify-center">
            <button
              onClick={onNewDebate}
              className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-colors"
            >
              Start New Debate
            </button>
          </div>
        </footer>
      )}

      {/* Voting Modal */}
      {isWaitingForVote && <VotingModal onVote={onVote} />}
    </div>
  );
}

// Streaming message component - shows content as it's being typed
interface StreamingMessageProps {
  speaker: 'PRO' | 'CON' | 'MODERATOR' | 'JUDGE' | 'AUDIENCE' | 'SCORING';
  content: string;
}

const speakerConfig = {
  PRO: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-500 text-white',
  },
  CON: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-500 text-white',
  },
  MODERATOR: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-500 text-white',
  },
  JUDGE: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-300',
    badge: 'bg-yellow-500 text-white',
  },
  AUDIENCE: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    badge: 'bg-purple-500 text-white',
  },
  SCORING: {
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    badge: 'bg-indigo-500 text-white',
  },
};

function StreamingMessage({ speaker, content }: StreamingMessageProps) {
  const config = speakerConfig[speaker];
  const isCentered = ['MODERATOR', 'JUDGE', 'AUDIENCE', 'SCORING'].includes(speaker);

  return (
    <div className={`flex ${isCentered ? 'justify-center' : speaker === 'PRO' ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`
          max-w-2xl p-4 rounded-lg border-2
          ${config.bg} ${config.border}
          ${isCentered ? 'w-full max-w-3xl' : 'max-w-xl'}
        `}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-1 rounded text-sm font-bold ${config.badge}`}>
            {speaker}
          </span>
          <span className="text-sm text-gray-500 italic">typing...</span>
        </div>
        <div className="text-gray-800 whitespace-pre-wrap leading-relaxed">
          {content || (
            <span className="inline-flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          )}
          <span className="animate-pulse">|</span>
        </div>
      </div>
    </div>
  );
}
