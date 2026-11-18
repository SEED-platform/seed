export type ReportConfiguration = {
  id: number | null;
  name: string;
  x_column: string | null;
  y_column: string | null;
  access_level_instance_id: number | null;
  access_level_depth: number | null;
  cycles: number[];
  filter_group_id: number | null;
}

export type ReportConfigurationUpsertPayload = Omit<ReportConfiguration, 'id'>

export type ReportConfigurationsResponse = {
  status: string;
  data: ReportConfiguration[];
}

export type ReportConfigurationResponse = {
  status: string;
  data: ReportConfiguration;
}
