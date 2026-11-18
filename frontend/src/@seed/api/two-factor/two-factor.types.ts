export type TwoFactorMethod = 'disabled' | 'email' | 'token'

export type TwoFactorMethods = {
  disabled: boolean;
  email: boolean;
  token: boolean;
}

export type SetTwoFactorMethodResponse = {
  status?: string;
  message?: string;
  methods?: TwoFactorMethods;
  qr_code?: string;
}

export type ResendTwoFactorTokenEmailResponse = {
  message: string;
}

export type GenerateTwoFactorQrCodeResponse = {
  qr_code: string;
}

export type VerifyTwoFactorCodeResponse = {
  success?: boolean;
  error?: string;
}
