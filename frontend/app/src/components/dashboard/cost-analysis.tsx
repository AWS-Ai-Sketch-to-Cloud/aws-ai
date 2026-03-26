
"use client"

import { Receipt } from "lucide-react"
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ScrollArea } from "@/components/ui/scroll-area"

interface CostAnalysisProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
  monthlyTotal?: number | null
  costBreakdown?: Record<string, number> | null
  region?: string | null
  currency?: string | null
  assumptions?: {
    pricing_source?: string
    pricing_error?: string
    monthly_total_usd?: number
    monthly_total_krw?: number
    optimization?: {
      cost_optimization?: {
        actions?: string[]
        optimized_monthly_total?: number
        savings_amount?: number
        savings_percent?: number
        currency?: string
      }
      quality_recommendations?: {
        add?: string[]
        remove?: string[]
      }
      scenarios?: Array<{
        name: string
        monthly_total: number
        delta_amount: number
        delta_percent: number
        currency: string
        notes?: string[]
      }>
      recommended_scenario?: string
    }
  } | null
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
      <div className="flex h-[600px] items-center justify-center">
        <Empty>
          <EmptyMedia variant="icon"><Receipt className="h-10 w-10" strokeWidth={1} /></EmptyMedia>
          <EmptyTitle>비용 분석</EmptyTitle>
          <EmptyDescription>분석 완료 후 실제 비용 추정 결과가 표시됩니다.</EmptyDescription>
        </Empty>
      </div>
    )
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 animate-spin rounded-full border-2 border-muted border-t-primary" />
          <p className="mt-4 text-sm font-medium text-foreground">비용 계산 중...</p>
        </div>
      </div>
    )
  }

  const total = monthlyTotal ?? 0
  const breakdown = costBreakdown ?? {}
  const items = Object.entries(breakdown).filter(([name, value]) => {
    if (name.toLowerCase() === "total") return false
    return Number(value) > 0
  })

  return (
    <ScrollArea className="h-[600px]">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-foreground">월간 비용 추정</h3>
        <p className="text-xs text-muted-foreground">{region ?? "N/A"}</p>
        {assumptions?.pricing_source ? (
          <p className="mt-1 text-xs text-muted-foreground">
            pricing source: <span className="font-medium">{assumptions.pricing_source}</span>
          </p>
        ) : null}
        {assumptions?.pricing_error ? (
          <div className="mt-2 rounded-lg border border-amber-300/50 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            실시간 AWS 가격 조회 실패로 fallback 추정값이 사용되었습니다.
          </div>
        ) : null}

        <div className="mt-4 rounded-xl border border-border/50 bg-secondary/20 p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Monthly Total</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{new Intl.NumberFormat("ko-KR", { style: "currency", currency: currency || "KRW", maximumFractionDigits: 0 }).format(total)}</p>
        </div>

        {assumptions?.monthly_total_usd && assumptions?.monthly_total_krw ? (
          <p className="mt-2 text-xs text-muted-foreground">
            USD {assumptions.monthly_total_usd.toFixed(2)} / KRW {Math.round(assumptions.monthly_total_krw).toLocaleString("ko-KR")}
          </p>
        ) : null}

        <div className="mt-4 space-y-2">
          {items.length === 0 ? (
            <div className="rounded-lg border border-border/30 p-3 text-sm text-muted-foreground">상세 비용 항목 없음</div>
          ) : (
            items.map(([name, value]) => (
              <div key={name} className="rounded-lg border border-border/30 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">{name}</span>
                  <span className="text-sm font-semibold text-primary">{new Intl.NumberFormat("ko-KR", { style: "currency", currency: currency || "KRW", maximumFractionDigits: 0 }).format(Number(value))}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {assumptions?.optimization ? (
          <div className="mt-6 space-y-3">
            <h4 className="text-sm font-semibold text-foreground">AI 최적화 제안</h4>
            {assumptions.optimization.cost_optimization?.actions?.length ? (
              <div className="rounded-lg border border-emerald-300/50 bg-emerald-50 p-3">
                <p className="text-xs font-medium text-emerald-700">절감 액션</p>
                {assumptions.optimization.cost_optimization.actions.map((item) => (
                  <p key={item} className="mt-1 text-xs text-emerald-700">- {item}</p>
                ))}
                <p className="mt-2 text-xs text-emerald-700">
                  예상 절감: {assumptions.optimization.cost_optimization.savings_amount ?? 0}{" "}
                  {assumptions.optimization.cost_optimization.currency ?? currency ?? "USD"} (
                  {assumptions.optimization.cost_optimization.savings_percent ?? 0}%)
                </p>
              </div>
            ) : null}

            {assumptions.optimization.quality_recommendations?.add?.length ? (
              <div className="rounded-lg border border-blue-300/50 bg-blue-50 p-3">
                <p className="text-xs font-medium text-blue-700">추가 권장</p>
                {assumptions.optimization.quality_recommendations.add.map((item) => (
                  <p key={item} className="mt-1 text-xs text-blue-700">- {item}</p>
                ))}
              </div>
            ) : null}

            {assumptions.optimization.quality_recommendations?.remove?.length ? (
              <div className="rounded-lg border border-orange-300/50 bg-orange-50 p-3">
                <p className="text-xs font-medium text-orange-700">제거 검토</p>
                {assumptions.optimization.quality_recommendations.remove.map((item) => (
                  <p key={item} className="mt-1 text-xs text-orange-700">- {item}</p>
                ))}
              </div>
            ) : null}

            {assumptions.optimization.scenarios?.length ? (
              <div className="rounded-lg border border-border/40 p-3">
                <p className="text-xs font-medium text-foreground">시나리오 비교</p>
                <div className="mt-2 grid gap-2">
                  {assumptions.optimization.scenarios.map((scenario) => (
                    <div key={scenario.name} className="rounded-md border border-border/30 bg-secondary/20 p-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold text-foreground">
                          {scenario.name}
                          {assumptions.optimization?.recommended_scenario === scenario.name ? (
                            <span className="ml-1 rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">추천</span>
                          ) : null}
                        </p>
                        <p className="text-xs text-foreground">
                          {new Intl.NumberFormat("ko-KR", {
                            style: "currency",
                            currency: scenario.currency || currency || "USD",
                            maximumFractionDigits: 0,
                          }).format(Number(scenario.monthly_total))}
                        </p>
                      </div>
                      <p className={`mt-1 text-[11px] ${Number(scenario.delta_amount) <= 0 ? "text-emerald-700" : "text-orange-700"}`}>
                        {Number(scenario.delta_amount) <= 0 ? "절감" : "증가"}: {Math.abs(Number(scenario.delta_amount)).toFixed(2)} ({Math.abs(Number(scenario.delta_percent)).toFixed(2)}%)
                      </p>
                      {scenario.notes?.length ? (
                        <p className="mt-1 text-[11px] text-muted-foreground">{scenario.notes.join(" / ")}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </ScrollArea>
  )
}

