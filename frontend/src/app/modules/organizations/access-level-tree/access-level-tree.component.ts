import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { debounceTime, distinctUntilChanged, Subject, takeUntil } from 'rxjs'
import type { AccessLevelInstance, AccessLevelTree, CurrentUser } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import type { DrawerMode } from '@seed/components'
import { PageComponent } from '@seed/components'
import { ImageOverlayDirective, SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { MediaWatcherService } from '@seed/services'
import type {
  CreateInstanceData,
  DeleteInstanceData,
  EditAccessLevelsData,
  RenameInstanceData,
  UploadInstancesData,
} from './access-level-tree.types'
import { CreateInstanceDialogComponent } from './create-instance-dialog'
import { DeleteInstanceDialogComponent } from './delete-instance-dialog'
import { EditAccessLevelsDialogComponent } from './edit-access-levels-dialog'
import { RenameInstanceDialogComponent } from './rename-instance-dialog'
import { UploadInstancesDialogComponent } from './upload-instances-dialog'

@Component({
  selector: 'seed-organizations-access-level-tree',
  templateUrl: './access-level-tree.component.html',
  imports: [CommonModule, ImageOverlayDirective, MaterialImports, PageComponent, SharedImports],
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  styles: `
    seed-organizations-access-level-tree .mat-drawer-inner-container {
      overflow-y: auto !important;
      display: flex;
      flex-direction: column;
    }
  `,
})
export class AccessLevelTreeComponent implements OnInit, OnDestroy {
  private _matDialog = inject(MatDialog)
  private _mediaWatcherService = inject(MediaWatcherService)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)

  private readonly _unsubscribeAll$ = new Subject<void>()
  private _organizationId: number
  private _filterValue = ''
  private _filterSubject$ = new Subject<string>()
  currentUser: CurrentUser
  accessLevelNames: AccessLevelTree['accessLevelNames']
  accessLevelTree: AccessLevelTree['accessLevelTree']
  filteredAccessLevelTree?: AccessLevelTree['accessLevelTree']
  drawerMode: DrawerMode = 'side'
  drawerOpened = true
  helpOpened = false
  expanded = new Set<number>()
  allExpanded = false
  private _savedExpanded: Set<number> | null = null

  ngOnInit(): void {
    this._filterSubject$.pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this._unsubscribeAll$)).subscribe((value) => {
      this.filterAccessLevelTree(value)
    })

    this._mediaWatcherService.onMediaChange$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ matchingAliases }) => {
      if (matchingAliases.includes('md')) {
        this.drawerMode = 'side'
        this.drawerOpened = true
      } else {
        this.drawerMode = 'over'
        this.drawerOpened = false
      }
    })

    this._organizationService.accessLevelTree$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ accessLevelNames, accessLevelTree }) => {
      this.accessLevelNames = accessLevelNames
      this.accessLevelTree = accessLevelTree
      this.filterAccessLevelTree(this._filterValue)
    })

    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.currentUser = currentUser
    })

    this._userService.currentOrganizationId$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organizationId) => {
      this._organizationId = organizationId
    })
  }

  toggleDrawer = (): void => {
    this.drawerOpened = !this.drawerOpened
    if (this.drawerOpened) {
      this.helpOpened = false
    }
  }

  toggleExpand = (id: number): void => {
    if (this.expanded.has(id)) {
      this.expanded.delete(id)
    } else {
      this.expanded.add(id)
    }
    this._updateAllExpandedState()
  }

  expandAll = (): void => {
    this._addAllIds(this.filteredAccessLevelTree ?? this.accessLevelTree)
    this.allExpanded = true
  }

  collapseAll = (): void => {
    this.expanded.clear()
    this.allExpanded = false
  }

  toggleExpandAll = (): void => {
    if (this.allExpanded) {
      this.collapseAll()
    } else {
      this.expandAll()
    }
  }

  toggleHelp = () => {
    this.helpOpened = !this.helpOpened
  }

  countChildren = (instance: AccessLevelInstance): number => {
    return (instance.children ?? []).reduce((count, child) => count + 1 + this.countChildren(child), 0)
  }

  editAccessLevels(): void {
    this._matDialog.open(EditAccessLevelsDialogComponent, {
      autoFocus: false,
      disableClose: true,
      panelClass: 'seed-dialog-panel',
      width: '640px',
      data: {
        accessLevelNames: this.accessLevelNames,
        organizationId: this._organizationId,
      } satisfies EditAccessLevelsData,
    })
  }

  createInstance(parentInstance: AccessLevelInstance) {
    const dialog = this._matDialog.open(CreateInstanceDialogComponent, {
      autoFocus: false,
      disableClose: true,
      data: {
        accessLevelNames: this.accessLevelNames,
        parentInstance: this._getUnfilteredInstance(parentInstance),
        organizationId: this._organizationId,
      } satisfies CreateInstanceData,
      panelClass: 'seed-dialog-panel',
    })

    dialog.afterClosed().subscribe((created: boolean) => {
      if (created) {
        // Expand the parent where the child was just created
        this.expanded.add(parentInstance.id)
      }
    })
  }

  renameInstance(instance: AccessLevelInstance): void {
    this._matDialog.open(RenameInstanceDialogComponent, {
      autoFocus: false,
      disableClose: true,
      data: {
        accessLevelNames: this.accessLevelNames,
        accessLevelTree: this.accessLevelTree,
        instance,
        organizationId: this._organizationId,
      } satisfies RenameInstanceData,
      panelClass: 'seed-dialog-panel',
    })
  }

  deleteInstance(instance: AccessLevelInstance): void {
    this._organizationService.canDeleteAccessLevelInstance(this._organizationId, instance.id).subscribe(({ reasons }) => {
      const warnings = reasons ?? []
      const totalChildren = this.countChildren(this._getUnfilteredInstance(instance))
      if (totalChildren > 0) {
        warnings.push(`Has ${totalChildren} Access Level Instance${totalChildren === 1 ? '' : 's'} below this one`)
      }

      this._matDialog.open(DeleteInstanceDialogComponent, {
        autoFocus: false,
        disableClose: true,
        data: {
          instance,
          organizationId: this._organizationId,
          warnings,
        } satisfies DeleteInstanceData,
        panelClass: 'seed-dialog-panel',
      })
    })
  }

  onFilterChange(value: string) {
    this._filterValue = value
    this._filterSubject$.next(value)
  }

  // Handle debounced filter
  filterAccessLevelTree(filter: string) {
    const filterTree = (tree: AccessLevelInstance[]): AccessLevelInstance[] => {
      return tree
        .map((instance) => ({
          ...instance,
          ...(instance.children ? { children: filterTree(instance.children) } : {}),
        }))
        .filter((instance) => instance.name.toLowerCase().includes(filter.toLowerCase()) || instance.children?.length > 0)
    }

    if (filter) {
      // Save expanded state before filtering (only on first filter keystroke)
      if (!this._savedExpanded) {
        this._savedExpanded = new Set(this.expanded)
      }
      this.filteredAccessLevelTree = filterTree(this.accessLevelTree)
      // Expand all nodes with children in the filtered tree so matches are visible
      this.expanded = new Set<number>()
      this._addAllIds(this.filteredAccessLevelTree)
      this._updateAllExpandedState()
    } else {
      this.filteredAccessLevelTree = undefined
      // Restore previous expanded state
      if (this._savedExpanded) {
        this.expanded = this._savedExpanded
        this._savedExpanded = null
      }
      this._updateAllExpandedState()
    }
  }

  uploadInstances() {
    this._matDialog.open(UploadInstancesDialogComponent, {
      autoFocus: false,
      disableClose: true,
      data: {
        organizationId: this._organizationId,
      } satisfies UploadInstancesData,
      panelClass: 'seed-dialog-panel',
      width: '640px',
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _addAllIds(tree: AccessLevelInstance[]): void {
    for (const instance of tree) {
      if (instance.children?.length > 0) {
        this.expanded.add(instance.id)
        this._addAllIds(instance.children)
      }
    }
  }

  private _updateAllExpandedState(): void {
    const tree = this.filteredAccessLevelTree ?? this.accessLevelTree
    this.allExpanded = this._areAllExpanded(tree)
  }

  private _areAllExpanded(tree: AccessLevelInstance[]): boolean {
    for (const instance of tree) {
      if (instance.children?.length > 0) {
        if (!this.expanded.has(instance.id) || !this._areAllExpanded(instance.children)) {
          return false
        }
      }
    }
    return true
  }

  // When a filter is used, lookup the unfiltered instance to accurately get the child instances
  private _getUnfilteredInstance(instance: AccessLevelInstance): AccessLevelInstance {
    const path: string[] = []
    for (const name of this.accessLevelNames) {
      if (name in instance.path) {
        path.push(instance.path[name])
      } else {
        break
      }
    }

    // Remove the root name
    path.shift()
    let unfilteredInstance = this.accessLevelTree[0]

    for (const instanceName of path) {
      unfilteredInstance = unfilteredInstance.children.find((child) => child.name === instanceName)
    }

    return unfilteredInstance
  }
}
