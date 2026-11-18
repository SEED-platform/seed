import type { IsActiveMatchOptions, Params, QueryParamsHandling } from '@angular/router'

export type NavigationItem = {
  id?: string;
  title?: string;
  subtitle?: string;
  type: 'aside' | 'basic' | 'collapsible' | 'divider' | 'group' | 'spacer';
  hidden?: (item: NavigationItem) => boolean;
  active?: boolean;
  disabled?: boolean;
  tooltip?: string;
  link?: string;
  fragment?: string;
  preserveFragment?: boolean;
  queryParams?: Params | null;
  queryParamsHandling?: QueryParamsHandling | null;
  externalLink?: boolean;
  target?: '_blank' | '_self' | '_parent' | '_top';
  regexMatch?: RegExp;
  exactMatch?: boolean;
  isActiveMatchOptions?: IsActiveMatchOptions;
  fn?: (item: NavigationItem) => void;
  classes?: {
    title?: string;
    subtitle?: string;
    icon?: string;
    wrapper?: string;
  };
  icon?: string;
  badge?: {
    title?: string;
    classes?: string;
  };
  children?: NavigationItem[];
}

export type VerticalNavigationAppearance = 'default' | 'dense'

export type VerticalNavigationMode = 'over' | 'side'

export type VerticalNavigationPosition = 'left' | 'right'
