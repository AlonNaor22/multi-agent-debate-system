import type { DebatePhase } from '../../types/debate';
import { strings } from '../../constants/strings';

interface DebateProgressProps {
  phase: DebatePhase | null;
}

// The full backend phase sequence, in order. `currentIndex` into this array
// drives which display step below is active.
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

// The six display steps the bar collapses the nine phases into. Each step is
// active from its startIndex in phaseOrder until the next step begins.
const displaySteps = [
  { label: strings.progress.introduction, startIndex: 0 }, // introduction
  { label: strings.progress.openings, startIndex: 1 },     // opening_pro/_con
  { label: strings.progress.rebuttals, startIndex: 3 },    // rebuttal (incl. audience vote)
  { label: strings.progress.closings, startIndex: 4 },     // closing_pro/_con
  { label: strings.progress.verdict, startIndex: 6 },      // verdict
  { label: strings.progress.scoring, startIndex: 7 },      // scoring
];

export function DebateProgress({ phase }: DebateProgressProps) {
  const currentIndex = phase ? phaseOrder.indexOf(phase) : -1;
  const isFinished = phase === 'finished';

  // The step the debate is currently in: the last one whose range has started.
  // None is active before the first phase_change arrives, and none once
  // finished — at that point every step reads as completed instead.
  let activeStepIndex = -1;
  if (!isFinished) {
    for (let i = 0; i < displaySteps.length; i++) {
      if (currentIndex >= displaySteps[i].startIndex) activeStepIndex = i;
    }
  }

  return (
    <div className="flex items-center justify-center gap-2 py-2">
      {displaySteps.map((step, index) => {
        const isActive = index === activeStepIndex;
        const isCompleted = isFinished || index < activeStepIndex;

        return (
          <div key={step.label} className="flex items-center">
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
              {step.label}
            </div>
            {index < displaySteps.length - 1 && (
              <div className={`w-4 h-0.5 ${isCompleted ? 'bg-green-300' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
