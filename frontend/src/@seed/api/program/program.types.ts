import type { ChartDataset } from 'chart.js'

export type Program = {
  actual_emission_column: number | null;
  actual_energy_column: number | null;
  cycles: number[];
  emission_metric_type: string | null;
  energy_metric_type: string | null;
  filter_group: number | null;
  id?: number;
  name: string;
  organization_id: number | null;
  target_emission_column: number | null;
  target_energy_column: number | null;
  x_axis_columns: number[];
  energy_bool?: boolean;
  emission_bool?: boolean;
}

export type ProgramUpsertPayload = Pick<
  Program,
  | 'actual_emission_column'
  | 'actual_energy_column'
  | 'cycles'
  | 'emission_metric_type'
  | 'energy_metric_type'
  | 'filter_group'
  | 'name'
  | 'target_emission_column'
  | 'target_energy_column'
  | 'x_axis_columns'
>

export type EvaluatedProgram = {
  actual_emission_column: number;
  actual_emission_column_name: string;
  actual_energy_column: number;
  actual_energy_column_name: string;
  cycles: { id: number; name: string }[];
  emission_bool: boolean;
  emission_metric: boolean;
  emission_metric_type: number;
  energy_bool: boolean;
  energy_metric: boolean;
  energy_metric_type: number;
  filter_group: number | null;
  target_emission_column: number;
  target_energy_column: number;
}

export type ProgramsResponse = {
  status: string;
  compliance_metrics: Program[];
}

export type ProgramResponse = {
  status: string;
  compliance_metric: Program;
}

export type ProgramData = {
  cycles: { id: number; name: string }[];
  graph_data: GraphData;
  meta: { organization: number; compliance_metric: number };
  metric: EvaluatedProgram;
  name: string;
  properties_by_cycles: Record<number, Record<string, unknown>[]>;
  results_by_cycles: ResultsByCycles;
}

// compliant -> n: No, u: Unknown, y: Yes
export type ResultsByCycles = { n: number[]; u: number[]; y: number[] }

type GraphData = {
  datasets: { data: number[]; label: string; backgroundColor?: string }[];
  labels: string[];
}

export type PropertyInsightDataset = ChartDataset<'scatter', PropertyInsightPoint[]>

export type PropertyInsightPoint = {
  id: number;
  name: string;
  x: number;
  y: number;
  target: number;
  distance?: number;
}

export type SimpleCartesianScale = {
  type: 'linear' | 'category';
  title: { display: boolean; text: string };
}
