export type EmailTemplate = {
  id: number;
  name: string;
  description: string;
  subject: string;
  content: string;
  html_content: string;
  created: string;
  last_updated: string;
  default_template_id?: number;
  language: string;
}

export type CreateEmailTemplateResponse = {
  status: string;
  data: EmailTemplate;
}

export type ListEmailTemplatesResponse = {
  status: string;
  data: EmailTemplate[];
}

export type SendEmailResponse = {
  status: string;
  data: SentEmailData;
}

export type SentEmailData = {
  backend_alias: string;
  bcc: string;
  cc: string;
  context: string;
  created: string;
  expires_at: string | null;
  from_email: string;
  headers: string;
  html_message: string;
  id: number;
  last_updated: string;
  message: string;
  number_of_retries: number | null;
  priority: number;
  scheduled_time: string | null;
  status: number;
  subject: string;
  template_id: number;
  to: string;
}
