export type Rule = {
  condition: Condition;
  cross_cycle: boolean;
  data_type: 0 | 1 | 2 | 3 | 4 | 5;
  enabled: boolean;
  field: string;
  for_derived_column: boolean;
  id: number;
  max: number | null;
  min: number | null;
  not_null: boolean;
  required: boolean;
  rule_type: number;
  severity: number;
  status_label: number;
  table_name: 'PropertyState' | 'TaxLotState' | 'Goal';
  text_match: string | null;
  units: string;
}

export type Condition = 'exclude' | 'include' | 'required' | 'not_null' | 'range'

import type { FormControl, FormGroup } from '@angular/forms'

export type DataQualityFormGroup = FormGroup<{
  id: FormControl<number | null>;
  condition: FormControl<'exclude' | 'include' | 'required' | 'not_null' | 'range'>;
  cross_cycle: FormControl<boolean>;
  data_type: FormControl<number | null>;
  enabled: FormControl<boolean>;
  field: FormControl<string>;
  for_derived_column: FormControl<boolean>;
  min: FormControl<number | null>;
  max: FormControl<number | null>;
  not_null: FormControl<boolean>;
  required: FormControl<boolean>;
  rule_type: FormControl<number | null>;
  severity: FormControl<number | null>;
  status_label: FormControl<number | null>;
  table_name: FormControl<'PropertyState' | 'TaxLotState' | 'Goal'>;
  text_match: FormControl<string | null>;
  units: FormControl<string>;
}>

export type UnitSymbols
  = 'ft**2' | 'm**2' | 'kBtu/ft**2/year' | 'gal/ft**2/year' | 'GJ/m**2/year' | 'MJ/m**2/year' | 'kWh/m**2/year' | 'kBtu/m**2/year'
export type UnitNames
  = 'square feet' | 'square metres' | 'kBtu/sq. ft./year' | 'gal/sq. ft./year' | 'GJ/m²/year' | 'MJ/m²/year' | 'kWh/m²/year' | 'kBtu/m²/year'

export type DataQualityResultsResponse = {
  data: DataQualityResults[];
}

export type DataQualityResults = {
  [key: string]: unknown;
  data_quality_results: DataQualityResult[];
}

export type DataQualityResult = {
  condition: string;
  detailed_message: string;
  field: string;
  formatted_field: string;
  label: string;
  message: string;
  severity: string;
  table_name: string;
  value: unknown;
}
