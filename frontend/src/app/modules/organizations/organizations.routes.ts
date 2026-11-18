import { inject } from '@angular/core'
import type { Routes, UrlMatchResult, UrlSegment } from '@angular/router'
import { switchMap, take } from 'rxjs'
import { OrganizationService, UserService } from '@seed/api'
import type { OrganizationGenericTypeMatcher } from './organizations.types'
import {
  AccessLevelTreeComponent,
  ColumnsComponent,
  CyclesComponent,
  DataQualityComponent,
  DerivedColumnsComponent,
  EmailTemplatesComponent,
  LabelsComponent,
  MembersComponent,
  SettingsComponent,
} from '.'

const genericTypeMatcher = (args: OrganizationGenericTypeMatcher) => (segments: UrlSegment[]): UrlMatchResult | null => {
  // Lazy-loaded children receive an empty segment list for the bare `/organizations` URL
  if (segments[0]?.path === args.validPage && args.validTypes.includes(segments[1]?.path)) {
    return { consumed: segments, posParams: { type: segments[1] } }
  }
  return null
}

export const dataQualityTypeMatcher = (segments: UrlSegment[]) => {
  const args = { segments, validTypes: ['goal', 'properties', 'taxlots'], validPage: 'data-quality' }
  return genericTypeMatcher(args)(segments)
}

export const derivedColumnsTypeMatcher = (segments: UrlSegment[]) => {
  const args = { segments, validTypes: ['properties', 'taxlots'], validPage: 'derived-columns' }
  return genericTypeMatcher(args)(segments)
}

export default [
  // Bare `/organizations` lands on the first Organizations sidebar page
  { path: '', pathMatch: 'full', redirectTo: 'settings' },
  { path: 'settings', component: SettingsComponent, loadChildren: () => import('app/modules/organizations/settings/settings.routes') },
  {
    path: 'access-level-tree',
    title: 'Access Level Tree',
    component: AccessLevelTreeComponent,
    resolve: {
      accessLevelTree: () => {
        const organizationService = inject(OrganizationService)
        const userService = inject(UserService)
        return userService.currentOrganizationId$.pipe(
          take(1),
          switchMap(() => {
            return organizationService.accessLevelTree$
          }),
        )
      },
    },
  },
  {
    path: 'columns',
    component: ColumnsComponent,
    loadChildren: () => import('app/modules/organizations/columns/columns.routes'),
  },
  {
    matcher: dataQualityTypeMatcher,
    title: 'Data Quality',
    component: DataQualityComponent,
  },
  {
    matcher: derivedColumnsTypeMatcher,
    title: 'Derived Columns',
    component: DerivedColumnsComponent,
  },
  {
    path: 'cycles',
    title: 'Cycles',
    component: CyclesComponent,
  },
  {
    path: 'email-templates',
    title: 'Email Templates',
    component: EmailTemplatesComponent,
  },
  {
    path: 'labels',
    title: 'Labels',
    component: LabelsComponent,
  },
  {
    path: 'members',
    title: 'Members',
    component: MembersComponent,
  },
] satisfies Routes
