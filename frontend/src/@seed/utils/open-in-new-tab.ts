export const openInNewTab = (url: string): void => {
  if (url) {
    Object.assign(document.createElement('a'), {
      href: url,
      rel: 'noopener noreferrer',
      target: '_blank',
    }).click()
  }
}
