export type CustomReportParameter = {
  column: number;
  location: 'first_axis' | 'second_axis';
  aggregations: number[];
}

export type CustomReport = {
  id: number;
  name: string;
  organization_id: number;
  cycles: number[];
  filter_groups: number[];
  parameters: CustomReportParameter[];
}

export type CustomReportResponse = {
  status: string;
  data_view: CustomReport;
}

export type CustomReportsResponse = {
  status: string;
  data_views: CustomReport[];
}

export type CustomReportGraphDataset = {
  column: string;
  filter_group: string;
  aggregation: string;
  data: (number | null)[];
  label?: string;
  backgroundColor?: string;
  borderColor?: string;
  tension?: number;
  yAxisID?: string;
  borderDash?: number[];
}

export type CustomReportGraphData = {
  labels: string[];
  datasets: CustomReportGraphDataset[];
}

export type CustomReportColumnCycleData = {
  Average: number | null;
  Minimum: number | null;
  Maximum: number | null;
  Sum: number | null;
  Count: number | null;
  views_by_default_field: Record<string, number | null>;
}

export type CustomReportFilterGroupData = {
  cycles_by_id: Record<number, CustomReportColumnCycleData>;
}

export type CustomReportColumnData = {
  filter_groups_by_id: Record<number, CustomReportFilterGroupData>;
}

export type CustomReportEvaluateResponse = {
  status: string;
  data: {
    meta: { organization_id: number; data_view_id: number };
    graph_data: CustomReportGraphData;
    columns_by_id: Record<number, CustomReportColumnData>;
    views_by_filter_group_id: Record<number, Record<string, string>>;
  };
}

export type CustomReportUpsertPayload = {
  name: string;
  filter_groups: number[];
  cycles: number[];
  parameters: CustomReportParameter[];
}
