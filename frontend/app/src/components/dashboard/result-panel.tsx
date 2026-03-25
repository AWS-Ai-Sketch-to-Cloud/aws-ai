"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ArchitectureDiagram } from "./architecture-diagram"
import { TerraformCode } from "./terraform-code"
import { CostAnalysis } from "./cost-analysis"
import { GitBranch, FileCode, Receipt } from "lucide-react"

interface ResultPanelProps {
  activeTab: "architecture" | "terraform" | "cost"
  setActiveTab: (tab: "architecture" | "terraform" | "cost") => void
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
  architectureJson?: {
    ec2?: { count?: number; instance_type?: string }
    rds?: { enabled?: boolean; engine?: string | null }
    bedrock?: { enabled?: boolean; model?: string | null }
    additional_services?: string[]
    public?: boolean
    region?: string
  } | null
  terraformCode?: string | null
  monthlyTotal?: number | null
  costBreakdown?: Record<string, number> | null
  region?: string | null
  currency?: string | null
}

export function ResultPanel({
  activeTab,
  setActiveTab,
  generationStatus,
  architectureJson,
  terraformCode,
  monthlyTotal,
  costBreakdown,
  region,
  currency,
}: ResultPanelProps) {
  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm overflow-hidden">
      <CardHeader className="border-b border-border/30 pb-0">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
          <TabsList className="h-11 w-full justify-start gap-1 rounded-none border-none bg-transparent p-0">
            <TabsTrigger value="architecture" className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-4 text-sm font-medium text-muted-foreground transition-all data-[state=active]:border-primary data-[state=active]:text-foreground">
              <GitBranch className="mr-2 h-4 w-4" strokeWidth={1.5} />
              아키텍처
            </TabsTrigger>
            <TabsTrigger value="terraform" className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-4 text-sm font-medium text-muted-foreground transition-all data-[state=active]:border-primary data-[state=active]:text-foreground">
              <FileCode className="mr-2 h-4 w-4" strokeWidth={1.5} />
              Terraform
            </TabsTrigger>
            <TabsTrigger value="cost" className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-4 text-sm font-medium text-muted-foreground transition-all data-[state=active]:border-primary data-[state=active]:text-foreground">
              <Receipt className="mr-2 h-4 w-4" strokeWidth={1.5} />
              비용
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs value={activeTab}>
          <TabsContent value="architecture" className="m-0">
            <ArchitectureDiagram generationStatus={generationStatus} architectureJson={architectureJson} />
          </TabsContent>
          <TabsContent value="terraform" className="m-0">
            <TerraformCode generationStatus={generationStatus} terraformCode={terraformCode} />
          </TabsContent>
          <TabsContent value="cost" className="m-0">
            <CostAnalysis
              generationStatus={generationStatus}
              monthlyTotal={monthlyTotal}
              costBreakdown={costBreakdown}
              region={region}
              currency={currency}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

