import type { Vote } from '../../types/debate';
import { strings } from '../../constants/strings';

interface VotingModalProps {
  onVote: (vote: Vote) => void;
}

export function VotingModal({ onVote }: VotingModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="voting-modal-title"
        className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 animate-in fade-in zoom-in duration-200"
      >
        <h2 id="voting-modal-title" className="text-2xl font-bold text-center mb-2 text-gray-800">
          {strings.voting.title}
        </h2>
        <p className="text-gray-600 text-center mb-6">
          {strings.voting.prompt}
        </p>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => onVote('PRO')}
            className="w-full py-4 px-6 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl" aria-hidden="true">👍</span>
            {strings.voting.proWinning}
          </button>
          <button
            onClick={() => onVote('CON')}
            className="w-full py-4 px-6 bg-red-500 hover:bg-red-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl" aria-hidden="true">👎</span>
            {strings.voting.conWinning}
          </button>
          <button
            onClick={() => onVote('TIE')}
            className="w-full py-4 px-6 bg-gray-500 hover:bg-gray-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl" aria-hidden="true">🤝</span>
            {strings.voting.tie}
          </button>
        </div>
      </div>
    </div>
  );
}
