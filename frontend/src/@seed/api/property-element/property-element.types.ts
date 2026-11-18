export type PropertyElement = {
  id: number;
  code: string;
  description: string | null;
  installation_date: string | null;
  condition_index: number | null;
  remaining_service_life: number | null;
  replacement_cost: number | null;
  extra_data: Record<string, unknown>;
}
