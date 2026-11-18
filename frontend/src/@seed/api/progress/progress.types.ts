export type ProgressStatus = 'not-started' | 'parsing' | 'in-progress' | 'completed' | 'failed' | 'success' | 'error'

export type ProgressResponse = {
  func_name: string;
  message: object | string | null;
  progress: number;
  progress_key: string;
  stacktrace: string | null;
  status: ProgressStatus;
  status_message: string;
  summary: string | null;
  total: number | null;
  unique_id: number | string;
  total_records?: number;
  completed_records?: number;
}

export type FullProgressResponse = {
  progress?: ProgressResponse;
  progress_key?: string;
  status?: string;
  errors?: unknown;
  message?: string;
}

export type SubProgressResponse = {
  progress_data: ProgressResponse;
  sub_progress_data: ProgressResponse;
}
