"use client"

import { Receipt, TrendingDown, CheckCircle2, AlertCircle, ArrowRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

interface CostAnalysisProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
}

const costData = {
  services: [
    { name: "EC2 Auto Scaling", description: "t3.large x 2 instances", monthly: 121.44, optimized: 72.86, savings: "40%", recommendation: "1-year reserved instances recommended" },
    { name: "RDS MySQL Multi-AZ", description: "db.t3.medium (100GB)", monthly: 148.92, optimized: 89.35, savings: "40%", recommendation: "Reserved instances can reduce cost" },
    { name: "Application Load Balancer", description: "ALB and LCU usage", monthly: 22.56, optimized: 22.56, savings: "0%", recommendation: null },
    { name: "CloudFront CDN", description: "1TB data transfer", monthly: 85.0, optimized: 85.0, savings: "0%", recommendation: null },
    { name: "S3 Storage", description: "100GB Standard", monthly: 2.3, optimized: 1.15, savings: "50%", recommendation: "Use S3 Intelligent-Tiering" },
  ],
  summary: {
    totalMonthly: 380.22,
    totalOptimized: 270.92,
    totalSavings: 109.3,
    savingsPercent: "28.7%",
  },
}

export function CostAnalysis({ generationStatus }: CostAnalysisProps) {
  if (generationStatus === "idle") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Empty>
          <EmptyMedia variant="icon">
            <Receipt className="h-10 w-10" strokeWidth={1} />
          </EmptyMedia>
          <EmptyTitle>비용 분석</EmptyTitle>
          <EmptyDescription>아키텍처가 생성되면 상세 비용 분석과 최적화 권장안이 표시됩니다.</EmptyDescription>
        </Empty>
      </div>
    )
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="h-16 w-16 animate-spin rounded-full border-2 border-muted border-t-primary" />
            <Receipt className="absolute left-1/2 top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 text-primary" strokeWidth={1.5} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">비용 분석 중...</p>
            <p className="text-xs text-muted-foreground">AWS 요금을 계산하고 있습니다</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="h-[600px]">
      <div className="p-6">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">월간 예상 비용</h3>
            <p className="text-xs text-muted-foreground">AWS Seoul (ap-northeast-2) 기준</p>
          </div>
          <Badge className="border-success/20 bg-success/10 text-success">
            <TrendingDown className="mr-1 h-3 w-3" strokeWidth={1.5} />
            Optimization Available
          </Badge>
        </div>

        <div className="mb-6 grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-border/50 bg-secondary/20 p-4">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current</p>
            <p className="mt-1 text-2xl font-semibold text-foreground">${costData.summary.totalMonthly.toFixed(2)}</p>
          </div>
          <div className="rounded-xl border border-border/50 bg-primary/5 p-4">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Optimized</p>
            <p className="mt-1 text-2xl font-semibold text-primary">${costData.summary.totalOptimized.toFixed(2)}</p>
          </div>
          <div className="rounded-xl border border-success/20 bg-success/5 p-4">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Savings</p>
            <p className="mt-1 text-2xl font-semibold text-success">${costData.summary.totalSavings.toFixed(2)}</p>
          </div>
        </div>

        <Separator className="mb-6 bg-border/30" />

        <div className="space-y-2">
          {costData.services.map((service) => (
            <div key={service.name} className="rounded-lg border border-border/30 p-3">
              <div className="grid grid-cols-12 items-center gap-4">
                <div className="col-span-6">
                  <p className="text-sm font-medium text-foreground">{service.name}</p>
                  <p className="text-[11px] text-muted-foreground">{service.description}</p>
                </div>
                <div className="col-span-2 text-right text-sm text-foreground">${service.monthly.toFixed(2)}</div>
                <div className="col-span-2 text-right text-sm font-medium text-primary">${service.optimized.toFixed(2)}</div>
                <div className="col-span-2 text-right">
                  {service.savings !== "0%" ? (
                    <Badge variant="secondary" className="border-success/20 bg-success/10 text-[10px] text-success">
                      {service.savings}
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </div>
              </div>

              {service.recommendation && (
                <div className="mt-2 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2">
                  <AlertCircle className="h-3.5 w-3.5 text-primary" strokeWidth={1.5} />
                  <span className="text-[11px] text-primary">{service.recommendation}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        <Separator className="my-6 bg-border/30" />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-success" strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium text-foreground">Annual Savings</p>
              <p className="text-xs text-muted-foreground">After applying recommendations</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold text-success">${(costData.summary.totalSavings * 12).toFixed(2)}</p>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-center rounded-xl border border-primary/20 bg-primary/5 p-4">
          <span className="text-sm text-foreground">Apply Optimization</span>
          <ArrowRight className="ml-2 h-4 w-4 text-primary" strokeWidth={1.5} />
        </div>
      </div>
    </ScrollArea>
  )
}
