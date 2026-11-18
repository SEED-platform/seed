import { Injectable } from '@angular/core'
import { MockApiHandler } from '@seed/mock-api/index'
import type { MockApiMethods } from './mock-api.types'

@Injectable({ providedIn: 'root' })
export class MockApiService {
  private _handlers: Record<string, Map<string, MockApiHandler>> = {
    get: new Map<string, MockApiHandler>(),
    post: new Map<string, MockApiHandler>(),
    patch: new Map<string, MockApiHandler>(),
    delete: new Map<string, MockApiHandler>(),
    put: new Map<string, MockApiHandler>(),
    head: new Map<string, MockApiHandler>(),
    jsonp: new Map<string, MockApiHandler>(),
    options: new Map<string, MockApiHandler>(),
  }

  /**
   * Find the handler from the service
   * with the given method and url
   *
   * @param method
   * @param url
   */
  findHandler(
    method: string,
    url: string,
  ): {
    handler: MockApiHandler | undefined;
    urlParams: Record<string, string>;
  } {
    // Prepare the return object
    const matchingHandler: {
      handler: MockApiHandler | undefined;
      urlParams: Record<string, string>;
    } = {
      handler: undefined,
      urlParams: {},
    }

    // Split the url
    const urlParts = url.split('/')

    // Get all related request handlers
    const handlers = this._handlers[method.toLowerCase()]

    // Iterate through the handlers
    for (const [handlerUrl, handler] of handlers.entries()) {
      // Skip if there is already a matching handler
      if (matchingHandler.handler) {
        return
      }

      // Split the handler url
      const handlerUrlParts = handlerUrl.split('/')

      // Skip if the lengths of the urls we are comparing are not the same
      if (urlParts.length !== handlerUrlParts.length) {
        continue
      }

      // Compare
      const matches = handlerUrlParts.every((handlerUrlPart, index) => handlerUrlPart === urlParts[index] || handlerUrlPart.startsWith(':'))

      // If there is a match...
      if (matches) {
        // Assign the matching handler
        matchingHandler.handler = handler

        // Extract and assign the parameters
        matchingHandler.urlParams = Object.fromEntries(
          handlerUrlParts
            .map((handlerUrlPart, index) => (handlerUrlPart.startsWith(':') ? [handlerUrlPart.substring(1), urlParts[index]] : undefined))
            .filter(Boolean),
        ) as Record<string, string>
      }
    }

    return matchingHandler
  }

  /**
   * Register GET request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onGet(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('get', url, delay)
  }

  /**
   * Register POST request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onPost(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('post', url, delay)
  }

  /**
   * Register PATCH request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onPatch(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('patch', url, delay)
  }

  /**
   * Register DELETE request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onDelete(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('delete', url, delay)
  }

  /**
   * Register PUT request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onPut(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('put', url, delay)
  }

  /**
   * Register HEAD request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onHead(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('head', url, delay)
  }

  /**
   * Register JSONP request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onJsonp(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('jsonp', url, delay)
  }

  /**
   * Register OPTIONS request handler
   *
   * @param url - URL address of the mocked API endpoint
   * @param delay - Delay of the response in milliseconds
   */
  onOptions(url: string, delay?: number): MockApiHandler {
    return this._registerHandler('options', url, delay)
  }

  /**
   * Register and return a new instance of the handler
   *
   * @param method
   * @param url
   * @param delay
   * @private
   */
  private _registerHandler(method: MockApiMethods, url: string, delay?: number): MockApiHandler {
    // Create a new instance of MockApiRequestHandler
    const mockHttp = new MockApiHandler(url, delay)

    // Store the handler to access it from the interceptor
    this._handlers[method].set(url, mockHttp)

    // Return the instance
    return mockHttp
  }
}
