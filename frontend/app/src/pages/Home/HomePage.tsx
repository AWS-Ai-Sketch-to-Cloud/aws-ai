import { Link } from "react-router";
import {
  ArrowRight,
  Boxes,
  Cloud,
  Cuboid,
  GitBranch,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import PageMeta from "../../components/common/PageMeta";

const FEATURE_CARDS = [
  {
    icon: Sparkles,
    title: "요구사항을 읽는 AI",
    copy: "문장과 스케치를 함께 읽고 서비스 의도를 AWS 아키텍처로 해석합니다.",
  },
  {
    icon: GitBranch,
    title: "Terraform까지 연결",
    copy: "분석 결과가 끝나지 않고 바로 검토 가능한 인프라 코드로 이어집니다.",
  },
  {
    icon: ShieldCheck,
    title: "배포 전 검토 흐름",
    copy: "비용, 버전 비교, 배포 준비 상태를 한 콘솔에서 이어서 점검합니다.",
  },
];

const PROCESS_STEPS = [
  "아이디어와 스케치 업로드",
  "AI 아키텍처 분석",
  "Terraform 초안 생성",
  "비용 및 배포 흐름 검토",
];

function HeroScene() {
  return (
    <div className="relative h-[420px] w-full perspective-[1800px] sm:h-[520px]">
      <div className="absolute inset-0 rounded-[2.5rem] bg-[radial-gradient(circle_at_center,_rgba(72,123,255,0.18),_transparent_48%)]" />

      <div className="absolute left-1/2 top-1/2 h-[320px] w-[320px] -translate-x-1/2 -translate-y-1/2 [transform-style:preserve-3d] sm:h-[380px] sm:w-[380px]">
        <div className="absolute inset-0 animate-[heroFloat_8s_ease-in-out_infinite] [transform-style:preserve-3d]">
          <div className="absolute left-1/2 top-1/2 h-44 w-44 -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-white/15 bg-white/8 backdrop-blur-md [transform:rotateX(66deg)_rotateZ(42deg)_translateZ(40px)] sm:h-52 sm:w-52" />
          <div className="absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-[#58e1c1]/30 bg-[#58e1c1]/12 shadow-[0_0_80px_rgba(88,225,193,0.18)] [transform:rotateX(66deg)_rotateZ(42deg)_translateZ(120px)] sm:h-48 sm:w-48" />
          <div className="absolute left-1/2 top-1/2 h-36 w-36 -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-[#487bff]/35 bg-[#487bff]/16 shadow-[0_0_90px_rgba(72,123,255,0.22)] [transform:rotateX(66deg)_rotateZ(42deg)_translateZ(200px)] sm:h-44 sm:w-44" />

          <div className="absolute left-[14%] top-[18%] rounded-[1.5rem] border border-white/18 bg-[#0f1728]/84 px-4 py-3 text-white shadow-[0_18px_50px_rgba(15,23,40,0.35)] backdrop-blur [transform:translateZ(220px)_rotateY(-18deg)] animate-[heroOrbit_12s_linear_infinite]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10">
                <Cloud className="h-5 w-5 text-[#58e1c1]" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">Infra</p>
                <p className="text-sm font-semibold">AWS Topology</p>
              </div>
            </div>
          </div>

          <div className="absolute right-[12%] top-[26%] rounded-[1.5rem] border border-white/18 bg-white/96 px-4 py-3 text-[#122033] shadow-[0_18px_50px_rgba(72,123,255,0.18)] [transform:translateZ(180px)_rotateY(16deg)] animate-[heroDrift_10s_ease-in-out_infinite]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#edf3ff]">
                <Boxes className="h-5 w-5 text-[#487bff]" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-[#7d8ba0]">Output</p>
                <p className="text-sm font-semibold">Terraform Draft</p>
              </div>
            </div>
          </div>

          <div className="absolute bottom-[10%] left-[18%] rounded-[1.5rem] border border-white/18 bg-white/96 px-4 py-3 text-[#122033] shadow-[0_18px_50px_rgba(72,123,255,0.18)] [transform:translateZ(240px)_rotateY(-14deg)] animate-[heroDrift_9s_ease-in-out_infinite_reverse]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#effdf7]">
                <Workflow className="h-5 w-5 text-[#16a34a]" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-[#7d8ba0]">Flow</p>
                <p className="text-sm font-semibold">Deploy Readiness</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <>
      <PageMeta
        title="Sketch-to-Cloud | AI Infrastructure Studio"
        description="스케치와 요구사항을 AWS 아키텍처와 Terraform으로 연결하는 AI 인프라 스튜디오"
      />

      <div className="min-h-screen overflow-hidden bg-[linear-gradient(180deg,#f8fbff_0%,#eef4ff_100%)] text-[#122033]">
        <header className="sticky top-0 z-40 border-b border-white/70 bg-white/72 backdrop-blur-xl">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 sm:px-8 lg:px-10">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#122033] text-white shadow-[0_12px_32px_rgba(18,32,51,0.18)]">
                <Cuboid className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold tracking-tight">Sketch-to-Cloud</p>
                <p className="text-xs text-[#65748b]">AI Infrastructure Studio</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="hidden rounded-full border border-[#d9e4f2] bg-white px-4 py-2 text-sm font-semibold text-[#314257] transition hover:border-[#487bff] hover:text-[#487bff] sm:inline-flex"
              >
                로그인
              </Link>
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 rounded-full bg-[#122033] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1b2c44]"
              >
                무료로 시작
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </header>

        <main>
          <section className="relative mx-auto flex min-h-[calc(100vh-78px)] w-full max-w-7xl items-center px-6 py-14 sm:px-8 lg:px-10">
            <div className="grid w-full gap-12 xl:grid-cols-[0.94fr_1.06fr] xl:items-center">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-[#d9e4f2] bg-white/88 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#487bff] shadow-[0_12px_28px_rgba(72,123,255,0.08)]">
                  <Sparkles className="h-3.5 w-3.5" />
                  From sketch to deployment
                </div>

                <h1 className="mt-7 text-5xl font-semibold leading-[1.02] tracking-[-0.05em] text-[#122033] sm:text-6xl lg:text-7xl">
                  아이디어를
                  <br />
                  AWS 설계 경험으로
                  <br />
                  바꾸는 첫 화면
                </h1>

                <p className="mt-6 max-w-2xl text-base leading-8 text-[#65748b] sm:text-lg">
                  Sketch-to-Cloud는 요구사항, 손그림, 저장소 정보를 읽고 AWS
                  아키텍처와 Terraform 초안, 비용 감각, 배포 준비 흐름까지 연결하는
                  AI 인프라 제품입니다.
                </p>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#122033] px-6 py-4 text-sm font-semibold text-white shadow-[0_18px_40px_rgba(18,32,51,0.18)] transition hover:-translate-y-0.5 hover:bg-[#1a2c45]"
                  >
                    로그인하러 가기
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    to="/signup"
                    className="inline-flex items-center justify-center rounded-2xl border border-[#d9e4f2] bg-white px-6 py-4 text-sm font-semibold text-[#314257] shadow-[0_10px_24px_rgba(72,123,255,0.08)] transition hover:-translate-y-0.5 hover:border-[#487bff] hover:text-[#122033]"
                  >
                    팀 계정 만들기
                  </Link>
                </div>
              </div>

              <HeroScene />
            </div>
          </section>

          <section className="mx-auto w-full max-w-7xl px-6 py-10 sm:px-8 lg:px-10">
            <div className="grid gap-5 lg:grid-cols-3">
              {FEATURE_CARDS.map((item) => {
                const Icon = item.icon;
                return (
                  <article
                    key={item.title}
                    className="rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-[0_24px_80px_rgba(72,123,255,0.12)] backdrop-blur"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#edf3ff] text-[#487bff]">
                      <Icon className="h-6 w-6" />
                    </div>
                    <h2 className="mt-5 text-xl font-semibold tracking-[-0.03em]">{item.title}</h2>
                    <p className="mt-3 text-sm leading-7 text-[#65748b]">{item.copy}</p>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="mx-auto w-full max-w-7xl px-6 py-14 sm:px-8 lg:px-10">
            <div className="grid gap-8 xl:grid-cols-[0.9fr_1.1fr] xl:items-center">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#487bff]">
                  Product flow
                </p>
                <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
                  한 번의 입력이
                  <br />
                  구조, 코드, 검토로 이어집니다.
                </h2>
              </div>

              <div className="grid gap-3">
                {PROCESS_STEPS.map((step, index) => (
                  <div
                    key={step}
                    className="flex items-center gap-4 rounded-[1.75rem] border border-white/70 bg-white/88 px-5 py-4 shadow-[0_18px_48px_rgba(72,123,255,0.10)] backdrop-blur"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#122033] text-sm font-semibold text-white">
                      {index + 1}
                    </div>
                    <p className="text-sm font-semibold text-[#122033]">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="mx-auto w-full max-w-7xl px-6 pb-18 pt-10 sm:px-8 lg:px-10">
            <div className="overflow-hidden rounded-[2.5rem] border border-white/70 bg-[#0f1728] px-8 py-10 text-white shadow-[0_24px_80px_rgba(15,23,40,0.18)] sm:px-10 lg:px-12">
              <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/45">
                    Ready to start
                  </p>
                  <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
                    소개 페이지는 여기까지.
                    <br />
                    이제 실제 시스템으로 들어가면 됩니다.
                  </h2>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68 sm:text-base">
                    로그인 후 워크스페이스에서 요구사항 입력, 아키텍처 분석, Terraform
                    결과, 비용 검토, 배포 흐름을 바로 사용할 수 있습니다.
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-4 text-sm font-semibold text-[#122033] transition hover:bg-[#eef4ff]"
                  >
                    로그인하러 가기
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    to="/signup"
                    className="inline-flex items-center justify-center rounded-2xl border border-white/16 bg-white/8 px-6 py-4 text-sm font-semibold text-white transition hover:bg-white/12"
                  >
                    회원가입
                  </Link>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
