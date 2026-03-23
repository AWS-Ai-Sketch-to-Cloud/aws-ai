import { useState } from "react";
import PageMeta from "../../components/common/PageMeta";

type SessionDetail = {
  sessionId: string;
  status: string;
  architecture: unknown;
  terraform: unknown;
  cost: unknown;
  error: unknown;
};

type AppState = {
  baseUrl: string;
  loginId: string;
  email: string;
  password: string;
  displayName: string;
  projectName: string;
  projectDescription: string;
  inputText: string;
  inputImageUrl: string;
  projectId: string;
  sessionId: string;
  accessToken: string;
  refreshToken: string;
};

export default function SketchConsole() {
  const [state, setState] = useState<AppState>({
    baseUrl: "http://127.0.0.1:8000",
    loginId: "demo_user",
    email: "demo_user@example.com",
    password: "DemoPass123!",
    displayName: "데모 사용자",
    projectName: "AI 인프라 설계 프로젝트",
    projectDescription: "텍스트/스케치 기반 인프라 자동 생성",
    inputText: "서울 리전에 EC2 2대와 MySQL RDS 1대를 프라이빗으로 구성",
    inputImageUrl: "",
    projectId: "",
    sessionId: "",
    accessToken: "",
    refreshToken: "",
  });
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [resultText, setResultText] = useState<string>("아직 실행 결과가 없습니다.");
  const [logs, setLogs] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const setField = <K extends keyof AppState>(key: K, value: AppState[K]) => {
    setState((prev) => ({ ...prev, [key]: value }));
  };

  const pushLog = (message: string) => {
    const now = new Date().toISOString();
    setLogs((prev) => [`[${now}] ${message}`, ...prev].slice(0, 200));
  };

  const api = async (path: string, method: "GET" | "POST", body?: unknown) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const res = await fetch(`${state.baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new Error(`${method} ${path} 실패 (${res.status}): ${JSON.stringify(data)}`);
    }
    setResultText(JSON.stringify(data, null, 2));
    return data;
  };

  const ensureAuth = async () => {
    try {
      await api("/api/auth/register", "POST", {
        loginId: state.loginId,
        email: state.email,
        password: state.password,
        displayName: state.displayName,
      });
      pushLog("회원가입 성공");
    } catch {
      pushLog("회원가입 생략(기존 계정 사용)");
    }

    const login = await api("/api/auth/login", "POST", {
      loginId: state.loginId,
      password: state.password,
    });
    setField("accessToken", String(login.accessToken ?? ""));
    setField("refreshToken", String(login.refreshToken ?? ""));
    pushLog("로그인 성공");
  };

  const createProjectAndSession = async () => {
    const project = await api("/api/projects", "POST", {
      name: state.projectName,
      description: state.projectDescription,
    });
    const projectId = String(project.projectId);
    setField("projectId", projectId);
    pushLog(`프로젝트 생성: ${projectId}`);

    const session = await api(`/api/projects/${projectId}/sessions`, "POST", {
      inputType: state.inputImageUrl ? "TEXT_WITH_SKETCH" : "TEXT",
      inputText: state.inputText,
      inputImageUrl: state.inputImageUrl || null,
    });
    const sessionId = String(session.sessionId);
    setField("sessionId", sessionId);
    pushLog(`세션 생성: ${sessionId}`);
    return sessionId;
  };

  const runPipeline = async () => {
    setIsRunning(true);
    try {
      pushLog("파이프라인 시작");
      await ensureAuth();
      const sessionId = await createProjectAndSession();

      await api(`/sessions/${sessionId}/analyze`, "POST", {
        input_text: state.inputText,
        input_type: state.inputImageUrl ? "sketch" : "text",
      });
      pushLog("아키텍처 분석 완료");

      await api(`/api/sessions/${sessionId}/terraform`, "POST");
      pushLog("Terraform 생성 완료");

      await api(`/api/sessions/${sessionId}/cost`, "POST");
      pushLog("비용 계산 완료");

      const sessionDetail = await api(`/api/sessions/${sessionId}`, "GET");
      setDetail(sessionDetail as SessionDetail);
      pushLog("상세 조회 완료");
      pushLog("파이프라인 성공");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      pushLog(`실패: ${msg}`);
      setResultText(msg);
    } finally {
      setIsRunning(false);
    }
  };

  const box = "rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";
  const input = "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 text-sm dark:border-gray-700";

  return (
    <>
      <PageMeta title="Sketch-to-Cloud 프로젝트" description="입력 기반 인프라 자동 생성" />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          <div className={box}>
            <p className="text-xs font-semibold tracking-wider text-brand-600">SKETCH TO CLOUD</p>
            <h1 className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">텍스트/스케치로 클라우드 설계 자동 생성</h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              입력만 하면 아키텍처 분석, Terraform 코드 생성, 비용 계산까지 자동으로 실행됩니다.
            </p>
          </div>

          <div className={box}>
            <h2 className="mb-4 text-lg font-semibold">입력</h2>
            <div className="grid grid-cols-1 gap-3">
              <input className={input} value={state.projectName} onChange={(e) => setField("projectName", e.target.value)} placeholder="프로젝트 이름" />
              <input className={input} value={state.projectDescription} onChange={(e) => setField("projectDescription", e.target.value)} placeholder="프로젝트 설명" />
              <textarea className="w-full rounded-lg border border-gray-300 p-3 text-sm dark:border-gray-700" rows={4} value={state.inputText} onChange={(e) => setField("inputText", e.target.value)} />
              <input className={input} value={state.inputImageUrl} onChange={(e) => setField("inputImageUrl", e.target.value)} placeholder="스케치 이미지 URL (선택)" />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={runPipeline}
                disabled={isRunning}
                className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-60"
              >
                {isRunning ? "실행 중..." : "자동 실행"}
              </button>
              <button
                onClick={() => setShowAdvanced((v) => !v)}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium dark:border-gray-700"
              >
                {showAdvanced ? "고급 설정 숨기기" : "고급 설정"}
              </button>
            </div>
          </div>

          {showAdvanced && (
            <div className={box}>
              <h2 className="mb-4 text-lg font-semibold">고급 설정</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input className={input} value={state.baseUrl} onChange={(e) => setField("baseUrl", e.target.value)} placeholder="백엔드 주소" />
                <input className={input} value={state.loginId} onChange={(e) => setField("loginId", e.target.value)} placeholder="로그인 ID" />
                <input className={input} value={state.email} onChange={(e) => setField("email", e.target.value)} placeholder="이메일" />
                <input className={input} type="password" value={state.password} onChange={(e) => setField("password", e.target.value)} placeholder="비밀번호" />
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 text-sm">
                <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                  <p className="text-gray-500">projectId</p>
                  <p className="break-all font-medium">{state.projectId || "-"}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                  <p className="text-gray-500">sessionId</p>
                  <p className="break-all font-medium">{state.sessionId || "-"}</p>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6 xl:col-span-5">
          <div className={`${box} xl:sticky xl:top-24`}>
            <h2 className="text-lg font-semibold">결과</h2>
            <pre className="mt-3 h-56 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs dark:border-gray-800 dark:bg-gray-900">
              {resultText}
            </pre>

            <h3 className="mt-5 text-sm font-semibold">최종 상태</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-gray-50 p-2 dark:bg-gray-800/50">
                <p className="text-gray-500">세션 상태</p>
                <p className="font-semibold">{detail?.status ?? "-"}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-2 dark:bg-gray-800/50">
                <p className="text-gray-500">sessionId</p>
                <p className="break-all font-semibold">{detail?.sessionId ?? "-"}</p>
              </div>
            </div>

            <h3 className="mt-5 text-sm font-semibold">실행 로그</h3>
            <pre className="mt-2 h-64 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs dark:border-gray-800 dark:bg-gray-900">
              {logs.join("\n") || "아직 로그가 없습니다."}
            </pre>
          </div>
        </section>
      </div>
    </>
  );
}
