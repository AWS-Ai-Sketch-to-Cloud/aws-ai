import { FormEvent, ReactNode, useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  ArrowRight,
  Bot,
  Cloud,
  Info,
  Sparkles,
  Workflow,
} from "lucide-react";
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
  title: string;
  tooltip?: string;
  brandColor: string;
  iconColor: string;
  borderColor: string;
  buttonClassName?: string;
  iconWrapperClassName?: string;
  logo: ReactNode;
};

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

const SOCIAL_BUTTONS: SocialButton[] = [
  {
    key: "naver",
    title: "네이버로 로그인",
    brandColor: "#03A94D",
    iconColor: "#FFFFFF",
    borderColor: "#03A94D",
    buttonClassName:
      "h-12 w-12 rounded-full p-0 shadow-none hover:translate-y-0 hover:brightness-95 hover:shadow-none",
    iconWrapperClassName: "h-12 w-12",
    logo: (
      <img
        src="/NAVER_login_Light_EN_green_icon_H48.png"
        alt=""
        aria-hidden="true"
        className="h-full w-full rounded-full object-cover"
      />
    ),
  },
  {
    key: "google",
    title: "Google로 로그인",
    brandColor: "#FFFFFF",
    iconColor: "#202124",
    borderColor: "#747775",
    buttonClassName:
      "h-12 w-12 rounded-full shadow-none hover:translate-y-0 hover:shadow-[0_1px_2px_0_rgba(60,64,67,0.3),0_1px_3px_1px_rgba(60,64,67,0.15)]",
    iconWrapperClassName: "h-5 w-5",
    logo: (
      <svg viewBox="0 0 48 48" className="h-full w-full" aria-hidden="true">
        <path
          fill="#EA4335"
          d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
        />
        <path
          fill="#4285F4"
          d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
        />
        <path
          fill="#FBBC05"
          d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
        />
        <path
          fill="#34A853"
          d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
        />
        <path fill="none" d="M0 0h48v48H0z" />
      </svg>
    ),
  },
  {
    key: "kakao",
    title: "카카오로 로그인",
    brandColor: "#FEE500",
    iconColor: "#191919",
    borderColor: "#E7CF00",
    buttonClassName:
      "h-12 w-12 rounded-full shadow-none hover:translate-y-0 hover:brightness-95 hover:shadow-none",
    iconWrapperClassName: "h-7 w-7",
    logo: (
      <svg
        viewBox="0 0 24 24"
        className="h-full w-full fill-current"
        aria-hidden="true"
      >
        <path d="M12 4C6.48 4 2 7.58 2 12c0 2.82 1.81 5.3 4.54 6.72L5.5 22l3.87-2.12c.84.14 1.72.22 2.63.22 5.52 0 10-3.58 10-8s-4.48-8.1-10-8.1Z" />
      </svg>
    ),
  },
  {
    key: "github",
    title: "GitHub로 로그인",
    tooltip: "GitHub 저장소를 바로 불러오려면 GitHub 로그인이 가장 빠릅니다.",
    brandColor: "#24292F",
    iconColor: "#FFFFFF",
    borderColor: "#24292F",
    buttonClassName:
      "h-12 w-12 rounded-full shadow-none hover:translate-y-0 hover:brightness-110 hover:shadow-none",
    iconWrapperClassName: "h-7 w-7",
    logo: (
      <svg
        viewBox="0 0 24 24"
        className="h-full w-full fill-current"
        aria-hidden="true"
      >
        <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.38 7.86 10.9.58.1.79-.25.79-.56v-2.16c-3.2.69-3.87-1.35-3.87-1.35-.52-1.32-1.28-1.67-1.28-1.67-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.02 1.76 2.69 1.25 3.35.95.1-.74.4-1.25.72-1.53-2.55-.29-5.23-1.27-5.23-5.68 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.47.11-3.06 0 0 .97-.31 3.19 1.18a11.1 11.1 0 0 1 5.81 0c2.22-1.49 3.19-1.18 3.19-1.18.62 1.59.23 2.77.11 3.06.73.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.39-5.25 5.67.41.36.77 1.06.77 2.13v3.16c0 .31.21.66.8.55A11.52 11.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
      </svg>
    ),
  },
];

