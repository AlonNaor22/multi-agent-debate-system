import { useEffect, useRef } from 'react';
import { useDebateStore } from '../../stores/debateStore';
import { DebateMessage } from './DebateMessage';
import { DebateProgress } from './DebateProgress';
import { TypingIndicator } from './TypingIndicator';
import { VotingModal } from './VotingModal';

interface DebateChatProps {
  onVote: (vote: 'PRO' | 'CON' | 'TIE') => void;
  onNewDebate: () => void;
}

export function DebateChat({ onVote, onNewDebate }: DebateChatProps) {
  const { topic, proStyle, conStyle, phase, messages, isTyping, currentSpeaker, isWaitingForVote } = useDebateStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

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

          {isTyping && currentSpeaker && (
            <div className={`flex ${
              currentSpeaker === 'PRO' ? 'justify-start' :
              currentSpeaker === 'CON' ? 'justify-end' :
              'justify-center'
            }`}>
              <TypingIndicator speaker={currentSpeaker} />
            </div>
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
