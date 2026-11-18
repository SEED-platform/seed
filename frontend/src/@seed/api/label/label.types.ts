export type Label = {
  id: number;
  name: string;
  color: LabelColor;
  organization_id: number;
  show_in_list: boolean;
  is_applied?: number[];
  /** view ids the label was applied to by a goal's cross-cycle data quality check */
  is_applied_by_goal?: number[];
}

export type LabelColor = 'red' | 'orange' | 'white' | 'blue' | 'light blue' | 'green' | 'gray'

export type LabelOperator = 'and' | 'or' | 'exclude'

export type PropertyViewLabel = {
  id: number;
  propertyview: number;
  statuslabel: number;
  goal: number | null;
  name: string;
  color: LabelColor;
  show_in_list: boolean;
}
