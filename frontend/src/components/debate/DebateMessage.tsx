import type { DebateMessage as DebateMessageType } from '../../types/debate';

interface DebateMessageProps {
  message: DebateMessageType;
}

const speakerConfig = {
  PRO: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-500 text-white',
    align: 'self-start',
  },
  CON: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-500 text-white',
    align: 'self-end',
  },
  MODERATOR: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-500 text-white',
    align: 'self-center',
  },
  JUDGE: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-300',
    badge: 'bg-yellow-500 text-white',
    align: 'self-center',
  },
  AUDIENCE: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    badge: 'bg-purple-500 text-white',
    align: 'self-center',
  },
  SCORING: {
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    badge: 'bg-indigo-500 text-white',
    align: 'self-center',
  },
};

export function DebateMessage({ message }: DebateMessageProps) {
  const config = speakerConfig[message.speaker];
  const isCentered = ['MODERATOR', 'JUDGE', 'AUDIENCE', 'SCORING'].includes(message.speaker);

  return (
    <div className={`flex ${isCentered ? 'justify-center' : message.speaker === 'PRO' ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`
          max-w-2xl p-4 rounded-lg border-2
          ${config.bg} ${config.border}
          ${isCentered ? 'w-full max-w-3xl' : 'max-w-xl'}
        `}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-1 rounded text-sm font-bold ${config.badge}`}>
            {message.speaker}
          </span>
          {message.label && (
            <span className="text-sm text-gray-600 font-medium">
              {message.label}
            </span>
          )}
        </div>
        <div className="text-gray-800 whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
      </div>
    </div>
  );
}
