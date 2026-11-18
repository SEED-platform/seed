// Generates a random id
export const randomId = (length = 10): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let name = ''

  for (let i = 0; i < length; ++i) {
    name += chars.charAt(Math.floor(Math.random() * chars.length))
  }

  return name
}
