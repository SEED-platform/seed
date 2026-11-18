import { downloadBlob } from './download-blob'

export const csvDownload = (title: string, data: Record<string, unknown>[]) => {
  const headers = Object.keys(data[0])
  const csv = [headers.join(','), ...data.map((row) => headers.map((header) => JSON.stringify(row[header] ?? '')).join(','))].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `${title}.csv`)
}
