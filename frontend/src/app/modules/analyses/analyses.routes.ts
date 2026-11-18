import type { Routes } from '@angular/router'
import { AnalysesComponent, AnalysisComponent, AnalysisViewComponent } from '.'

export default [
  {
    path: '',
    title: 'Analyses',
    component: AnalysesComponent,
  },
  {
    path: ':id',
    title: 'Analysis',
    component: AnalysisComponent,
  },
  {
    path: ':id/views/:viewId',
    title: 'Analysis View',
    component: AnalysisViewComponent,
  },
] satisfies Routes
