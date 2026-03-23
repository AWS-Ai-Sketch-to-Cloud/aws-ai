import { useMemo, useState } from "react";
import PageMeta from "../../components/common/PageMeta";

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;

type ApiState = {
  baseUrl: string;
  loginId: string;
  email: string;
  password: string;
  displayName: string;
  contentType: string;
  fileName: string;
  inputImageUrl: string;
  projectName: string;
  projectDescription: string;
  projectId: string;
  sessionId: string;
  inputText: string;
  architectureJson: string;
  accessToken: string;
  refreshToken: string;
  patchStatus: string;
  patchErrorCode: string;
  patchErrorMessage: string;
};

const defaultArchitecture = `{
  "vpc": true,
  "ec2": { "count": 2, "instance_type": "t3.micro" },
  "rds": { "enabled": true, "engine": "mysql" },
  "public": false,
  "region": "ap-northeast-2"
}`;

export default function SketchConsole() {
  const [state, setState] = useState<ApiState>({
    baseUrl: "http://127.0.0.1:8000",
    loginId: "demo_user",
    email: "demo_user@example.com",
    password: "DemoPass123!",
    displayName: "데모 사용자",
    contentType: "image/png",
    fileName: "architecture-sketch.png",
    inputImageUrl: "",
    projectName: "클라우드 설계 프로젝트",
    projectDescription: "terraform + 비용 계산 흐름",
    projectId: "",
    sessionId: "",
    inputText: "서울 리전에 EC2 2대와 MySQL RDS 1대를 프라이빗으로 구성",
    architectureJson: defaultArchitecture,
    accessToken: "",
    refreshToken: "",
    patchStatus: "ANALYZING",
    patchErrorCode: "",
    patchErrorMessage: "",
  });
  const [resultText, setResultText] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);

  const currentUser = useMemo(() => {
    if (!state.accessToken.startsWith("uid:")) {
      return "-";
    }
    return state.accessToken.slice(4);
  }, [state.accessToken]);

  const patchState = <K extends keyof ApiState>(key: K, value: ApiState[K]) => {
    setState((prev) => ({ ...prev, [key]: value }));
  };

  const appendLog = (message: string) => {
    const now = new Date().toISOString();
    setLogs((prev) => [`[${now}] ${message}`, ...prev].slice(0, 200));
  };

  const apiCall = async (
    path: string,
    method: "GET" | "POST" | "PATCH",
    body?: JsonValue,
    useAuth = false
  ) => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (useAuth && state.accessToken) {
      headers.Authorization = `Bearer ${state.accessToken}`;
    }

    const response = await fetch(`${state.baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const text = await response.text();
    let data: JsonValue = text;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }

    if (!response.ok) {
      const err = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      throw new Error(`${method} ${path} 실패 (${response.status}): ${err}`);
    }

    setResultText(typeof data === "string" ? data : JSON.stringify(data, null, 2));
    appendLog(`${method} ${path} -> OK`);
    return data;
  };

  const run = async (label: string, fn: () => Promise<void>) => {
    try {
      appendLog(`${label} 시작`);
      await fn();
      appendLog(`${label} 완료`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      appendLog(`${label} 실패: ${message}`);
      setResultText(message);
    }
  };

  const inputBase =
    "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 text-sm dark:border-gray-700";
  const cardBase =
    "rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";

  return (
    <>
      <PageMeta title="Sketch-to-Cloud 콘솔" description="Sketch-to-Cloud API v2 콘솔" />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-8">
          <div className={cardBase}>
            <p className="text-xs font-medium tracking-wider text-brand-600">WORKFLOW</p>
            <h1 className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">Sketch-to-Cloud 프로젝트 콘솔</h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              아래 1~4단계를 순서대로 실행하면 아키텍처 저장, Terraform 생성, 비용 계산이 한 번에 검증됩니다.
            </p>
          </div>

          <div className={cardBase}>
            <h2 className="mb-4 text-lg font-semibold">1) 접속/인증</h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input value={state.baseUrl} onChange={(e) => patchState("baseUrl", e.target.value)} placeholder="백엔드 주소" className={`${inputBase} md:col-span-2`} />
              <input value={state.loginId} onChange={(e) => patchState("loginId", e.target.value)} placeholder="로그인 ID" className={inputBase} />
              <input value={state.displayName} onChange={(e) => patchState("displayName", e.target.value)} placeholder="표시 이름" className={inputBase} />
              <input value={state.email} onChange={(e) => patchState("email", e.target.value)} placeholder="이메일" className={inputBase} />
              <input type="password" value={state.password} onChange={(e) => patchState("password", e.target.value)} placeholder="비밀번호" className={inputBase} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button onClick={() => run("회원가입", async () => { await apiCall("/api/auth/register", "POST", { loginId: state.loginId, email: state.email, password: state.password, displayName: state.displayName }); })} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">회원가입</button>
              <button onClick={() => run("로그인", async () => { const data = (await apiCall("/api/auth/login", "POST", { loginId: state.loginId, password: state.password })) as Record<string, unknown>; patchState("accessToken", String(data.accessToken ?? "")); patchState("refreshToken", String(data.refreshToken ?? "")); })} className="rounded-lg bg-success-500 px-4 py-2 text-sm font-medium text-white">로그인</button>
              <button onClick={() => run("내 정보", async () => void (await apiCall("/api/users/me", "GET", undefined, true)))} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium dark:border-gray-700">내 정보</button>
              <button onClick={() => run("로그아웃", async () => { await apiCall("/api/auth/logout", "POST", { refreshToken: state.refreshToken }); patchState("accessToken", ""); patchState("refreshToken", ""); })} className="rounded-lg border border-error-300 px-4 py-2 text-sm font-medium text-error-600">로그아웃</button>
            </div>
          </div>

          <div className={cardBase}>
            <h2 className="mb-4 text-lg font-semibold">2) 업로드/프로젝트/세션</h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input value={state.contentType} onChange={(e) => patchState("contentType", e.target.value)} placeholder="Content-Type" className={inputBase} />
              <input value={state.fileName} onChange={(e) => patchState("fileName", e.target.value)} placeholder="파일명" className={inputBase} />
              <input value={state.inputImageUrl} onChange={(e) => patchState("inputImageUrl", e.target.value)} placeholder="이미지 URL" className={`${inputBase} md:col-span-2`} />
              <input value={state.projectName} onChange={(e) => patchState("projectName", e.target.value)} placeholder="프로젝트 이름" className={inputBase} />
              <input value={state.projectDescription} onChange={(e) => patchState("projectDescription", e.target.value)} placeholder="프로젝트 설명" className={inputBase} />
              <input value={state.projectId} onChange={(e) => patchState("projectId", e.target.value)} placeholder="프로젝트 ID" className={inputBase} />
              <input value={state.sessionId} onChange={(e) => patchState("sessionId", e.target.value)} placeholder="세션 ID" className={inputBase} />
            </div>
            <textarea value={state.inputText} onChange={(e) => patchState("inputText", e.target.value)} rows={3} className="mt-3 w-full rounded-lg border border-gray-300 p-3 text-sm dark:border-gray-700" />
            <div className="mt-4 flex flex-wrap gap-2">
              <button onClick={() => run("이미지 URL 발급", async () => { const data = (await apiCall("/api/uploads/images", "POST", { contentType: state.contentType, fileName: state.fileName })) as Record<string, unknown>; patchState("inputImageUrl", String(data.url ?? "")); })} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium dark:border-gray-700">이미지 URL 발급</button>
              <button onClick={() => run("프로젝트 생성", async () => { const data = (await apiCall("/api/projects", "POST", { name: state.projectName, description: state.projectDescription })) as Record<string, unknown>; patchState("projectId", String(data.projectId ?? "")); })} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">프로젝트 생성</button>
              <button onClick={() => run("세션 생성", async () => { const data = (await apiCall(`/api/projects/${state.projectId}/sessions`, "POST", { inputType: state.inputImageUrl ? "TEXT_WITH_SKETCH" : "TEXT", inputText: state.inputText, inputImageUrl: state.inputImageUrl || null })) as Record<string, unknown>; patchState("sessionId", String(data.sessionId ?? "")); })} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white">세션 생성</button>
              <button onClick={() => run("프로젝트 목록 조회", async () => void (await apiCall("/api/projects", "GET")))} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium dark:border-gray-700">프로젝트 목록</button>
              <button onClick={() => run("프로젝트 세션 목록 조회", async () => void (await apiCall(`/api/projects/${state.projectId}/sessions`, "GET")))} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium dark:border-gray-700">프로젝트 세션 목록</button>
            </div>
          </div>

          <div className={cardBase}>
            <h2 className="mb-4 text-lg font-semibold">3) 아키텍처/결과 생성</h2>
            <textarea value={state.architectureJson} onChange={(e) => patchState("architectureJson", e.target.value)} rows={9} className="w-full rounded-lg border border-gray-300 p-3 font-mono text-xs dark:border-gray-700" />
            <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
              <button onClick={() => run("아키텍처 저장", async () => { await apiCall(`/api/sessions/${state.sessionId}/architecture`, "POST", { schemaVersion: "v1", architectureJson: JSON.parse(state.architectureJson) }); })} className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-medium text-white">아키텍처 저장</button>
              <button onClick={() => run("테라폼 생성", async () => void (await apiCall(`/api/sessions/${state.sessionId}/terraform`, "POST")))} className="rounded-lg bg-success-500 px-3 py-2 text-sm font-medium text-white">테라폼 생성</button>
              <button onClick={() => run("비용 계산", async () => void (await apiCall(`/api/sessions/${state.sessionId}/cost`, "POST")))} className="rounded-lg bg-warning-500 px-3 py-2 text-sm font-medium text-white">비용 계산</button>
              <button onClick={() => run("상세 조회", async () => void (await apiCall(`/api/sessions/${state.sessionId}`, "GET")))} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium dark:border-gray-700">상세 조회</button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
              <select value={state.patchStatus} onChange={(e) => patchState("patchStatus", e.target.value)} className={inputBase}>
                <option value="CREATED">CREATED</option>
                <option value="ANALYZING">ANALYZING</option>
                <option value="ANALYZED">ANALYZED</option>
                <option value="GENERATING_TERRAFORM">GENERATING_TERRAFORM</option>
                <option value="GENERATED">GENERATED</option>
                <option value="COST_CALCULATED">COST_CALCULATED</option>
                <option value="FAILED">FAILED</option>
              </select>
              <input value={state.patchErrorCode} onChange={(e) => patchState("patchErrorCode", e.target.value)} placeholder="errorCode (선택)" className={inputBase} />
              <input value={state.patchErrorMessage} onChange={(e) => patchState("patchErrorMessage", e.target.value)} placeholder="errorMessage (선택)" className={inputBase} />
            </div>
            <div className="mt-3">
              <button
                onClick={() =>
                  run("세션 상태 갱신", async () => {
                    await apiCall(`/api/sessions/${state.sessionId}/status`, "PATCH", {
                      status: state.patchStatus,
                      errorCode: state.patchErrorCode || null,
                      errorMessage: state.patchErrorMessage || null,
                    });
                  })
                }
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium dark:border-gray-700"
              >
                세션 상태 PATCH
              </button>
            </div>
          </div>
        </section>

        <section className="space-y-6 xl:col-span-4">
          <div className={`${cardBase} xl:sticky xl:top-24`}>
            <h2 className="text-lg font-semibold">실시간 상태</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <p className="text-gray-500">현재 사용자</p>
                <p className="mt-1 break-all font-medium">{currentUser}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <p className="text-gray-500">현재 세션</p>
                <p className="mt-1 break-all font-medium">{state.sessionId || "-"}</p>
              </div>
            </div>

            <h3 className="mt-5 text-sm font-semibold text-gray-800 dark:text-white/90">응답 결과</h3>
            <pre className="mt-2 h-56 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs dark:border-gray-800 dark:bg-gray-900">
              {resultText || "아직 결과가 없습니다."}
            </pre>

            <h3 className="mt-5 text-sm font-semibold text-gray-800 dark:text-white/90">실행 로그</h3>
            <pre className="mt-2 h-56 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs dark:border-gray-800 dark:bg-gray-900">
              {logs.join("\n") || "아직 로그가 없습니다."}
            </pre>
          </div>
        </section>
      </div>
    </>
  );
}
