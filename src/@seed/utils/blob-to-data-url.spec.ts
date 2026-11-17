import { firstValueFrom } from 'rxjs'
import { blobToDataUrl } from './blob-to-data-url'

describe('blobToDataUrl', () => {
  it('reads a blob as a data: URL', async () => {
    const dataUrl = await firstValueFrom(blobToDataUrl(new Blob(['png'], { type: 'image/png' })))

    expect(dataUrl).toBe(`data:image/png;base64,${btoa('png')}`)
  })
})
