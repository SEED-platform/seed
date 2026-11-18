import type { Routes } from '@angular/router'
import { AdminComponent } from 'app/modules/profile/admin/admin.component'
import { ProfileDeveloperComponent } from 'app/modules/profile/developer/developer.component'
import { ProfileInfoComponent } from 'app/modules/profile/info/info.component'
import { ProfileSecurityComponent } from 'app/modules/profile/security/security.component'
import { ProfileSettingsComponent } from 'app/modules/profile/settings/settings.component'
import { ProfileTwoFactorComponent } from 'app/modules/profile/two-factor/two-factor.component'

export default [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'info',
  },
  {
    path: 'info',
    title: 'Profile Info',
    component: ProfileInfoComponent,
  },
  {
    path: 'security',
    title: 'Security',
    component: ProfileSecurityComponent,
  },
  {
    path: 'two-factor',
    title: 'Two Factor Profile',
    component: ProfileTwoFactorComponent,
  },
  {
    path: 'developer',
    title: 'Developer',
    component: ProfileDeveloperComponent,
  },
  {
    path: 'admin',
    title: 'Admin',
    component: AdminComponent,
  },
  {
    path: 'display',
    title: 'Display',
    component: ProfileSettingsComponent,
  },
] satisfies Routes
