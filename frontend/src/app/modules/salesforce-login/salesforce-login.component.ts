import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { TranslocoDirective } from '@jsverse/transloco'
import { combineLatest, Subject, switchMap, takeUntil } from 'rxjs'
import type { Organization } from '@seed/api'
import { OrganizationService, SalesforcePortfolioService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

type AuthState = 'pending' | 'success' | 'failure'

@Component({
  selector: 'seed-salesforce-login',
  imports: [MaterialImports, TranslocoDirective],
  changeDetection: ChangeDetectionStrategy.Eager,
  templateUrl: './salesforce-login.component.html',
})
export class SalesforceLoginComponent implements OnDestroy, OnInit {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _salesforcePortfolioService = inject(SalesforcePortfolioService)
  private _organizationService = inject(OrganizationService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  state: AuthState = 'pending'
  errorMessage = ''
  canRetry = false
  private _organization: Organization | null = null

  ngOnInit() {
    combineLatest([this._route.queryParams, this._organizationService.currentOrganization$])
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(([params, organization]) => {
          this._organization = organization
          this.canRetry = organization.user_role !== 'viewer'
          return this._salesforcePortfolioService.getToken(params.code as string, organization.id)
        }),
      )
      .subscribe({
        next: (response) => {
          if (response.status === 'success') {
            this.state = 'success'
          } else {
            this.state = 'failure'
            this.errorMessage = response.response ?? ''
          }
        },
        error: () => {
          this.state = 'failure'
        },
      })
  }

  navigateToPortfolioSummary(): void {
    void this._router.navigate(['/insights/portfolio-summary'])
  }

  navigateToOrgSettings(): void {
    void this._router.navigate(['/organizations', this._organization?.id, 'settings'])
  }

  tryAgain(): void {
    if (!this._organization) return
    this._salesforcePortfolioService
      .getLoginUrl(this._organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(({ url }) => {
        if (url) window.location.href = url
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
