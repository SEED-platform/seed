import type { SerializedColumn } from '../column'

export type FacilitiesPlan = {
  id: number;
  organization: number;
  name: string;
  energy_running_sum_percentage: number;
  compliance_cycle_year_column: number | null;
  include_in_total_denominator_column: number | null;
  exclude_from_plan_column: number | null;
  require_in_plan_column: number | null;
  electric_energy_usage_column: number | null;
  gas_energy_usage_column: number | null;
  steam_energy_usage_column: number | null;
}

export type FacilitiesPlanUpsertPayload = Omit<FacilitiesPlan, 'id' | 'organization'>

export type FacilitiesPlanResponse = {
  id: number;
  organization: number;
  name: string;
  energy_running_sum_percentage: number;
  compliance_cycle_year_column: number | null;
  include_in_total_denominator_column: number | null;
  exclude_from_plan_column: number | null;
  require_in_plan_column: number | null;
  electric_energy_usage_column: number | null;
  gas_energy_usage_column: number | null;
  steam_energy_usage_column: number | null;
}

export type FacilitiesPlansResponse = {
  status: string;
  data: FacilitiesPlanResponse[];
}

// The serializer exposes the plan's columns as a named map on the run response
export type FacilitiesPlanRunColumns = {
  compliance_cycle_year_column?: SerializedColumn;
  include_in_total_denominator_column?: SerializedColumn;
  exclude_from_plan_column?: SerializedColumn;
  require_in_plan_column?: SerializedColumn;
  electric_energy_usage_column?: SerializedColumn;
  gas_energy_usage_column?: SerializedColumn;
  steam_energy_usage_column?: SerializedColumn;
}
