export interface Guest {
  name: string;
  job_title: string;
  title: string;
  stance: string;
  color: string;
  avatar_seed: string;
}

export interface Participant extends Guest {
  id: string;
  discussion_id: string;
  status: 'standby' | 'preparing' | 'speaking';
  thinking_summary: string;
  is_host: boolean;
}

export interface Speech {
  id: number;
  participant_id: string;
  round: number;
  content: string;
  speech_type: string;
  created_at: number;
}

export interface Discussion {
  id: string;
  topic: string;
  status: 'assembling' | 'active' | 'concluded' | 'cancelled';
  current_round: number;
  max_rounds: number;
  convergence_score: number | null;
  created_at: number;
  conclusion: string | null;
  participant_count?: number;
}

export interface Findings {
  consensus: string[];
  disagreements: string[];
}

export interface SSEEvent {
  event: string;
  data: any;
  timestamp: number;
}
