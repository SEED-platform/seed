import type { Scenario } from '@seed/api'

export type TimelineEventType = 'NoteEvent' | 'AnalysisEvent' | 'ATEvent'

export type TimelineNote = {
  id: number;
  text: string;
  updated: string;
}

export type TimelineAnalysis = {
  name: string;
  service: string;
  created_at: string;
  start_time: string | null;
  end_time: string | null;
  status: string;
}

export type TimelineEvent = {
  id: number;
  cycle: number;
  cycle_end_date: string;
  modified: string;
  user_id: number | null;
  event_type: TimelineEventType;
  audit_date?: string;
  note?: TimelineNote;
  analysis?: TimelineAnalysis;
  scenarios?: Scenario[];
}

export type TimelineEventsResponse = {
  status: string;
  data: TimelineEvent[];
}

export type TimelineCycle = {
  cycle: number;
  cycle_end_date: string;
  events: TimelineEvent[];
}
