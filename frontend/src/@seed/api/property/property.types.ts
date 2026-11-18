export type PropertyColumnStats = {
  non_null_count: number;
  null_count: number;
  distinct_count: number;
  min: number | string | boolean | null;
  max: number | string | boolean | null;
  avg: number | string | boolean | null;
  sum: number | string | boolean | null;
  median: number | null;
  p05: number | null;
  p25: number | null;
  p75: number | null;
  p95: number | null;
  stddev: number | null;
  mode: number | string | null;
  top_k: { value: string; count: number }[] | null;
  unique_count: number | null;
  uniqueness_ratio: number | null;
  blank_count: number | null;
}

export type PropertyColumnSummary = {
  column_name: string;
  display_name: string;
  is_extra_data: boolean;
  data_type: string;
  db_type: string;
  stats: PropertyColumnStats;
}

export type PropertyColumnSummaryCycle = {
  cycle_id: number;
  total_records: number;
  columns: PropertyColumnSummary[];
}

export type PropertyColumnSummaryResponse = {
  status: string;
  selected_cycle_ids: number[];
  selected_column_names: string[];
  total_records: number;
  include_raw_data: boolean;
  cycles: PropertyColumnSummaryCycle[];
}
