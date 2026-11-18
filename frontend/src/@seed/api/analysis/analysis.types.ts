// Highlight Subset type
export type Highlight = {
  name: string;
  value: string;
}

// Analysis type
export type Analysis = {
  configuration: Record<string, unknown>; // configuration is different for each analysis type
  created_at: string;
  cycles: number[];
  end_time: string;
  id: number;
  name: string;
  organization: number;
  parsed_results: Record<string, unknown>; // parsed_results is different for each analysis type
  service: AnalysisServiceType;
  start_time: string;
  status: string;
  user: number;
  access_level_instance: number;
  number_of_analysis_property_views: number;
  views: number[];
  highlights: Highlight[];
  _finished_with_tasks: boolean; // used to determine if an analysis has no currently running tasks
}

export type AnalysisCreateData = {
  name: string;
  service: AnalysisServiceType;
  configuration: Record<string, unknown>;
  property_view_ids: number[];
  access_level_instance_id: number;
}

export type AnalysisServiceType
  = 'BSyncr' | 'BETTER' | 'EUI' | 'CO2' | 'EEEJ' | 'Element Statistics' | 'Building Upgrade Recommendation' | 'HVAC Metrics'

// Analysis by View type
export type View = {
  id: number;
  analysis: number;
  cycle: number;
  display_name: string;
  output_files: AnalysisOutputFile[];
  parsed_results: Record<string, unknown>;
  property: number;
  property_state: number;
  messages?: string[]; // used for analysis ag grid
}

export type AnalysisOutputFile = {
  analysis_property_view: number;
  content_type: string;
  file: string;
  id: number;
}

export type ListAnalysesResponse = {
  status: 'success';
  analyses: Analysis[];
  // Omitted if there are no analyses or with `include_views=false`
  views?: View[];
  original_views?: Record<number, number>;
}

export type AnalysisResponse = {
  status: 'success';
  analysis: Analysis;
}

export type PropertyAnalysesResponse = {
  status: 'success';
  analyses: Analysis[];
}

export type AnalysesViews = {
  analyses: Analysis[];
  views: View[];
}

export type AnalysisViews = {
  status: 'success';
  views: View[];
  original_views: Record<number, number>;
}

export type AnalysisView = {
  status: 'success';
  view: View;
  original_view: number;
}

export type AnalysesMessage = {
  id: number;
  analysis: number;
  analysis_property_view: number;
  debug_message: string;
  type: string;
  user_message: string;
}

export type ListMessagesResponse = {
  status: 'success';
  messages: AnalysesMessage[];
}

export type AnalysisSummary = {
  stats: AnalysisSummaryStats[];
  number_extra_data_fields: number;
  status: string;
  total_records: number;
  total_sqft: number;
}

export type AnalysisSummaryStats = {
  column_name: string;
  count: number;
  display_name: string;
  is_extra_data: boolean;
}

// Column (with data) used by an organization's properties/tax lots, as returned by the
// `used_columns` endpoint. Like the column list endpoints, it renames `shared_field_type` to `sharedFieldType`.
export type UsedColumn = {
  id: number;
  name: string;
  organization_id: number;
  table_name: 'PropertyState' | 'TaxLotState';
  column_name: string;
  display_name: string;
  sharedFieldType: 'None' | 'Public';
}

export type UsedColumnsResponse = {
  status: string;
  columns: UsedColumn[];
}

export type SavingsTarget = 'AGGRESSIVE' | 'CONSERVATIVE' | 'NOMINAL'
export type SelectMetersType = 'all' | 'date_range' | 'select_cycle'
export type BenchmarkDataType = 'DEFAULT' | 'GENERATE'

export type BETTERConfig = {
  benchmark_data_type: BenchmarkDataType;
  cycle_id: number;
  enable_pvwatts: boolean;
  meter: { start_date: string; end_date: string };
  min_model_r_squared: number;
  preprocess_meters: boolean;
  portfolio_analysis: boolean;
  savings_target: SavingsTarget;
  select_meters: SelectMetersType;
}

export type AnalysisConfig = BETTERConfig | Record<string, unknown>

export type BSyncrModelTypes
  = | 'Simple Linear Regression'
    | 'Three bsyncrOptionsParameter Linear Model Cooling'
    | 'Three Parameter Linear Model Heating'
    | 'Four Parameter Linear Model'
