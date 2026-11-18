export type Meter = {
  alias: string;
  config: MeterConfig;
  connection_type: string;
  id: number;
  is_virtual: boolean;
  property_display_field: string;
  property_id: number;
  scenario_id: number | null;
  scenario_name: string | null;
  service_group: string | null;
  service_id: number | null;
  service_name: string | null;
  source: string;
  source_id: string;
  system_id: number | null;
  system_name: string | null;
  type: string;
  view_id: number;
}

export type MeterConfig = {
  connection: 'outside' | 'service';
  direction: 'exported' | 'imported';
  group_id: null;
  service_id: null;
  system_id: null;
  use: string;
}

export type MeterUsage = {
  column_defs: { field: string; displayName?: string }[];
  readings: MeterReading[];
}

export type MeterReading = {
  [key: string]: number | string;
  end_time: string;
  start_time: string;
}
