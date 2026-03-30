import { FormEvent, useState } from "react";
import { Link } from "react-router";
import { useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";
import { toast } from "../../hooks/use-toast";
import { getApiErrorMessage } from "../../lib/api-error";

type LoginFieldErrors = {
  loginId?: string;
  password?: string;
  auth?: string;
};

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

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
      sessionStorage.setItem(
        "stc-auth",
        JSON.stringify({
          loginId: login.user.loginId,
          accessToken: login.accessToken,
          refreshToken: login.refreshToken,
          user: login.user,
          apiBaseUrl: API_BASE_URL,
        }),
      );
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
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#49CDDF]">Sketch to Cloud</p>
              <h1 className="mt-6 max-w-xl text-5xl font-semibold leading-tight">
                스케치와 텍스트를 AWS 설계 파이프라인으로 바로 연결합니다.
              </h1>
            </section>

            <section className="rounded-3xl border border-[#E7E7E7] bg-white p-8 text-gray-900 shadow-2xl shadow-[#49CDDF]/10 backdrop-blur sm:p-10">
              <div className="mx-auto max-w-md">
                <h2 className="mt-4 text-3xl font-semibold">로그인</h2>

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
                        setFieldErrors((current) => ({ ...current, loginId: undefined, auth: undefined }));
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
                        setFieldErrors((current) => ({ ...current, password: undefined, auth: undefined }));
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
                  <Link
                    to="/signup"
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl border border-gray-200 px-4 text-sm font-semibold text-gray-700 transition hover:border-[#49CDDF] hover:text-[#49CDDF]"
                  >
                    회원가입 페이지로 이동
                  </Link>
                </form>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
