import type { HttpRequest } from '@angular/common/http'
import type { Observable } from 'rxjs'

export type MockApiReplyCallback
  = ((data: { request: HttpRequest<unknown>; urlParams: Record<string, string> }) => [number, unknown] | Observable<unknown>) | undefined

export type MockApiMethods = 'get' | 'post' | 'patch' | 'delete' | 'put' | 'head' | 'jsonp' | 'options'
