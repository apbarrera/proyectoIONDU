export interface LoginCredentials {
  email: string;
  password: string;
}

/** Respuesta de POST /api/auth/login y /api/auth/refresh. */
export interface AuthTokenResponse {
  accessToken: string;
  tokenType: 'Bearer';
  /** Segundos de validez del token de acceso. */
  expiresIn: number;
  user: {
    id: string;
    email: string;
    createdAt: string;
  };
}
