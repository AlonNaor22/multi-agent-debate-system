export type DebatePhase =
  | 'introduction'
  | 'opening_pro'
  | 'opening_con'
  | 'rebuttal'
  | 'closing_pro'
  | 'closing_con'
  | 'verdict'
  | 'scoring'
  | 'finished';

export type Speaker = 'PRO' | 'CON' | 'MODERATOR' | 'JUDGE' | 'AUDIENCE' | 'SCORING';

export interface StyleInfo {
  name: string;
  description: string;
}

export interface DebateMessage {
  speaker: Speaker;
  content: string;
  label?: string;
  phase: DebatePhase;
}

// Structured judge scoring (mirrors src/scoring.py DebateScores).
export interface ArgumentScore {
  summary: string;
  score: number;
  reason: string;
}

export interface DebateScores {
  pro_arguments: ArgumentScore[];
  con_arguments: ArgumentScore[];
  pro_average: number;
  con_average: number;
  winner: 'PRO' | 'CON' | 'TIE';
  strongest_argument: string;
  weakest_argument: string;
}

export interface DebateConfig {
  topic: string;
  proStyle: string;
  conStyle: string;
}

export interface DebateSession {
  debateId: string;
  topic: string;
  proStyle: string;
  conStyle: string;
}

// WebSocket message types
export type WSMessageType =
  | 'debate_started'
  | 'phase_change'
  | 'message_start'
  | 'message_chunk'
  | 'message_complete'
  | 'vote_required'
  | 'vote_received'
  | 'argument_scores'
  | 'debate_complete'
  | 'error';

export interface WSMessage {
  type: WSMessageType;
  debate_id: string;
  data: Record<string, unknown>;
}

export interface DebateTranscriptEntry {
  speaker: string;
  content: string;
  phase: string;
}

// Persisted debates (GET /api/debates and /api/debates/{id}). Field names are
// snake_case to match the API payload directly.
export interface PastDebateSummary {
  id: string;
  topic: string;
  pro_style: string;
  con_style: string;
  winner: 'PRO' | 'CON' | 'TIE' | null;
  message_count: number;
  created_at: string;
  completed_at: string;
}

export interface PastDebateDetail extends PastDebateSummary {
  transcript: DebateTranscriptEntry[];
  argument_scores: DebateScores | null;
}
