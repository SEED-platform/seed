import { BreakpointObserver } from '@angular/cdk/layout'
import { inject, Injectable } from '@angular/core'
import { map, ReplaySubject } from 'rxjs'
import { screens } from '../config/config.screens'

@Injectable({ providedIn: 'root' })
export class MediaWatcherService {
  private _breakpointObserver = inject(BreakpointObserver)
  private _onMediaChange = new ReplaySubject<{ matchingAliases: string[]; matchingQueries: Record<string, string> }>(1)

  constructor() {
    const mediaQueries = Object.fromEntries(Object.entries(screens).map(([alias, minWidth]) => [alias, `(min-width: ${minWidth})`]))

    const aliasMap = Object.entries(mediaQueries).reduce<Record<string, string>>((acc, [alias, query]) => ({ ...acc, [query]: alias }), {})

    this._breakpointObserver
      .observe(Object.values(mediaQueries))
      .pipe(
        map(({ breakpoints }) => {
          // Prepare the observable values and set their defaults
          const matchingAliases: string[] = []
          const matchingQueries: Record<string, string> = {}

          for (const [query] of Object.entries(breakpoints).filter(([, isMatch]) => isMatch)) {
            // Find the alias of the matching query
            const alias = aliasMap[query]

            matchingAliases.push(alias)
            matchingQueries[alias] = query
          }

          // Execute the observable
          this._onMediaChange.next({
            matchingAliases,
            matchingQueries,
          })
        }),
      )
      .subscribe()
  }

  get onMediaChange$() {
    return this._onMediaChange.asObservable()
  }

  onMediaQueryChange$(query: string | string[]) {
    return this._breakpointObserver.observe(query)
  }
}
