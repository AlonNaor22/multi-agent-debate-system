import type { DebatePhase } from '../../types/debate';

interface DebateProgressProps {
  phase: DebatePhase | null;
}

const phases: { key: DebatePhase; label: string }[] = [
  { key: 'introduction', label: 'Intro' },
  { key: 'opening_pro', label: 'Opening' },
  { key: 'opening_con', label: 'Opening' },
  { key: 'rebuttal', label: 'Rebuttals' },
  { key: 'closing_pro', label: 'Closing' },
  { key: 'closing_con', label: 'Closing' },
  { key: 'verdict', label: 'Verdict' },
  { key: 'scoring', label: 'Scoring' },
  { key: 'finished', label: 'Done' },
];

const phaseOrder = phases.map(p => p.key);

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
