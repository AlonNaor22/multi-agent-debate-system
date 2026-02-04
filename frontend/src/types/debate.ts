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
