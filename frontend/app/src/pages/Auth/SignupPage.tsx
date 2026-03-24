import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";
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

export default function SignupPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [loginId, setLoginId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<SignupFieldErrors>({});

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
        setFieldErrors({
          submit: getApiErrorMessage(body, "회원가입에 실패했습니다."),
        });
        return;
      }

      navigate("/");
    } catch (error) {
      setFieldErrors({
        submit:
          error instanceof Error
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
        description="Sketch-to-Cloud 회원가입"
      />
      <div className="relative min-h-screen overflow-hidden bg-[#FDFDFD] px-6 py-10 text-[#202020]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,153,0,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(73,205,223,0.18),_transparent_28%)]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center">
          <section className="w-full max-w-xl rounded-3xl border border-[#E7E7E7] bg-white p-8 text-gray-900 shadow-2xl shadow-[#49CDDF]/10 backdrop-blur sm:p-10">
            <div className="mx-auto max-w-md">
              <h2 className="mt-2 text-3xl font-semibold">회원가입</h2>
              <p className="mt-3 text-sm leading-6 text-gray-500">
                정보를 입력하면 계정이 생성됩니다.
              </p>

              <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">
                    이름
                  </span>
                  <input
                    className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                      fieldErrors.displayName
                        ? "border-red-400 focus:border-red-500"
                        : "border-gray-200 focus:border-[#49CDDF]"
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
                    placeholder="서비스에서 표시할 이름을 입력해 주세요."
                  />
                  {fieldErrors.displayName ? (
                    <p className="mt-2 text-sm font-medium text-red-500">
                      {fieldErrors.displayName}
                    </p>
                  ) : null}
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">
                    로그인 ID
                  </span>
                  <input
                    className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                      fieldErrors.loginId
                        ? "border-red-400 focus:border-red-500"
                        : "border-gray-200 focus:border-[#49CDDF]"
                    }`}
                    value={loginId}
                    onChange={(event) => {
                      setLoginId(
                        event.target.value.replace(/\s/g, "").toLowerCase(),
                      );
                      setFieldErrors((current) => ({
                        ...current,
                        loginId: undefined,
                        submit: undefined,
                      }));
                    }}
                    placeholder="영문 소문자와 숫자만 사용할 수 있습니다."
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
                  <span className="mb-2 block text-sm font-medium text-gray-700">
                    이메일
                  </span>
                  <input
                    type="text"
                    inputMode="email"
                    className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                      fieldErrors.email
                        ? "border-red-400 focus:border-red-500"
                        : "border-gray-200 focus:border-[#49CDDF]"
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
                    placeholder="이메일을 입력해 주세요."
                  />
                  {fieldErrors.email ? (
                    <p className="mt-2 text-sm font-medium text-red-500">
                      {fieldErrors.email} (예: sample@sample.com)
                    </p>
                  ) : null}
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">
                    비밀번호
                  </span>
                  <input
                    type="password"
                    className={`h-12 w-full rounded-xl border px-4 text-sm outline-none transition ${
                      fieldErrors.password
                        ? "border-red-400 focus:border-red-500"
                        : "border-gray-200 focus:border-[#49CDDF]"
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
                    placeholder="비밀번호를 입력해 주세요."
                  />
                  {fieldErrors.password ? (
                    <p className="mt-2 text-sm font-medium text-red-500">
                      {fieldErrors.password}
                    </p>
                  ) : (
                    <div className="mt-2 rounded-xl border border-[#FFE0B5] bg-[#FFF7EC] px-3 py-3 text-sm text-[#7A4B00]">
                      <p className="font-medium text-[#5E3A00]">
                        비밀번호 안내
                      </p>
                      <ul className="mt-2 list-disc space-y-1 pl-5 marker:text-[#FF9900]">
                        <li>8자 이상 128자 이하로 입력해 주세요.</li>
                        <li>
                          대문자, 소문자, 숫자, 특수문자 중 2종류 이상을
                          포함해야 합니다.
                        </li>
                        <li>
                          동일 숫자 3자리 연속, 연속 숫자 3자리 이상은 사용할 수
                          없습니다.
                        </li>
                      </ul>
                    </div>
                  )}
                </label>

                {fieldErrors.submit ? (
                  <p className="text-sm font-medium text-red-500">
                    {fieldErrors.submit}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-[#FF9900] px-4 text-sm font-semibold text-white transition hover:bg-[#e68a00] disabled:opacity-60"
                >
                  {isSubmitting ? "처리 중..." : "회원가입"}
                </button>

                <Link
                  to="/"
                  className="inline-flex h-12 w-full items-center justify-center rounded-xl border border-gray-200 px-4 text-sm font-semibold text-gray-700 transition hover:border-[#49CDDF] hover:text-[#49CDDF]"
                >
                  로그인으로 이동
                </Link>
              </form>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
