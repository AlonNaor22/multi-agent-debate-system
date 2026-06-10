import type { DebateScores, ArgumentScore } from '../../types/debate';

interface ScoreboardProps {
  scores: DebateScores;
}

function ScoreBar({ score, barColor }: { score: number; barColor: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} rounded-full transition-all`}
          style={{ width: `${Math.max(0, Math.min(10, score)) * 10}%` }}
        />
      </div>
      <span className="w-12 text-right text-sm font-semibold text-gray-700">{score}/10</span>
    </div>
  );
}

interface SideColumnProps {
  title: string;
  args: ArgumentScore[];
  average: number;
  headerClass: string;
  barColor: string;
}

function SideColumn({ title, args, average, headerClass, barColor }: SideColumnProps) {
  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden">
      <div className={`flex items-center justify-between px-3 py-2 font-bold ${headerClass}`}>
        <span>{title}</span>
        <span className="text-sm font-medium">avg {average}/10</span>
      </div>
      <div className="divide-y divide-gray-100">
        {args.length === 0 && (
          <p className="px-3 py-3 text-sm text-gray-400 italic">No arguments scored.</p>
        )}
        {args.map((arg, index) => (
          <div key={index} className="px-3 py-3 space-y-1.5">
            <p className="text-sm font-medium text-gray-800">{arg.summary}</p>
            <ScoreBar score={arg.score} barColor={barColor} />
            <p className="text-xs text-gray-500">{arg.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Scoreboard({ scores }: ScoreboardProps) {
  const winnerLabel = scores.winner === 'TIE' ? "It's a tie" : `${scores.winner} wins`;

  return (
    <div className="rounded-lg border-2 border-indigo-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-indigo-700">Argument Scores</h2>
        <span className="rounded-full bg-indigo-600 px-3 py-1 text-sm font-bold text-white">
          {winnerLabel}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <SideColumn
          title="PRO"
          args={scores.pro_arguments}
          average={scores.pro_average}
          headerClass="bg-green-100 text-green-800"
          barColor="bg-green-500"
        />
        <SideColumn
          title="CON"
          args={scores.con_arguments}
          average={scores.con_average}
          headerClass="bg-red-100 text-red-800"
          barColor="bg-red-500"
        />
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-lg bg-green-50 p-3">
          <span className="font-semibold text-green-800">Strongest argument: </span>
          <span className="text-gray-700">{scores.strongest_argument}</span>
        </div>
        <div className="rounded-lg bg-amber-50 p-3">
          <span className="font-semibold text-amber-800">Weakest argument: </span>
          <span className="text-gray-700">{scores.weakest_argument}</span>
        </div>
      </div>
    </div>
  );
}
