export type CycleGoal = {
  id: number;
  current_cycle: {
    id: number;
    end: string;
    start: string;
    name: string;
  };
  salesforce_annual_report_id?: string;
  salesforce_annual_report_name?: string;
}

export type CycleGoalsResponse = {
  status: string;
  cycle_goals: CycleGoal[];
}

export type Goal = {
  access_level_instance: number;
  area_column: number;
  area_column_name: string;
  baseline_cycle: number;
  baseline_cycle_name: string;
  commitment_sqft: number;
  eui_column1: number;
  eui_column1_name: string;
  eui_column2?: number;
  eui_column2_name?: string;
  eui_column3?: number;
  eui_column3_name?: string;
  id: number;
  level_name: string;
  level_name_index: number;
  name: string;
  organization: number;
  partner_note: string;
  partner_note_approval: boolean;
  partner_note_approval_time?: string;
  partner_note_approval_user?: number;
  partner_note_approval_user_name?: string;
  salesforce_goal_id?: string;
  salesforce_goal_name?: string;
  salesforce_partner_id?: string;
  salesforce_partner_name?: string;
  target_percentage: number;
  transactions_column?: string;
  type: 'standard' | 'transaction';
  access_level_instance_name: string;
  cycle_goals: CycleGoal[];
}

export type GoalsResponse = {
  status: string;
  goals: Goal[];
}

export type PortfolioSummary = {
  baseline_cycle_name: string;
  baseline_total_sqft: number;
  baseline_total_kbtu: number;
  baseline_weighted_eui: number;
  total_properties: number;
  shared_sqft: number;
  total_passing: number;
  total_new_or_acquired: number;
  passing_committed: number;
  passing_shared: number;
  current_cycle_name: string;
  current_total_sqft: number;
  current_total_kbtu: string;
  current_weighted_eui: number;
  sqft_change: number;
  eui_change: number;
}

export type WeightedEUI = {
  'Cycle Name': string;
  'Baseline?': string;
  EUI: string;
  Goal: number;
  'Annual % Imp': number;
  'Cumulative % Imp': number;
}

export type weightedEUIsResponse = {
  status: string;
  results: WeightedEUI[];
}

export type GoalNote = {
  id: number;
  goal: number;
  property: number;
  question: string | null;
  resolution: string | null;
  passed_checks: boolean;
  new_or_acquired: boolean;
}

export type HistoricalNote = {
  id: number;
  text: string;
  property: number;
}

export type GoalProperty = {
  id: number;
  baseline_cycle: string;
  current_cycle: string;
  baseline_view_id: number | null;
  current_view_id: number | null;
  baseline_sqft: number | null;
  current_sqft: number | null;
  baseline_eui: number | null;
  current_eui: number | null;
  baseline_kbtu: number | null;
  current_kbtu: number | null;
  sqft_change: number | null;
  eui_change: number | null;
  goal_note: GoalNote | null;
  historical_note: HistoricalNote | null;
} & Record<string, unknown>

export type GoalPagination = {
  page: number;
  start: number;
  end: number;
  num_pages: number;
  has_next: boolean;
  has_previous: boolean;
  total: number;
}

export type GoalPropertiesResponse = {
  properties: GoalProperty[];
  pagination: GoalPagination;
  property_lookup: Record<number, number>;
}

export type SalesforceAnnualReport = {
  id: string;
  baseline_portfolio_kbtu: number | null;
  baseline_portfolio_eui: number | null;
  reporting_year_start: string | null;
  reporting_year_end: string | null;
  number_of_properties: number | null;
  portfolio_average_eui: number | null;
  shared_square_feet: number | null;
  reviewed_square_feet: number | null;
  ei_annual_improvement: number | null;
  portfolio_kbtu: number | null;
  total_ei_improvement: number | null;
  new_energy_savings: number | null;
  report_status: string | null;
  review_status: string | null;
}

export type SalesforceSummaryEntry = {
  id: number;
  seed: PortfolioSummary;
  salesforce: SalesforceAnnualReport | Record<string, never>;
}

export type SalesforceSummaryResponse = Record<string, SalesforceSummaryEntry>
