import { useEffect, useState } from 'react';
import type {
  PastDebateSummary,
  PastDebateDetail,
  Speaker,
  DebatePhase,
} from '../../types/debate';
import { DebateMessage } from './DebateMessage';
import { Scoreboard } from './Scoreboard';

interface PastDebatesProps {
  /** Return to the setup screen to start a new debate. */
  onBack: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const winnerBadge: Record<string, string> = {
  PRO: 'bg-green-100 text-green-700',
  CON: 'bg-red-100 text-red-700',
  TIE: 'bg-gray-100 text-gray-600',
};

function WinnerTag({ winner }: { winner: string | null }) {
  if (!winner) return null;
  const label = winner === 'TIE' ? 'Tie' : `${winner} won`;
  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${winnerBadge[winner] ?? winnerBadge.TIE}`}>
      {label}
    </span>
  );
}

export function PastDebates({ onBack }: PastDebatesProps) {
  const [debates, setDebates] = useState<PastDebateSummary[] | null>(null);
  const [selected, setSelected] = useState<PastDebateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let active = true;
    fetch('/api/debates')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load past debates');
        return res.json();
      })
      .then((data: PastDebateSummary[]) => {
        if (active) setDebates(data);
      })
      .catch(() => {
        if (active) setError('Could not load past debates.');
      });
    return () => {
      active = false;
    };
  }, []);

  const openDetail = (id: string) => {
    setLoadingDetail(true);
    setError(null);
    fetch(`/api/debates/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load debate');
        return res.json();
      })
      .then((data: PastDebateDetail) => setSelected(data))
      .catch(() => setError('Could not load that debate.'))
      .finally(() => setLoadingDetail(false));
  };

  // ---- Detail view ---------------------------------------------------------
  if (selected) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button
          onClick={() => setSelected(null)}
          className="mb-4 text-sm text-blue-600 hover:text-blue-700 hover:underline"
        >
          ← Back to list
        </button>

        <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-2xl font-bold text-gray-800">{selected.topic}</h1>
            <WinnerTag winner={selected.winner} />
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm">
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded font-medium capitalize">
              PRO: {selected.pro_style}
            </span>
            <span className="text-gray-400">vs</span>
            <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium capitalize">
              CON: {selected.con_style}
            </span>
            <span className="ml-auto text-gray-500">{formatDate(selected.completed_at)}</span>
          </div>
        </div>

        <div className="space-y-4">
          {selected.transcript.map((entry, index) => (
            <DebateMessage
              key={index}
              message={{
                speaker: entry.speaker as Speaker,
                content: entry.content,
                phase: entry.phase as DebatePhase,
              }}
            />
          ))}
          {selected.argument_scores && <Scoreboard scores={selected.argument_scores} />}
        </div>
      </div>
    );
  }

  // ---- List view -----------------------------------------------------------
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Past Debates</h1>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors"
        >
          + New Debate
        </button>
      </div>

      {error && <p className="mb-4 text-red-500">{error}</p>}

      {debates === null && !error && <p className="text-gray-500">Loading…</p>}

      {debates && debates.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-10 text-center text-gray-500">
          No debates yet — start one and it'll show up here.
        </div>
      )}

      {debates && debates.length > 0 && (
        <ul className="space-y-3">
          {debates.map((d) => (
            <li key={d.id}>
              <button
                onClick={() => openDetail(d.id)}
                disabled={loadingDetail}
                className="w-full text-left bg-white rounded-xl shadow-sm border p-4 hover:border-blue-300 hover:shadow transition-all disabled:opacity-60"
              >
                <div className="flex items-start justify-between gap-4">
                  <h2 className="font-semibold text-gray-800">{d.topic}</h2>
                  <WinnerTag winner={d.winner} />
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                  <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded capitalize">
                    PRO: {d.pro_style}
                  </span>
                  <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded capitalize">
                    CON: {d.con_style}
                  </span>
                  <span>· {d.message_count} messages</span>
                  <span className="ml-auto">{formatDate(d.completed_at)}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
