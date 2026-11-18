import type { InventoryDisplayType } from 'app/modules/inventory'

export type InventoryGroupsResponse = {
  status: string;
  data: InventoryGroup[];
}

export type InventoryGroupResponse = {
  status: string;
  data: InventoryGroup;
}

export type InventoryGroup = {
  access_level_instance: number;
  access_level_instance_data: Record<string, unknown>;
  id: number;
  inventory_list: number[];
  inventory_type: InventoryDisplayType;
  name: string;
  organization: number;
  systems: GroupSystem[];
  views_list: number[];
}

export type GroupSystem = {
  cooling_capacity: number | null;
  count: number;
  des_type: string;
  efficiency: number | null;
  energy_capacity: number | null;
  evse_type: string;
  group_id: number;
  heating_capacity: number | null;
  id: number;
  mode: string;
  name: string;
  power: number | null;
  power_capacity: number | null;
  services: GroupService[];
  type: string;
  voltage: number | null;
}

export type GroupService = {
  emission_factor: number | null;
  id: number;
  name: string;
  properties: number[];
}

export type SystemsByTypeResponse = {
  status: string;
  data: Record<string, GroupSystem[]>;
}

export type SystemType = 'DES' | 'EVSE' | 'Battery' | 'Aggregate Meter'

export type DesType = 'Boiler' | 'Chiller' | 'CHP'

export type EvseType = 'Level1-120V' | 'Level2-240V' | 'Level3-DC Fast'

export type GroupDashboardResponse = {
  status: string;
  data: GroupDashboard;
}

export type GroupDashboard = {
  'Gross Floor Area': number | null;
  'Site EUI': number | null;
  'Views Count': number;
  'Views Missing Site EUI': number;
  'Views Missing Gross Floor Area': number;
  importing_total: Record<string, number>;
  exporting_total: Record<string, number>;
}

export type GroupSankeyResponse = {
  status: string;
  data: GroupSankeyEntry[];
}

export type GroupSankeyEntry = {
  from: string;
  to: string;
  flow: number | null;
}

export type GroupPropertiesResponse = {
  status: string;
  data: GroupProperty[];
}

export type GroupProperty = {
  property_id: number;
  property_display_name: string;
}

export type GroupMeterUsageResponse = {
  status: string;
  data: {
    readings: Record<string, unknown>[];
    column_defs: { field: string; headerName?: string }[];
  };
}

export type GroupMetersResponse = {
  status: string;
  data: GroupMeter[];
}

export type GroupMeterConfig = {
  direction: 'imported' | 'exported';
  use: 'outside' | 'using' | 'offering';
  connection: 'outside' | 'service';
  group_id: number | null;
  system_id: number | null;
  service_id: number | null;
}

export type GroupMeter = {
  id: number;
  type: string;
  alias: string;
  source: string;
  source_id: string;
  connection_type: string;
  property_id: number | null;
  property_display_field: string | null;
  view_id: number | null;
  system_id: number | null;
  system_name: string | null;
  service_id: number | null;
  service_name: string | null;
  service_group: number | null;
  scenario_id: number | null;
  scenario_name: string | null;
  is_virtual: boolean;
  config: GroupMeterConfig;
}

export type MeterInterval = 'Exact' | 'Month' | 'Year'

export type MeterReadingDetail = {
  start_time: string;
  end_time: string;
  reading: number | null;
  source_unit: string | null;
  conversion_factor: number;
}

export type GroupServiceDetail = {
  id: number;
  system_name: string;
  name: string;
  service_meters: {
    in: { meter_id: number; meter_alias: string; has_meter_data: boolean }[];
    out: { meter_id: number; meter_alias: string; has_meter_data: boolean }[];
  };
  properties: {
    property_id: number;
    property_view_id: number;
    property_display_name: string;
    meter_id: number;
    meter_alias: string;
    meter_type: string;
    has_meter_data: boolean;
  }[];
}
