import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";

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
  const [errorMessage, setErrorMessage] = useState("");

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ displayName, loginId, email, password }),
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail ?? "회원가입에 실패했습니다.");
      }

      navigate("/");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "회원가입 중 오류가 발생했습니다.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <PageMeta title="회원가입 | Sketch-to-Cloud" description="Sketch-to-Cloud 회원가입" />
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
                  <span className="mb-2 block text-sm font-medium text-gray-700">이름</span>
                  <input
                    className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="이름"
                    required
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">로그인 ID</span>
                  <input
                    className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                    value={loginId}
                    onChange={(event) => setLoginId(event.target.value)}
                    placeholder="login id"
                    required
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">이메일</span>
                  <input
                    type="email"
                    className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="email@example.com"
                    required
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-gray-700">비밀번호</span>
                  <input
                    type="password"
                    className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="password"
                    required
                  />
                </label>

                {errorMessage ? (
                  <p className="text-sm font-medium text-red-500">{errorMessage}</p>
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
