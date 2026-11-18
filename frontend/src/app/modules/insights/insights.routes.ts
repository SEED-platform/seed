import type { Routes } from '@angular/router'
import {
  CustomReportsComponent,
  DefaultReportsComponent,
  FacilitiesPlanComponent,
  PortfolioSummaryComponent,
  ProgramOverviewComponent,
  PropertyInsightsComponent,
} from '.'

export default [
  {
    path: 'custom-reports',
    title: 'Custom Reports',
    component: CustomReportsComponent,
  },
  {
    path: 'custom-reports/:id',
    title: 'Custom Reports',
    component: CustomReportsComponent,
  },
  {
    path: 'default-reports',
    title: 'Default Reports',
    component: DefaultReportsComponent,
  },
  {
    path: 'program-overview',
    title: 'Program Overview',
    component: ProgramOverviewComponent,
  },
  {
    path: 'program-overview/:id',
    title: 'Program Overview',
    component: ProgramOverviewComponent,
  },
  {
    path: 'property-insights',
    title: 'Property Insights',
    component: PropertyInsightsComponent,
  },
  {
    path: 'property-insights/:id',
    title: 'Property Insights',
    component: PropertyInsightsComponent,
  },
  {
    path: 'portfolio-summary',
    title: 'Portfolio Summary',
    component: PortfolioSummaryComponent,
  },
  {
    path: 'facilities-plan',
    title: 'Facilities Plan',
    component: FacilitiesPlanComponent,
  },
] satisfies Routes
