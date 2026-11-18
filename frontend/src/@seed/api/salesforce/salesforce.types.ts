export type SalesforceConfig = {
  id: number;
  indication_label: number;
  violation_label: number;
  compliance_label: number;
  account_rec_type: string;
  contact_rec_type: string;
  last_update_date: string;
  unique_benchmark_id_fieldname: string;
  seed_benchmark_id_column: string;
  url: string;
  username: string;
  password: string;
  security_token: string;
  domain: string;
  cycle_fieldname: string;
  status_fieldname: string;
  labels_fieldname: string;
  contact_email_column: number;
  contact_name_column: number;
  account_name_column: number;
  default_contact_account_name: string;
  logging_email: string;
  benchmark_contact_fieldname: string;
  data_admin_email_column: number;
  data_admin_name_column: number;
  data_admin_account_name_column: number;
  default_data_admin_account_name: string;
  data_admin_contact_fieldname: number;
  update_at_hour: number;
  update_at_minute: number;
  delete_label_after_sync: boolean;
}

export type SalesforceConfigResponse = {
  status: string;
  salesforce_config: SalesforceConfig;
}

export type SalesforceConfigsResponse = {
  status: string;
  salesforce_configs: SalesforceConfig[];
}

export type SalesforceMapping = {
  id: number;
  organization_id: number;
  column: number;
  salesforce_fieldname: string;
}

export type BbSalesforceConfig = {
  id: number;
  organization_id: number;
  salesforce_url: string;
  client_id: string;
  client_secret: string;
}

export type BbSalesforceConfigResponse = {
  status: string;
  bb_salesforce_config: BbSalesforceConfig;
}

export type BbSalesforceConfigsResponse = {
  status: string;
  bb_salesforce_configs: BbSalesforceConfig;
}

export type BbSalesforceLoginUrlResponse = {
  status: string;
  url?: string;
  response?: string;
}

export type BbSalesforceTokenResponse = {
  status: string;
  response?: string;
}

export type BbSalesforceVerifyTokenResponse = {
  valid: boolean;
}

export type BbSalesforceLogoutResponse = {
  status: string;
}

export type SalesforceMappingDeleteResponse = {
  status: string;
  message: string;
}

export type SalesforceMappingResponse = {
  status: string;
  salesforce_mapping: SalesforceMapping;
}

export type SalesforceMappingsResponse = {
  status: string;
  salesforce_mappings: SalesforceMapping[];
}

export type SalesforceConnectionTestResponse = {
  status: string;
  message?: string;
}
