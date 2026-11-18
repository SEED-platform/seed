import { InjectionToken } from '@angular/core'
import type { SEEDConfig } from './config.types'

export const SEED_CONFIG = new InjectionToken<SEEDConfig>('SEED_APP_CONFIG')
