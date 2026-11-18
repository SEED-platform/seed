import { inject, Injectable } from '@angular/core'
import { MockApiService } from '@seed/mock-api'
import { heroicons, material } from 'app/mock-api/ui/icons/data'

@Injectable({ providedIn: 'root' })
export class IconsMockApi {
  private _mockApiService = inject(MockApiService)

  private readonly _heroicons = heroicons
  private readonly _material = material

  constructor() {
    // Register Mock API handlers
    this.registerHandlers()
  }

  /**
   * Register Mock API handlers
   */
  registerHandlers(): void {
    // -----------------------------------------------------------------------------------------------------
    // @ Heroicons outline icons - GET
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onGet('api/ui/icons/heroicons-outline').reply(() => [
      200,
      {
        namespace: 'heroicons-outline',
        name: 'Heroicons Outline',
        grid: 'icon-size-6',
        list: structuredClone(this._heroicons),
      },
    ])

    // -----------------------------------------------------------------------------------------------------
    // @ Heroicons solid icons - GET
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onGet('api/ui/icons/heroicons-solid').reply(() => [
      200,
      {
        namespace: 'heroicons-solid',
        name: 'Heroicons Solid',
        grid: 'icon-size-6',
        list: structuredClone(this._heroicons),
      },
    ])

    // -----------------------------------------------------------------------------------------------------
    // @ Material solid icons - GET
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onGet('api/ui/icons/material-solid').reply(() => [
      200,
      {
        namespace: 'mat-solid',
        name: 'Material Solid',
        grid: 'icon-size-6',
        list: structuredClone(this._material),
      },
    ])

    // -----------------------------------------------------------------------------------------------------
    // @ Material outline icons - GET
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onGet('api/ui/icons/material-outline').reply(() => [
      200,
      {
        namespace: 'mat-outline',
        name: 'Material Outline',
        grid: 'icon-size-6',
        list: structuredClone(this._material),
      },
    ])

    // -----------------------------------------------------------------------------------------------------
    // @ Material twotone icons - GET
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onGet('api/ui/icons/material-twotone').reply(() => [
      200,
      {
        namespace: '',
        name: 'Material Twotone',
        grid: 'icon-size-6',
        list: structuredClone(this._material),
      },
    ])
  }
}
