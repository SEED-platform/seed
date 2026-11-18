// Types
export type Scheme = 'auto' | 'dark' | 'light'
export type Themes = { id: string; name: string }[]

/**
 * AppConfig interface. Update this interface to strictly type your config
 * object.
 */
export type SEEDConfig = {
  layout: string;
  passwordPattern: RegExp;
  scheme: Scheme;
  theme: 'theme-default';
  themes: Themes;
}
