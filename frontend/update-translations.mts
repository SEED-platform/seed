import fs from 'node:fs/promises'
import path from 'node:path'
import AdmZip from 'adm-zip'
import { LokaliseApi } from '@lokalise/node-api'
import ora from 'ora'

const branch = 'angular'
const spinner = ora({
  text: `Fetching translations for the '${branch}' branch...`,
  spinner: {
    frames: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    interval: 80,
  },
}).start()

try {
  // Ignore certificate errors on networks with corporate proxies
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

  const lokaliseApi = new LokaliseApi({
    apiKey: process.env.LOKALISE_TOKEN,
    enableCompression: true,
  })

  const {
    items: [{ project_id }],
  } = await lokaliseApi.projects().list()

  const { bundle_url } = await lokaliseApi.files().download(`${project_id}:${branch}`, {
    add_newline_eof: true,
    format: 'json',
    indentation: '2sp',
    original_filenames: false,
  })

  const zipResponse = await fetch(bundle_url)

  const i18nDir = 'public/i18n'
  const zip = new AdmZip(Buffer.from(await zipResponse.arrayBuffer()))
  const resolvedI18nDir = path.resolve(i18nDir)

  await Promise.all(
    zip
      .getEntries()
      .filter((entry) => !entry.isDirectory)
      .map(async (entry) => {
        // Strip the top-level directory the bundle wraps its files in (equivalent to `strip: 1`)
        const relativePath = entry.entryName.split('/').slice(1).join('/')
        if (!relativePath) return

        const destination = path.resolve(resolvedI18nDir, relativePath)
        if (!destination.startsWith(resolvedI18nDir + path.sep)) {
          throw new Error(`Refusing to extract entry outside of target directory: ${entry.entryName}`)
        }

        await fs.mkdir(path.dirname(destination), { recursive: true })
        await fs.writeFile(destination, entry.getData())
      }),
  )

  // Fix UTC modified timestamps
  const now = new Date()
  const files = await fs.readdir(i18nDir)
  await Promise.all(
    files.map(async (file) => {
      const filePath = path.join(i18nDir, file)
      await fs.utimes(filePath, now, now)
    }),
  )

  spinner.succeed('Translations updated')
} catch (err) {
  spinner.fail('Failed to update translations')
  console.error(err)
}
