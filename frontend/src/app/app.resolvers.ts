import { inject } from '@angular/core'
import { forkJoin } from 'rxjs'
import { ConfigService, OrganizationService, UserService, VersionService } from '@seed/api'

export const configResolver = () => {
  const configService = inject(ConfigService)
  return configService.config$
}

export const initialDataResolver = () => {
  const organizationService = inject(OrganizationService)
  const userService = inject(UserService)
  const versionService = inject(VersionService)

  // Fork join multiple API endpoint calls to wait on all of them to finish
  return forkJoin([versionService.get(), userService.getCurrentUser(), organizationService.getBrief()])
}
