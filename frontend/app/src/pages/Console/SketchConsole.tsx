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
};

const DEFAULT_API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

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
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [githubRepos, setGithubRepos] = useState<GitHubRepoItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isAnalyzingRepo, setIsAnalyzingRepo] = useState(false);
  const [repoAnalysis, setRepoAnalysis] = useState<GitHubRepoAnalyzeResponse | null>(null);

  const getAuth = (): AuthSession | null => {
    try {
      const raw = sessionStorage.getItem("stc-auth");
      if (!raw) return null;
      return JSON.parse(raw) as AuthSession;
    } catch {
      return null;
    }
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
      const data = (await res.json().catch(() => ({}))) as { detail?: string };
      if (res.status === 401) {
        throw new Error("인증이 만료되었습니다. 다시 로그인해 주세요. (401 Unauthorized)");
      }
      throw new Error(data.detail ?? `HTTP ${res.status}`);
    }

    return res;
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

      const analyzeRes = await authFetch(`${apiBaseUrl}/sessions/${session.sessionId}/analyze`, auth.accessToken, {
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

      const detailRes = await authFetch(`${apiBaseUrl}/api/sessions/${session.sessionId}`, auth.accessToken);
      const detail = (await detailRes.json()) as {
        architecture?: { architectureJson?: Record<string, unknown> };
        terraform?: { terraformCode?: string };
        cost?: {
          monthlyTotal?: number;
          costBreakdownJson?: Record<string, number>;
          region?: string;
          currency?: string;
          assumptionJson?: {
            ec2_count?: number;
            pricing_source?: string;
            pricing_error?: string;
            monthly_total_usd?: number;
            monthly_total_krw?: number;
          };
        };
      };

      console.groupCollapsed("[STC] Analysis Result");
      console.info("sessionId", session.sessionId);
      console.info("analysisMeta", analyze.analysisMeta);
      console.info("parsedJson", analyze.parsed_json);
      console.info("costAssumptions", detail.cost?.assumptionJson);
      console.info("costBreakdown", detail.cost?.costBreakdownJson);
      console.groupEnd();

      setArchitectureJson(detail.architecture?.architectureJson ?? analyze.parsed_json ?? null);
      setTerraformCode(detail.terraform?.terraformCode ?? null);
      setMonthlyTotal(detail.cost?.monthlyTotal ?? null);
      setCostBreakdown(detail.cost?.costBreakdownJson ?? null);
      setRegion(detail.cost?.region ?? null);
      setCurrency(detail.cost?.currency ?? null);
      setCostAssumptions(detail.cost?.assumptionJson ?? null);
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
      setErrorMessage(error instanceof Error ? error.message : "생성 중 오류가 발생했습니다.");
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
    try {
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
      setErrorMessage(error instanceof Error ? error.message : "GitHub 레포 조회 중 오류가 발생했습니다.");
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const analyzeSelectedGitHubRepo = async () => {
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
    setErrorMessage(null);
    try {
      const res = await authFetch(`${apiBaseUrl}/api/github/repo-analysis`, auth.accessToken, {
        method: "POST",
        body: JSON.stringify({ fullName: selectedRepo }),
      });
      const data = (await res.json()) as GitHubRepoAnalyzeResponse;
      setRepoAnalysis(data);
    } catch (error) {
      setRepoAnalysis(null);
      setErrorMessage(error instanceof Error ? error.message : "GitHub 레포 분석 중 오류가 발생했습니다.");
    } finally {
      setIsAnalyzingRepo(false);
    }
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
                onClick={analyzeSelectedGitHubRepo}
                disabled={isAnalyzingRepo || !selectedRepo}
                className="h-10 rounded-md bg-[#FF9900] px-4 text-sm font-medium text-white disabled:opacity-60"
              >
                {isAnalyzingRepo ? "AWS 분석 중..." : "선택 레포 AWS 분석"}
              </button>
            </div>
            {repoAnalysis ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">{repoAnalysis.fullName}</p>
                <p className="mt-1 text-sm text-slate-700">{repoAnalysis.summary}</p>
                {repoAnalysis.findings.length > 0 ? (
                  <>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Findings</p>
                    <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                      {repoAnalysis.findings.map((finding) => (
                        <li key={finding}>{finding}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Recommended Stack
                </p>
                <p className="mt-1 text-sm text-slate-800">{repoAnalysis.recommendedStack.join(", ")}</p>
                <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Deployment Steps
                </p>
                <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                  {repoAnalysis.deploymentSteps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
                {repoAnalysis.risks.length > 0 ? (
                  <>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Risks</p>
                    <ul className="mt-1 list-disc pl-5 text-sm text-rose-700">
                      {repoAnalysis.risks.map((risk) => (
                        <li key={risk}>{risk}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
                {repoAnalysis.cost ? (
                  <>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Estimated Cost</p>
                    <p className="mt-1 text-sm text-slate-800">
                      {(repoAnalysis.cost.monthlyTotal ?? repoAnalysis.cost.monthly_total ?? 0).toLocaleString()}{" "}
                      {repoAnalysis.cost.currency ?? "USD"} / month
                    </p>
                  </>
                ) : null}
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Architecture JSON
                  </summary>
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
                    {JSON.stringify(repoAnalysis.architectureJson, null, 2)}
                  </pre>
                </details>
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Terraform Preview
                  </summary>
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
                    {repoAnalysis.terraformCode}
                  </pre>
                </details>
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

