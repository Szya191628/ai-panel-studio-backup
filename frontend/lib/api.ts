import { Discussion, Participant, Guest, Findings } from './types';

const BASE_URL = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    throw new Error(`HTTP error! status: ${resp.status}`);
  }
  return resp.json();
}

// Discussion CRUD
export async function createDiscussion(
  topic: string,
  host: Guest,
  experts: Guest[],
  maxRounds: number = 5
): Promise<{ ok: boolean; discussion_id: string }> {
  return fetchJSON('/discussions', {
    method: 'POST',
    body: JSON.stringify({ topic, host, experts, max_rounds: maxRounds }),
  });
}

export async function listDiscussions(): Promise<{
  ok: boolean;
  discussions: Discussion[];
}> {
  return fetchJSON('/discussions');
}

export async function getDiscussion(
  id: string
): Promise<{
  ok: boolean;
  discussion: Discussion;
  participants: Participant[];
  speeches: Speech[];
  findings: Findings;
}> {
  return fetchJSON(`/discussions/${id}`);
}

export async function confirmDiscussion(
  id: string
): Promise<{ ok: boolean }> {
  return fetchJSON(`/discussions/${id}/confirm`, { method: 'POST' });
}

export async function generateSpeech(
  discussionId: string,
  participantId: string
): Promise<any> {
  return fetchJSON(
    `/discussions/${discussionId}/generate-speech?participant_id=${participantId}`,
    { method: 'POST' }
  );
}

export async function endDiscussion(
  id: string,
  conclusion?: string
): Promise<any> {
  return fetchJSON(`/discussions/${id}/end`, {
    method: 'POST',
    body: JSON.stringify({ conclusion }),
  });
}

export async function runDiscussion(
  id: string,
  maxRounds?: number
): Promise<any> {
  const params = maxRounds ? `?max_rounds=${maxRounds}` : '';
  return fetchJSON(`/discussions/${id}/run${params}`, { method: 'POST' });
}

// Guest generation
export async function generateGuests(
  topic: string,
  expertCount: number = 4
): Promise<{ ok: boolean; host: Guest; experts: Guest[] }> {
  return fetchJSON('/guests/generate', {
    method: 'POST',
    body: JSON.stringify({ topic, expert_count: expertCount }),
  });
}

// SSE connection
export function createSSEConnection(
  discussionId: string,
  onEvent: (event: string, data: any) => void
): EventSource {
  const eventSource = new EventSource(`${BASE_URL}/discussions/${discussionId}/events`);

  const events = [
    'init',
    'speech_start',
    'speech_token',
    'speech_end',
    'speech',
    'finding_update',
    'round_summary',
    'status_change',
    'participant_status',
    'thinking',
    'draft',
    'speech_evolution',
    'error',
    'ping',
  ];

  events.forEach((eventType) => {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(eventType, data);
      } catch {
        onEvent(eventType, e.data);
      }
    });
  });

  eventSource.onerror = () => {
    console.error('SSE connection error');
  };

  return eventSource;
}

// Types for API
export interface Speech {
  id: number;
  participant_id: string;
  round: number;
  content: string;
  speech_type: string;
  created_at: number;
}
