import type { DebatePhase } from '../../types/debate';

interface DebateProgressProps {
  phase: DebatePhase | null;
}

// The full backend phase sequence, in order. The progress bar collapses these
// nine phases into the six display steps built in the component below; the
// `currentIndex` into this array is what drives which steps read as complete.
const phaseOrder: DebatePhase[] = [
  'introduction',
  'opening_pro',
  'opening_con',
  'rebuttal',
  'closing_pro',
  'closing_con',
  'verdict',
  'scoring',
  'finished',
];

export function DebateProgress({ phase }: DebateProgressProps) {
  const currentIndex = phase ? phaseOrder.indexOf(phase) : -1;

  // Simplified phase display
  const displayPhases = [
    { label: 'Introduction', completed: currentIndex >= 0 },
    { label: 'Openings', completed: currentIndex >= 2 },
    { label: 'Rebuttals', completed: currentIndex >= 3 },
    { label: 'Closings', completed: currentIndex >= 5 },
    { label: 'Verdict', completed: currentIndex >= 6 },
    { label: 'Scoring', completed: currentIndex >= 7 },
  ];

  const activePhaseIndex = displayPhases.findIndex((p, i) =>
    i === displayPhases.length - 1 ? !p.completed : !displayPhases[i + 1].completed && p.completed
  );

  return (
    <div className="flex items-center justify-center gap-2 py-2">
      {displayPhases.map((p, index) => {
        const isActive = index === activePhaseIndex || (index === 0 && currentIndex === 0);
        const isCompleted = p.completed && index < activePhaseIndex;

        return (
          <div key={p.label} className="flex items-center">
            <div
              className={`
                px-3 py-1 rounded-full text-xs font-medium transition-all
                ${isActive
                  ? 'bg-blue-500 text-white ring-2 ring-blue-300'
                  : isCompleted
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-500'
                }
              `}
            >
              {p.label}
            </div>
            {index < displayPhases.length - 1 && (
              <div className={`w-4 h-0.5 ${isCompleted ? 'bg-green-300' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
