import { FormEvent, ReactNode, useState } from "react";
import { Link, useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";
import { toast } from "../../hooks/use-toast";
import { getApiErrorMessage } from "../../lib/api-error";
import { saveAuthSession } from "../../lib/auth-session";

type LoginFieldErrors = {
  loginId?: string;
  password?: string;
  auth?: string;
};

type LoginResponse = {
  user: {
    userId: string;
    loginId: string;
    email: string;
    displayName: string;
    role: string;
  };
  accessToken: string;
  refreshToken: string;
};

type SocialProvider = "naver" | "google" | "kakao" | "github";

type SocialButton = {
  key: SocialProvider;
  label: string;
  brandColor: string;
  textColor: string;
  borderColor: string;
  enabled: boolean;
  logo: ReactNode;
};

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

const SOCIAL_BUTTONS: SocialButton[] = [
  {
    key: "naver",
    label: "네이버 로그인",
    brandColor: "#03C75A",
    textColor: "#FFFFFF",
    borderColor: "#03C75A",
    enabled: true,
    logo: <span className="text-base font-black tracking-[-0.03em]">N</span>,
  },
  {
    key: "google",
    label: "구글 로그인",
    brandColor: "#FFFFFF",
    textColor: "#202124",
    borderColor: "#DADCE0",
    enabled: true,
    logo: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
        <path
          fill="#4285F4"
          d="M21.6 12.23c0-.68-.06-1.18-.19-1.7H12v3.22h5.53c-.11.8-.72 2-2.08 2.82l-.02.11 3.04 2.35.21.02c1.92-1.77 3.02-4.37 3.02-7.42Z"
        />
        <path
          fill="#34A853"
          d="M12 22c2.7 0 4.96-.89 6.61-2.41l-3.15-2.45c-.84.59-1.96 1-3.46 1-2.64 0-4.88-1.73-5.68-4.14l-.1.01-3.16 2.44-.03.1C4.67 19.84 8.06 22 12 22Z"
        />
        <path
          fill="#FBBC05"
          d="M6.32 14c-.21-.61-.33-1.27-.33-1.95s.12-1.34.32-1.95l-.01-.13-3.2-2.48-.1.05A9.96 9.96 0 0 0 2 12.05c0 1.61.39 3.13 1.08 4.46L6.32 14Z"
        />
        <path
          fill="#EA4335"
          d="M12 5.91c1.9 0 3.18.82 3.91 1.5l2.86-2.8C16.95 2.91 14.7 2 12 2 8.06 2 4.67 4.16 3.02 7.45l3.31 2.56C7.12 7.64 9.36 5.91 12 5.91Z"
        />
      </svg>
    ),
  },
  {
    key: "kakao",
    label: "카카오톡 로그인",
    brandColor: "#FEE500",
    textColor: "#191919",
    borderColor: "#E7CF00",
    enabled: true,
    logo: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden="true">
        <path d="M12 4C6.48 4 2 7.58 2 12c0 2.82 1.81 5.3 4.54 6.72L5.5 22l3.87-2.12c.84.14 1.72.22 2.63.22 5.52 0 10-3.58 10-8s-4.48-8.1-10-8.1Z" />
      </svg>
    ),
  },
  {
    key: "github",
    label: "깃허브 로그인",
    brandColor: "#24292F",
    textColor: "#FFFFFF",
    borderColor: "#24292F",
    enabled: true,
    logo: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden="true">
        <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.38 7.86 10.9.58.1.79-.25.79-.56v-2.16c-3.2.69-3.87-1.35-3.87-1.35-.52-1.32-1.28-1.67-1.28-1.67-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.02 1.76 2.69 1.25 3.35.95.1-.74.4-1.25.72-1.53-2.55-.29-5.23-1.27-5.23-5.68 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.47.11-3.06 0 0 .97-.31 3.19 1.18a11.1 11.1 0 0 1 5.81 0c2.22-1.49 3.19-1.18 3.19-1.18.62 1.59.23 2.77.11 3.06.73.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.39-5.25 5.67.41.36.77 1.06.77 2.13v3.16c0 .31.21.66.8.55A11.52 11.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
      </svg>
    ),
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});

  const applyLoginApiError = (status: number, message: string) => {
    if (status === 401) {
      setFieldErrors({ password: message });
      return;
    }

    if (status === 422) {
      if (message.includes("아이디")) {
        setFieldErrors({ loginId: message });
        return;
      }

      if (message.includes("비밀번호")) {
        setFieldErrors({ password: message });
        return;
      }
    }

    setFieldErrors({ auth: message });
  };

  const startSocialLogin = (provider: SocialProvider) => {
    window.location.href = `${API_BASE_URL}/api/auth/social/${provider}/start`;
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    const nextErrors: LoginFieldErrors = {};

    if (!loginId.trim()) {
      nextErrors.loginId = "아이디를 입력해 주세요.";
    }
    if (!password) {
      nextErrors.password = "비밀번호를 입력해 주세요.";
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setIsSubmitting(false);
      return;
    }

    setFieldErrors({});

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ loginId, password }),
      });

      const data = (await res.json().catch(() => ({}))) as LoginResponse | unknown;

      if (!res.ok) {
        const message = getApiErrorMessage(data, "로그인에 실패했습니다.");
        applyLoginApiError(res.status, message);
        return;
      }

      const login = data as LoginResponse;
      saveAuthSession({
        user: login.user,
        accessToken: login.accessToken,
        refreshToken: login.refreshToken,
        apiBaseUrl: API_BASE_URL,
      });
      toast({
        title: "로그인 완료",
        description: "대시보드로 이동합니다.",
        variant: "success",
      });
      navigate("/dashboard");
    } catch (error) {
      setFieldErrors({
        auth:
          error instanceof TypeError
            ? "서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해 주세요."
            : error instanceof Error
              ? error.message
              : "로그인 중 오류가 발생했습니다.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <PageMeta title="로그인 | Sketch-to-Cloud" description="Sketch-to-Cloud 로그인" />
      <div className="relative min-h-screen overflow-hidden bg-[#FDFDFD] px-6 py-10 text-[#202020]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,153,0,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(73,205,223,0.18),_transparent_28%)]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center">
          <div className="grid w-full gap-8 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="hidden rounded-3xl border border-[#E7E7E7] bg-white/80 p-10 backdrop-blur lg:block">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#49CDDF]">
                Sketch to Cloud
              </p>
              <h1 className="mt-6 max-w-xl text-5xl font-semibold leading-tight">
                스케치와 텍스트를 AWS 설계 파이프라인으로 바로 연결합니다.
              </h1>
            </section>

            <section className="rounded-3xl border border-[#E7E7E7] bg-white p-8 text-gray-900 shadow-2xl shadow-[#49CDDF]/10 backdrop-blur sm:p-10">
              <div className="mx-auto max-w-md">
                <h2 className="mt-4 text-3xl font-semibold">로그인</h2>
                <p className="mt-3 text-sm leading-6 text-gray-500">
                  소셜 계정으로 빠르게 시작하거나 기존 ID로 로그인할 수 있습니다.
                </p>

                <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">로그인 ID</span>
                    <input
                      className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                        fieldErrors.loginId
                          ? "border-red-400 focus:border-red-500"
                          : "border-gray-200 focus:border-[#49CDDF]"
                      }`}
                      value={loginId}
                      onChange={(event) => {
                        setLoginId(event.target.value.replace(/\s/g, "").toLowerCase());
                        setFieldErrors((current) => ({
                          ...current,
                          loginId: undefined,
                          auth: undefined,
                        }));
                      }}
                      placeholder="아이디 입력"
                      autoCapitalize="none"
                      autoCorrect="off"
                    />
                    {fieldErrors.loginId ? (
                      <p className="mt-2 text-sm font-medium text-red-500">{fieldErrors.loginId}</p>
                    ) : null}
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">비밀번호</span>
                    <input
                      type="password"
                      className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                        fieldErrors.password || fieldErrors.auth
                          ? "border-red-400 focus:border-red-500"
                          : "border-gray-200 focus:border-[#49CDDF]"
                      }`}
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value.replace(/\s/g, ""));
                        setFieldErrors((current) => ({
                          ...current,
                          password: undefined,
                          auth: undefined,
                        }));
                      }}
                      placeholder="비밀번호 입력"
                    />
                    {fieldErrors.password ? (
                      <p className="mt-2 text-sm font-medium text-red-500">{fieldErrors.password}</p>
                    ) : fieldErrors.auth ? (
                      <p className="mt-2 text-sm font-medium text-red-500">{fieldErrors.auth}</p>
                    ) : null}
                  </label>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-[#FF9900] px-4 text-sm font-semibold text-white transition hover:bg-[#e68a00] disabled:opacity-60"
                  >
                    {isSubmitting ? "로그인 중..." : "로그인"}
                  </button>

                  <div className="flex items-center gap-3 py-1">
                    <div className="h-px flex-1 bg-gray-200" />
                    <span className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-400">
                      또는 소셜 로그인
                    </span>
                    <div className="h-px flex-1 bg-gray-200" />
                  </div>

                  <div className="space-y-3">
                    {SOCIAL_BUTTONS.map((socialButton) => (
                      <button
                        key={socialButton.key}
                        type="button"
                        disabled={!socialButton.enabled}
                        onClick={() => startSocialLogin(socialButton.key)}
                        className="flex h-12 w-full items-center rounded-xl border px-4 text-left shadow-sm transition duration-150 hover:brightness-[0.96] hover:shadow-md hover:shadow-black/10 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:brightness-100 disabled:hover:shadow-sm"
                        style={{
                          backgroundColor: socialButton.brandColor,
                          color: socialButton.textColor,
                          borderColor: socialButton.borderColor,
                        }}
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-black/10">
                          {socialButton.logo}
                        </span>
                        <span className="flex-1 text-center pr-8 text-sm font-bold tracking-[0.02em]">
                          {socialButton.label}
                        </span>
                      </button>
                    ))}
                  </div>

                  <p className="text-center text-sm text-gray-600">
                    아직 회원이 아니신가요?{" "}
                    <Link
                      to="/signup"
                      className="font-semibold text-[#49CDDF] transition hover:text-[#2db7ca]"
                    >
                      회원가입
                    </Link>
                  </p>
                </form>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
