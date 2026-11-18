export type ReportChartPoint = {
  id: number;
  yr_e: string;
  x: number | string;
  y: number | string;
  display_name?: string;
}

export type ReportPropertyCount = {
  yr_e: string;
  cycle: string;
  num_properties: number;
  'num_properties_w-data': number;
  color?: string;
}

export type ReportAxisStatValues = {
  values: number[];
  children?: Record<string, number[]>;
}

export type ReportAxisData = Record<string, Record<string, ReportAxisStatValues>>

export type ReportDataResponse = {
  status: string;
  data: {
    chart_data: ReportChartPoint[];
    property_counts: ReportPropertyCount[];
    axis_data: ReportAxisData;
  };
}

export type AggregatedChartPoint = {
  x: number | string;
  y: number | string;
  yr_e: string;
}

export type AggregatedReportDataResponse = {
  status: string;
  aggregated_data: {
    chart_data: AggregatedChartPoint[];
    property_counts: ReportPropertyCount[];
  };
}

export type AxisVariable = {
  name: string;
  label: string;
  varName: string;
  axisLabel: string;
}
