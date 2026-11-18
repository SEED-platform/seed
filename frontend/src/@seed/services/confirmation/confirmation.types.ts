export type ConfirmationConfig = {
  title?: string;
  message?: string;
  width?: 'normal' | 'wide';
  icon?: {
    show?: boolean;
    name?: string;
    color?: 'primary' | 'accent' | 'warn' | 'basic' | 'info' | 'success' | 'warning' | 'error';
  };
  actions?: {
    confirm?: {
      show?: boolean;
      label?: string;
      color?: 'primary' | 'accent' | 'warn';
    };
    cancel?: {
      show?: boolean;
      label?: string;
    };
  };
  dismissible?: boolean;
}
