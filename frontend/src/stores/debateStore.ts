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
  currentSpeaker: Speaker | null;
  isTyping: boolean;
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
  setCurrentSpeaker: (speaker: Speaker | null) => void;
  setIsTyping: (isTyping: boolean) => void;
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
  currentSpeaker: null,
  isTyping: false,
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
      isTyping: false,
      currentSpeaker: null,
      streamingContent: '',
      streamingSpeaker: null,
    })),

  setCurrentSpeaker: (currentSpeaker) => set({ currentSpeaker }),
  setIsTyping: (isTyping) => set({ isTyping }),
  setIsWaitingForVote: (isWaitingForVote) => set({ isWaitingForVote }),
  setError: (error) => set({ error }),
  setScores: (scores) => set({ scores }),

  endDebate: () =>
    set((state) => ({
      isDebating: false,
      isTyping: false,
      currentSpeaker: null,
      isWaitingForVote: false,
      streamingContent: '',
      streamingSpeaker: null,
      // Keep phase as 'finished' so the chat stays visible
      phase: state.phase === 'finished' ? 'finished' : state.phase,
    })),

  reset: () => set(initialState),

  // Streaming actions
  startStreaming: (speaker) =>
    set({
      streamingSpeaker: speaker,
      streamingContent: '',
      isTyping: true,
      currentSpeaker: speaker,
    }),

  appendStreamingChunk: (chunk) =>
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    })),

  finishStreaming: (label) => {
    const state = get();
    if (state.streamingSpeaker && state.streamingContent) {
      set((s) => ({
        messages: [...s.messages, {
          speaker: state.streamingSpeaker!,
          content: state.streamingContent,
          label,
          phase: s.phase || 'introduction',
        }],
        streamingContent: '',
        streamingSpeaker: null,
        isTyping: false,
        currentSpeaker: null,
      }));
    }
  },
}));
