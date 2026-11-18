import type { OnDestroy, OnInit } from '@angular/core'
import { Component, inject } from '@angular/core'
import type { Observable } from 'rxjs'
import { Subject, takeUntil } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { Scheme } from '@seed/services'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

type ColorScheme = Exclude<Scheme, 'auto'>

@Component({
  selector: 'seed-profile-settings',
  templateUrl: './settings.component.html',
  imports: [MaterialImports, SharedImports],
})
export class ProfileSettingsComponent implements OnInit, OnDestroy {
  private _configService = inject(ConfigService)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  currentUser: CurrentUser
  saving = false
  scheme: ColorScheme
  scheme$: Observable<ColorScheme> = this._configService.scheme$

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.currentUser = currentUser
    })

    this.scheme$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((scheme) => {
      this.scheme = scheme
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  setScheme(scheme: ColorScheme): void {
    if (this.saving || !this.currentUser?.settings || this.currentUser.settings.colorScheme === scheme) return

    const previousScheme = this.currentUser.settings.colorScheme
    const settings = { ...this.currentUser.settings, colorScheme: scheme }

    this.saving = true
    this._configService.config = { scheme }
    this._organizationService
      .updateOrganizationUser(this.currentUser.org_user_id, this.currentUser.org_id, settings)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe({
        next: ({ data }) => {
          this.currentUser.settings = data.settings
          this.saving = false
          this._snackBar.success('Changes Saved')
        },
        error: () => {
          this._configService.config = { scheme: previousScheme ?? 'auto' }
          this.saving = false
        },
      })
  }
}
