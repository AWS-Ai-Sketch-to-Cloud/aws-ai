import { FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";

export default function LoginPage() {
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sessionStorage.setItem(
      "stc-auth",
      JSON.stringify({
        loginId,
        password,
      }),
    );
    navigate("/console");
  };

  return (
    <>
      <PageMeta
        title="로그인 | Sketch-to-Cloud"
        description="Sketch-to-Cloud 로그인"
      />
      <div className="relative min-h-screen overflow-hidden bg-gray-950 px-6 py-10 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.14),_transparent_28%)]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center">
          <div className="grid w-full gap-8 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="hidden rounded-3xl border border-white/10 bg-white/5 p-10 backdrop-blur lg:block">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">
                Sketch to Cloud
              </p>
              <h1 className="mt-6 max-w-xl text-5xl font-semibold leading-tight">
                스케치와 텍스트를 AWS 설계 파이프라인으로 바로 연결합니다.
              </h1>
              <p className="mt-6 max-w-lg text-base leading-7 text-gray-300">
                로그인 후 콘솔에서 프로젝트를 만들고, 세션을 실행하고, 아키텍처
                분석과 Terraform 생성, 비용 계산까지 한 흐름으로 진행할 수
                있습니다.
              </p>
              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    입력
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    텍스트와 스케치 이미지 URL로 세션을 생성합니다.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    파이프라인
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    분석, Terraform, 비용 계산 단계를 순서대로 실행합니다.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">
                    결과
                  </p>
                  <p className="mt-3 text-sm text-gray-200">
                    세션 상태와 구조화된 JSON 결과를 확인합니다.
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-white p-8 text-gray-900 shadow-2xl shadow-black/20 backdrop-blur sm:p-10">
              <div className="mx-auto max-w-md">
                <h2 className="mt-4 text-3xl font-semibold">로그인</h2>
                <p className="mt-3 text-sm leading-6 text-gray-500">
                  앱은 이제 이 화면에서 시작합니다. 로그인 후 메인 콘솔로
                  이동합니다.
                </p>

                <form className="mt-8 space-y-5" onSubmit={onSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      로그인 ID
                    </span>
                    <input
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-cyan-500"
                      value={loginId}
                      onChange={(event) => setLoginId(event.target.value)}
                      placeholder="아이디를 입력해 주세요."
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-gray-700">
                      비밀번호
                    </span>
                    <input
                      type="password"
                      className="h-12 w-full rounded-xl border border-gray-200 px-4 text-sm outline-none transition focus:border-cyan-500"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="비밀번호를 입력해 주세요."
                    />
                  </label>

                  <button
                    type="submit"
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-gray-950 px-4 text-sm font-semibold text-white transition hover:bg-cyan-700"
                  >
                    로그인
                  </button>
                  <button
                    type="submit"
                    className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-gray-950 px-4 text-sm font-semibold text-white transition hover:bg-cyan-700"
                  >
                    회원가입
                  </button>
                </form>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
