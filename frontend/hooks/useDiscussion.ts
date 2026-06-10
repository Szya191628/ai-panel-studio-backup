'use client';

import { create } from 'zustand';
import { Discussion, Participant, Speech, Findings } from '@/lib/types';

interface DiscussionState {
  // Current discussion data
  currentDiscussion: Discussion | null;
  participants: Participant[];
  speeches: Speech[];
  findings: Findings;
  conclusion: string | null;
  convergence: number | null;

  // Streaming state
  streamingContent: string;
  streamingSpeaker: string | null;
  isRunning: boolean;

  // Actions
  setDiscussion: (discussion: Discussion) => void;
  setParticipants: (participants: Participant[]) => void;
  addSpeech: (speech: Speech) => void;
  setFindings: (findings: Findings) => void;
  setConclusion: (conclusion: string | null) => void;
  setConvergence: (convergence: number | null) => void;
  setStreamingContent: (content: string) => void;
  setStreamingSpeaker: (speaker: string | null) => void;
  setIsRunning: (running: boolean) => void;
  updateParticipantStatus: (id: string, status: Participant['status'], thinking_summary?: string) => void;
  reset: () => void;
}

const initialState = {
  currentDiscussion: null,
  participants: [],
  speeches: [],
  findings: { consensus: [], disagreements: [] },
  conclusion: null,
  convergence: null,
  streamingContent: '',
  streamingSpeaker: null,
  isRunning: false,
};

export const useDiscussion = create<DiscussionState>((set) => ({
  ...initialState,

  setDiscussion: (discussion) => set({ currentDiscussion: discussion }),
  setParticipants: (participants) => set({ participants }),
  addSpeech: (speech) => set((state) => ({ speeches: [...state.speeches, speech] })),
  setFindings: (findings) => set({ findings }),
  setConclusion: (conclusion) => set({ conclusion }),
  setConvergence: (convergence) => set({ convergence }),
  setStreamingContent: (content) => set({ streamingContent: content }),
  setStreamingSpeaker: (speaker) => set({ streamingSpeaker: speaker }),
  setIsRunning: (running) => set({ isRunning: running }),
  updateParticipantStatus: (id, status, thinking_summary) =>
    set((state) => ({
      participants: state.participants.map((p) =>
        p.id === id ? { ...p, status, ...(thinking_summary !== undefined ? { thinking_summary } : {}) } : p
      ),
    })),
  reset: () => set(initialState),
}));
