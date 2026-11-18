import { Injectable } from '@angular/core'
import type { NavigationItem } from '@seed/components'

@Injectable({ providedIn: 'root' })
export class SeedNavigationService {
  private _componentRegistry = new Map<string, unknown>()
  private _navigationStore = new Map<string, NavigationItem[]>()

  /**
   * Register navigation component
   */
  registerComponent(name: string, component: unknown): void {
    this._componentRegistry.set(name, component)
  }

  /**
   * Deregister navigation component
   */
  deregisterComponent(name: string): void {
    this._componentRegistry.delete(name)
  }

  /**
   * Get navigation component from the registry
   */
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters
  getComponent<T>(name: string): T | undefined {
    if (this._componentRegistry.has(name)) {
      return this._componentRegistry.get(name) as T
    }
    return undefined
  }

  /**
   * Store the given navigation with the given key
   */
  storeNavigation(key: string, navigation: NavigationItem[]): void {
    // Add to the store
    this._navigationStore.set(key, navigation)
  }

  /**
   * Get navigation from storage by key
   */
  getNavigation(key: string): NavigationItem[] {
    return this._navigationStore.get(key) ?? []
  }

  /**
   * Delete the navigation from the storage
   */
  deleteNavigation(key: string): void {
    // Check if the navigation exists
    if (!this._navigationStore.has(key)) {
      console.warn(`Navigation with the key '${key}' does not exist in the store.`)
    }

    // Delete from the storage
    this._navigationStore.delete(key)
  }

  /**
   * Utility function that returns a flattened
   * version of the given navigation array
   */
  getFlatNavigation(navigation: NavigationItem[], flatNavigation: NavigationItem[] = []): NavigationItem[] {
    for (const item of navigation) {
      if (item.type === 'basic') {
        flatNavigation.push(item)
        continue
      }

      if (item.type === 'aside' || item.type === 'collapsible' || item.type === 'group') {
        if (item.children) {
          this.getFlatNavigation(item.children, flatNavigation)
        }
      }
    }

    return flatNavigation
  }

  /**
   * Utility function that returns the item
   * with the given id from given navigation
   */
  getItem(id: string, navigation: NavigationItem[]): NavigationItem | null {
    for (const item of navigation) {
      if (item.id === id) {
        return item
      }

      if (item.children) {
        const childItem = this.getItem(id, item.children)

        if (childItem) {
          return childItem
        }
      }
    }

    return null
  }

  /**
   * Utility function that returns the item's parent
   * with the given id from given navigation
   */
  getItemParent(
    id: string,
    navigation: NavigationItem[],
    parent: NavigationItem[] | NavigationItem,
  ): NavigationItem[] | NavigationItem | null {
    for (const item of navigation) {
      if (item.id === id) {
        return parent
      }

      if (item.children) {
        const childItem = this.getItemParent(id, item.children, item)

        if (childItem) {
          return childItem
        }
      }
    }

    return null
  }
}
