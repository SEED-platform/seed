import type { Column } from '../column'
import type { FacilitiesPlanRunColumns } from '../facilities-plan'

export type FacilitiesPlanRun = {
  id: number;
  facilities_plan: number;
  cycle: number | null;
  ali: number | null;
  ali_name: string;
  ali_level: string;
  name: string | null;
  run_at: string | null;
  display_columns: Column[];
  columns: FacilitiesPlanRunColumns;
  property_display_field: Column;
}

export type FacilitiesPlanRunCreatePayload = {
  facilities_plan: number;
  cycle: number;
  ali: number;
  name: string;
  display_columns: number[];
}

export type FacilitiesPlanRunUpdatePayload = Omit<FacilitiesPlanRunCreatePayload, 'ali' | 'cycle'>

export type FacilitiesPlanRunsResponse = {
  status: string;
  data: FacilitiesPlanRun[];
}

export type FacilitiesPlanRunPropertiesParams = {
  [key: string]: unknown;
  page?: number;
  per_page?: number;
  only_ids?: boolean;
}

export type FacilitiesPlanRunProperty = {
  [key: string]: unknown;
  property_view_id: number;
  total_energy_usage: number;
  percentage_of_total_energy_usage: number;
  rank: number;
  running_percentage: number;
  running_square_footage: number;
}

export type FacilitiesPlanRunPagination = {
  start: number;
  end: number;
  page: number;
  num_pages: number;
  has_next: boolean;
  has_previous: boolean;
  total: number;
}

export type FacilitiesPlanRunPropertiesResponse = {
  properties: FacilitiesPlanRunProperty[];
  pagination: FacilitiesPlanRunPagination;
}

export type FacilitiesPlanRunIdsResponse = {
  ids: number[];
}

export type FacilitiesPlanRunColumnFilter = {
  name: string;
  column_name: string;
  operator: string;
  value: string | number;
}

export type FacilitiesPlanRunColumnSort = {
  name: string;
  column_name: string;
  direction: 'asc' | 'desc';
  priority: number;
}
