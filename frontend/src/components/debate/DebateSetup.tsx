import { useEffect, useState } from 'react';
import { useDebateStore } from '../../stores/debateStore';
import type { StyleInfo } from '../../types/debate';

interface DebateSetupProps {
  onStart: (topic: string, proStyle: string, conStyle: string) => void;
  isLoading: boolean;
}

const styleIcons: Record<string, string> = {
  passionate: '🔥',
  aggressive: '⚔️',
  academic: '📚',
  humorous: '😄',
};

export function DebateSetup({ onStart, isLoading }: DebateSetupProps) {
  const { topic, proStyle, conStyle, availableStyles, setTopic, setProStyle, setConStyle, setAvailableStyles } = useDebateStore();
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch available styles on mount
    fetch('/api/config/styles')
      .then(res => res.json())
      .then(data => setAvailableStyles(data.styles))
      .catch(err => console.error('Failed to fetch styles:', err));
  }, [setAvailableStyles]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setLocalError('Please enter a debate topic');
      return;
    }
    setLocalError(null);
    onStart(topic.trim(), proStyle, conStyle);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">
          Multi-Agent Debate System
        </h1>
        <p className="text-gray-600">
          Watch AI agents debate any topic with different personalities
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Topic Input */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <label htmlFor="topic" className="block text-lg font-semibold text-gray-700 mb-3">
            Debate Topic
          </label>
          <input
            id="topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Should artificial intelligence be regulated by governments?"
            className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors text-lg"
            disabled={isLoading}
          />
          {localError && (
            <p className="mt-2 text-red-500 text-sm">{localError}</p>
          )}
        </div>

        {/* Style Selection */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* PRO Styles */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-green-600 mb-4 flex items-center gap-2">
              <span className="w-3 h-3 bg-green-500 rounded-full"></span>
              PRO Agent Style
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {availableStyles.map((style: StyleInfo) => (
                <StyleCard
                  key={`pro-${style.name}`}
                  style={style}
                  isSelected={proStyle === style.name}
                  onClick={() => setProStyle(style.name)}
                  disabled={isLoading}
                  colorClass="green"
                />
              ))}
            </div>
          </div>

          {/* CON Styles */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-red-600 mb-4 flex items-center gap-2">
              <span className="w-3 h-3 bg-red-500 rounded-full"></span>
              CON Agent Style
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {availableStyles.map((style: StyleInfo) => (
                <StyleCard
                  key={`con-${style.name}`}
                  style={style}
                  isSelected={conStyle === style.name}
                  onClick={() => setConStyle(style.name)}
                  disabled={isLoading}
                  colorClass="red"
                />
              ))}
            </div>
          </div>
        </div>

        {/* Start Button */}
        <div className="flex justify-center">
          <button
            type="submit"
            disabled={isLoading || !topic.trim()}
            className={`
              px-8 py-4 text-xl font-bold rounded-xl transition-all
              ${isLoading || !topic.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg hover:shadow-xl'
              }
            `}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting Debate...
              </span>
            ) : (
              'Start Debate'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

interface StyleCardProps {
  style: StyleInfo;
  isSelected: boolean;
  onClick: () => void;
  disabled: boolean;
  colorClass: 'green' | 'red';
}

function StyleCard({ style, isSelected, onClick, disabled, colorClass }: StyleCardProps) {
  const selectedBorder = colorClass === 'green' ? 'border-green-500 ring-2 ring-green-200' : 'border-red-500 ring-2 ring-red-200';
  const selectedBg = colorClass === 'green' ? 'bg-green-50' : 'bg-red-50';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`
        p-4 rounded-lg border-2 text-left transition-all
        ${isSelected
          ? `${selectedBorder} ${selectedBg}`
          : 'border-gray-200 hover:border-gray-300 bg-white'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      <div className="text-2xl mb-1">{styleIcons[style.name] || '🎭'}</div>
      <div className="font-semibold capitalize text-gray-800">{style.name}</div>
      <div className="text-xs text-gray-500 mt-1 line-clamp-2">{style.description}</div>
    </button>
  );
}
