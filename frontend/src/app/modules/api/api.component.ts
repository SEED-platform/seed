import type { AfterViewInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { lastValueFrom, map } from 'rxjs'
import SwaggerUI from 'swagger-ui-dist/swagger-ui-es-bundle'
import { PageComponent } from '@seed/components'
import { AuthService } from '../../core/auth'

@Component({
  selector: 'seed-api',
  templateUrl: './api.component.html',
  styleUrl: './api.component.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageComponent],
})
export class ApiComponent implements AfterViewInit {
  private _route = inject(ActivatedRoute)
  private _authService = inject(AuthService)

  ngAfterViewInit(): void {
    SwaggerUI({
      dom_id: '#swagger-ui',
      spec: this._route.snapshot.data.schema as Record<string, unknown>,
      requestInterceptor: (request) => {
        return lastValueFrom(
          this._authService.isAuthenticated().pipe(
            map((isAuthenticated) => {
              if (isAuthenticated) {
                request.headers = {
                  ...(request.headers as Record<string, string>),
                  Authorization: `Bearer ${this._authService.accessToken}`,
                }
                return request
              } else {
                this._authService.signOut()
                location.reload()
              }
            }),
          ),
        )
      },
    })
  }
}
