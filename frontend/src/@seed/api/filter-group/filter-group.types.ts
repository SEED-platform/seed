export type FilterGroupInventoryType = 'Property' | 'Tax Lot'

export type FilterGroup = {
  id: number;
  name: string;
  organization_id: number;
  inventory_type: FilterGroupInventoryType;
  query_dict: Record<string, unknown>;
  and_labels: number[];
  or_labels: number[];
  exclude_labels: number[];
}

export type FilterGroupsResponse = {
  status: string;
  data: FilterGroup[];
}

export type FilterGroupResponse = {
  status: string;
  data: FilterGroup;
}

export type FilterGroupUpsertPayload = {
  name: string;
  inventory_type: FilterGroupInventoryType;
  query_dict: Record<string, unknown>;
  and_labels: number[];
  or_labels: number[];
  exclude_labels: number[];
}
