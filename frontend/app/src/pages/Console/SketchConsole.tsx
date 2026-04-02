import { useState } from "react";
import PageMeta from "../../components/common/PageMeta";
import { Header } from "../../components/dashboard/header";
import { ControlPanel } from "../../components/dashboard/control-panel";
import { ResultPanel } from "../../components/dashboard/result-panel";

type AuthSession = {
  accessToken: string;
  refreshToken: string;
  apiBaseUrl?: string;
};

type ApiErrorPayload = {
  detail?: string;
  requestId?: string;
};

type GitHubRepoItem = {
  fullName: string;
  name: string;
  owner: string;
  private: boolean;
  defaultBranch: string;
  htmlUrl: string;
  updatedAt: string;
};

type GitHubRepoListResponse = {
  repos: GitHubRepoItem[];
};

type ProjectListItem = {
  projectId: string;
  name: string;
  description?: string | null;
  createdAt: string;
  updatedAt: string;
};

type ProjectListResponse = {
  items: ProjectListItem[];
};

type SessionListItem = {
  sessionId: string;
  versionNo: number;
  inputType: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

type SessionListResponse = {
  items: SessionListItem[];
};

type SessionDetailResponse = {
  sessionId: string;
  projectId: string;
  versionNo: number;
  inputType: string;
  inputText?: string | null;
  inputImageUrl?: string | null;
  status: string;
  architecture?: { architectureJson?: Record<string, unknown> };
  terraform?: { terraformCode?: string | null };
  cost?: {
    monthlyTotal?: number | null;
    costBreakdownJson?: Record<string, number> | null;
    region?: string | null;
    currency?: string | null;
    assumptionJson?: {
      pricing_source?: string;
      pricing_error?: string;
      monthly_total_usd?: number;
      monthly_total_krw?: number;
    } | null;
  };
  error?: { code?: string | null; message?: string | null } | null;
};

type SessionCompareResponse = {
  baseSession: {
    sessionId: string;
    versionNo: number;
    status: string;
    createdAt: string;
  };
  targetSession: {
    sessionId: string;
    versionNo: number;
    status: string;
    createdAt: string;
  };
  jsonDiff: Array<{
    path: string;
    changeType: "added" | "removed" | "changed";
    before?: unknown;
    after?: unknown;
  }>;
  terraformDiff: {
    changed: boolean;
    diff: string;
  };
  costDiff: {
    changed: boolean;
    monthlyTotal: {
      before?: number | null;
      after?: number | null;
      delta?: number | null;
    };
    breakdown?: Record<
      string,
      {
        before?: number | null;
        after?: number | null;
        delta?: number | null;
      }
    >;
    assumptionsChanged?: Array<{
      path: string;
      changeType: "added" | "removed" | "changed";
      before?: unknown;
      after?: unknown;
    }>;
  };
};

type GitHubRepoAnalyzeResponse = {
  fullName: string;
  defaultBranch: string;
  scannedFileCount: number;
  summary: string;
  findings: string[];
  recommendedStack: string[];
  requiredServices: string[];
  languageHints: string[];
  dependencyFiles: string[];
  deploymentSteps: string[];
  risks: string[];
  costNotes: string[];
  detected: Record<string, boolean>;
  architectureJson: Record<string, unknown>;
  terraformCode: string;
  cost: {
    currency?: string;
    monthly_total?: number;
    monthlyTotal?: number;
    breakdown?: Record<string, number>;
    assumptions?: Record<string, unknown>;
  };
  confidenceScore: number;
  confidenceLabel: string;
  evidenceFiles: string[];
  analysisProvider: string;
  fallbackUsed: boolean;
  analysisMode: "deep";
  cacheHit: boolean;
  confidenceReasons: string[];
  improvementActions: string[];
};

type RepoAnalysisHealth = {
  policy: {
    aiOnly: boolean;
    bedrockEnabled: boolean;
    bedrockStrictMode: boolean;
    bedrockFallbackEnabled: boolean;
    ready: boolean;
  };
  cache: {
    size: number;
    ttlSeconds: number;
    hits: number;
    misses: number;
    puts: number;
  };
  failures: {
    total: number;
    byStage: Record<string, number>;
    byType: Record<string, number>;
    recent: Array<{
      timestamp?: string;
      stage?: string;
      error_type?: string;
      error_message?: string;
      repo?: string;
    }>;
  };
  recommendations: string[];
};

type RepoAnalysisFeedback = {
  timestamp?: string;
  userId?: string;
  fullName?: string;
  verdict?: "APPROVE" | "HOLD";
  note?: string | null;
};

type GitHubConnectionStatus = {
  oauthConfigured: boolean;
  tokenPresent: boolean;
  tokenValid: boolean;
  githubApiReachable: boolean;
  accountLogin?: string | null;
  privateRepoAccess: boolean;
  estimatedRepoCount?: number | null;
  issues: string[];
};

type RepoReadiness = {
  score: number;
  grade: "A" | "B" | "C" | "D";
  checklist: Array<{ name: string; ok: boolean; detail: string }>;
};

const DEFAULT_API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

const replaceText = (source: string, before: string, after: string): string =>
  source.split(before).join(after);

const simplifyAwsWords = (text: string): string => {
  let out = text;
  out = replaceText(out, "IaC", "코드로 인프라 관리");
  out = replaceText(out, "Terraform", "테라폼(인프라 자동 생성 코드)");
  out = replaceText(out, "CDK", "CDK(코드로 인프라 구성)");
  out = replaceText(out, "GitHub Actions", "깃허브 자동 배포");
  out = replaceText(out, "CI/CD", "자동 테스트/배포");
  out = replaceText(out, "ECS", "ECS(컨테이너 실행 서비스)");
  out = replaceText(out, "EKS", "EKS(쿠버네티스 운영 서비스)");
  out = replaceText(out, "OIDC", "안전한 배포 인증");
  out = replaceText(out, "PR", "코드 리뷰 요청(PR)");
  out = replaceText(out, "WAF", "웹 공격 차단(WAF)");
  out = replaceText(out, "ALB", "로드밸런서(ALB)");
  out = replaceText(out, "RDS", "관리형 데이터베이스(RDS)");
  out = replaceText(out, "Secrets Manager/SSM", "AWS 비밀값 저장소");
  return out;
};

const formatCurrencyDelta = (value?: number | null): string => {
  if (value === null || value === undefined) {
    return "-";
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

const previewValue = (value: unknown): string => {
  if (value === null) return "null";
  if (value === undefined) return "-";
  if (typeof value === "string") return value;
  try {
    const serialized = JSON.stringify(value);
    return serialized.length > 160 ? `${serialized.slice(0, 157)}...` : serialized;
  } catch {
    return String(value);
  }
};

const buildRepoReportMarkdown = (analysis: GitHubRepoAnalyzeResponse): string => {
  const lines: string[] = [];
  lines.push(`# AWS 분석 리포트 - ${analysis.fullName}`);
  lines.push("");
  lines.push(`- 기본 브랜치: ${analysis.defaultBranch}`);
  lines.push(`- 신뢰도: ${analysis.confidenceLabel} (${Math.round(analysis.confidenceScore * 100)}%)`);
  lines.push(`- 분석 엔진: ${analysis.analysisProvider}`);
  lines.push("");
  lines.push("## 요약");
  lines.push(simplifyAwsWords(analysis.summary));
  lines.push("");
  if (analysis.findings.length > 0) {
    lines.push("## 핵심 요약");
    analysis.findings.forEach((item) => lines.push(`- ${simplifyAwsWords(item)}`));
    lines.push("");
  }
  if (analysis.recommendedStack.length > 0) {
    lines.push("## 추천 구성");
    analysis.recommendedStack.forEach((item) => lines.push(`- ${item}`));
    lines.push("");
  }
  if (analysis.deploymentSteps.length > 0) {
    lines.push("## 배포 단계");
    analysis.deploymentSteps.forEach((item) => lines.push(`1. ${simplifyAwsWords(item)}`));
    lines.push("");
  }
  if (analysis.risks.length > 0) {
    lines.push("## 주의할 점");
    analysis.risks.forEach((item) => lines.push(`- ${simplifyAwsWords(item)}`));
    lines.push("");
  }
  if (analysis.costNotes.length > 0) {
    lines.push("## 비용 메모");
    analysis.costNotes.forEach((item) => lines.push(`- ${simplifyAwsWords(item)}`));
    lines.push("");
  }
  return lines.join("\n");
};

const StageBars = ({ title, data }: { title: string; data: Record<string, number> }) => {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? Math.max(...entries.map(([, v]) => v)) : 1;
  if (entries.length === 0) return null;
  return (
    <div className="mt-2">
      <p className="text-[11px] font-semibold text-slate-500">{title}</p>
      <div className="mt-1 space-y-1">
        {entries.map(([name, count]) => (
          <div key={name} className="flex items-center gap-2">
            <span className="w-28 truncate text-[11px] text-slate-600">{name}</span>
            <div className="h-2 flex-1 rounded bg-slate-200">
              <div
                className="h-2 rounded bg-slate-700"
                style={{ width: `${Math.max(6, (count / max) * 100)}%` }}
              />
            </div>
            <span className="w-8 text-right text-[11px] text-slate-700">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function SketchConsole() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<
    "idle" | "analyzing" | "complete" | "optimized"
  >("idle");
  const [activeTab, setActiveTab] = useState<"architecture" | "terraform" | "cost">(
    "architecture",
  );

  const [architectureJson, setArchitectureJson] = useState<Record<string, unknown> | null>(null);
  const [terraformCode, setTerraformCode] = useState<string | null>(null);
  const [monthlyTotal, setMonthlyTotal] = useState<number | null>(null);
  const [costBreakdown, setCostBreakdown] = useState<Record<string, number> | null>(null);
  const [region, setRegion] = useState<string | null>(null);
  const [currency, setCurrency] = useState<string | null>(null);
  const [costAssumptions, setCostAssumptions] = useState<{
    pricing_source?: string;
    pricing_error?: string;
    monthly_total_usd?: number;
    monthly_total_krw?: number;
  } | null>(null);
  const [analysisCoverage, setAnalysisCoverage] = useState<number | null>(null);
  const [analysisUnmetHints, setAnalysisUnmetHints] = useState<string[]>([]);
  const [analysisRationale, setAnalysisRationale] = useState<{
    summary?: string;
    intentPoints?: string[];
    designPoints?: string[];
    whyBetter?: string[];
  } | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [, setCurrentVersionNo] = useState<number | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [sessionHistory, setSessionHistory] = useState<SessionListItem[]>([]);
  const [isLoadingSessionHistory, setIsLoadingSessionHistory] = useState(false);
  const [isLoadingSessionDetail, setIsLoadingSessionDetail] = useState(false);
  const [compareSummary, setCompareSummary] = useState<SessionCompareResponse | null>(null);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const [compareBaseSessionId, setCompareBaseSessionId] = useState<string | null>(null);
  const [compareTargetSessionId, setCompareTargetSessionId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorRequestId, setErrorRequestId] = useState<string | null>(null);
  const [githubRepos, setGithubRepos] = useState<GitHubRepoItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isAnalyzingRepo, setIsAnalyzingRepo] = useState(false);
  const [repoAnalysis, setRepoAnalysis] = useState<GitHubRepoAnalyzeResponse | null>(null);
  const [analysisHealth, setAnalysisHealth] = useState<RepoAnalysisHealth | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);
  const [repoFeedback, setRepoFeedback] = useState<RepoAnalysisFeedback | null>(null);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [githubStatus, setGithubStatus] = useState<GitHubConnectionStatus | null>(null);
  const [isLoadingGitHubStatus, setIsLoadingGitHubStatus] = useState(false);
  const [readiness, setReadiness] = useState<RepoReadiness | null>(null);
  const [isLoadingReadiness, setIsLoadingReadiness] = useState(false);

  const getAuth = (): AuthSession | null => {
    try {
      const raw = sessionStorage.getItem("stc-auth");
      if (!raw) return null;
      return JSON.parse(raw) as AuthSession;
    } catch {
      return null;
    }
  };

  const applyUserError = (fallback: string, error: unknown) => {
    const raw = error instanceof Error ? error.message : fallback;
    const match = /\[([0-9a-fA-F-]{8,})\]$/.exec(raw);
    setErrorRequestId(match ? match[1] : null);
    setErrorMessage(match ? raw.replace(/\s*\[[0-9a-fA-F-]{8,}\]$/, "") : raw);
  };

  const authFetch = async (
    url: string,
    token: string,
    init?: RequestInit,
  ): Promise<Response> => {
    const headers = new Headers(init?.headers ?? {});
    headers.set("Authorization", `Bearer ${token}`);
    headers.set("Content-Type", "application/json");

    const res = await fetch(url, {
      ...init,
      headers,
    });

    if (!res.ok) {
      const data = (await res.json().catch(() => ({}))) as ApiErrorPayload;
      const detail = data.detail ?? "";
      const requestId = data.requestId ?? "";
      if (res.status === 401) {
        throw new Error(`로그인이 만료되었어요. 다시 로그인해 주세요.${requestId ? ` [${requestId}]` : ""}`);
      }
      if (res.status === 409 && detail.includes("GitHub")) {
        throw new Error(`GitHub 연결이 필요해요. GitHub 로그인으로 다시 연결해 주세요.${requestId ? ` [${requestId}]` : ""}`);
      }
      throw new Error(`${detail || `요청 처리 중 문제가 발생했어요. (${res.status})`}${requestId ? ` [${requestId}]` : ""}`);
    }

    return res;
  };

  const applySessionDetail = (detail: SessionDetailResponse) => {
    setCurrentProjectId(detail.projectId);
    setCurrentSessionId(detail.sessionId);
    setCurrentVersionNo(detail.versionNo);
    setArchitectureJson(detail.architecture?.architectureJson ?? null);
    setTerraformCode(detail.terraform?.terraformCode ?? null);
    setMonthlyTotal(detail.cost?.monthlyTotal ?? null);
    setCostBreakdown(detail.cost?.costBreakdownJson ?? null);
    setRegion(detail.cost?.region ?? null);
    setCurrency(detail.cost?.currency ?? null);
    setCostAssumptions(detail.cost?.assumptionJson ?? null);
    setGenerationStatus(detail.status === "COST_CALCULATED" ? "optimized" : "complete");
    if (detail.error?.message) {
      setErrorMessage(detail.error.message);
    }
  };

  const loadProjectSessions = async (projectId: string, token: string, apiBaseUrl: string) => {
    setIsLoadingSessionHistory(true);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/projects/${projectId}/sessions`, token);
      const data = (await res.json()) as SessionListResponse;
      setSessionHistory(data.items ?? []);
      return data.items ?? [];
    } finally {
      setIsLoadingSessionHistory(false);
    }
  };

  const loadProjects = async (token: string, apiBaseUrl: string) => {
    setIsLoadingProjects(true);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/projects`, token);
      const data = (await res.json()) as ProjectListResponse;
      setProjects(data.items ?? []);
      return data.items ?? [];
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const loadSessionDetail = async (sessionId: string, token: string, apiBaseUrl: string) => {
    setIsLoadingSessionDetail(true);
    try {
      const detailRes = await authFetch(`${apiBaseUrl}/api/sessions/${sessionId}`, token);
      const detail = (await detailRes.json()) as SessionDetailResponse;
      applySessionDetail(detail);
      return detail;
    } finally {
      setIsLoadingSessionDetail(false);
    }
  };

  const loadCompareSummary = async (
    sessionId: string,
    token: string,
    apiBaseUrl: string,
    baseSessionId?: string,
  ) => {
    setIsLoadingCompare(true);
    try {
      const compareUrl = new URL(`${apiBaseUrl}/api/sessions/${sessionId}/compare`);
      if (baseSessionId) {
        compareUrl.searchParams.set("baseSessionId", baseSessionId);
      }
      const compareRes = await authFetch(compareUrl.toString(), token);
      const compare = (await compareRes.json()) as SessionCompareResponse;
      setCompareSummary(compare);
      return compare;
    } catch (error) {
      setCompareSummary(null);
      throw error;
    } finally {
      setIsLoadingCompare(false);
    }
  };

  const openSessionVersion = async (sessionId: string) => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setErrorMessage(null);
    setErrorRequestId(null);

    try {
      const detail = await loadSessionDetail(sessionId, auth.accessToken, apiBaseUrl);
      const history = await loadProjectSessions(detail.projectId, auth.accessToken, apiBaseUrl);
      if (history.some((item) => item.sessionId === sessionId && item.versionNo > 1)) {
        try {
          await loadCompareSummary(sessionId, auth.accessToken, apiBaseUrl);
        } catch {
          setCompareSummary(null);
        }
      } else {
        setCompareSummary(null);
      }
    } catch (error) {
      applyUserError("세션 상세를 불러오지 못했어요.", error);
    }
  };

  const openProjectHistory = async (projectId: string) => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }

    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setErrorMessage(null);
    setErrorRequestId(null);
    setCurrentProjectId(projectId);
    setCompareSummary(null);

    try {
      const history = await loadProjectSessions(projectId, auth.accessToken, apiBaseUrl);
      if (history.length === 0) {
        setCurrentSessionId(null);
        setCurrentVersionNo(null);
        setArchitectureJson(null);
        setTerraformCode(null);
        setMonthlyTotal(null);
        setCostBreakdown(null);
        setRegion(null);
        setCurrency(null);
        setCostAssumptions(null);
        setGenerationStatus("idle");
        setCompareBaseSessionId(null);
        setCompareTargetSessionId(null);
        return;
      }

      const latest = history[0];
      await loadSessionDetail(latest.sessionId, auth.accessToken, apiBaseUrl);
      setCompareTargetSessionId(latest.sessionId);
      setCompareBaseSessionId(history[1]?.sessionId ?? null);
    } catch (error) {
      applyUserError("프로젝트 이력을 불러오지 못했어요.", error);
    }
  };

  const compareCurrentSession = async () => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("비교할 세션이 없습니다.");
      return;
    }
    if (!compareBaseSessionId || !compareTargetSessionId) {
      setErrorMessage("비교할 두 버전을 모두 선택해 주세요.");
      return;
    }
    if (compareBaseSessionId === compareTargetSessionId) {
      setErrorMessage("같은 버전끼리는 비교할 수 없습니다.");
      return;
    }
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setErrorMessage(null);
    setErrorRequestId(null);
    try {
      await loadCompareSummary(compareTargetSessionId, auth.accessToken, apiBaseUrl, compareBaseSessionId);
    } catch (error) {
      applyUserError("비교 결과를 불러오지 못했어요.", error);
    }
  };

  const findOrCreateProjectForRepoAnalysis = async (
    fullName: string,
    token: string,
    apiBaseUrl: string,
  ): Promise<{ projectId: string }> => {
    const projectName = `repo-${fullName}`;
    const projectListRes = await authFetch(`${apiBaseUrl}/api/projects`, token);
    const projectList = (await projectListRes.json()) as ProjectListResponse;
    const existing = (projectList.items ?? []).find((item) => item.name === projectName);
    if (existing) {
      return { projectId: existing.projectId };
    }

    const createRes = await authFetch(`${apiBaseUrl}/api/projects`, token, {
      method: "POST",
      body: JSON.stringify({
        name: projectName,
        description: `GitHub AWS analysis history for ${fullName}`,
      }),
    });
    return (await createRes.json()) as { projectId: string };
  };

  const persistRepoAnalysisAsSession = async (
    analysis: GitHubRepoAnalyzeResponse,
    token: string,
    apiBaseUrl: string,
  ) => {
    const project = await findOrCreateProjectForRepoAnalysis(analysis.fullName, token, apiBaseUrl);
    setCurrentProjectId(project.projectId);
    await loadProjects(token, apiBaseUrl);

    const sessionRes = await authFetch(
      `${apiBaseUrl}/api/projects/${project.projectId}/sessions`,
      token,
      {
        method: "POST",
        body: JSON.stringify({
          inputType: "TEXT",
          inputText: `GitHub repo analysis: ${analysis.fullName}`,
          inputImageUrl: null,
        }),
      },
    );
    const session = (await sessionRes.json()) as { sessionId: string; versionNo?: number };
    setCurrentSessionId(session.sessionId);
    setCurrentVersionNo(session.versionNo ?? null);

    await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/architecture`, token, {
      method: "POST",
      body: JSON.stringify({
        schemaVersion: "v1",
        architectureJson: analysis.architectureJson,
      }),
    });
    await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/terraform`, token, {
      method: "POST",
    });
    await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/cost`, token, {
      method: "POST",
    });

    const detail = await loadSessionDetail(session.sessionId, token, apiBaseUrl);
    await loadProjectSessions(project.projectId, token, apiBaseUrl);
    setCompareSummary(null);
    return detail;
  };

  const handleGenerate = async (payload: {
    description: string;
    uploadedFile: File | null;
  }) => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }

    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;

    setIsGenerating(true);
    setGenerationStatus("analyzing");
    setErrorMessage(null);
    setErrorRequestId(null);
    setArchitectureJson(null);
    setTerraformCode(null);
    setMonthlyTotal(null);
    setCostBreakdown(null);
    setRegion(null);
    setCurrency(null);
    setCostAssumptions(null);
    setAnalysisCoverage(null);
    setAnalysisUnmetHints([]);
    setAnalysisRationale(null);
    setCurrentProjectId(null);
    setCurrentSessionId(null);
    setCurrentVersionNo(null);
    setSessionHistory([]);
    setCompareSummary(null);
    setCompareBaseSessionId(null);
    setCompareTargetSessionId(null);

    try {
      const toDataUrl = (file: File): Promise<string> =>
        new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result ?? ""));
          reader.onerror = () => reject(new Error("이미지 인코딩 실패"));
          reader.readAsDataURL(file);
        });

      let imageUrl: string | null = null;
      let imageDataUrl: string | null = null;
      if (payload.uploadedFile) {
        imageDataUrl = await toDataUrl(payload.uploadedFile);
        const upRes = await fetch(`${apiBaseUrl}/api/uploads/images`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contentType: payload.uploadedFile.type || "image/png",
            fileName: payload.uploadedFile.name,
          }),
        });

        if (!upRes.ok) {
          throw new Error("업로드 URL 생성 실패");
        }
        const up = (await upRes.json()) as { url: string };
        imageUrl = up.url;
      }

      const projectRes = await authFetch(`${apiBaseUrl}/api/projects`, auth.accessToken, {
        method: "POST",
        body: JSON.stringify({
          name: `project-${Date.now()}`,
          description: payload.description || "dashboard generated project",
        }),
      });
      const project = (await projectRes.json()) as { projectId: string };
      setCurrentProjectId(project.projectId);
      await loadProjects(auth.accessToken, apiBaseUrl);

      const inputType = payload.uploadedFile
        ? payload.description
          ? "TEXT_WITH_SKETCH"
          : "SKETCH"
        : "TEXT";

      const sessionRes = await authFetch(
        `${apiBaseUrl}/api/projects/${project.projectId}/sessions`,
        auth.accessToken,
        {
          method: "POST",
          body: JSON.stringify({
            inputType,
            inputText: payload.description || null,
            inputImageUrl: imageUrl,
          }),
        },
      );
      const session = (await sessionRes.json()) as { sessionId: string };
      setCurrentSessionId(session.sessionId);
      setCurrentVersionNo(null);

      const analyzeRes = await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/analyze`, auth.accessToken, {
        method: "POST",
        body: JSON.stringify({
          input_text: payload.description?.trim()
            ? payload.description
            : `Analyze the uploaded architecture diagram and infer AWS resources and counts precisely.`,
          input_type: payload.uploadedFile ? "sketch" : "text",
          input_image_data_url: imageDataUrl,
        }),
      });
      const analyze = (await analyzeRes.json()) as {
        status: "generated" | "failed";
        parsed_json?: Record<string, unknown>;
        error?: { code?: string; message?: string };
        analysisMeta?: {
          provider?: string;
          modelId?: string | null;
          usedImage?: boolean;
          fallbackUsed?: boolean;
          requirementCoverage?: number;
          unmetHints?: string[];
          rationale?: {
            summary?: string;
            intentPoints?: string[];
            designPoints?: string[];
            whyBetter?: string[];
          };
        };
      };
      if (analyze.status !== "generated") {
        const code = analyze.error?.code ? `[${analyze.error.code}] ` : "";
        throw new Error(`${code}${analyze.error?.message ?? "AI 분석 실패"}`);
      }

      await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/terraform`, auth.accessToken, {
        method: "POST",
      });
      await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}/cost`, auth.accessToken, {
        method: "POST",
      });

      const detail = await loadSessionDetail(session.sessionId, auth.accessToken, apiBaseUrl);
      const history = await loadProjectSessions(project.projectId, auth.accessToken, apiBaseUrl);
      setCompareTargetSessionId(session.sessionId);
      setCompareBaseSessionId(history.find((item) => item.sessionId !== session.sessionId)?.sessionId ?? null);
      setCompareSummary(null);

      console.groupCollapsed("[STC] Analysis Result");
      console.info("sessionId", session.sessionId);
      console.info("analysisMeta", analyze.analysisMeta);
      console.info("parsedJson", analyze.parsed_json);
      console.info("costAssumptions", detail.cost?.assumptionJson);
      console.info("costBreakdown", detail.cost?.costBreakdownJson);
      console.groupEnd();

      setArchitectureJson(detail.architecture?.architectureJson ?? analyze.parsed_json ?? null);
      setAnalysisCoverage(
        typeof analyze.analysisMeta?.requirementCoverage === "number"
          ? analyze.analysisMeta.requirementCoverage
          : null,
      );
      setAnalysisUnmetHints(analyze.analysisMeta?.unmetHints ?? []);
      setAnalysisRationale(analyze.analysisMeta?.rationale ?? null);

      setGenerationStatus("complete");
      setTimeout(() => setGenerationStatus("optimized"), 300);
    } catch (error) {
      console.error("[STC] Generation Failed", error);
      setGenerationStatus("idle");
      applyUserError("생성 중 문제가 발생했어요.", error);
      setArchitectureJson(null);
      setTerraformCode(null);
      setMonthlyTotal(null);
      setCostBreakdown(null);
      setRegion(null);
      setCurrency(null);
      setCostAssumptions(null);
      setAnalysisCoverage(null);
      setAnalysisUnmetHints([]);
      setAnalysisRationale(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const loadGitHubRepos = async () => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }

    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsLoadingRepos(true);
    setErrorMessage(null);
    setErrorRequestId(null);
    try {
      await loadGitHubConnectionStatus();
      const res = await authFetch(`${apiBaseUrl}/api/github/repos`, auth.accessToken);
      const data = (await res.json()) as GitHubRepoListResponse;
      setGithubRepos(data.repos ?? []);
      if ((data.repos?.length ?? 0) > 0) {
        setSelectedRepo((current) => current || data.repos[0].fullName);
      }
    } catch (error) {
      setGithubRepos([]);
      setSelectedRepo("");
      setRepoAnalysis(null);
      applyUserError("GitHub 목록을 불러오지 못했어요.", error);
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const analyzeSelectedGitHubRepo = async (forceRefresh = false) => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }
    if (!selectedRepo) {
      setErrorMessage("분석할 GitHub 레포를 선택해 주세요.");
      return;
    }

    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsAnalyzingRepo(true);
    setGenerationStatus("analyzing");
    setErrorMessage(null);
    setErrorRequestId(null);
    setCompareSummary(null);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/github/repo-analysis`, auth.accessToken, {
        method: "POST",
        body: JSON.stringify({ fullName: selectedRepo, forceRefresh }),
      });
      const data = (await res.json()) as GitHubRepoAnalyzeResponse;
      setRepoAnalysis(data);
      await persistRepoAnalysisAsSession(data, auth.accessToken, apiBaseUrl);
      setAnalysisCoverage(null);
      setAnalysisUnmetHints([]);
      setAnalysisRationale({
        summary: simplifyAwsWords(data.summary),
        intentPoints: data.findings.slice(0, 3).map(simplifyAwsWords),
        designPoints: data.deploymentSteps.slice(0, 4).map(simplifyAwsWords),
        whyBetter: data.risks.slice(0, 3).map(simplifyAwsWords),
      });
      setActiveTab("architecture");
      setGenerationStatus("complete");
      setTimeout(() => setGenerationStatus("optimized"), 300);
      setRepoFeedback(null);
      try {
        await loadRepoAnalysisFeedback(data.fullName);
      } catch {
        // ignore feedback fetch failure after analysis
      }
    } catch (error) {
      setRepoAnalysis(null);
      setGenerationStatus("idle");
      applyUserError("레포 분석 중 문제가 발생했어요.", error);
    } finally {
      setIsAnalyzingRepo(false);
    }
  };

  const loadGitHubConnectionStatus = async () => {
    const auth = getAuth();
    if (!auth?.accessToken) return;
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsLoadingGitHubStatus(true);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/github/status`, auth.accessToken);
      const data = (await res.json()) as GitHubConnectionStatus;
      setGithubStatus(data);
    } catch {
      setGithubStatus(null);
    } finally {
      setIsLoadingGitHubStatus(false);
    }
  };

  const loadReadiness = async () => {
    const auth = getAuth();
    if (!auth?.accessToken) return;
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsLoadingReadiness(true);
    setErrorMessage(null);
    setErrorRequestId(null);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/ops/readiness`, auth.accessToken);
      const data = (await res.json()) as RepoReadiness;
      setReadiness(data);
    } catch (error) {
      setReadiness(null);
      applyUserError("서비스 준비도 조회에 실패했어요.", error);
    } finally {
      setIsLoadingReadiness(false);
    }
  };

  const loadRepoAnalysisFeedback = async (fullName: string) => {
    const auth = getAuth();
    if (!auth?.accessToken) return;
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    const res = await authFetch(
      `${apiBaseUrl}/api/ops/repo-analysis-feedback?fullName=${encodeURIComponent(fullName)}`,
      auth.accessToken,
    );
    const data = (await res.json()) as { fullName: string; feedback: RepoAnalysisFeedback | null };
    setRepoFeedback(data.feedback ?? null);
  };

  const saveRepoAnalysisFeedback = async (verdict: "APPROVE" | "HOLD") => {
    const auth = getAuth();
    if (!auth?.accessToken || !repoAnalysis) {
      setErrorMessage("저장할 분석 결과가 없습니다.");
      return;
    }
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsSavingFeedback(true);
    setErrorMessage(null);
    setErrorRequestId(null);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/ops/repo-analysis-feedback`, auth.accessToken, {
        method: "POST",
        body: JSON.stringify({
          fullName: repoAnalysis.fullName,
          verdict,
          note: verdict === "HOLD" ? "추가 검토 필요" : "배포 진행 가능",
        }),
      });
      const data = (await res.json()) as {
        fullName: string;
        verdict: "APPROVE" | "HOLD";
        note?: string | null;
      };
      setRepoFeedback({
        fullName: data.fullName,
        verdict: data.verdict,
        note: data.note,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      applyUserError("저장 중 문제가 발생했어요.", error);
    } finally {
      setIsSavingFeedback(false);
    }
  };

  const loadRepoAnalysisHealth = async () => {
    const auth = getAuth();
    if (!auth?.accessToken) {
      setErrorMessage("로그인이 필요합니다.");
      return;
    }
    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
    setIsLoadingHealth(true);
    setErrorMessage(null);
    setErrorRequestId(null);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/ops/repo-analysis-health`, auth.accessToken);
      const data = (await res.json()) as RepoAnalysisHealth;
      setAnalysisHealth(data);
    } catch (error) {
      setAnalysisHealth(null);
      applyUserError("문제 점검 정보를 가져오지 못했어요.", error);
    } finally {
      setIsLoadingHealth(false);
    }
  };

  const exportRepoReportMarkdown = async () => {
    if (!repoAnalysis) {
      setErrorMessage("내보낼 분석 결과가 없습니다.");
      return;
    }
    const markdown = buildRepoReportMarkdown(repoAnalysis);
    try {
      await navigator.clipboard.writeText(markdown);
    } catch {
      // ignore clipboard failure; file download still works
    }
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${repoAnalysis.fullName.replace("/", "_")}_aws_report.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportRepoReportPdf = () => {
    if (!repoAnalysis) {
      setErrorMessage("내보낼 분석 결과가 없습니다.");
      return;
    }
    const html = `
      <html>
      <head>
        <meta charset="utf-8" />
        <title>AWS 분석 리포트</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 24px; line-height: 1.5; }
          h1, h2 { margin: 0 0 8px 0; }
          ul { margin-top: 4px; }
        </style>
      </head>
      <body>
        <h1>AWS 분석 리포트 - ${repoAnalysis.fullName}</h1>
        <p><b>신뢰도</b>: ${repoAnalysis.confidenceLabel} (${Math.round(repoAnalysis.confidenceScore * 100)}%)</p>
        <p>${simplifyAwsWords(repoAnalysis.summary)}</p>
        <h2>추천 구성</h2>
        <ul>${repoAnalysis.recommendedStack.map((v) => `<li>${v}</li>`).join("")}</ul>
        <h2>배포 단계</h2>
        <ul>${repoAnalysis.deploymentSteps.map((v) => `<li>${simplifyAwsWords(v)}</li>`).join("")}</ul>
        <h2>주의할 점</h2>
        <ul>${repoAnalysis.risks.map((v) => `<li>${simplifyAwsWords(v)}</li>`).join("")}</ul>
      </body>
      </html>
    `;
    const popup = window.open("", "_blank", "width=960,height=720");
    if (!popup) {
      setErrorMessage("팝업이 차단되어 PDF 출력창을 열 수 없습니다.");
      return;
    }
    popup.document.open();
    popup.document.write(html);
    popup.document.close();
    popup.focus();
    popup.print();
  };

  return (
    <>
      <PageMeta title="Console | Sketch-to-Cloud" description="Sketch-to-Cloud 메인 대시보드" />
      <div className="min-h-screen bg-background">
        <Header generationStatus={generationStatus} />

        <main className="container mx-auto px-4 py-6 lg:px-6">
          {errorMessage ? (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
              {errorRequestId ? (
                <details className="mt-2 text-xs text-red-600">
                  <summary className="cursor-pointer">문제가 계속되면 이 코드로 문의하세요</summary>
                  ?? ??: {errorRequestId}
                </details>
              ) : null}
            </div>
          ) : null}
          <div className="mb-4 rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-800">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <button
                type="button"
                onClick={loadGitHubRepos}
                disabled={isLoadingRepos}
                className="h-10 rounded-md bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-60"
              >
                {isLoadingRepos ? "레포 불러오는 중..." : "GitHub 레포 불러오기"}
              </button>
              <select
                value={selectedRepo}
                onChange={(event) => setSelectedRepo(event.target.value)}
                className="h-10 min-w-[260px] rounded-md border border-slate-300 bg-white px-3 text-sm"
                disabled={githubRepos.length === 0}
              >
                {githubRepos.length === 0 ? (
                  <option value="">레포를 먼저 불러와 주세요</option>
                ) : (
                  githubRepos.map((repo) => (
                    <option key={repo.fullName} value={repo.fullName}>
                      {repo.fullName}
                    </option>
                  ))
                )}
              </select>
              <button
                type="button"
                onClick={() => analyzeSelectedGitHubRepo(false)}
                disabled={isAnalyzingRepo || !selectedRepo}
                className="h-10 rounded-md bg-[#FF9900] px-4 text-sm font-medium text-white disabled:opacity-60"
              >
                {isAnalyzingRepo ? "AWS 분석 중..." : "선택 레포 AWS 분석"}
              </button>
              <button
                type="button"
                onClick={() => analyzeSelectedGitHubRepo(true)}
                disabled={isAnalyzingRepo || !selectedRepo}
                className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-800 disabled:opacity-60"
              >
                캐시 무시 재분석
              </button>
              <button
                type="button"
                onClick={loadRepoAnalysisHealth}
                disabled={isLoadingHealth}
                className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-800 disabled:opacity-60"
              >
                {isLoadingHealth ? "확인 중..." : "문제 점검"}
              </button>
              <button
                type="button"
                onClick={loadGitHubConnectionStatus}
                disabled={isLoadingGitHubStatus}
                className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-800 disabled:opacity-60"
              >
                {isLoadingGitHubStatus ? "연결 확인 중..." : "GitHub 연결 점검"}
              </button>
              <button
                type="button"
                onClick={loadReadiness}
                disabled={isLoadingReadiness}
                className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-800 disabled:opacity-60"
              >
                {isLoadingReadiness ? "계산 중..." : "서비스 준비도"}
              </button>
            </div>
            {githubStatus ? (
              <div className="mt-3 rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-700">
                <p className="font-semibold text-slate-900">
                  GitHub 연결 상태:{" "}
                  {githubStatus.tokenValid && githubStatus.githubApiReachable ? "정상" : "점검 필요"}
                </p>
                <p className="mt-1">
                  OAuth 설정={String(githubStatus.oauthConfigured)} / 토큰={String(githubStatus.tokenPresent)} /
                  유효={String(githubStatus.tokenValid)}
                </p>
                <p className="mt-1">
                  계정={githubStatus.accountLogin ?? "-"} / private 접근={String(githubStatus.privateRepoAccess)} /
                  확인 레포수={githubStatus.estimatedRepoCount ?? 0}
                </p>
                {githubStatus.issues.length > 0 ? (
                  <ul className="mt-2 list-disc pl-5">
                    {githubStatus.issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            {readiness ? (
              <div className="mt-3 rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-700">
                <p className="font-semibold text-slate-900">
                  서비스 준비도: {readiness.score}점 ({readiness.grade})
                </p>
                <ul className="mt-2 list-disc pl-5">
                  {readiness.checklist.map((item) => (
                    <li key={item.name}>
                      {item.name}: {item.ok ? "정상" : "개선 필요"} - {item.detail}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {analysisHealth ? (
              <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                <p className="font-semibold text-slate-900">
                  AI 전용 정책: {analysisHealth.policy.ready ? "정상" : "주의 필요"}
                </p>
                <p className="mt-1">
                  Bedrock={String(analysisHealth.policy.bedrockEnabled)} / Strict=
                  {String(analysisHealth.policy.bedrockStrictMode)} / Fallback=
                  {String(analysisHealth.policy.bedrockFallbackEnabled)}
                </p>
                <p className="mt-1">
                  캐시: size {analysisHealth.cache.size}, hits {analysisHealth.cache.hits}, misses{" "}
                  {analysisHealth.cache.misses}
                </p>
                <p className="mt-1">최근 실패: {analysisHealth.failures.total}건</p>
                <StageBars title="실패 Stage 분포" data={analysisHealth.failures.byStage ?? {}} />
                <StageBars title="실패 유형 분포" data={analysisHealth.failures.byType ?? {}} />
                {analysisHealth.recommendations.length > 0 ? (
                  <ul className="mt-2 list-disc pl-5">
                    {analysisHealth.recommendations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            {repoAnalysis ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">{repoAnalysis.fullName}</p>
                <p className="mt-1 text-sm text-slate-700">{simplifyAwsWords(repoAnalysis.summary)}</p>
                <p className="mt-2 text-xs text-slate-500">
                  분석 결과를 아래 기존 탭(아키텍처/테라폼/비용)에 자동 반영했습니다.
                </p>
                <details className="mt-3 rounded-md border border-slate-200 bg-white px-3 py-2">
                  <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                    AI 분석 리포트 보기
                  </summary>
                  <div className="mt-3 text-xs text-slate-700">
                    <p>
                      신뢰도: <span className="font-semibold">{repoAnalysis.confidenceLabel}</span>{" "}
                      ({Math.round(repoAnalysis.confidenceScore * 100)}%)
                    </p>
                    <p className="mt-1">분석 엔진: {repoAnalysis.analysisProvider}</p>
                    <p className="mt-1">
                      분석 모드: 정밀 분석
                      {repoAnalysis.cacheHit ? " (캐시 결과)" : ""}
                    </p>
                    {repoAnalysis.evidenceFiles.length > 0 ? (
                      <p className="mt-1 break-all">
                        근거 파일: {repoAnalysis.evidenceFiles.slice(0, 8).join(", ")}
                      </p>
                    ) : null}
                  </div>
                  {repoAnalysis.confidenceReasons.length > 0 ? (
                    <>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        신뢰도 근거
                      </p>
                      <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                        {repoAnalysis.confidenceReasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {repoAnalysis.improvementActions.length > 0 ? (
                    <>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">정확도 높이기</p>
                      <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                        {repoAnalysis.improvementActions.map((action) => (
                          <li key={action}>{action}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {repoAnalysis.findings.length > 0 ? (
                    <>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        초보자용 핵심 요약
                      </p>
                      <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                        {repoAnalysis.findings.map((finding) => (
                          <li key={finding}>{simplifyAwsWords(finding)}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">추천 구성</p>
                  <p className="mt-1 text-sm text-slate-800">{repoAnalysis.recommendedStack.join(", ")}</p>
                  <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">다음에 할 일</p>
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                    {repoAnalysis.deploymentSteps.map((step) => (
                      <li key={step}>{simplifyAwsWords(step)}</li>
                    ))}
                  </ul>
                  {repoAnalysis.risks.length > 0 ? (
                    <>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">주의할 점</p>
                      <ul className="mt-1 list-disc pl-5 text-sm text-rose-700">
                        {repoAnalysis.risks.map((risk) => (
                          <li key={risk}>{simplifyAwsWords(risk)}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {repoAnalysis.cost ? (
                    <>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">예상 월 비용</p>
                      <p className="mt-1 text-sm text-slate-800">
                        {(repoAnalysis.cost.monthlyTotal ?? repoAnalysis.cost.monthly_total ?? 0).toLocaleString()}{" "}
                        {repoAnalysis.cost.currency ?? "USD"} / month
                      </p>
                    </>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={exportRepoReportMarkdown}
                      className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800"
                    >
                      리포트 Markdown 내보내기
                    </button>
                    <button
                      type="button"
                      onClick={exportRepoReportPdf}
                      className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800"
                    >
                      PDF 출력창 열기
                    </button>
                    <button
                      type="button"
                      onClick={() => saveRepoAnalysisFeedback("APPROVE")}
                      disabled={isSavingFeedback}
                      className="h-9 rounded-md bg-emerald-600 px-3 text-xs font-medium text-white disabled:opacity-60"
                    >
                      {isSavingFeedback ? "저장 중..." : "분석 승인"}
                    </button>
                    <button
                      type="button"
                      onClick={() => saveRepoAnalysisFeedback("HOLD")}
                      disabled={isSavingFeedback}
                      className="h-9 rounded-md bg-amber-500 px-3 text-xs font-medium text-white disabled:opacity-60"
                    >
                      {isSavingFeedback ? "저장 중..." : "보류"}
                    </button>
                  </div>
                  {repoFeedback ? (
                    <p className="mt-2 text-xs text-slate-600">
                      최근 판단:{" "}
                      <span className="font-semibold">
                        {repoFeedback.verdict === "APPROVE" ? "승인" : "보류"}
                      </span>
                      {repoFeedback.note ? ` (${repoFeedback.note})` : ""}
                    </p>
                  ) : null}
                </details>
              </div>
            ) : null}
          </div>
          <div className="mb-4 rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-800">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">프로젝트 탐색</p>
                <p className="mt-1 text-xs text-slate-500">
                  이전에 생성한 프로젝트를 다시 열고 그 안의 세션 버전 이력을 이어서 확인할 수 있습니다.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    const auth = getAuth();
                    if (!auth?.accessToken) {
                      setErrorMessage("로그인이 필요합니다.");
                      return;
                    }
                    const apiBaseUrl = auth.apiBaseUrl ?? DEFAULT_API_BASE_URL;
                    setErrorMessage(null);
                    setErrorRequestId(null);
                    try {
                      await loadProjects(auth.accessToken, apiBaseUrl);
                    } catch (error) {
                      applyUserError("프로젝트 목록을 불러오지 못했어요.", error);
                    }
                  }}
                  disabled={isLoadingProjects}
                  className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 disabled:opacity-50"
                >
                  {isLoadingProjects ? "프로젝트 불러오는 중..." : "프로젝트 목록 새로고침"}
                </button>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {projects.length === 0 ? (
                <p className="text-xs text-slate-500">
                  아직 불러온 프로젝트가 없습니다. 위 버튼을 눌러 기존 프로젝트 목록을 가져와 보세요.
                </p>
              ) : (
                projects.map((project) => (
                  <button
                    key={project.projectId}
                    type="button"
                    onClick={() => {
                      void openProjectHistory(project.projectId);
                    }}
                    className={`rounded-md border px-3 py-2 text-left text-xs transition ${
                      currentProjectId === project.projectId
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-semibold">{project.name}</div>
                    <div className={currentProjectId === project.projectId ? "text-slate-200" : "text-slate-500"}>
                      {project.description || "설명 없음"}
                    </div>
                    <div className={currentProjectId === project.projectId ? "mt-1 text-[10px] text-slate-300" : "mt-1 text-[10px] text-slate-400"}>
                      updated {project.updatedAt.slice(0, 10)}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="mb-4 rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-800">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">세션 이력</p>
                <p className="mt-1 text-xs text-slate-500">
                  현재 프로젝트의 버전 흐름을 확인하고 원하는 두 버전을 골라 비교할 수 있습니다.
                </p>
                {currentProjectId ? (
                  <p className="mt-1 text-[11px] text-slate-400">projectId: {currentProjectId}</p>
                ) : (
                  <p className="mt-1 text-[11px] text-slate-400">생성을 한 번 실행하면 여기서 v1, v2 이력이 보입니다.</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    void compareCurrentSession();
                  }}
                  disabled={
                    !compareBaseSessionId ||
                    !compareTargetSessionId ||
                    isLoadingCompare ||
                    compareBaseSessionId === compareTargetSessionId
                  }
                  className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 disabled:opacity-50"
                >
                  {isLoadingCompare ? "비교 불러오는 중..." : "선택 버전끼리 비교"}
                </button>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-4 text-[11px] text-slate-500">
              <span>
                기준 버전:{" "}
                <strong className="text-slate-700">
                  {sessionHistory.find((item) => item.sessionId === compareBaseSessionId)?.versionNo
                    ? `v${sessionHistory.find((item) => item.sessionId === compareBaseSessionId)?.versionNo}`
                    : "-"}
                </strong>
              </span>
              <span>
                비교 버전:{" "}
                <strong className="text-slate-700">
                  {sessionHistory.find((item) => item.sessionId === compareTargetSessionId)?.versionNo
                    ? `v${sessionHistory.find((item) => item.sessionId === compareTargetSessionId)?.versionNo}`
                    : "-"}
                </strong>
              </span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {isLoadingSessionHistory ? (
                <p className="text-xs text-slate-500">세션 목록을 불러오는 중입니다.</p>
              ) : sessionHistory.length === 0 ? (
                <p className="text-xs text-slate-500">아직 저장된 세션 이력이 없습니다.</p>
              ) : (
                sessionHistory.map((item) => (
                  <button
                    key={item.sessionId}
                    type="button"
                    onClick={() => {
                      void openSessionVersion(item.sessionId);
                    }}
                    disabled={isLoadingSessionDetail}
                    className={`rounded-md border px-3 py-2 text-left text-xs transition ${
                      currentSessionId === item.sessionId
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
                    } disabled:opacity-60`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold">v{item.versionNo}</div>
                        <div className={currentSessionId === item.sessionId ? "text-slate-200" : "text-slate-500"}>
                          {item.status}
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] ${
                            compareBaseSessionId === item.sessionId
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          기준
                        </span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] ${
                            compareTargetSessionId === item.sessionId
                              ? "bg-blue-100 text-blue-700"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          비교
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 flex gap-1">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setCompareBaseSessionId(item.sessionId);
                          setCompareSummary(null);
                        }}
                        className="rounded border border-slate-300 px-2 py-1 text-[10px] text-slate-700 hover:bg-slate-50"
                      >
                        기준 선택
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setCompareTargetSessionId(item.sessionId);
                          setCompareSummary(null);
                        }}
                        className="rounded border border-slate-300 px-2 py-1 text-[10px] text-slate-700 hover:bg-slate-50"
                      >
                        비교 선택
                      </button>
                    </div>
                  </button>
                ))
              )}
            </div>

            {compareSummary ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-semibold text-slate-900">
                  비교 요약: v{compareSummary.baseSession.versionNo} {"->"} v{compareSummary.targetSession.versionNo}
                </p>
                <div className="mt-2 grid gap-2 md:grid-cols-3">
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="text-[11px] text-slate-500">JSON 변경</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">
                      {compareSummary.jsonDiff.length}건
                    </p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="text-[11px] text-slate-500">Terraform 변경</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">
                      {compareSummary.terraformDiff.changed ? "있음" : "없음"}
                    </p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="text-[11px] text-slate-500">월 비용 차이</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">
                      {formatCurrencyDelta(compareSummary.costDiff.monthlyTotal.delta)}
                    </p>
                  </div>
                </div>
                <div className="mt-3 grid gap-3 xl:grid-cols-[1.2fr_1fr]">
                  <div className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold text-slate-700">JSON diff 상세</p>
                      <span className="text-[11px] text-slate-500">
                        {compareSummary.jsonDiff.length}개 변경
                      </span>
                    </div>
                    {compareSummary.jsonDiff.length === 0 ? (
                      <p className="mt-2 text-xs text-slate-500">아키텍처 JSON 변경이 없습니다.</p>
                    ) : (
                      <div className="mt-2 space-y-2">
                        {compareSummary.jsonDiff.map((item) => (
                          <div
                            key={`${item.path}-${item.changeType}`}
                            className="rounded-md border border-slate-200 bg-slate-50 p-2"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded bg-slate-900 px-1.5 py-0.5 text-[10px] text-white">
                                {item.changeType}
                              </span>
                              <code className="text-[11px] text-slate-700">{item.path}</code>
                            </div>
                            <div className="mt-2 grid gap-2 md:grid-cols-2">
                              <div className="rounded border border-slate-200 bg-white p-2">
                                <p className="text-[10px] font-semibold text-slate-500">기준 버전</p>
                                <p className="mt-1 break-all text-[11px] text-slate-700">
                                  {previewValue(item.before)}
                                </p>
                              </div>
                              <div className="rounded border border-slate-200 bg-white p-2">
                                <p className="text-[10px] font-semibold text-slate-500">비교 버전</p>
                                <p className="mt-1 break-all text-[11px] text-slate-700">
                                  {previewValue(item.after)}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-slate-700">Terraform diff</p>
                        <span className="text-[11px] text-slate-500">
                          {compareSummary.terraformDiff.changed ? "변경 있음" : "변경 없음"}
                        </span>
                      </div>
                      {compareSummary.terraformDiff.diff ? (
                        <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-[11px] text-slate-100">
                          <code>{compareSummary.terraformDiff.diff}</code>
                        </pre>
                      ) : (
                        <p className="mt-2 text-xs text-slate-500">Terraform 코드 차이가 없습니다.</p>
                      )}
                    </div>

                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <p className="text-xs font-semibold text-slate-700">비용 비교 상세</p>
                      <div className="mt-2 grid gap-2 md:grid-cols-3">
                        <div className="rounded border border-slate-200 bg-slate-50 p-2">
                          <p className="text-[10px] font-semibold text-slate-500">기준 월 비용</p>
                          <p className="mt-1 text-sm font-semibold text-slate-900">
                            {formatCurrencyDelta(compareSummary.costDiff.monthlyTotal.before)}
                          </p>
                        </div>
                        <div className="rounded border border-slate-200 bg-slate-50 p-2">
                          <p className="text-[10px] font-semibold text-slate-500">비교 월 비용</p>
                          <p className="mt-1 text-sm font-semibold text-slate-900">
                            {formatCurrencyDelta(compareSummary.costDiff.monthlyTotal.after)}
                          </p>
                        </div>
                        <div className="rounded border border-slate-200 bg-slate-50 p-2">
                          <p className="text-[10px] font-semibold text-slate-500">증감</p>
                          <p className="mt-1 text-sm font-semibold text-slate-900">
                            {formatCurrencyDelta(compareSummary.costDiff.monthlyTotal.delta)}
                          </p>
                        </div>
                      </div>

                      {compareSummary.costDiff.breakdown &&
                      Object.keys(compareSummary.costDiff.breakdown).length > 0 ? (
                        <div className="mt-3 overflow-x-auto">
                          <table className="min-w-full text-left text-[11px] text-slate-700">
                            <thead>
                              <tr className="border-b border-slate-200 text-slate-500">
                                <th className="py-2 pr-3 font-semibold">항목</th>
                                <th className="py-2 pr-3 font-semibold">기준</th>
                                <th className="py-2 pr-3 font-semibold">비교</th>
                                <th className="py-2 font-semibold">증감</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(compareSummary.costDiff.breakdown).map(([key, delta]) => (
                                <tr key={key} className="border-b border-slate-100">
                                  <td className="py-2 pr-3 font-medium text-slate-800">{key}</td>
                                  <td className="py-2 pr-3">{formatCurrencyDelta(delta.before)}</td>
                                  <td className="py-2 pr-3">{formatCurrencyDelta(delta.after)}</td>
                                  <td className="py-2">{formatCurrencyDelta(delta.delta)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="mt-3 text-xs text-slate-500">비용 breakdown 변경 정보가 없습니다.</p>
                      )}

                      {compareSummary.costDiff.assumptionsChanged &&
                      compareSummary.costDiff.assumptionsChanged.length > 0 ? (
                        <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                          <p className="text-[11px] font-semibold text-slate-700">비용 가정 변경</p>
                          <div className="mt-2 space-y-2">
                            {compareSummary.costDiff.assumptionsChanged.map((item) => (
                              <div key={`${item.path}-${item.changeType}`} className="rounded bg-white p-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-700">
                                    {item.changeType}
                                  </span>
                                  <code className="text-[11px] text-slate-700">{item.path}</code>
                                </div>
                                <p className="mt-1 text-[11px] text-slate-600">
                                  {previewValue(item.before)} {"->"} {previewValue(item.after)}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            ) : compareBaseSessionId && compareTargetSessionId && compareBaseSessionId === compareTargetSessionId ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                서로 다른 두 버전을 골라 비교해 주세요.
              </div>
            ) : !compareBaseSessionId || !compareTargetSessionId ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                세션 카드에서 `기준 선택`, `비교 선택`을 눌러 두 버전을 고른 뒤 비교할 수 있습니다.
              </div>
            ) : currentSessionId && sessionHistory[0]?.sessionId === currentSessionId ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                비교 버튼을 누르면 선택한 두 버전의 차이를 요약해서 보여줍니다.
              </div>
            ) : null}
          </div>
          {analysisCoverage !== null && analysisCoverage < 0.75 ? (
            <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              요구사항 반영률이 낮습니다 ({Math.round(analysisCoverage * 100)}%). 미반영 힌트:{" "}
              {analysisUnmetHints.length ? analysisUnmetHints.join(", ") : "없음"}
            </div>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[420px_1fr] xl:grid-cols-[480px_1fr]">
            <ControlPanel onGenerate={handleGenerate} isGenerating={isGenerating} />
            <ResultPanel
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              generationStatus={generationStatus}
              architectureJson={architectureJson}
              architectureRationale={analysisRationale}
              terraformCode={terraformCode}
              monthlyTotal={monthlyTotal}
              costBreakdown={costBreakdown}
              region={region}
              currency={currency}
              assumptions={costAssumptions}
            />
          </div>
        </main>
      </div>
    </>
  );
}

