import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import {
  ArrowRight,
  CheckCircle2,
  Cloud,
  ShieldCheck,
  Sparkles,
  UserRoundPlus,
} from "lucide-react";
import PageMeta from "../../components/common/PageMeta";
import { toast } from "../../hooks/use-toast";
import { getApiErrorMessage } from "../../lib/api-error";
import { validateLoginId, validatePassword } from "../../lib/auth-validation";

type SignupFieldErrors = {
  displayName?: string;
  loginId?: string;
  email?: string;
  password?: string;
  submit?: string;
};

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

const CHECKLIST = [
  "로그인 ID는 영문 소문자와 숫자만 사용",
  "비밀번호는 8자 이상, 128자 이하",
  "대문자/소문자/숫자/특수문자 중 2종류 이상 포함",
];

export default function SignupPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [loginId, setLoginId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<SignupFieldErrors>({});

  const signupContext = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return {
      provider: params.get("provider"),
      email: params.get("email"),
      displayName: params.get("displayName"),
    };
  }, [location.search]);

  useEffect(() => {
    if (signupContext.email) {
      setEmail(signupContext.email);
    }
    if (signupContext.displayName) {
      setDisplayName(signupContext.displayName);
    }
  }, [signupContext.displayName, signupContext.email]);

  const applyRegisterApiError = (status: number, message: string) => {
    if (status === 409) {
      if (message.includes("아이디") || message.toLowerCase().includes("login")) {
        setFieldErrors({ loginId: message });
        return;
      }

      if (message.includes("이메일") || message.toLowerCase().includes("email")) {
        setFieldErrors({ email: message });
        return;
      }
    }

    setFieldErrors({ submit: message });
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    const nextErrors: SignupFieldErrors = {};

    if (!displayName.trim()) {
      nextErrors.displayName = "이름을 입력해 주세요.";
    }

    const loginIdError = validateLoginId(loginId);
    if (loginIdError) {
      nextErrors.loginId = loginIdError;
    }

    if (!email.trim()) {
      nextErrors.email = "이메일을 입력해 주세요.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "올바른 이메일 형식으로 입력해 주세요.";
    }

    const passwordError = validatePassword(password);
    if (passwordError) {
      nextErrors.password = passwordError;
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setIsSubmitting(false);
      return;
    }

    setFieldErrors({});

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ displayName, loginId, email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        applyRegisterApiError(
          res.status,
          getApiErrorMessage(body, "회원가입에 실패했습니다."),
        );
        return;
      }

      toast({
        title: "회원가입 완료",
        description: "이제 로그인할 수 있습니다.",
        variant: "success",
      });
      navigate("/login");
    } catch (error) {
      setFieldErrors({
        submit:
          error instanceof TypeError
            ? "서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해 주세요."
            : error instanceof Error
              ? error.message
              : "회원가입 중 오류가 발생했습니다.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <PageMeta
        title="회원가입 | Sketch-to-Cloud"
        description="Sketch-to-Cloud 회원가입 페이지"
      />
      <div className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,#f7fbff_0%,#ecf3ff_100%)] text-[#122033]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(72,123,255,0.2),_transparent_30%),radial-gradient(circle_at_85%_20%,_rgba(32,201,151,0.16),_transparent_24%)]" />
        <div className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-6 py-10 sm:px-8 lg:px-10">
          <div className="grid w-full gap-8 xl:grid-cols-[0.96fr_1.04fr]">
            <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-[0_24px_80px_rgba(72,123,255,0.14)] backdrop-blur sm:p-8">
              <div className="absolute inset-x-0 top-0 h-1 rounded-t-[2rem] bg-[linear-gradient(90deg,#58e1c1_0%,#487bff_100%)]" />
              <div className="mx-auto max-w-md">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#edf3ff] text-[#487bff]">
                    <UserRoundPlus className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#487bff]">
                      Create account
                    </p>
                    <p className="text-sm text-[#65748b]">워크스페이스를 시작할 계정을 만듭니다</p>
                  </div>
                </div>

                <h1 className="mt-8 text-3xl font-semibold tracking-[-0.03em] text-[#122033]">
                  회원가입
                </h1>
                <p className="mt-3 text-sm leading-6 text-[#65748b]">
                  기본 정보를 입력하면 Sketch-to-Cloud 대시보드와 AWS 설계 흐름을 바로
                  사용할 수 있습니다.
                </p>

                {signupContext.provider ? (
                  <div className="mt-5 rounded-2xl border border-[#cde3ff] bg-[#f3f8ff] px-4 py-4 text-sm text-[#31517e]">
                    <p className="font-semibold text-[#122033]">
                      {signupContext.provider.toUpperCase()} 로그인 연동 대기 중
                    </p>
                    <p className="mt-1 leading-6">
                      회원가입을 마치면 소셜 로그인 흐름으로 다시 이어집니다.
                    </p>
                  </div>
                ) : null}

                <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[#314257]">이름</span>
                    <input
                      className={`h-12 w-full rounded-2xl border bg-[#f9fbff] px-4 text-sm outline-none transition ${
                        fieldErrors.displayName
                          ? "border-red-400 focus:border-red-500"
                          : "border-[#d9e4f2] focus:border-[#487bff]"
                      }`}
                      value={displayName}
                      onChange={(event) => {
                        setDisplayName(event.target.value);
                        setFieldErrors((current) => ({
                          ...current,
                          displayName: undefined,
                          submit: undefined,
                        }));
                      }}
                      placeholder="서비스에 표시할 이름을 입력하세요"
                    />
                    {fieldErrors.displayName ? (
                      <p className="mt-2 text-sm font-medium text-red-500">
                        {fieldErrors.displayName}
                      </p>
                    ) : null}
                  </label>

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
                          submit: undefined,
                        }));
                      }}
                      placeholder="영문 소문자와 숫자만 사용할 수 있습니다"
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
                    <span className="mb-2 block text-sm font-medium text-[#314257]">이메일</span>
                    <input
                      type="text"
                      inputMode="email"
                      className={`h-12 w-full rounded-2xl border bg-[#f9fbff] px-4 text-sm outline-none transition ${
                        fieldErrors.email
                          ? "border-red-400 focus:border-red-500"
                          : "border-[#d9e4f2] focus:border-[#487bff]"
                      }`}
                      value={email}
                      onChange={(event) => {
                        setEmail(event.target.value);
                        setFieldErrors((current) => ({
                          ...current,
                          email: undefined,
                          submit: undefined,
                        }));
                      }}
                      placeholder="sample@company.com"
                    />
                    {fieldErrors.email ? (
                      <p className="mt-2 text-sm font-medium text-red-500">{fieldErrors.email}</p>
                    ) : null}
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[#314257]">
                      비밀번호
                    </span>
                    <input
                      type="password"
                      className={`h-12 w-full rounded-2xl border bg-[#f9fbff] px-4 text-sm outline-none transition ${
                        fieldErrors.password
                          ? "border-red-400 focus:border-red-500"
                          : "border-[#d9e4f2] focus:border-[#487bff]"
                      }`}
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value.replace(/\s/g, ""));
                        setFieldErrors((current) => ({
                          ...current,
                          password: undefined,
                          submit: undefined,
                        }));
                      }}
                      placeholder="안전한 비밀번호를 입력하세요"
                    />
                    {fieldErrors.password ? (
                      <p className="mt-2 text-sm font-medium text-red-500">
                        {fieldErrors.password}
                      </p>
                    ) : (
                      <div className="mt-3 rounded-2xl border border-[#d9e4f2] bg-[#f8fbff] px-4 py-4">
                        <div className="flex items-center gap-2 text-[#122033]">
                          <ShieldCheck className="h-4 w-4 text-[#487bff]" />
                          <p className="text-sm font-semibold">비밀번호 규칙</p>
                        </div>
                        <div className="mt-3 space-y-2">
                          {CHECKLIST.map((item) => (
                            <div
                              key={item}
                              className="flex items-start gap-2 text-sm leading-6 text-[#65748b]"
                            >
                              <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#58e1c1]" />
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </label>

                  {fieldErrors.submit ? (
                    <p className="text-sm font-medium text-red-500">{fieldErrors.submit}</p>
                  ) : null}

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-[#122033] px-4 text-sm font-semibold text-white transition hover:bg-[#1b2c44] disabled:opacity-60"
                  >
                    {isSubmitting ? "계정 생성 중..." : "회원가입"}
                    {!isSubmitting ? <ArrowRight className="h-4 w-4" /> : null}
                  </button>

                  <Link
                    to="/"
                    className="inline-flex h-12 w-full items-center justify-center rounded-2xl border border-[#d9e4f2] bg-white px-4 text-sm font-semibold text-[#314257] transition hover:border-[#487bff] hover:text-[#487bff]"
                  >
                    로그인으로 돌아가기
                  </Link>
                </form>
              </div>
            </section>

            <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-[#0f1728] px-7 py-8 text-white shadow-[0_24px_80px_rgba(15,23,40,0.24)] sm:px-10 sm:py-10">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(72,123,255,0.42),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(32,201,151,0.22),_transparent_26%)]" />
              <div className="relative">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-4 py-2 text-sm text-white/80 backdrop-blur">
                  <Sparkles className="h-4 w-4 text-[#58e1c1]" />
                  Setup your cloud workspace
                </div>

                <h2 className="mt-6 max-w-xl text-4xl font-semibold leading-tight sm:text-5xl">
                  설계 자동화를 시작할
                  <br />
                  작업 공간을 만드세요.
                </h2>
                <p className="mt-5 max-w-xl text-base leading-7 text-white/72 sm:text-lg">
                  계정을 만들면 요구사항 정리, 인프라 초안 생성, 비용 검토, GitHub 기반
                  분석 흐름까지 한 화면에서 이어집니다.
                </p>

                <div className="mt-8 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-3xl border border-white/12 bg-white/8 p-5 backdrop-blur">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
                      <Cloud className="h-5 w-5 text-[#58e1c1]" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold text-white">AWS 중심 워크플로우</h3>
                    <p className="mt-2 text-sm leading-6 text-white/68">
                      아키텍처 구상부터 Terraform 기반 초안 생성까지 연결된 경험을
                      제공합니다.
                    </p>
                  </div>

                  <div className="rounded-3xl border border-white/12 bg-white/8 p-5 backdrop-blur">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
                      <ShieldCheck className="h-5 w-5 text-[#58e1c1]" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold text-white">검토 가능한 결과물</h3>
                    <p className="mt-2 text-sm leading-6 text-white/68">
                      팀이 바로 확인할 수 있는 구조, 코드, 비용 감각을 함께 정리합니다.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
