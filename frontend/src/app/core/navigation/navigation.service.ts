import { inject, Injectable } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { DatasetService } from '@seed/api'
import type { NavigationItem, VerticalNavigationComponent } from '@seed/components'
import { SeedNavigationService } from '@seed/components'

@Injectable({ providedIn: 'root' })
export class NavigationService {
  private _datasetService = inject(DatasetService)
  private _seedNavigationService = inject(SeedNavigationService)
  private _router = inject(Router)
  private _route = inject(ActivatedRoute)

  private _badgeClasses = 'px-2 bg-primary-900 rounded-full'

  inventoryChildrenProperties: NavigationItem[] = [
    {
      id: 'properties',
      link: '/properties',
      title: 'Properties',
      icon: 'fa-solid:building',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/create',
      link: '/properties/create',
      title: 'Create Property',
      icon: 'fa-solid:plus',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/column-list-profiles',
      link: '/properties/column-list-profiles',
      title: 'Column Profiles',
      icon: 'fa-solid:sliders',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/cross-cycles',
      link: '/properties/cross-cycles',
      title: 'Cross Cycles',
      icon: 'fa-solid:shuffle',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/groups',
      link: '/properties/groups',
      title: 'Groups',
      icon: 'fa-solid:sitemap',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/map',
      link: '/properties/map',
      title: 'Map',
      icon: 'fa-solid:map-location-dot',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'properties/summary',
      link: '/properties/summary',
      title: 'Summary',
      icon: 'fa-solid:clipboard-list',
      type: 'basic',
      exactMatch: true,
    },
  ]
  inventoryChildrenTaxlots: NavigationItem[] = [
    {
      id: 'taxlots',
      link: '/taxlots',
      title: 'Tax Lots',
      icon: 'fa-solid:building',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'taxlots/create',
      link: '/taxlots/create',
      title: 'Create Tax Lot',
      icon: 'fa-solid:plus',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'taxlots/column-list-profiles',
      link: '/taxlots/column-list-profiles',
      title: 'Column Profiles',
      icon: 'fa-solid:sliders',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'taxlots/cross-cycles',
      link: '/taxlots/cross-cycles',
      title: 'Cross Cycles',
      icon: 'fa-solid:shuffle',
      type: 'basic',
      exactMatch: true,
    },
    {
      id: 'taxlots/map',
      link: '/taxlots/map',
      title: 'Map',
      icon: 'fa-solid:map-location-dot',
      type: 'basic',
      exactMatch: true,
    },
  ]

