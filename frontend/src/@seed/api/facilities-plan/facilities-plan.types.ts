import type { Column } from '../column'

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
  compliance_cycle_year_column?: Column;
  include_in_total_denominator_column?: Column;
  exclude_from_plan_column?: Column;
  require_in_plan_column?: Column;
  electric_energy_usage_column?: Column;
  gas_energy_usage_column?: Column;
  steam_energy_usage_column?: Column;
}
