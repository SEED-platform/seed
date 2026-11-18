/**
 * Saves a blob as a file named `filename`. Give files that users can upload a generic type (e.g.,
 * application/octet-stream) so an HTML or SVG file can never render from the app's origin
 */
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()

  // Revoke after the click is handled so the download isn't cancelled
  setTimeout(() => {
    URL.revokeObjectURL(url)
  })
}
