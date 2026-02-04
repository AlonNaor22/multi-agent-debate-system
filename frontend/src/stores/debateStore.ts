import { create } from 'zustand';
import type { DebatePhase, Speaker, DebateMessage, StyleInfo } from '../types/debate';

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
  endDebate: () => void;
  reset: () => void;
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
};

export const useDebateStore = create<DebateState>((set) => ({
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
    }),

  setPhase: (phase) => set({ phase }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      isTyping: false,
      currentSpeaker: null,
    })),

  setCurrentSpeaker: (currentSpeaker) => set({ currentSpeaker }),
  setIsTyping: (isTyping) => set({ isTyping }),
  setIsWaitingForVote: (isWaitingForVote) => set({ isWaitingForVote }),
  setError: (error) => set({ error }),

  endDebate: () =>
    set({
      isDebating: false,
      isTyping: false,
      currentSpeaker: null,
      isWaitingForVote: false,
    }),

  reset: () => set(initialState),
}));
