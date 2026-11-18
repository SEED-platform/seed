import type { Column, LabelOperator, UserRole } from '@seed/api'

export type OrgCycle = {
  name: string;
  cycle_id: number;
  num_properties: number;
  num_taxlots: number;
}

type OrgUser = {
  first_name: string;
  last_name: string;
  email: string;
  id: number;
}

export type BriefOrganization = {
  name: string;
  org_id: number;
  parent_id: number | null;
  is_parent: boolean;
  id: number;
  user_role: UserRole;
  display_decimal_places: number;
  salesforce_enabled: boolean;
  bb_salesforce_enabled: boolean;
  access_level_names: string[];
  audit_template_conditional_import: boolean;
  property_display_field: string;
  taxlot_display_field: string;
}

export type Organization = BriefOrganization & {
  number_of_users: number;
  user_is_owner: boolean;
  owners: OrgUser[];
  sub_orgs: (Organization & { is_parent: false })[];
  parent_id: number;
  display_units_eui: string;
  display_units_ghg: string;
  display_units_ghg_intensity: string;
  display_units_water_use: string;
  display_units_wui: string;
  display_units_area: string;
  cycles: OrgCycle[];
  created: string;
  mapquest_api_key: string;
  geocoding_enabled: boolean;
  better_analysis_api_key: string;
  better_host_url: string;
  display_meter_units: Record<string, string>;
  display_meter_water_units: Record<string, string>;
  thermal_conversion_assumption: number;
  comstock_enabled: boolean;
  new_user_email_from: string;
  new_user_email_subject: string;
  new_user_email_content: string;
  new_user_email_signature: string;
  at_organization_token: string;
  at_host_url: string;
  audit_template_user: string;
  audit_template_password: string;
  audit_template_city_id: number | null;
  audit_template_report_type: string;
  audit_template_status_types: string;
  audit_template_sync_enabled: boolean;
  ubid_threshold: number;
  inventory_count: number;
  public_feed_enabled: boolean;
  public_feed_labels: boolean;
  public_geojson_enabled: boolean;
  default_reports_x_axis_options: Column[];
  default_reports_y_axis_options: Column[];
  require_2fa: boolean;
  // Not part of the standard organization GET response; fetched separately via
  // `getQueryThreshold` and attached here before `updateSettings` saves it back.
  query_threshold?: number;
  // Write-only: attached before `updateSettings` to persist the public column selection.
  public_fields?: { id: number }[];
}

export type OrganizationSettings = Omit<Organization, 'default_reports_x_axis_options' | 'default_reports_y_axis_options'> & {
  default_reports_x_axis_options: number[];
  default_reports_y_axis_options: number[];
}

export type OrganizationResponse = {
  status: string;
  organization: Organization;
}
export type OrganizationsResponse = {
  organizations: (BriefOrganization | Organization)[];
}

// A column marked as publicly shared, as returned by the `shared_fields` endpoint.
export type SharedField = {
  table_name: string;
  name: string;
  column_name: string;
  display_name: string;
}

export type SharedFieldsResponse = {
  status: string;
  public_fields: SharedField[];
}

export type QueryThresholdResponse = {
  status: string;
  query_threshold: number;
}

export type OrganizationUser = {
  access_level: string;
  access_level_instance_id: number;
  access_level_instance_name: string;
  email: string;
  first_name: string;
  last_name: string;
  number_of_orgs: number;
  role: UserRole;
  user_id: number;
  settings: OrganizationUserSettings;
}

export type OrganizationUserSettings = {
  [key: string]: unknown;
  colorScheme?: 'dark' | 'light';
  cycleId?: number;
  sorts?: UserSettingsSorts;
  filters?: UserSettingsFilters;
  profile?: UserSettingsProfiles;
  crossCycles?: UserSettingsCrossCycles;
  labels?: UserLabelSettings;
  pins?: UserPinSettings;
  insights?: InsightsUserSettings;
}

type UserSettingsFilters = {
  properties?: Record<string, unknown>;
  taxlots?: Record<string, unknown>;
}

type UserSettingsSorts = {
  properties?: string[];
  taxlots?: string[];
}

type UserSettingsProfiles = {
  detail?: { properties?: number; taxlots?: number };
  list?: { properties?: number; taxlots?: number };
}

type UserSettingsCrossCycles = {
  properties?: number[];
  taxlots?: number[];
}

type UserPinSettings = {
  properties?: {
    left: string[];
    right: string[];
  };
  taxlots?: {
    left: string[];
    right: string[];
  };
}

type UserLabelSettings = { ids: number[]; operator: LabelOperator }

export type InsightDatasetVisibility = 'compliant' | 'non-compliant' | 'unknown' | 'whisker'

export type PropertyInsightsUserSettings = {
  programId?: number | null;
  cycleId?: number | null;
  metricType?: 0 | 1 | null;
  xAxisColumnId?: number | null;
  accessLevel?: string | null;
  accessLevelInstanceId?: number | null;
  datasetVisibility?: InsightDatasetVisibility[];
}

export type InsightsUserSettings = {
  propertyInsights?: PropertyInsightsUserSettings;
  portfolioSummary?: { goalId?: number };
}

export type OrganizationUsersResponse = {
  users: OrganizationUser[];
  status: string;
}

export type OrganizationUserResponse = {
  data: OrganizationUser;
  status: string;
}

export type AccessLevelTreeResponse = {
  access_level_names: string[];
  access_level_tree: AccessLevelInstance[];
}

export type AccessLevelTree = {
  accessLevelNames: string[];
  accessLevelTree: AccessLevelInstance[];
}

export type AccessLevelInstancesByDepth = {
  accessLevelNames: string[];
  accessLevelInstancesByDepth: AccessLevelsByDepth;
}

export type AccessLevelInstance = {
  id: number;
  name: string;
  organization: number;
  path: Record<string, string>;
  children?: AccessLevelInstance[];
}

export type AccessLevelsByDepth = Record<number, { id: number; name: string }[]>

export type UpdateAccessLevelsRequest = {
  access_level_names: string[];
}

export type UpdateAccessLevelsResponse = string[]

export type CreateAccessLevelInstanceRequest = {
  name: string;
  parent_id: number;
}

export type EditAccessLevelInstanceRequest = {
  name: string;
}

export type EditAccessLevelInstanceResponse = {
  status: 'success';
}

export type CanDeleteInstanceResponse = {
  can_delete: boolean;
  reasons?: string[];
}

export type UploadAccessLevelInstancesResponse = {
  success: boolean;
  tempfile?: string;
  message?: string;
}

export type StartSavingAccessLevelInstancesRequest = {
  filename: string;
}

export type MatchingCriteriaColumnsResponse = {
  PropertyState: string[];
  TaxLotState: string[];
}

export type FilterByViewsResponse = {
  access_level_instance_ids: number[];
  status: string;
}

export type AdminOrganization = {
  id: number;
  name: string;
  created: string;
  number_of_users: number;
  user_count?: number;
  property_count?: number;
  taxlot_count?: number;
}

export type AdminOrganizationsResponse = {
  organizations: AdminOrganization[];
}

export type CreateOrganizationResponse = {
  status: string;
  organization: AdminOrganization;
}

export type AddUserToOrgResponse = {
  status: string;
}
