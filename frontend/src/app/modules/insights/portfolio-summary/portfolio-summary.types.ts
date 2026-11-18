import type { CycleGoal, Goal, Organization } from '@seed/api'

export type ConfigureGoalsData = {
  goals: Goal[];
  isLoggedIntoBbSalesforce: boolean;
  bb_salesforce_enabled: boolean;
}

export type AddCycleData = {
  currentGoal: Goal;
  isLoggedIntoBbSalesforce: boolean;
  existingCycleGoal?: CycleGoal;
}

export type LabelColumnKey = 'baseline' | 'current'

export type SyncSalesforceData = {
  goal: Goal;
  currentCycleGoal: CycleGoal;
  organization: Organization;
}

export type PortfolioSummaryGridContext = {
  labelsExpanded: Record<LabelColumnKey, boolean>;
  toggleLabels: (key: LabelColumnKey) => void;
}
