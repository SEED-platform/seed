import { Hex, SHA256 } from 'crypto-es'

export const sha256 = (text: string) => SHA256(text).toString(Hex)
