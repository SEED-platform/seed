import { Observable } from 'rxjs'

/**
 * Reads a blob as a data: URL, e.g., to show a fetched image where the CSP allows data: but not blob: URLs
 */
export const blobToDataUrl = (blob: Blob): Observable<string> => {
  return new Observable<string>((subscriber) => {
    const reader = new FileReader()
    reader.onload = () => {
      subscriber.next(reader.result as string)
      subscriber.complete()
    }
    reader.onerror = () => {
      subscriber.error(reader.error)
    }
    reader.readAsDataURL(blob)

    return () => {
      if (reader.readyState === FileReader.LOADING) reader.abort()
    }
  })
}
