import type { ReactNode } from 'react';
import type { Speaker } from '../../types/debate';

// Per-speaker bubble colours (background, border, and badge). One source of
// truth shared by the committed-message bubble (DebateMessage) and the live
// streaming bubble (DebateChat) so the two can't drift apart.
const speakerStyles: Record<Speaker, { bg: string; border: string; badge: string }> = {
  PRO: { bg: 'bg-green-50', border: 'border-green-200', badge: 'bg-green-500 text-white' },
  CON: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white' },
  MODERATOR: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-blue-500 text-white' },
  JUDGE: { bg: 'bg-yellow-50', border: 'border-yellow-300', badge: 'bg-yellow-500 text-white' },
  AUDIENCE: { bg: 'bg-purple-50', border: 'border-purple-200', badge: 'bg-purple-500 text-white' },
  SCORING: { bg: 'bg-indigo-50', border: 'border-indigo-200', badge: 'bg-indigo-500 text-white' },
};

// PRO sits on the left and CON on the right; the moderator, judge, audience, and
// scoring messages are centered and rendered wider.
const CENTERED_SPEAKERS: Speaker[] = ['MODERATOR', 'JUDGE', 'AUDIENCE', 'SCORING'];

interface SpeakerBubbleProps {
  speaker: Speaker;
  /** Optional node shown to the right of the speaker badge — e.g. a turn label or a "typing…" hint. */
  headerExtra?: ReactNode;
  /** The bubble body (message text, or a streaming placeholder). */
  children: ReactNode;
}

/**
 * The shared chat-bubble chrome for a single speaker: the row alignment, the
 * coloured bubble, and the speaker badge. Callers supply whatever goes next to
 * the badge (`headerExtra`) and the body (`children`).
 */
export function SpeakerBubble({ speaker, headerExtra, children }: SpeakerBubbleProps) {
  const style = speakerStyles[speaker];
  const isCentered = CENTERED_SPEAKERS.includes(speaker);
  const rowAlign = isCentered ? 'justify-center' : speaker === 'PRO' ? 'justify-start' : 'justify-end';

  return (
    <div className={`flex ${rowAlign}`}>
      <div
        className={`
          max-w-2xl p-4 rounded-lg border-2
          ${style.bg} ${style.border}
          ${isCentered ? 'w-full max-w-3xl' : 'max-w-xl'}
        `}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-1 rounded text-sm font-bold ${style.badge}`}>
            {speaker}
          </span>
          {headerExtra}
        </div>
        <div className="text-gray-800 whitespace-pre-wrap leading-relaxed">
          {children}
        </div>
      </div>
    </div>
  );
}
