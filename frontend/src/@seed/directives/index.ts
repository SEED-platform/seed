import { TranslocoDirective } from '@jsverse/transloco'
import { ExternalLinkDirective } from './external-link'

export * from './external-link'
export * from './image-overlay'
export * from './scroll-reset'
export * from './scrollbar'

export const SharedImports = [ExternalLinkDirective, TranslocoDirective]
