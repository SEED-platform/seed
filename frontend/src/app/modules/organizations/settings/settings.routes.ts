import type { Routes } from '@angular/router'
import { ApiKeysComponent } from './api-keys/api-keys.component'
import { AuditTemplateComponent } from './audit-template/audit-template.component'
import { DisplayFieldsComponent } from './display-fields/display-fields.component'
import { DisplayUnitsComponent } from './display-units/display-units.component'
import { EmailComponent } from './email/email.component'
import { FacilitiesPlanSettingsComponent } from './facilities-plan/facilities-plan.component'
import { MaintenanceComponent } from './maintenance/maintenance.component'
import { OptionsComponent } from './options/options.component'
import { SalesforceBuildingIntegrationComponent } from './salesforce-building-integration/salesforce-building-integration.component'
import { SharingComponent } from './sharing/sharing.component'
import { TwoFactorComponent } from './two-factor/two-factor.component'
import { UBIDComponent } from './ubid/ubid.component'

export default [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'options',
  },
  {
    path: 'options',
    title: 'Options',
    component: OptionsComponent,
  },
  {
    path: 'api-keys',
    title: 'API Keys',
    component: ApiKeysComponent,
  },
  {
    path: 'audit-template',
    title: 'Audit Template',
    component: AuditTemplateComponent,
  },
  {
    path: 'display-fields',
    title: 'Display Fields',
    component: DisplayFieldsComponent,
  },
  {
    path: 'display-units',
    title: 'Display Units',
    component: DisplayUnitsComponent,
  },
  {
    path: 'email',
    title: 'Email',
    component: EmailComponent,
  },
  {
    path: 'facilities-plan',
    title: 'Facilities Plan',
    component: FacilitiesPlanSettingsComponent,
  },
  {
    path: 'maintenance',
    title: 'Maintenance',
    component: MaintenanceComponent,
  },
  {
    path: 'salesforce-building-integration',
    title: 'Salesforce Integration',
    component: SalesforceBuildingIntegrationComponent,
  },
  {
    path: 'sharing',
    title: 'Public Data Sharing',
    component: SharingComponent,
  },
  {
    path: 'two-factor',
    title: 'Two-Factor Authentication',
    component: TwoFactorComponent,
  },
  {
    path: 'ubid',
    title: 'UBID',
    component: UBIDComponent,
  },
] satisfies Routes
