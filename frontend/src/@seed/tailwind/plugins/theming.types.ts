export type Palette = {
  [key: number]: string;
  DEFAULT?: string;
}

export type Theme = {
  primary: Palette;
  accent?: Palette;
  warn?: Palette;
  'on-warn'?: Palette;
}

export type Themes = {
  [key: string]: Theme;
  default: Theme;
}
