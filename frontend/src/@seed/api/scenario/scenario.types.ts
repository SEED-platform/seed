// Mirrors PropertyMeasureSerializer in the backend
export type Measure = {
  [key: string]: unknown;
  annual_cost_savings: number | null;
  annual_electricity_savings: number | null;
  annual_natural_gas_savings: number | null;
  annual_peak_electricity_reduction: number | null;
  application_scale: string;
  category: string;
  category_affected: string;
  category_display_name: string;
  cost_capital_replacement: number | null;
  cost_installation: number | null;
  cost_material: number | null;
  cost_mv: number | null;
  cost_residual_value: number | null;
  cost_total_first: number | null;
  description: string | null;
  display_name: string;
  id: number;
  implementation_status: string;
  measure_id: string;
  name: string;
  recommended: boolean;
  scenario_id: number;
  useful_life: number | null;
}

export type Scenario = {
  [key: string]: unknown;
  annual_cost_savings: number | null;
  annual_electricity_savings: number | null;
  annual_natural_gas_savings: number | null;
  annual_peak_electricity_reduction: number | null;
  id: number;
  measures: Measure[];
  name: string;
  propertyState: number;
}
