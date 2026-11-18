import { inject, Injectable } from '@angular/core'
import type { CurrentUser } from '@seed/api'
import { MockApiService } from '@seed/mock-api'
import { user as userData } from './data'

@Injectable({ providedIn: 'root' })
export class UserMockApi {
  private _mockApiService = inject(MockApiService)

  private _user: CurrentUser = userData

  constructor() {
    // Register Mock API handlers
    this.registerHandlers()
  }

  /**
   * Register Mock API handlers
   */
  registerHandlers(): void {
    this._mockApiService.onGet('/api/v3/users/current/').reply(() => [200, structuredClone(this._user)])

    this._mockApiService.onPatch('api/common/user').reply(({ request }) => {
      // Get the user mock-api
      const user = structuredClone((request.body as { user: CurrentUser }).user)

      // Update the user mock-api
      this._user = { ...this._user, ...user }

      // Return the response
      return [200, structuredClone(this._user)]
    })
  }
}
