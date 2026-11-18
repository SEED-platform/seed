import { config } from '@dotenvx/dotenvx'

config({ quiet: true })

export default {
  '/api/': {
    target: process.env.SEED_HOST ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    logLevel: 'debug',
    secure: false,
    onProxyReq: (proxyReq) => {
      const target = process.env.SEED_HOST ?? 'http://127.0.0.1:8000'
      proxyReq.setHeader('origin', target)
      proxyReq.setHeader('referer', `${target}/`)
    },
    onProxyRes: (proxyRes) => {
      // Fix http-proxy mangling 204 No Content responses
      // Some Django endpoints send a JSON body with 204, which causes parse errors
      if (proxyRes.statusCode === 204) {
        proxyRes.headers['content-length'] = '0'
        delete proxyRes.headers['content-type']
      }
    },
  },
  '/media/': {
    target: process.env.SEED_HOST ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    logLevel: 'debug',
    secure: false,
  },
  '/branding/': {
    target: process.env.SEED_HOST ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    logLevel: 'debug',
    secure: false,
  },
  '/static/': {
    target: process.env.SEED_HOST ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    logLevel: 'debug',
    secure: false,
  },
}