  navigation: NavigationItem[] = [
    {
      id: 'inventory',
      title: 'Inventory',
      type: 'collapsible',
      icon: 'fa-solid:building',
      // regexMatch: /^\/(properties|taxlots)/,
      children: this.inventoryChildrenProperties,
    },
    {
      id: 'data',
      title: 'Data',
      type: 'basic',
      icon: 'fa-solid:sitemap',
      link: '/data',
    },
    {
      id: 'organizations',
      title: 'Organizations',
      type: 'collapsible',
      icon: 'fa-solid:users',
      children: [
        {
          id: 'organizations/settings',
          link: '/organizations/settings',
          title: 'Settings',
          icon: 'fa-solid:gears',
          type: 'basic',
        },
        {
          id: 'organizations/access-level-tree',
          link: '/organizations/access-level-tree',
          title: 'Access Level Tree',
          icon: 'fa-solid:sitemap',
          type: 'basic',
        },
        {
          id: 'organizations/columns',
          link: '/organizations/columns/list/properties',
          title: 'Columns',
          icon: 'fa-solid:sliders',
          type: 'basic',
          regexMatch: /^\/organizations\/columns/,
        },
        {
          id: 'organizations/cycles',
          link: '/organizations/cycles',
          title: 'Cycles',
          icon: 'fa-solid:calendar-days',
          type: 'basic',
        },
        {
          id: 'organizations/data-quality',
          link: '/organizations/data-quality/properties',
          title: 'Data Quality',
          icon: 'fa-solid:flag',
          type: 'basic',
          regexMatch: /^\/organizations\/data-quality\/(properties|taxlots|goal)/,
        },
        {
          id: 'organizations/derived-columns',
          link: '/organizations/derived-columns/properties',
          title: 'Derived Columns',
          icon: 'fa-solid:calculator',
          type: 'basic',
          regexMatch: /^\/organizations\/derived-columns\/(properties|taxlots)/,
        },
        {
          id: 'organizations/email-templates',
          link: '/organizations/email-templates',
          title: 'Email Templates',
          icon: 'fa-solid:envelope',
          type: 'basic',
        },
        {
          id: 'organizations/labels',
          link: '/organizations/labels',
          title: 'Labels',
          icon: 'fa-solid:tags',
          type: 'basic',
        },
        {
          id: 'organizations/members',
          link: '/organizations/members',
          title: 'Members',
          icon: 'fa-solid:users',
          type: 'basic',
        },
      ],
    },
    {
      id: 'insights',
      title: 'Insights',
      type: 'collapsible',
      icon: 'fa-solid:gauge-high',
      children: [
        {
          id: 'insights/program-overview',
          link: '/insights/program-overview',
          title: 'Program Overview',
          icon: 'fa-solid:chart-column',
          type: 'basic',
        },
        {
          id: 'insights/property-insights',
          link: '/insights/property-insights',
          title: 'Property Insights',
          icon: 'fa-solid:chart-line',
          type: 'basic',
        },
        {
          id: 'insights/default-reports',
          link: '/insights/default-reports',
          title: 'Default Reports',
          icon: 'fa-solid:chart-column',
          type: 'basic',
        },
        {
          id: 'insights/custom-reports',
          link: '/insights/custom-reports',
          title: 'Custom Reports',
          icon: 'fa-solid:chart-area',
          type: 'basic',
        },
        {
          id: 'insights/portfolio-summary',
          link: '/insights/portfolio-summary',
          title: 'Portfolio Summary',
          icon: 'fa-solid:square-poll-horizontal',
          type: 'basic',
        },
        {
          id: 'insights/facilities-plan',
          link: '/insights/facilities-plan',
          title: 'Facilities Plan',
          icon: 'fa-solid:building-circle-check',
          type: 'basic',
        },
      ],
    },
    {
      id: 'analyses',
      title: 'Analyses',
      type: 'basic',
      icon: 'fa-solid:chart-bar',
      link: '/analyses',
    },
    {
      type: 'divider',
    },
    {
      id: 'documentation',
      title: 'Documentation',
      type: 'basic',
      icon: 'fa-solid:book',
      link: '/documentation',
    },
    {
      id: 'api',
      title: 'API Documentation',
      type: 'basic',
      icon: 'fa-solid:code',
      link: '/api-documentation',
    },
    {
      id: 'contact',
      title: 'Contact',
      type: 'basic',
      icon: 'fa-solid:circle-question',
      link: '/contact',
    },
    {
      id: 'about',
      title: 'About',
      type: 'basic',
      icon: 'fa-solid:circle-info',
      link: '/about',
    },
  ]

  constructor() {
    this._datasetService.datasetCount$.subscribe((count) => {
      // Use a timeout to avoid the race condition where mainNavigation hasn't been registered yet
      setTimeout(() => {
        this.updateBadge('data', 'mainNavigation', count)
      })
    })
    this.getNavigation()
  }

  getNavigation(hiddenNavigation: string[] = []): NavigationItem[] {
    const currentUrl = this._router.url
    if (currentUrl.toLowerCase().startsWith('/properties')) {
      this.navigation[0].children = this.inventoryChildrenProperties
    } else if (currentUrl.toLowerCase().startsWith('/taxlots')) {
      this.navigation[0].children = this.inventoryChildrenTaxlots
    }
    return this.navigation.filter((item) => !item.id || !hiddenNavigation.includes(item.id))
  }

  updateBadge(itemId: string, navigationName: string, title: string | number) {
    const dataComponent: VerticalNavigationComponent | undefined = this._seedNavigationService.getComponent(navigationName)

    if (dataComponent) {
      // Get the navigation item, update the badge and refresh the component
      const navigation = dataComponent.navigation()
      const item = this._seedNavigationService.getItem(itemId, navigation)
      item.badge = {
        title: String(title),
        classes: this._badgeClasses,
      }
      dataComponent.refresh()
    }
  }
}
