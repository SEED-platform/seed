export type ConfigResponse = {
  allow_signup: boolean;
  branding: {
    logo_url: string;
    home_hero_image_url: string;
    home_heading: string;
    home_text: string;
    login_heading: string;
    login_text: string;
    home_content_mode: string;
  };
  hidden_navigation: string[];
  integrations: { salesforce: boolean; better: boolean };
}