const FEATURE_ITEMS = [
  {
    icon: Bot,
    title: "AI 설계 해석",
    description: "요구사항과 스케치를 읽고 AWS 아키텍처 초안을 자동 생성합니다.",
  },
  {
    icon: Workflow,
    title: "Terraform 생성",
    description: "검토 가능한 IaC 코드와 리소스 구성을 한 흐름으로 정리합니다.",
  },
  {
    icon: Cloud,
    title: "배포 준비 단축",
    description: "인프라 검토, 예산 감각, 배포 전 체크포인트를 한 화면에서 봅니다.",
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState<SocialProvider | null>(null);
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});

  const applyLoginApiError = (status: number, message: string) => {
    if (status === 401) {
      setFieldErrors({ password: message });
      return;
    }

    if (status === 422) {
      if (message.includes("아이디") || message.toLowerCase().includes("login")) {
        setFieldErrors({ loginId: message });
        return;
      }

      if (
        message.includes("비밀번호") ||
        message.toLowerCase().includes("password")
      ) {
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
      nextErrors.loginId = "로그인 ID를 입력해 주세요.";
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
        description: "워크스페이스로 이동합니다.",
        variant: "success",
      });
      navigate("/workspace");
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
      <PageMeta
        title="로그인 | Sketch-to-Cloud"
        description="Sketch-to-Cloud 로그인 페이지"
      />
      <div className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,#f7fbff_0%,#ecf3ff_100%)] text-[#122033]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(72,123,255,0.2),_transparent_30%),radial-gradient(circle_at_85%_20%,_rgba(32,201,151,0.16),_transparent_24%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,32,51,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(18,32,51,0.04)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(circle_at_center,black,transparent_85%)]" />

        <div className="relative mx-auto flex min-h-screen w-full max-w-7xl items-center px-6 py-10 sm:px-8 lg:px-10">
          <div className="grid w-full gap-8 xl:grid-cols-[1.08fr_0.92fr]">
            <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-[#0f1728] px-7 py-8 text-white shadow-[0_24px_80px_rgba(15,23,40,0.24)] sm:px-10 sm:py-10">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(72,123,255,0.42),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(32,201,151,0.22),_transparent_26%)]" />
              <div className="relative">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-4 py-2 text-sm text-white/80 backdrop-blur">
                  <Sparkles className="h-4 w-4 text-[#58e1c1]" />
                  New infrastructure workflow
                </div>

                <h1 className="mt-6 max-w-2xl text-4xl font-semibold leading-tight sm:text-5xl">
                  아이디어를 입력하면
                  <br />
                  배포 가능한 AWS 설계 흐름으로 이어집니다.
                </h1>
                <p className="mt-5 max-w-xl text-base leading-7 text-white/72 sm:text-lg">
                  Sketch-to-Cloud는 스케치, 요구사항, 저장소 정보를 바탕으로
                  인프라 구조와 Terraform 초안을 연결하는 AI 워크벤치입니다.
                </p>

                <div className="mt-8 space-y-4">
                  {FEATURE_ITEMS.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div
                        key={item.title}
                        className="rounded-2xl border border-white/12 bg-white/6 p-5 backdrop-blur"
                      >
                        <div className="flex items-start gap-4">
                          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
                            <Icon className="h-5 w-5 text-[#58e1c1]" />
                          </div>
                          <div>
                            <h2 className="text-lg font-semibold text-white">{item.title}</h2>
                            <p className="mt-2 text-sm leading-6 text-white/68">
                              {item.description}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>

            <section className="relative rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-[0_24px_80px_rgba(72,123,255,0.14)] backdrop-blur sm:p-8">
              <div className="absolute inset-x-0 top-0 h-1 rounded-t-[2rem] bg-[linear-gradient(90deg,#487bff_0%,#58e1c1_100%)]" />
              <div className="mx-auto max-w-md">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#edf3ff] text-[#487bff]">
                    <Cloud className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#487bff]">
                      Sketch-to-Cloud
                    </p>
                    <p className="text-sm text-[#65748b]">AI 기반 AWS 설계 워크스페이스</p>
                  </div>
                </div>

                <h2 className="mt-8 text-3xl font-semibold tracking-[-0.03em] text-[#122033]">
                  로그인
                </h2>
                <p className="mt-3 text-sm leading-6 text-[#65748b]">
                  소셜 계정으로 빠르게 시작하거나 기존 로그인 ID로 계속 진행할 수
                  있습니다.
                </p>

                <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[#314257]">
                      로그인 ID
                    </span>
                    <input
                      className={`h-12 w-full rounded-2xl border bg-[#f9fbff] px-4 text-sm outline-none transition ${
                        fieldErrors.loginId
                          ? "border-red-400 focus:border-red-500"
                          : "border-[#d9e4f2] focus:border-[#487bff]"
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
                      placeholder="아이디를 입력하세요"
                      autoCapitalize="none"
                      autoCorrect="off"
                    />
                    {fieldErrors.loginId ? (
                      <p className="mt-2 text-sm font-medium text-red-500">
                        {fieldErrors.loginId}
                      </p>
                    ) : null}
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[#314257]">
                      비밀번호
                    </span>
                    <input
                      type="password"
                      className={`h-12 w-full rounded-2xl border bg-[#f9fbff] px-4 text-sm outline-none transition ${
                        fieldErrors.password || fieldErrors.auth
                          ? "border-red-400 focus:border-red-500"
                          : "border-[#d9e4f2] focus:border-[#487bff]"
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
                      placeholder="비밀번호를 입력하세요"
                    />
                    {fieldErrors.password ? (
                      <p className="mt-2 text-sm font-medium text-red-500">
                        {fieldErrors.password}
                      </p>
                    ) : fieldErrors.auth ? (
                      <p className="mt-2 text-sm font-medium text-red-500">
                        {fieldErrors.auth}
                      </p>
                    ) : null}
                  </label>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-[#122033] px-4 text-sm font-semibold text-white transition hover:bg-[#1b2c44] disabled:opacity-60"
                  >
                    {isSubmitting ? "로그인 중..." : "로그인"}
                    {!isSubmitting ? <ArrowRight className="h-4 w-4" /> : null}
                  </button>

                  <div className="flex items-center gap-3 py-1">
                    <div className="h-px flex-1 bg-[#d9e4f2]" />
                    <span className="text-xs font-semibold uppercase tracking-[0.24em] text-[#7f8ca0]">
                      Social
                    </span>
                    <div className="h-px flex-1 bg-[#d9e4f2]" />
                  </div>

                  <div className="flex items-center justify-center gap-5 py-1">
                    {SOCIAL_BUTTONS.map((socialButton) => (
                      <div
                        key={socialButton.key}
                        className={`relative ${activeTooltip === socialButton.key ? "z-[200]" : ""}`}
                        onMouseEnter={() =>
                          setActiveTooltip(socialButton.tooltip ? socialButton.key : null)
                        }
                        onMouseLeave={() => setActiveTooltip(null)}
                        onFocus={() =>
                          setActiveTooltip(socialButton.tooltip ? socialButton.key : null)
                        }
                        onBlur={() => setActiveTooltip(null)}
                      >
                        <button
                          type="button"
                          onClick={() => startSocialLogin(socialButton.key)}
                          aria-label={socialButton.title}
                          title={socialButton.title}
                          className={`relative inline-flex h-12 w-12 items-center justify-center border transition duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#487bff] focus-visible:ring-offset-2 ${socialButton.buttonClassName ?? ""}`}
                          style={{
                            backgroundColor: socialButton.brandColor,
                            color: socialButton.iconColor,
                            borderColor: socialButton.borderColor,
                          }}
                        >
                          <span
                            className={`flex items-center justify-center ${
                              socialButton.iconWrapperClassName ?? ""
                            }`}
                          >
                            {socialButton.logo}
                          </span>
                        </button>

                        {socialButton.key === "github" ? (
                          <span className="pointer-events-none absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full border border-white bg-[#122033] text-white shadow-lg">
                            <Info className="h-3.5 w-3.5" />
                          </span>
                        ) : null}

                        {socialButton.tooltip && activeTooltip === socialButton.key ? (
                          <span className="pointer-events-none absolute left-1/2 top-0 z-[220] flex w-72 -translate-x-1/2 -translate-y-[calc(100%+1rem)] flex-col items-center rounded-2xl bg-[#122033] px-5 py-4 text-center text-white shadow-2xl">
                            <span className="text-sm font-semibold leading-6 text-white">
                              GitHub로 로그인하면 저장소 연동이 바로 가능합니다.
                            </span>
                            <span className="mt-2 text-xs leading-5 text-white/75">
                              프로젝트 구조 분석과 리포지토리 연결 흐름을 빠르게 시작할
                              수 있습니다.
                            </span>
                            <span className="absolute -bottom-2 h-4 w-4 rotate-45 bg-[#122033]" />
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-[#d9e4f2] bg-[#f8fbff] px-4 py-4">
                    <p className="text-sm font-semibold text-[#122033]">처음 사용하는 계정인가요?</p>
                    <p className="mt-1 text-sm leading-6 text-[#65748b]">
                      회원가입 후 로그인하면 워크스페이스에서 아키텍처 생성 흐름을 바로
                      사용할 수 있습니다.
                    </p>
                    <Link
                      to="/signup"
                      className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[#487bff] transition hover:text-[#2f64ef]"
                    >
                      회원가입으로 이동
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </form>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
