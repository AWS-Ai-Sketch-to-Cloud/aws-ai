import { Link } from "react-router";
import { ArrowRight, Compass, Sparkles } from "lucide-react";
import PageMeta from "../../components/common/PageMeta";

export default function NotFound() {
  return (
    <>
      <PageMeta
        title="페이지를 찾을 수 없음 | Sketch-to-Cloud"
        description="요청한 페이지가 존재하지 않습니다."
      />
      <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 py-10 text-[#122033]">
        <div className="w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/70 bg-white/88 shadow-[0_24px_80px_rgba(72,123,255,0.14)] backdrop-blur">
          <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
            <section className="bg-[#0f1728] px-8 py-10 text-white sm:px-10">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white/75">
                <Sparkles className="h-3.5 w-3.5 text-[#58e1c1]" />
                Lost route
              </div>
              <p className="mt-8 text-7xl font-semibold leading-none">404</p>
              <h1 className="mt-4 text-3xl font-semibold leading-tight">
                찾으려는 화면이
                <br />
                현재 경로에 없습니다.
              </h1>
              <p className="mt-4 max-w-md text-sm leading-7 text-white/72">
                링크가 바뀌었거나 잘못된 주소로 접근했을 수 있습니다. 메인 화면으로
                돌아가서 다시 시작하세요.
              </p>
            </section>

            <section className="px-8 py-10 sm:px-10">
              <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-[#edf3ff] text-[#487bff]">
                <Compass className="h-7 w-7" />
              </div>
              <h2 className="mt-6 text-2xl font-semibold text-[#122033]">
                이동 가능한 시작점
              </h2>
              <p className="mt-3 text-sm leading-7 text-[#65748b]">
                로그인 화면으로 돌아가거나, 인증이 완료된 상태라면 워크스페이스 경로로
                다시 접근해 보세요.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#122033] px-5 text-sm font-semibold text-white transition hover:bg-[#1b2c44]"
                >
                  홈으로 이동
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/workspace"
                  className="inline-flex h-12 items-center justify-center rounded-2xl border border-[#d9e4f2] bg-white px-5 text-sm font-semibold text-[#314257] transition hover:border-[#487bff] hover:text-[#487bff]"
                >
                  워크스페이스 열기
                </Link>
              </div>
            </section>
          </div>
        </div>
        <p className="mt-6 text-sm text-[#65748b]">
          &copy; {new Date().getFullYear()} Sketch-to-Cloud
        </p>
      </div>
    </>
  );
}
