import type { OnDestroy, OnInit } from '@angular/core'
import { booleanAttribute, ChangeDetectionStrategy, ChangeDetectorRef, Component, inject, input, ViewEncapsulation } from '@angular/core'
import { Router } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { UserService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { sha256 } from '@seed/utils'
import { AuthService } from 'app/core/auth/auth.service'

@Component({
  selector: 'seed-user',
  templateUrl: './user.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  exportAs: 'user',
  imports: [MaterialImports],
})
export class UserComponent implements OnInit, OnDestroy {
  private _authService = inject(AuthService)
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _router = inject(Router)
  private _userService = inject(UserService)

  showAvatar = input(true, { transform: booleanAttribute })
  user: CurrentUser
  avatarUrl: string

  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Subscribe to user changes
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.user = currentUser
      this.avatarUrl = `https://www.gravatar.com/avatar/${sha256(this.user.email.toLowerCase())}?size=128&d=mp`

      // Mark for check
      this._changeDetectorRef.markForCheck()
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  signOut(): void {
    this._authService.signOut()
  }

  goToProfile() {
    void this._router.navigate(['/profile'])
  }

  goToSettings(): void {
    void this._router.navigate(['/profile/display'])
  }
}
