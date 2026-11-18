import { inject } from '@angular/core'
import type { ActivatedRouteSnapshot, CanActivateFn, Routes } from '@angular/router'
import { Router } from '@angular/router'
import { DetailComponent } from 'app/modules/inventory-detail/detail/detail.component'
import {
  ColumnListProfilesComponent,
  GroupsComponent,
  InventoryComponent,
  CrossCyclesComponent as InventoryListCrossCyclesComponent,
  MapComponent,
} from 'app/modules/inventory-list'
import {
  AnalysesComponent,
  CrossCyclesComponent,
  DetailLayoutComponent,
  MetersComponent,
  NotesComponent,
  SensorsComponent,
  TimelineComponent,
  UbidsComponent,
} from '../inventory-detail'
import { ColumnDetailProfilesComponent } from '../inventory-detail/column-detail-profiles/column-detail-profiles.component'
import { GroupDashboardComponent } from '../inventory-list/groups/detail/dashboard/dashboard.component'
import { GroupDetailLayoutComponent } from '../inventory-list/groups/detail/group-detail-layout.component'
import { GroupMapComponent } from '../inventory-list/groups/detail/map/map.component'
import { GroupMetersComponent } from '../inventory-list/groups/detail/meters/meters.component'
import { GroupPropertiesComponent } from '../inventory-list/groups/detail/properties/properties.component'
import { ServiceDetailComponent } from '../inventory-list/groups/detail/systems/service-detail/service-detail.component'
import { GroupSystemsComponent } from '../inventory-list/groups/detail/systems/systems.component'
import { SummaryComponent } from '../inventory-list/summary/summary.component'
import { InventoryCreateComponent } from './create/inventory-create.component'
import type { InventoryType } from './inventory.types'

type NewType = {
  type: InventoryType;
}

type InventoryParam = NewType
const integerId: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const router = inject(Router)
  const id = Number(route.params.id)
  if (!Number.isInteger(id)) {
    void router.navigateByUrl('/data')
    return false
  }
  return true
}

export default [
  // Place new routes like /settings before :id
  {
    path: 'create',
    title: (route) => {
      const type = (route.params as InventoryParam).type
      return type === 'properties' ? 'Create Property' : 'Create Tax Lot'
    },
    component: InventoryCreateComponent,
  },
  {
    path: 'groups',
    title: 'Groups',
    component: GroupsComponent,
  },
  {
    path: 'groups/:groupId',
    title: 'Group Detail',
    component: GroupDetailLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', title: 'Dashboard', component: GroupDashboardComponent },
      { path: 'properties', title: 'Properties', component: GroupPropertiesComponent },
      { path: 'systems', title: 'Systems & Services', component: GroupSystemsComponent },
      { path: 'systems/services/:systemId/:serviceId', title: 'Service Detail', component: ServiceDetailComponent },
      { path: 'meters', title: 'Meters', component: GroupMetersComponent },
      { path: 'map', title: 'Map', component: GroupMapComponent },
    ],
  },
  {
    path: 'column-list-profiles',
    title: 'Column Profiles',
    component: ColumnListProfilesComponent,
  },
  {
    path: 'cross-cycles',
    title: 'Cross Cycles',
    component: InventoryListCrossCyclesComponent,
  },
  {
    path: 'map',
    title: 'Map',
    component: MapComponent,
  },
  {
    path: 'summary',
    title: 'Summary',
    component: SummaryComponent,
  },
  {
    path: ':id',
    title: (route) => {
      const type = (route.params as InventoryParam).type
      return type === 'properties' ? 'Property Detail' : 'Tax Lot Detail'
    },
    component: DetailLayoutComponent,
    canActivate: [integerId],
    children: [
      { path: '', component: DetailComponent },
      { path: 'analyses', title: 'Analyses', component: AnalysesComponent },
      { path: 'cross-cycles', title: 'Cross Cycles', component: CrossCyclesComponent },
      { path: 'column-detail-profiles', title: 'Column Detail Profiles', component: ColumnDetailProfilesComponent },
      { path: 'meters', title: 'Meters', component: MetersComponent },
      { path: 'notes', title: 'Notes', component: NotesComponent },
      { path: 'sensors', title: 'Sensors', component: SensorsComponent },
      { path: 'timeline', title: 'Timeline', component: TimelineComponent },
      { path: 'ubids', title: 'UBIDs', component: UbidsComponent },
    ],
  },
  {
    path: '',
    title: (route) => {
      const type = (route.params as InventoryParam).type
      return type === 'properties' ? 'Properties' : 'Tax Lots'
    },
    component: InventoryComponent,
  },
] satisfies Routes
