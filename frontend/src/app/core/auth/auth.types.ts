export type TokenResponse = {
  access?: string;
  refresh?: string;
  two_factor_required?: boolean;
  two_factor_method?: 'email' | 'token';
}

export type UserToken = {
  token_type: 'access' | 'refresh';
  exp: number;
  iat: number;
  jti: string;
  user_id: number;
}
