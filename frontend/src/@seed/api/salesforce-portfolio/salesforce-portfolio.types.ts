export type SalesforcePortfolioConfig = {
  organization?: number;
  salesforce_url?: string;
  client_id?: string;
  client_secret?: string;
}

export type SalesforcePortfolioConfigResponse = {
  status: string;
  bb_salesforce_configs: SalesforcePortfolioConfig;
}

export type verifyTokenResponse = {
  status: string;
  valid: boolean;
  message: string;
}

export type getTokenResponse = {
  status: string;
  response: string;
}

export type SalesforceGoal = {
  id: string;
  name: string;
}

export type SalesforcePartner = {
  id: string;
  name: string;
  goals: SalesforceGoal[];
}

export type getPartnersResponse = {
  status: string;
  results: SalesforcePartner[];
}

export type AnnualReport = {
  id: string;
  name: string;
}

export type getAnnualReportsResponse = {
  status: string;
  results: AnnualReport[];
}

export type loginUrlResponse = {
  status: string;
  message?: string;
  url?: string;
}
