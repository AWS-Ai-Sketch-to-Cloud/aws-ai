"use client";

import { Receipt } from "lucide-react";
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { ScrollArea } from "@/components/ui/scroll-area";

interface CostAnalysisProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized";
  monthlyTotal?: number | null;
  costBreakdown?: Record<string, number> | null;
  region?: string | null;
  currency?: string | null;
  assumptions?: {
    pricing_source?: string;
    pricing_error?: string;
    monthly_total_usd?: number;
    monthly_total_krw?: number;
    optimization?: {
      cost_optimization?: {
        actions?: string[];
        optimized_monthly_total?: number;
        savings_amount?: number;
        savings_percent?: number;
        currency?: string;
      };
      quality_recommendations?: {
        add?: string[];
        remove?: string[];
      };
      scenarios?: Array<{
        name: string;
        monthly_total: number;
        delta_amount: number;
        delta_percent: number;
        currency: string;
        notes?: string[];
      }>;
      recommended_scenario?: string;
    };
  } | null;
}

export function CostAnalysis({
  generationStatus,
  monthlyTotal,
  costBreakdown,
  region,
  currency,
  assumptions,
}: CostAnalysisProps) {
  if (generationStatus === "idle") {
    return (
      <div className="flex h-[640px] items-center justify-center bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
        <Empty>
          <EmptyMedia variant="icon">
            <Receipt className="h-10 w-10" strokeWidth={1.4} />
          </EmptyMedia>
          <EmptyTitle>비용 분석</EmptyTitle>
          <EmptyDescription>
            분석이 끝나면 예상 월 비용과 최적화 포인트가 표시됩니다.
          </EmptyDescription>
        </Empty>
      </div>
    );
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[640px] items-center justify-center bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 animate-spin rounded-full border-2 border-[#d9e4f2] border-t-[#487bff]" />
          <p className="mt-4 text-sm font-semibold text-[#122033]">비용을 계산하는 중...</p>
        </div>
      </div>
    );
  }

  const total = monthlyTotal ?? 0;
  const breakdown = costBreakdown ?? {};
  const items = Object.entries(breakdown).filter(([name, value]) => {
    if (name.toLowerCase() === "total") return false;
    return Number(value) > 0;
  });

  return (
    <ScrollArea className="h-[640px] bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
      <div className="p-6">
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[1.5rem] border border-[#d9e4f2] bg-white/88 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#487bff]">
              Monthly total
            </p>
            <p className="mt-3 text-3xl font-semibold text-[#122033]">
              {new Intl.NumberFormat("ko-KR", {
                style: "currency",
                currency: currency || "KRW",
                maximumFractionDigits: 0,
              }).format(total)}
            </p>
            <p className="mt-2 text-sm text-[#65748b]">리전: {region ?? "N/A"}</p>
            {assumptions?.pricing_source ? (
              <p className="mt-1 text-xs text-[#7d8ba0]">
                pricing source: <span className="font-medium">{assumptions.pricing_source}</span>
              </p>
            ) : null}
          </div>

          <div className="rounded-[1.5rem] border border-[#d9e4f2] bg-white/88 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#487bff]">
              Notes
            </p>
            {assumptions?.pricing_error ? (
              <div className="mt-3 rounded-2xl border border-[#ffd99c] bg-[#fff7e8] px-4 py-3 text-sm text-[#8b5a00]">
                실시간 AWS 가격 조회에 실패해 fallback 추정값을 사용했습니다.
              </div>
            ) : (
              <p className="mt-3 text-sm leading-6 text-[#65748b]">
                현재 계산된 리소스 기준으로 월 비용을 추정했습니다. 상세 항목과
                최적화 제안을 함께 검토하세요.
              </p>
            )}
          </div>
        </div>

        <div className="mt-5 space-y-3">
          <p className="text-sm font-semibold text-[#122033]">비용 항목</p>
          {items.length === 0 ? (
            <div className="rounded-2xl border border-[#d9e4f2] bg-white/88 p-4 text-sm text-[#65748b]">
              상세 비용 항목이 아직 없습니다.
            </div>
          ) : (
            items.map(([name, value]) => (
              <div
                key={name}
                className="rounded-2xl border border-[#d9e4f2] bg-white/88 p-4"
              >
                <div className="flex items-center justify-between gap-4">
                  <span className="text-sm font-medium text-[#122033]">{name}</span>
                  <span className="text-sm font-semibold text-[#487bff]">
                    {new Intl.NumberFormat("ko-KR", {
                      style: "currency",
                      currency: currency || "KRW",
                      maximumFractionDigits: 0,
                    }).format(Number(value))}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </ScrollArea>
  );
}
