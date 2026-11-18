import { inject } from '@angular/core'
import type { Routes } from '@angular/router'
import { SwaggerService } from '@seed/api'
import { ApiComponent } from './api.component'

export default [
  {
    path: '',
    title: 'API Documentation',
    component: ApiComponent,
    resolve: {
      schema: () => {
        const swaggerService = inject(SwaggerService)
        return swaggerService.getSchema()
      },
    },
  },
] satisfies Routes
