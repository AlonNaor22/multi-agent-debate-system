import type { Speaker } from '../../types/debate';

interface TypingIndicatorProps {
  speaker: Speaker;
}

const speakerColors: Record<Speaker, string> = {
  PRO: 'bg-green-100 text-green-800',
  CON: 'bg-red-100 text-red-800',
  MODERATOR: 'bg-blue-100 text-blue-800',
  JUDGE: 'bg-yellow-100 text-yellow-800',
  AUDIENCE: 'bg-purple-100 text-purple-800',
  SCORING: 'bg-indigo-100 text-indigo-800',
};

export function TypingIndicator({ speaker }: TypingIndicatorProps) {
  const colorClass = speakerColors[speaker];

  return (
    <div className="flex items-center gap-2 p-3 rounded-lg max-w-xs animate-pulse bg-gray-100">
      <span className={`px-2 py-1 rounded text-sm font-medium ${colorClass}`}>
        {speaker}
      </span>
      <span className="text-gray-600">is thinking...</span>
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
}
