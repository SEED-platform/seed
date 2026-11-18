import { OverlayContainer } from '@angular/cdk/overlay'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, DOCUMENT, inject, isDevMode, Renderer2, ViewEncapsulation } from '@angular/core'
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router'
import { combineLatest, filter, map, Subject, takeUntil } from 'rxjs'
import { UserService, VersionService } from '@seed/api'
import type { Scheme, SEEDConfig } from '@seed/services'
import { ConfigService, MediaWatcherService, PlatformService } from '@seed/services'
import { DevSettingsComponent } from './common/dev-settings/dev-settings.component'
import { EmptyLayoutComponent } from './layouts/empty/empty.component'
import { LandingLayoutComponent } from './layouts/landing/landing.component'
import { MainLayoutComponent } from './layouts/main/main.component'

@Component({
  selector: 'layout-wrapper',
  templateUrl: './layout.component.html',
  styleUrl: './layout.component.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [DevSettingsComponent, EmptyLayoutComponent, LandingLayoutComponent, MainLayoutComponent],
})
export class LayoutComponent implements OnInit, OnDestroy {
  private _route = inject(ActivatedRoute)
  private _configService = inject(ConfigService)
  private _document = inject(DOCUMENT)
  private _mediaWatcherService = inject(MediaWatcherService)
  private _overlayContainer = inject(OverlayContainer)
  private _platformService = inject(PlatformService)
  private _renderer = inject(Renderer2)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private _versionService = inject(VersionService)

  config: SEEDConfig
  layout: string
  scheme: Scheme
  theme: string
  isDevMode = isDevMode()
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ settings }) => {
      const { colorScheme } = settings
      this._configService.config = { scheme: colorScheme === 'dark' || colorScheme === 'light' ? colorScheme : 'auto' }
    })

    // Set the theme and scheme based on the configuration
    combineLatest([
      this._configService.config$,
      this._mediaWatcherService.onMediaQueryChange$(['(prefers-color-scheme: dark)', '(prefers-color-scheme: light)']),
    ])
      .pipe(
        takeUntil(this._unsubscribeAll$),
        map(([config, mql]) => {
          const options = {
            scheme: config.scheme,
            theme: config.theme,
          }

          // If the scheme is set to 'auto'...
          if (config.scheme === 'auto') {
            // Decide the scheme using the media query
            options.scheme = mql.breakpoints['(prefers-color-scheme: dark)'] ? 'dark' : 'light'
          }

          return options
        }),
      )
      .subscribe((options) => {
        // Store the options
        this.scheme = options.scheme
        this.theme = options.theme

        // Update the scheme and theme
        this._updateScheme()
        this._updateTheme()
      })

    this._versionService.version$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ version }) => {
      // Set the app version
      this._renderer.setAttribute(this._document.querySelector('[ng-version]'), 'seed-version', version)
    })

    // Subscribe to config changes
    this._configService.config$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((config: SEEDConfig) => {
      // Store the config
      this.config = config

      // Update the layout
      this._updateLayout()
    })

    // Subscribe to NavigationEnd event
    this._router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        // Update the layout
        this._updateLayout()
      })

    // Set the OS name
    this._renderer.addClass(this._document.body, this._platformService.osName)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  /**
   * Update the selected layout
   */
  private _updateLayout(): void {
    // Get the current activated route
    let route = this._route
    while (route.firstChild) {
      route = route.firstChild
    }

    // 1. Set the layout from the config
    this.layout = this.config.layout

    // 2. Get the query parameter from the current route and
    // set the layout and save the layout to the config
    const layoutFromQueryParam = route.snapshot.queryParamMap.get('layout')
    if (layoutFromQueryParam) {
      this.layout = layoutFromQueryParam
      if (this.config) {
        this.config.layout = layoutFromQueryParam
      }
    }

    // 3. Iterate through the paths and change the layout as we find
    // a config for it.
    //
    // The reason we do this is that there might be empty grouping
    // paths or component-less routes along the path. Because of that,
    // we cannot just assume that the layout configuration will be
    // in the last path's config or in the first path's config.
    //
    // So, we get all the paths that matched starting from root all
    // the way to the current activated route, walk through them one
    // by one and change the layout as we find the layout config. This
    // way, layout configuration can live anywhere within the path and
    // we won't miss it.
    //
    // Also, this will allow overriding the layout in any time so we
    // can have different layouts for different routes.
    const paths = route.pathFromRoot
    for (const path of paths) {
      // Check if there is a 'layout' data
      if (path.routeConfig?.data?.layout) {
        // Set the layout
        this.layout = path.routeConfig.data.layout as string
      }
    }
  }

  /**
   * Update the selected scheme
   *
   * @private
   */
  private _updateScheme(): void {
    // Remove class names for all schemes
    this._document.body.classList.remove('light', 'dark')
    this._overlayContainer.getContainerElement().classList.remove('light', 'dark')

    // Add class name for the currently selected scheme
    this._document.body.classList.add(this.scheme)
    this._overlayContainer.getContainerElement().classList.add(this.scheme)
  }

  /**
   * Update the selected theme
   *
   * @private
   */
  private _updateTheme(): void {
    // Find the class name for the previously selected theme and remove it
    for (const className of this._document.body.classList) {
      if (className.startsWith('theme-')) {
        this._document.body.classList.remove(className, className.split('-')[1])
      }
    }
    for (const className of this._overlayContainer.getContainerElement().classList) {
      if (className.startsWith('theme-')) {
        this._overlayContainer.getContainerElement().classList.remove(className, className.split('-')[1])
      }
    }

    // Add class name for the currently selected theme
    this._document.body.classList.add(this.theme)
    this._overlayContainer.getContainerElement().classList.add(this.theme)
  }
}
