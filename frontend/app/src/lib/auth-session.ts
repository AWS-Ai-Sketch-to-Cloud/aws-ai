export type AuthUser = {
  userId: string;
  loginId: string;
  email: string;
  displayName: string;
  role: string;
};

export type StoredAuthSession = {
  loginId: string;
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
  apiBaseUrl: string;
};

export type SocialCallbackPayload = {
  provider: string;
  user: AuthUser;
  accessToken: string;
  refreshToken: string;
};

export type SocialSignupPayload = {
  provider: string;
  providerUserId: string;
  email: string;
  displayName: string;
};

export function saveAuthSession(payload: {
  user: AuthUser;
  accessToken: string;
  refreshToken: string;
  apiBaseUrl: string;
}) {
  const session: StoredAuthSession = {
    loginId: payload.user.loginId,
    accessToken: payload.accessToken,
    refreshToken: payload.refreshToken,
    user: payload.user,
    apiBaseUrl: payload.apiBaseUrl,
  };

  sessionStorage.setItem("stc-auth", JSON.stringify(session));
}

function decodeEncodedPayload<T>(encodedPayload: string): T {
  const normalized = encodedPayload.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const decoded = new TextDecoder().decode(bytes);
  return JSON.parse(decoded) as T;
}

export function decodeSocialPayload(encodedPayload: string): SocialCallbackPayload {
  return decodeEncodedPayload<SocialCallbackPayload>(encodedPayload);
}

export function decodeSocialSignupPayload(encodedPayload: string): SocialSignupPayload {
  return decodeEncodedPayload<SocialSignupPayload>(encodedPayload);
}
