import { AsyncPipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { RouterLink } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { ConfigService, UserService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-home',
  templateUrl: './home.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AsyncPipe, MaterialImports, RouterLink, SharedImports],
})
export class HomeComponent implements OnDestroy, OnInit {
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  readonly config$ = inject(ConfigService).config$
  currentUser: CurrentUser

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.currentUser = currentUser
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
