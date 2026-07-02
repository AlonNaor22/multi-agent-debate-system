import { create } from 'zustand';
import type { DebatePhase, Speaker, DebateMessage, StyleInfo, DebateScores } from '../types/debate';

interface DebateState {
  // Setup state
  topic: string;
  proStyle: string;
  conStyle: string;
  availableStyles: StyleInfo[];

  // Debate state
  debateId: string | null;
  phase: DebatePhase | null;
  messages: DebateMessage[];
  isDebating: boolean;
  isWaitingForVote: boolean;
  error: string | null;

  // Final structured scoreboard (set when the judge's scores arrive)
  scores: DebateScores | null;

  // Streaming state
  streamingContent: string;
  streamingSpeaker: Speaker | null;

  // Actions
  setTopic: (topic: string) => void;
  setProStyle: (style: string) => void;
  setConStyle: (style: string) => void;
  setAvailableStyles: (styles: StyleInfo[]) => void;
  startDebate: (debateId: string, topic: string, proStyle: string, conStyle: string) => void;
  setPhase: (phase: DebatePhase) => void;
  addMessage: (message: DebateMessage) => void;
  setIsWaitingForVote: (waiting: boolean) => void;
  setError: (error: string | null) => void;
  setScores: (scores: DebateScores) => void;
  endDebate: () => void;
  reset: () => void;

  // Streaming actions
  startStreaming: (speaker: Speaker) => void;
  appendStreamingChunk: (chunk: string) => void;
  finishStreaming: (label?: string) => void;
}

const initialState = {
  topic: '',
  proStyle: 'passionate',
  conStyle: 'passionate',
  availableStyles: [],
  debateId: null,
  phase: null,
  messages: [],
  isDebating: false,
  isWaitingForVote: false,
  error: null,
  scores: null,
  streamingContent: '',
  streamingSpeaker: null,
};

export const useDebateStore = create<DebateState>((set, get) => ({
  ...initialState,

  setTopic: (topic) => set({ topic }),
  setProStyle: (proStyle) => set({ proStyle }),
  setConStyle: (conStyle) => set({ conStyle }),
  setAvailableStyles: (availableStyles) => set({ availableStyles }),

  startDebate: (debateId, topic, proStyle, conStyle) =>
    set({
      debateId,
      topic,
      proStyle,
      conStyle,
      isDebating: true,
      messages: [],
      phase: null,
      error: null,
      scores: null,
      streamingContent: '',
      streamingSpeaker: null,
    }),

  setPhase: (phase) => set({ phase }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      streamingContent: '',
      streamingSpeaker: null,
    })),

  setIsWaitingForVote: (isWaitingForVote) => set({ isWaitingForVote }),
  // Setting an error ends the current turn: clear any dangling streaming/typing
  // indicator and dismiss the vote modal so a mid-debate failure doesn't leave
  // the UI frozen. Clearing the error (setError(null)) just wipes the message.
  setError: (error) =>
    set(
      error
        ? {
            error,
            streamingContent: '',
            streamingSpeaker: null,
            isWaitingForVote: false,
          }
        : { error: null }
    ),
  setScores: (scores) => set({ scores }),

  // phase is left untouched: debate_complete arrives after the final
  // phase_change to 'finished', and that 'finished' phase is what keeps the
  // chat (with its "New Debate" button) on screen.
  endDebate: () =>
    set({
      isDebating: false,
      isWaitingForVote: false,
      streamingContent: '',
      streamingSpeaker: null,
    }),

  reset: () => set(initialState),

  // Streaming actions
  startStreaming: (speaker) =>
    set({
      streamingSpeaker: speaker,
      streamingContent: '',
    }),

  appendStreamingChunk: (chunk) =>
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    })),

  finishStreaming: (label) => {
    const state = get();
    if (!state.streamingSpeaker) return;
    set((s) => ({
      messages: [...s.messages, {
        speaker: state.streamingSpeaker!,
        content: state.streamingContent,
        label,
        phase: s.phase || 'introduction',
      }],
      streamingContent: '',
      streamingSpeaker: null,
    }));
  },
}));
