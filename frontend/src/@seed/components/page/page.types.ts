import type { InventoryType } from 'app/modules/inventory'

/**
 * A breadcrumb is either a plain label or a label that links to a parent page.
 * Labels are translated unless `translate` is false (use false for user data such as a dataset name).
 */
export type Breadcrumb = string | BreadcrumbItem

export type BreadcrumbItem = {
  label: string;
  link?: string | null;
  translate?: boolean;
}

export type Config = {
  action?: () => void;
  actionClasses?: string;
  actionIcon?: string;
  actionText?: string;
  action2?: () => void;
  action2Classes?: string;
  action2Icon?: string;
  action2Text?: string;
  breadcrumbs?: Breadcrumb[];
  compactHeader?: boolean;
  dense?: boolean; // compact header (the default); set false for the roomier legacy header
  subTitle?: string;
  switchLink?: boolean; // shows a 'switch to <other type>' link beside the title instead of the tab strip
  sideNavToggle?: boolean;
  tabs?: InventoryType[];
  title: string;
  titleIcon?: string;
}
