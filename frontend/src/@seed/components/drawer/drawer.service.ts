import { Injectable } from '@angular/core'
import type { MatDrawer } from '@angular/material/sidenav'
import type { DrawerComponent } from '@seed/components'

@Injectable({ providedIn: 'root' })
export class DrawerService {
  private _componentRegistry: Map<string, DrawerComponent> = new Map<string, DrawerComponent>()
  private _drawerRef?: MatDrawer

  /**
   * Register drawer component
   *
   * @param name
   * @param component
   */
  registerComponent(name: string, component: DrawerComponent): void {
    this._componentRegistry.set(name, component)
  }

  /**
   * Deregister drawer component
   *
   * @param name
   */
  deregisterComponent(name: string): void {
    this._componentRegistry.delete(name)
  }

  /**
   * Get drawer component from the registry
   *
   * @param name
   */
  getComponent(name: string): DrawerComponent | undefined {
    return this._componentRegistry.get(name)
  }

  setDrawer(drawer: MatDrawer) {
    this._drawerRef = drawer
  }

  toggle() {
    void this._drawerRef?.toggle()
  }
}
