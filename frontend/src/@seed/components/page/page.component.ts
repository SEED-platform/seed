import { CommonModule } from '@angular/common'
import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input, ViewEncapsulation } from '@angular/core'
import { ActivatedRoute, Router, RouterLink } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { LoadingService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory'
import { DrawerService } from '../drawer'
import { InventoryTabComponent } from './inventory-tab'
import type { BreadcrumbItem, Config } from './page.types'

@Component({
  selector: 'seed-page',
  templateUrl: './page.component.html',
  imports: [CommonModule, MaterialImports, InventoryTabComponent, RouterLink, SharedImports],
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  styles: ':host { @apply flex; @apply flex-auto }',
})
export class PageComponent implements OnDestroy {
  @Input() config: Config
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _drawerService = inject(DrawerService)
  private _loadingService = inject(LoadingService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  type = this._route.snapshot.paramMap.get('type') as InventoryType
  loading: boolean
  hasLoaded: boolean

  constructor() {
    // show loading only once
    this._loadingService.show$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((loading) => {
      if (!this.hasLoaded && !loading) {
        this.loading = false
        this.hasLoaded = true
      } else if (!this.hasLoaded) {
        this.loading = true
      }
    })
  }

  // Every page uses the compact header unless its config opts out with `dense: false`
  get dense(): boolean {
    return this.config.dense ?? true
  }

  get headerPaddingClass(): string {
    if (this.dense) return 'pt-2.5'
    return this.config.compactHeader ? 'py-3 sm:py-4' : 'py-6 sm:py-8'
  }

  get tabsPaddingBottom(): string | null {
    // Just enough room under the title row for a header action button
    if (this.dense) return '3px !important'
    return this.config.tabs ? '15px !important' : null
  }

  // The dense header has 10px top / 3px bottom padding, so nudge header buttons up 3px to sit visually centered
  get actionsClass(): string {
    return this.dense ? 'sm:relative sm:-top-[3px]' : ''
  }

  // Normalizes plain-string crumbs to items, and drops empty labels (e.g. a name that hasn't loaded yet)
  get breadcrumbs(): BreadcrumbItem[] {
    const crumbs = this.config.breadcrumbs ?? []
    return crumbs.map((crumb) => (typeof crumb === 'string' ? { label: crumb } : crumb)).filter((crumb) => Boolean(crumb.label))
  }

  get otherInventoryType(): InventoryType | undefined {
    return this.config.tabs?.find((tab) => tab !== this.type)
  }

  // Pulls the toggle up beside the breadcrumbs, but never above the header's top padding
  get sideNavToggleClass(): string {
    if (!this.config.sideNavToggle) return ''
    return this.dense ? '-ml-10 -mt-2.5' : '-ml-10 -mt-3'
  }

  get titleClass(): string {
    return this.dense ? 'text-3xl leading-8' : 'text-3xl leading-7 sm:leading-10 md:text-4xl'
  }

  toggleDrawer() {
    this._drawerService.toggle()
  }

  async toggleInventoryType(type: InventoryType) {
    // Hack to route to reload the current component
    if (type !== this.type) {
      const newUrl = this._router.url.replace(/^\/(properties|taxlots)/, `/${type}`)
      await this._router.navigateByUrl('/', { skipLocationChange: true })
      await this._router.navigateByUrl(newUrl)
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
