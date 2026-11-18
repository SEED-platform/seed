export type AuditTemplateReportTypesResponse = {
  status: string;
  data: string[];
}

export type AuditTemplateConfig = {
  id: string;
  update_at_day: number;
  update_at_hour: number;
  update_at_minute: number;
  last_update_date?: string;
  organization: number;
}

export type AuditTemplateConfigResponse = {
  status: string;
  data: AuditTemplateConfig[];
}

export type AuditTemplateConfigCreateResponse = {
  status: string;
  data: AuditTemplateConfig;
}
