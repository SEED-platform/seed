export type AlertAppearance = 'border' | 'fill' | 'outline' | 'soft'

export type AlertType = 'primary' | 'accent' | 'warn' | 'basic' | 'info' | 'success' | 'warning' | 'error'

export type Alert = { type: AlertType; message: string }
