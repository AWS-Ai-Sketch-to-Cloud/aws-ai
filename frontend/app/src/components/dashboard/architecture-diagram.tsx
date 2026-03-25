"use client"

import { useMemo } from "react"
import { ReactFlow, Background, Controls, type Node, type Edge, Handle, Position, MarkerType } from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Bot, Cloud, Database, Globe, Server } from "lucide-react"
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty"

interface ArchitectureDiagramProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
  architectureJson?: {
    ec2?: { count?: number; instance_type?: string }
    rds?: { enabled?: boolean; engine?: string | null }
    bedrock?: { enabled?: boolean; model?: string | null }
    additional_services?: string[]
    public?: boolean
    region?: string
  } | null
}

function CustomNode({ data }: { data: { label: string; icon: "globe" | "cloud" | "server" | "database" | "bot" } }) {
  const iconMap = {
    globe: <Globe className="h-5 w-5" strokeWidth={1.5} />,
    cloud: <Cloud className="h-5 w-5" strokeWidth={1.5} />,
    server: <Server className="h-5 w-5" strokeWidth={1.5} />,
    database: <Database className="h-5 w-5" strokeWidth={1.5} />,
    bot: <Bot className="h-5 w-5" strokeWidth={1.5} />,
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card/80 px-4 py-3 backdrop-blur-sm">
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-0 !bg-muted-foreground/60" />
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/70">{iconMap[data.icon]}</div>
        <span className="text-xs font-medium whitespace-nowrap">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-0 !bg-muted-foreground/60" />
    </div>
  )
}

const nodeTypes = { custom: CustomNode }

function buildGraph(architectureJson: ArchitectureDiagramProps["architectureJson"]): { nodes: Node[]; edges: Edge[] } {
  const region = architectureJson?.region ?? "ap-northeast-2"
  const ec2Count = architectureJson?.ec2?.count ?? 1
  const ec2Type = architectureJson?.ec2?.instance_type ?? "t3.micro"
  const rdsEnabled = Boolean(architectureJson?.rds?.enabled)
  const rdsEngine = architectureJson?.rds?.engine ?? "mysql"
  const bedrockEnabled = Boolean(architectureJson?.bedrock?.enabled)
  const bedrockModel = architectureJson?.bedrock?.model ?? "anthropic.claude-3-haiku-20240307-v1:0"
  const additionalServices = (architectureJson?.additional_services ?? []).filter(
    (s: string) => !["bedrock", "rds", "ec2", "vpc"].includes(String(s).toLowerCase()),
  )

  const nodes: Node[] = [
    { id: "entry", type: "custom", position: { x: 250, y: 0 }, data: { label: `Internet (${region})`, icon: "globe" } },
    { id: "vpc", type: "custom", position: { x: 250, y: 120 }, data: { label: `VPC (${architectureJson?.public ? "public" : "private"})`, icon: "cloud" } },
    { id: "ec2", type: "custom", position: { x: 120, y: 250 }, data: { label: `EC2 x${ec2Count} (${ec2Type})`, icon: "server" } },
  ]

  const edges: Edge[] = [
    {
      id: "e-entry-vpc",
      source: "entry",
      target: "vpc",
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--primary)" },
      style: { stroke: "var(--primary)", strokeWidth: 1.5 },
    },
    {
      id: "e-vpc-ec2",
      source: "vpc",
      target: "ec2",
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-2)" },
      style: { stroke: "var(--chart-2)", strokeWidth: 1.5 },
    },
  ]

  if (rdsEnabled) {
    nodes.push({
      id: "rds",
      type: "custom",
      position: { x: 380, y: 250 },
      data: { label: `RDS (${rdsEngine})`, icon: "database" },
    })
    edges.push({
      id: "e-ec2-rds",
      source: "ec2",
      target: "rds",
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-4)" },
      style: { stroke: "var(--chart-4)", strokeWidth: 1.5 },
    })
  }

  if (bedrockEnabled) {
    nodes.push({
      id: "bedrock",
      type: "custom",
      position: { x: 250, y: 380 },
      data: { label: `Bedrock (${bedrockModel})`, icon: "bot" },
    })
    edges.push({
      id: "e-ec2-bedrock",
      source: "ec2",
      target: "bedrock",
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-3)" },
      style: { stroke: "var(--chart-3)", strokeWidth: 1.5 },
    })
  }

  additionalServices.forEach((service: string, idx: number) => {
    const id = `svc-${service}-${idx}`
    nodes.push({
      id,
      type: "custom",
      position: { x: 60 + (idx % 4) * 170, y: 500 + Math.floor(idx / 4) * 110 },
      data: { label: String(service).toUpperCase(), icon: "cloud" },
    })
    edges.push({
      id: `e-ec2-${id}`,
      source: "ec2",
      target: id,
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--muted-foreground)" },
      style: { stroke: "var(--muted-foreground)", strokeWidth: 1.25, strokeDasharray: "4 4" },
    })
  })

  return { nodes, edges }
}

export function ArchitectureDiagram({ generationStatus, architectureJson }: ArchitectureDiagramProps) {
  const graph = useMemo(() => buildGraph(architectureJson), [architectureJson])

  if (generationStatus === "idle") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Empty>
          <EmptyMedia variant="icon">
            <Cloud className="h-6 w-6" strokeWidth={1.5} />
          </EmptyMedia>
          <EmptyTitle>아키텍처 다이어그램</EmptyTitle>
          <EmptyDescription>요구사항을 분석하면 구조가 시각화됩니다.</EmptyDescription>
        </Empty>
      </div>
    )
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 animate-spin rounded-full border-2 border-muted border-t-primary" />
          <p className="mt-4 text-sm font-medium text-foreground">아키텍처 분석 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[600px] w-full">
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        className="bg-background"
      >
        <Background color="var(--border)" gap={20} size={1} />
        <Controls
          className="!rounded-lg !border-border/50 !bg-card !shadow-none [&>button]:!border-border/50 [&>button]:!bg-card [&>button]:!text-muted-foreground"
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  )
}
