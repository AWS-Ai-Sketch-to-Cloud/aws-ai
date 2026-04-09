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
  authProvider?: "password" | "github" | "google" | "kakao" | "naver";
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
  authProvider?: "password" | "github" | "google" | "kakao" | "naver";
}) {
  const session: StoredAuthSession = {
    loginId: payload.user.loginId,
    accessToken: payload.accessToken,
    refreshToken: payload.refreshToken,
    user: payload.user,
    apiBaseUrl: payload.apiBaseUrl,
    authProvider: payload.authProvider ?? "password",
  };

  sessionStorage.setItem("stc-auth", JSON.stringify(session));
}

export function getStoredAuthSession(): StoredAuthSession | null {
  try {
    const raw = sessionStorage.getItem("stc-auth");
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as StoredAuthSession;
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  sessionStorage.removeItem("stc-auth");
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
