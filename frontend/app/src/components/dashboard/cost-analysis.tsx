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
}

export function CostAnalysis({ generationStatus, monthlyTotal, costBreakdown, region, currency }: CostAnalysisProps) {
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
  const items = Object.entries(breakdown)

  return (
    <ScrollArea className="h-[600px]">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-foreground">월간 비용 추정</h3>
        <p className="text-xs text-muted-foreground">{region ?? "N/A"}</p>

        <div className="mt-4 rounded-xl border border-border/50 bg-secondary/20 p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Monthly Total</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{new Intl.NumberFormat("ko-KR", { style: "currency", currency: currency || "KRW", maximumFractionDigits: 0 }).format(total)}</p>
        </div>

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
      </div>
    </ScrollArea>
  )
}

