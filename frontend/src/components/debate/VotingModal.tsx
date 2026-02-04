interface VotingModalProps {
  onVote: (vote: 'PRO' | 'CON' | 'TIE') => void;
}

export function VotingModal({ onVote }: VotingModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 animate-in fade-in zoom-in duration-200">
        <h2 className="text-2xl font-bold text-center mb-2 text-gray-800">
          Audience Vote
        </h2>
        <p className="text-gray-600 text-center mb-6">
          Who is winning the debate so far?
        </p>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => onVote('PRO')}
            className="w-full py-4 px-6 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl">👍</span>
            PRO is winning
          </button>
          <button
            onClick={() => onVote('CON')}
            className="w-full py-4 px-6 bg-red-500 hover:bg-red-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl">👎</span>
            CON is winning
          </button>
          <button
            onClick={() => onVote('TIE')}
            className="w-full py-4 px-6 bg-gray-500 hover:bg-gray-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl">🤝</span>
            It's a tie
          </button>
        </div>
      </div>
    </div>
  );
}
