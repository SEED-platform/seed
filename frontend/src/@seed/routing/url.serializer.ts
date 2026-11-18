import type { UrlSerializer, UrlTree } from '@angular/router'
import { DefaultUrlSerializer } from '@angular/router'

export class LowerCaseUrlSerializer implements UrlSerializer {
  private _default = new DefaultUrlSerializer()

  parse(url: string): UrlTree {
    const [path, query] = url.split('?')
    const normalized = query ? `${path.toLowerCase()}?${query}` : url.toLowerCase()
    return this._default.parse(normalized)
  }

  serialize(tree: UrlTree): string {
    return this._default.serialize(tree)
  }
}
