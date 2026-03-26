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
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
    } finally {
      setIsGenerating(false);
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

