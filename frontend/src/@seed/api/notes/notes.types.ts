export type Note = {
  created: string;
  id: number;
  log_data: NoteLogData[];
  name: string;
  note_type: string;
  organization_id: number;
  property_view_id: number;
  text: string;
  updated: string;
  user_id: number;
}

export type NoteLogData = {
  field: string;
  new_value: string | null;
  previous_value: string | null;
  state_id: number;
}

export type NoteData = {
  name: string;
  note_type: 'Note' | 'Log';
  text: string;
}
