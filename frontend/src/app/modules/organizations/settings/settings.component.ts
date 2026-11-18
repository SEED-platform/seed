import type { AfterViewInit, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild, ViewEncapsulation } from '@angular/core'
import type { MatDrawer } from '@angular/material/sidenav'
import { RouterOutlet } from '@angular/router'
import { ConfigService } from '@seed/api'
import type { NavigationItem } from '@seed/components'
import { DrawerService, VerticalNavigationComponent } from '@seed/components'
import { ScrollResetDirective } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, RouterOutlet, ScrollResetDirective, VerticalNavigationComponent],
})
export class SettingsComponent implements AfterViewInit, OnInit {
  @ViewChild('drawer') drawer!: MatDrawer
  private _drawerService = inject(DrawerService)
  private _deploymentConfigService = inject(ConfigService)

  readonly settingsNavigationMenu: NavigationItem[] = [
    {
      id: 'organizations/settings',
      title: 'Settings',
      type: 'group',
      children: [
        {
          id: 'organizations/settings/options',
          link: '/organizations/settings/options',
          title: 'Options',
          type: 'basic',
        },
        {
          id: 'organizations/settings/api-keys',
          link: '/organizations/settings/api-keys',
          title: 'API Keys',
          type: 'basic',
        },
        {
          id: 'organizations/settings/audit-template',
          link: '/organizations/settings/audit-template',
          title: 'Audit Template',
          type: 'basic',
        },
        {
          id: 'organizations/settings/display-fields',
          link: '/organizations/settings/display-fields',
          title: 'Display Fields',
          type: 'basic',
        },
        {
          id: 'organizations/settings/display-units',
          link: '/organizations/settings/display-units',
          title: 'Display Units',
          type: 'basic',
        },
        {
          id: 'organizations/settings/email',
          link: '/organizations/settings/email',
          title: 'Email',
          type: 'basic',
        },
        {
          id: 'organizations/settings/salesforce-building-integration',
          link: '/organizations/settings/salesforce-building-integration',
          title: 'Salesforce Integration',
          type: 'basic',
        },
        {
          id: 'organizations/settings/sharing',
          link: '/organizations/settings/sharing',
          title: 'Public Data Sharing',
          type: 'basic',
        },
        {
          id: 'organizations/settings/two-factor',
          link: '/organizations/settings/two-factor',
          title: 'Two-Factor Authentication',
          type: 'basic',
        },
        {
          id: 'organizations/settings/facilities-plan',
          link: '/organizations/settings/facilities-plan',
          title: 'Facilities Plan',
          type: 'basic',
        },
        {
          id: 'organizations/settings/ubid',
          link: '/organizations/settings/ubid',
          title: 'UBID',
          type: 'basic',
        },
        {
          type: 'divider',
        },
        {
          id: 'organizations/settings/maintenance',
          link: '/organizations/settings/maintenance',
          title: 'Maintenance',
          type: 'basic',
          classes: {
            title: 'text-warn-600 dark:text-warn-400',
          },
        },
      ],
    },
  ]

  ngOnInit() {
    this._deploymentConfigService.config$.subscribe(({ integrations }) => {
      if (!integrations.salesforce) {
        this.settingsNavigationMenu[0].children = this.settingsNavigationMenu[0].children.filter(
          ({ id }) => id !== 'organizations/settings/salesforce-building-integration',
        )
      }
    })
  }

  ngAfterViewInit() {
    this._drawerService.setDrawer(this.drawer)
  }
}
