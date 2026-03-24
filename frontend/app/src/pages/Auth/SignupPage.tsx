import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";

export default function SignupPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [loginId, setLoginId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sessionStorage.setItem(
      "stc-auth",
      JSON.stringify({
        displayName,
        loginId,
        email,
        password,
      }),
    );
    navigate("/dashboard");
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
          <div className="grid w-full gap-8 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="hidden rounded-3xl border border-[#E7E7E7] bg-white/80 p-10 backdrop-blur lg:block">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#49CDDF]">
                Sketch to Cloud
              </p>
              <h1 className="mt-6 max-w-xl text-5xl font-semibold leading-tight">
                회원가입 후 바로 인프라 설계 콘솔로 들어갈 수 있습니다.
              </h1>
              <p className="mt-6 max-w-lg text-base leading-7 text-gray-600">
                계정을 만들면 프로젝트와 세션을 분리해서 관리하고, 아키텍처
                분석부터 Terraform 생성, 비용 비교까지 한 흐름으로 확인할 수
                있습니다.
              </p>
              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-[#E7E7E7] bg-[#FFF7EB] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    프로젝트
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    프로젝트별로 세션 버전과 결과 이력을 관리합니다.
                  </p>
                </div>
                <div className="rounded-2xl border border-[#E7E7E7] bg-[#EEFDFE] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    자동화
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    분석, Terraform, 비용 계산을 서비스 파이프라인으로 실행합니다.
                  </p>
                </div>
                <div className="rounded-2xl border border-[#E7E7E7] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    비교
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    세션 버전 간 JSON, Terraform, 비용 차이를 비교할 수 있습니다.
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-[#E7E7E7] bg-white p-8 text-gray-900 shadow-2xl shadow-[#49CDDF]/10 backdrop-blur sm:p-10">
              <div className="mx-auto max-w-md">
                <h2 className="mt-4 text-3xl font-semibold">회원가입</h2>
                <p className="mt-3 text-sm leading-6 text-gray-500">
                  기본 정보를 입력하면 바로 콘솔로 이동합니다.
                </p>

                <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      이름
                    </span>
                    <input
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      placeholder="이름을 입력해 주세요."
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      로그인 ID
                    </span>
                    <input
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                      value={loginId}
                      onChange={(event) => setLoginId(event.target.value)}
                      placeholder="아이디를 입력해 주세요."
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      이메일
                    </span>
                    <input
                      type="email"
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="이메일을 입력해 주세요."
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      비밀번호
                    </span>
                    <input
                      type="password"
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-[#49CDDF]"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="비밀번호를 입력해 주세요."
                    />
                  </label>

                  <button
                    type="submit"
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-[#FF9900] px-4 text-sm font-semibold text-white transition hover:bg-[#e68a00]"
                  >
                    회원가입
                  </button>

                  <Link
                    to="/"
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl border border-gray-200 px-4 text-sm font-semibold text-gray-700 transition hover:border-[#49CDDF] hover:text-[#49CDDF]"
                  >
                    로그인 페이지로 이동
                  </Link>
                </form>

                <p className="mt-6 text-center text-sm text-gray-500">
                  이미 계정이 있으면{" "}
                  <Link
                    to="/"
                    className="font-semibold text-[#49CDDF] transition hover:text-[#36b8ca]"
                  >
                    로그인
                  </Link>
                  으로 돌아가세요.
                </p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
